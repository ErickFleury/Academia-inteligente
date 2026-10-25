"""Isolated lifecycle integration; real ORM/lifecycle, synthetic policies/providers."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from prescription_fixtures import enable_weekly_fixture, valid_case
from sqlalchemy import func, select
from test_training_generation import complete_onboarding, create_client
from test_training_generation import session as session
from training_fixtures import instructor

from app.integrations.embeddings import EmbeddingProviderError
from app.main import create_app
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding.models import Onboarding
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.prescription_contract import PrescriptionRejection, record_hash
from app.modules.training.prescription_development import (
    DevelopmentValidationRecord,
    IsolatedPrescriptionService,
    build_prescription_writer_context,
)
from app.modules.training.prescription_validation import validate_development_prescription
from app.modules.training.service import TrainingLifecycleService


@pytest.fixture
def setup(session):
    client = create_client(session, "prescription-dev-owner", "prescription-dev@example.test")
    instructor(session)
    case = valid_case(client.id)
    service = IsolatedPrescriptionService(
        client_ids={client.id}, context_supplier=lambda: deepcopy(case)
    )
    identity = AuthenticatedIdentity("prescription-dev-owner", "client", ("client",))
    professional = AuthenticatedIdentity("instructor-1", "instructor", ("instructor",))
    return service, case, identity, professional


def generate(
    session,
    setup,
    entry_point="initial",
    *,
    request_id=None,
    expected_revision=None,
    provider=None,
    base_version_id=None,
):
    service, case, identity, _ = setup

    def valid_provider(context):
        candidate = case["candidate"].model_copy(deep=True)
        candidate.expected_revision = context["current_revision"]
        candidate.input_snapshot_sha256 = context["input_snapshot_sha256"]
        return candidate

    return service.generate(
        session,
        identity,
        client_id=case["client_id"],
        request_id=request_id or uuid4(),
        entry_point=entry_point,
        expected_revision=expected_revision,
        provider=provider or valid_provider,
        base_version_id=base_version_id,
    )


def version(session, result):
    return session.get(TrainingPlanVersion, UUID(result["version_id"]))


def test_no_development_endpoints_are_registered_in_normal_application():
    app = create_app()
    assert "/training/drafts/{version_id}/prescription" in app.openapi()["paths"]
    assert not any(
        getattr(route, "endpoint", None)
        and route.endpoint.__module__.endswith("prescription_development")
        for route in app.routes
    )


@pytest.mark.parametrize("weekly", [False, True])
def test_writer_receives_the_exact_confirmed_schedule_and_dictionary_version(
    session, setup, weekly
):
    service, case, _, _ = setup
    if weekly:
        enable_weekly_fixture(case)
    calls = []

    def writer(context):
        calls.append(context)
        candidate = case["candidate"].model_copy(deep=True)
        candidate.expected_revision = context["current_revision"]
        return candidate

    outcome = generate(session, setup, provider=writer)
    assert outcome["status"] == "accepted"
    assert calls[0]["dictionary_version"] == case["catalog"].dictionary.version
    assert calls[0]["confirmed_schedule"] == (
        case["snapshot"].schedule.model_dump(mode="json") if weekly else None
    )


@pytest.mark.parametrize("state", ["missing", "false", "expired", "conflict"])
def test_writer_context_never_promotes_an_unconfirmed_schedule(state):
    case = valid_case()
    enable_weekly_fixture(case)
    case.pop("candidate")
    preflight = validate_development_prescription(candidate=None, **case)
    fact = case["snapshot"].facts["schedule_confirmed"]
    if state == "missing":
        del case["snapshot"].facts["schedule_confirmed"]
    elif state == "false":
        fact.value = False
    elif state == "expired":
        fact.valid_until = datetime.now(UTC) - timedelta(seconds=1)
    else:
        fact.conflict = True
    context = build_prescription_writer_context(case, preflight, None)
    assert context["confirmed_schedule"] is None


def test_complete_revision_needs_confirmed_schedule_before_writer_call(session, setup):
    service, case, _, _ = setup
    with pytest.raises(PrescriptionRejection, match="weekly_schedule_missing"):
        service.prepare(
            session,
            case["client_id"],
            None,
            lambda _: pytest.fail("Missing weekly inputs must reject before writing"),
            require_complete=True,
        )


def test_complete_proposal_submission_and_instructor_approval_preserve_trace(session, setup):
    service, case, identity, professional = setup
    created = generate(session, setup)
    draft = version(session, created)
    assert created["status"] == "accepted" and draft.status == "proposal"
    assert draft.submitted_for_review_at is None and draft.citations
    submitted = service.submit(
        session,
        identity,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
    )
    assert submitted["revision"] == 2 and draft.status == "proposal"
    approved = service.approve(
        session,
        professional,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
    )
    assert approved["status"] == "approved" and draft.status == "current"
    assert draft.responsible_employee_id is not None
    records = session.scalars(
        select(DevelopmentValidationRecord).where(
            DevelopmentValidationRecord.version_id == draft.id,
        )
    ).all()
    assert {r.revision for r in records} == {1, 2, 3}
    assert all(len(r.payload["trace"]) == 7 for r in records)


@pytest.mark.parametrize(
    "entry_point", ["initial", "targeted", "rebuild", "chat_edit", "correction", "prose"]
)
def test_all_prescriptive_paths_discard_unsupported_candidates_without_state(
    session, setup, entry_point
):
    _, case, _, _ = setup
    case["candidate"].sessions[0].items[0].decision_rules.pop("rest")
    result = generate(session, setup, entry_point)
    assert result["status"] == "rejected"
    assert "prescription" not in result and "projection" not in result
    assert session.scalar(select(func.count()).select_from(TrainingPlanVersion)) == 0
    assert session.scalar(select(func.count()).select_from(DevelopmentValidationRecord)) == 0


def test_rejected_edit_preserves_saved_content_revision_submission_and_record_count(session, setup):
    service, case, identity, _ = setup
    draft = version(session, generate(session, setup))
    service.submit(
        session,
        identity,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
    )
    session.refresh(draft)
    before = (
        draft.revision,
        draft.submitted_for_review_at,
        service.lifecycle.content(session, draft).model_dump(),
    )
    count = session.scalar(select(func.count()).select_from(DevelopmentValidationRecord))
    case["candidate"].sessions[0].items[0].sets = 99
    result = generate(session, setup, "chat_edit", expected_revision=draft.revision)
    assert result["status"] == "rejected"
    session.refresh(draft)
    assert (
        draft.revision,
        draft.submitted_for_review_at,
        service.lifecycle.content(session, draft).model_dump(),
    ) == before
    assert session.scalar(select(func.count()).select_from(DevelopmentValidationRecord)) == count


def test_replay_and_cached_drafts_revalidate_source_revocation(session, setup):
    _, case, _, _ = setup
    request_id = uuid4()
    created = generate(session, setup, request_id=request_id)
    replay = generate(
        session,
        setup,
        request_id=request_id,
        provider=lambda _: pytest.fail("replay must not call writer"),
    )
    assert replay["version_id"] == created["version_id"]
    case["source_catalog"]["sources"][0]["review_status"] = "excluded"
    for identifier in (request_id, uuid4()):
        failure = generate(
            session,
            setup,
            request_id=identifier,
            provider=lambda _: pytest.fail("cache must be checked first"),
        )
        assert failure["status"] == "rejected" and "prescription" not in failure


def test_late_source_change_after_writer_return_discards_candidate(session, setup):
    _, case, _, _ = setup

    def revoke(context):
        case["source_catalog"]["sources"][0]["review_status"] = "excluded"
        return case["candidate"]

    result = generate(session, setup, provider=revoke)
    assert result["status"] == "rejected"
    assert session.scalar(select(func.count()).select_from(TrainingPlanVersion)) == 0


def test_legacy_unvalidated_draft_cannot_be_replayed_as_qualified(session, setup):
    service, case, identity, _ = setup
    from test_training_lifecycle import data

    legacy = TrainingLifecycleService().create_proposal(
        session, client_id=case["client_id"], data=data(), origin="ai", created_by="ai"
    )
    outcome = generate(session, setup)
    assert outcome["status"] == "rejected" and "legacy" in outcome["reason_codes"][0]
    with pytest.raises(PrescriptionRejection):
        service.submit(
            session,
            identity,
            client_id=case["client_id"],
            version_id=legacy.id,
            expected_revision=legacy.revision,
        )


def test_manual_assumption_retains_ai_lineage_and_works_without_evidence_service(session, setup):
    service, case, identity, professional = setup
    draft = version(session, generate(session, setup))
    original = service.lifecycle.content(session, draft).model_dump()
    with pytest.raises(PermissionError):
        service.assume_manual(
            session,
            identity,
            client_id=case["client_id"],
            version_id=draft.id,
            expected_revision=draft.revision,
            reason="Revisão profissional",
        )
    service.context_supplier = lambda: (_ for _ in ()).throw(EmbeddingProviderError("unavailable"))
    result = service.assume_manual(
        session,
        professional,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
        reason="Revisão profissional",
    )
    assert result["status"] == "manual" and draft.status == "proposal"
    assert draft.origin == "ai" and draft.created_by == "ai" and not draft.citations
    assert service.lifecycle.content(session, draft).model_dump() == original
    approval = service.approve(
        session,
        professional,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
    )
    assert approval["manual"] is True and draft.status == "current"


def test_cross_client_access_and_non_development_accounts_are_denied(session, setup):
    service, case, _, _ = setup
    other = AuthenticatedIdentity("prescription-dev-other", "client", ("client",))
    with pytest.raises(PermissionError):
        service.generate(
            session,
            other,
            client_id=case["client_id"],
            request_id=uuid4(),
            entry_point="initial",
            provider=lambda _: None,
        )
    real_client = create_client(session, "ordinary-client", "ordinary@example.test")
    service.client_ids = frozenset({real_client.id})
    with pytest.raises(PermissionError, match="scope_required"):
        service.generate(
            session,
            other,
            client_id=real_client.id,
            request_id=uuid4(),
            entry_point="initial",
            provider=lambda _: None,
        )


def test_failed_commit_rolls_back_content_and_trace_together(session, setup, monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("injected")))
        with pytest.raises(RuntimeError, match="injected"):
            generate(session, setup)
    assert session.scalar(select(func.count()).select_from(TrainingPlanVersion)) == 0
    assert session.scalar(select(func.count()).select_from(DevelopmentValidationRecord)) == 0


def test_supported_ai_edit_clears_submission_and_keeps_prior_trace_immutable(session, setup):
    service, case, identity, _ = setup
    draft = version(session, generate(session, setup))
    original_record = session.scalar(select(DevelopmentValidationRecord))
    original_payload = deepcopy(original_record.payload)
    service.submit(
        session,
        identity,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
    )
    case["candidate"].sessions[0].items[0].rest_seconds = 40
    outcome = generate(session, setup, "chat_edit", expected_revision=draft.revision)
    assert outcome["status"] == "accepted" and draft.revision == 3
    assert draft.submitted_for_review_at is None
    assert service.lifecycle.content(session, draft).items[0].rest_seconds == 40
    session.refresh(original_record)
    assert original_record.payload == original_payload


def test_source_revocation_prevents_approval_without_altering_submitted_revision(session, setup):
    service, case, identity, professional = setup
    draft = version(session, generate(session, setup))
    service.submit(
        session,
        identity,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
    )
    revision = draft.revision
    case["source_catalog"]["sources"][0]["review_status"] = "excluded"
    with pytest.raises(PrescriptionRejection):
        service.approve(
            session,
            professional,
            client_id=case["client_id"],
            version_id=draft.id,
            expected_revision=revision,
        )
    session.refresh(draft)
    assert draft.status == "proposal" and draft.revision == revision


def test_incomplete_support_rejects_before_writer_is_called(session, setup):
    _, case, _, _ = setup
    case["source_catalog"]["sources"][0]["review_status"] = "excluded"
    outcome = generate(session, setup, provider=lambda _: pytest.fail("unsupported writer call"))
    assert outcome["status"] == "rejected"


def test_changed_writer_configuration_invalidates_replay(session, setup):
    _, case, _, _ = setup
    request_id = uuid4()
    assert generate(session, setup, request_id=request_id)["status"] == "accepted"
    case["execution"].writer_configuration_sha256 = "d" * 64
    outcome = generate(session, setup, request_id=request_id)
    assert outcome["status"] == "rejected"
    assert outcome["reason_codes"] == ["writer_configuration_changed"]


def test_confirmed_input_snapshot_is_bound_to_current_source_values_and_not_onboarding_mutation(
    session, setup
):
    service, case, identity, _ = setup
    case["snapshot"].facts["training_goal"].confirmed_at = None
    original = case["snapshot"].model_dump(mode="json")
    outcome = generate(session, setup)
    assert outcome["status"] == "rejected" and outcome["category"] == "missing_input"
    confirmation = service.confirm_inputs(
        session,
        identity,
        client_id=case["client_id"],
        expected_snapshot_hash=record_hash(case["snapshot"]),
    )
    assert confirmation["status"] == "confirmed"
    assert case["snapshot"].model_dump(mode="json") == original
    assert generate(session, setup)["status"] == "accepted"
    record = session.scalar(select(DevelopmentValidationRecord))
    assert set(record.payload["input_snapshot"]["facts"]) == set(original["facts"])


def test_stale_confirmation_and_conflicting_health_report_cannot_be_silently_confirmed(
    session, setup
):
    service, case, identity, _ = setup
    with pytest.raises(PrescriptionRejection, match="snapshot_changed"):
        service.confirm_inputs(
            session, identity, client_id=case["client_id"], expected_snapshot_hash="a" * 64
        )
    case["snapshot"].facts["uses_medications"].conflict = True
    with pytest.raises(PrescriptionRejection, match="requires_resolution"):
        service.confirm_inputs(
            session,
            identity,
            client_id=case["client_id"],
            expected_snapshot_hash=record_hash(case["snapshot"]),
        )


def test_instructor_trace_projection_does_not_leak_into_client_results(session, setup):
    service, case, identity, professional = setup
    created = generate(session, setup)
    assert "trace" not in created["prescription"]
    assert "input_snapshot" not in created["prescription"]
    assert "typed_content" not in created["prescription"]
    draft = version(session, created)
    with pytest.raises(PermissionError):
        service.review(
            session,
            identity,
            client_id=case["client_id"],
            version_id=draft.id,
            expected_revision=draft.revision,
        )
    reviewed = service.review(
        session,
        professional,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
    )
    assert len(reviewed["prescription"]["trace"]) == 7
    assert "input_snapshot" not in reviewed["prescription"]


def test_manual_edit_after_assumption_preserves_lineage_and_does_not_need_ai(session, setup):
    service, case, _, professional = setup
    draft = version(session, generate(session, setup))
    service.assume_manual(
        session,
        professional,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
        reason="Revisão",
    )
    data = service.lifecycle.content(session, draft)
    data.items[0].sets = 3
    service.context_supplier = lambda: pytest.fail("manual edit cannot call AI/evidence")
    service.revise_manual(
        session,
        professional,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
        data=data,
    )
    assert draft.origin == "ai" and not draft.citations
    approval = service.approve(
        session,
        professional,
        client_id=case["client_id"],
        version_id=draft.id,
        expected_revision=draft.revision,
    )
    assert approval["manual"]


def test_confirmed_full_plan_adaptation_validates_totals_and_preserves_current_history(
    session, setup
):
    service, case, identity, professional = setup
    enable_weekly_fixture(case)
    original = version(session, generate(session, setup))
    service.submit(
        session,
        identity,
        client_id=case["client_id"],
        version_id=original.id,
        expected_revision=original.revision,
    )
    service.approve(
        session,
        professional,
        client_id=case["client_id"],
        version_id=original.id,
        expected_revision=original.revision,
    )
    before = service.lifecycle.content(session, original).model_dump()
    original_revision = original.revision
    without_confirmation = generate(
        session,
        setup,
        "adaptation",
        base_version_id=original.id,
        expected_revision=original_revision,
    )
    assert without_confirmation["status"] == "rejected"
    assert without_confirmation["reason_codes"] == ["adaptation_confirmation_required"]
    case["candidate"].sessions[0].items[0].sets = 3

    def provider(context):
        candidate = case["candidate"].model_copy(deep=True)
        candidate.expected_revision = context["current_revision"]
        return candidate

    failure = service.generate(
        session,
        identity,
        client_id=case["client_id"],
        request_id=uuid4(),
        entry_point="adaptation",
        provider=provider,
        expected_revision=original_revision,
        base_version_id=original.id,
        adaptation_confirmed=True,
    )
    assert failure["status"] == "rejected"
    case["candidate"].sessions[0].items[0].sets = 2
    accepted = service.generate(
        session,
        identity,
        client_id=case["client_id"],
        request_id=uuid4(),
        entry_point="adaptation",
        provider=provider,
        expected_revision=original_revision,
        base_version_id=original.id,
        adaptation_confirmed=True,
    )
    assert accepted["status"] == "accepted"
    assert accepted["version_id"] != str(original.id)
    session.refresh(original)
    assert original.status == "current" and original.revision == original_revision
    assert service.lifecycle.content(session, original).model_dump() == before


def test_provider_unavailability_has_no_workout_fallback(session, setup):
    outcome = generate(
        session,
        setup,
        provider=lambda _: (_ for _ in ()).throw(EmbeddingProviderError("unavailable")),
    )
    assert outcome["status"] == "rejected" and outcome["category"] == "technical_unavailability"
    assert "prescription" not in outcome
    assert session.scalar(select(func.count()).select_from(TrainingPlanVersion)) == 0


def test_authoritative_onboarding_builder_is_owned_minimized_and_read_only(session, setup):
    service, case, identity, _ = setup
    with pytest.raises(PrescriptionRejection, match="completed_onboarding_required"):
        service.onboarding_snapshot(
            session, identity, client_id=case["client_id"], required_fields={"training_goal"}
        )
    complete_onboarding(session, "prescription-dev-owner")
    onboarding = session.scalar(select(Onboarding).where(Onboarding.client_id == case["client_id"]))
    before = (onboarding.training_goal, onboarding.updated_at, onboarding.completed_at)
    fields = {"training_goal", "training_experience", "uses_medications"}
    snapshot = service.onboarding_snapshot(
        session, identity, client_id=case["client_id"], required_fields=fields
    )
    assert set(snapshot.facts) == fields
    assert snapshot.facts["training_goal"].value == "Ganhar força"
    assert snapshot.facts["training_goal"].source_id == str(onboarding.id)
    assert (onboarding.training_goal, onboarding.updated_at, onboarding.completed_at) == before
    with pytest.raises(PrescriptionRejection, match="unavailable_in_onboarding"):
        service.onboarding_snapshot(
            session, identity, client_id=case["client_id"], required_fields={"adult_eligibility"}
        )


def test_seven_day_schedule_cannot_be_invented_by_writer(session, setup):
    _, case, _, _ = setup
    enable_weekly_fixture(case)
    case["candidate"].schedule.occurrences[0].day_index = 1
    outcome = generate(session, setup)
    assert outcome["status"] == "rejected"
    assert outcome["reason_codes"] == ["schedule_not_confirmed"]


def test_changed_progression_text_cannot_silently_replace_saved_instructions(session, setup):
    _, case, _, _ = setup
    request_id = uuid4()
    assert generate(session, setup, request_id=request_id)["status"] == "accepted"
    case["execution"].instructions["progress"].text_pt_br = "Outra instrução revisada."
    result = generate(session, setup, request_id=request_id)
    assert result["status"] == "rejected"
    assert result["reason_codes"] == ["saved_projection_requires_revalidation"]
