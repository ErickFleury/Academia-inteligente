"""Real lifecycle and migrations with synthetic observations and fake providers."""

import json
import runpy
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from prescription_fixtures import valid_case
from sqlalchemy import Column, Integer, MetaData, Table, inspect, select, text
from test_prescription_migration import migration_engine as migration_engine
from test_prescription_remediation import mode_case
from test_training_generation import create_client
from test_training_generation import session as session
from test_training_review import api as api

from app.modules.training.models import TrainingPlanItem
from app.modules.training.prescription_contract import PrescriptionRejection, record_hash
from app.modules.training.prescription_development import DevelopmentInputConfirmation
from app.modules.training.prescription_inputs import RequestInputSubmission, submit_request_inputs
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.service import TrainingLifecycleService


def test_request_input_api_uses_authenticated_owner_and_active_instructor(
    session, api, monkeypatch
):
    from training_fixtures import instructor

    from app.modules.identity.service import AuthenticatedIdentity
    from app.modules.training.prescription_runtime import OperationalPrescriptionService

    client = create_client(session, "input-owner", "input-owner@example.test")
    create_client(session, "input-other", "input-other@example.test")
    professional = instructor(session)
    case = valid_case(client.id)
    called = []

    def context(runtime, **kwargs):
        called.append(runtime.client_id)
        assert runtime.client_id == client.id
        return case

    monkeypatch.setattr(OperationalPrescriptionService, "_build_operational_context", context)
    http, identity = api
    identity.identity = AuthenticatedIdentity("input-owner", "", ("client",))
    response = http.get("/training/prescription/inputs")
    assert response.status_code == 200
    assert response.json()["snapshot_hash"] == record_hash(case["snapshot"])
    data = {
        "expected_snapshot_hash": record_hash(case["snapshot"]),
        "values": {"progression_observed": {"value": False}},
    }
    assert http.post(f"/training/clients/{client.id}/prescription/inputs", data).status_code == 403
    assert http.post("/training/prescription/inputs", data).status_code == 200
    saved = session.scalar(select(DevelopmentInputConfirmation))
    assert saved.client_id == client.id
    assert saved.snapshot["facts"]["progression_observed"]["confirmed_by_subject"] == "input-owner"
    identity.identity = AuthenticatedIdentity("instructor-1", "", ("instructor",))
    assert http.get(f"/training/clients/{client.id}/prescription/inputs").status_code == 200
    professional.active = False
    session.commit()
    count = len(called)
    assert http.get(f"/training/clients/{client.id}/prescription/inputs").status_code == 401
    assert len(called) == count


@pytest.mark.parametrize("mode", ["aerobic", "flexibility", "balance", "functional"])
def test_mode_projection_persists_and_roundtrips_without_zero_rest(session, mode):
    from app.modules.training.prescription_validation import validate_development_prescription

    client = create_client(session, "prescription-dev-modes", "mode@example.test")
    case = mode_case(mode)
    case["client_id"] = case["snapshot"].client_id = client.id
    case["candidate"].input_snapshot_sha256 = record_hash(case["snapshot"])
    result = validate_development_prescription(**case)
    draft = TrainingLifecycleService().create_proposal(
        session,
        client_id=client.id,
        data=TrainingPlanVersionInput.model_validate(result["projection"]),
        created_by="ai",
        origin="ai",
    )
    row = session.scalar(select(TrainingPlanItem))
    assert row.sets is None
    assert row.rest_seconds is None if mode == "aerobic" else row.rest_seconds == 45
    assert row.dose_details["mode"] == mode
    assert (
        TrainingLifecycleService().content(session, draft).model_dump(mode="json")
        == result["projection"]
    )


def test_complete_owner_bundle_reaches_real_runtime_without_human_review_rows(
    session, tmp_path, monkeypatch
):
    from test_prescription_remediation import owner_bundle
    from test_training_generation import complete_onboarding
    from training_fixtures import AcceptingTrainingReviewer

    from app.modules.knowledge.models import KnowledgeSource
    from app.modules.training import evidence_review
    from app.modules.training import prescription_authorization as authorization
    from app.modules.training import prescription_runtime as runtime_module
    from app.modules.training.owner_approval import OwnerApprovalRegistry

    client = create_client(session, "compiled-owner", "compiled-owner@example.test")
    complete_onboarding(
        session, "compiled-owner", training_goal="fixture", training_experience="none"
    )
    case, bundle = valid_case(client.id), owner_bundle()
    bundle["execution"]["contracts"][0].update(
        purpose="operational",
        writer_configuration_sha256=record_hash(runtime_module.writer_configuration()),
    )
    for part, filename in (
        ("policies", "prescription-policies.json"),
        ("execution", "prescription-execution.json"),
        ("accounting", "prescription-accounting.json"),
    ):
        (tmp_path / filename).write_text(json.dumps(bundle[part]), encoding="utf-8")
    catalog_path = tmp_path / "sources.json"
    catalog_path.write_text(json.dumps(case["source_catalog"]), encoding="utf-8")
    source = case["source_catalog"]["sources"][0]
    session.add(
        KnowledgeSource(
            **{
                key: source[key]
                for key in (
                    "id",
                    "title",
                    "url",
                    "authors",
                    "license",
                    "license_url",
                    "commercial_use_allowed",
                    "review_status",
                    "reviewed_by",
                )
            },
            language="pt-BR",
            reviewed_at=date.fromisoformat(source["reviewed_at"]),
            review_due_at=date.fromisoformat(source["review_due_at"]),
        )
    )
    session.commit()
    dependencies = {"source:synthetic": "a" * 64, "rule:SELECT_RESISTANCE": "b" * 64}
    owner = OwnerApprovalRegistry(
        decision_id="fixture-decision",
        decided_on=datetime.now(UTC).date(),
        status="approved",
        instruction="Synthetic instruction",
        governance_decision="Synthetic, no professional opinion",
        artifacts=dependencies,
    )
    record = authorization.BundleAuthorization(
        id="fixture-owner-bundle",
        owner_decision_id=owner.decision_id,
        decided_on=owner.decided_on,
        review_due_at=owner.decided_on + timedelta(days=1),
        status="approved",
        bundle_sha256=evidence_review.prescription_bundle_hash(bundle),
        policy_ids=["synthetic"],
        dependency_hashes=dependencies,
    )
    registry_path = tmp_path / "authorizations.json"
    registry_path.write_text(
        authorization.AuthorizationRegistry(authorizations=[record]).model_dump_json(),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_module, "ROOT", tmp_path)
    monkeypatch.setattr(runtime_module, "CATALOG_PATH", catalog_path)
    monkeypatch.setattr(authorization, "AUTHORIZATION_PATH", registry_path)
    monkeypatch.setattr(authorization, "load_owner_approval", lambda: owner)
    monkeypatch.setattr(
        evidence_review,
        "current_artifacts",
        lambda: {key: {"id": key, "sha256": digest} for key, digest in dependencies.items()},
    )
    monkeypatch.setattr(
        runtime_module, "retrieve_training_knowledge", lambda *args: case["evidence"]
    )
    runtime = runtime_module.OperationalPrescriptionService(
        session=session, client_id=client.id, subject="compiled-owner"
    )
    context = runtime._build_operational_context(collect_only=True)
    submit_request_inputs(
        session,
        context,
        RequestInputSubmission(
            expected_snapshot_hash=record_hash(context["snapshot"]),
            values={"progression_observed": {"value": False}},
        ),
        actor_role="client_owner",
        actor_subject="compiled-owner",
    )

    class Writer(AcceptingTrainingReviewer):
        def generate_prescription(self, context):
            candidate = case["candidate"].model_copy(deep=True)
            candidate.input_snapshot_sha256 = context["input_snapshot_sha256"]
            assert all("confirmed_by_subject" not in fact for fact in context["facts"].values())
            return candidate

    draft = runtime.generate_version(Writer())
    assert draft.status == "proposal" and draft.submitted_for_review_at is None
    assert runtime._record(session, draft).payload["approval_basis"] == "owner_decision"
    assert runtime._record(session, draft).payload["professional_review_performed"] is False
    assert all(
        not component["review_records"]
        for component in [
            *bundle["policies"]["policies"],
            bundle["policies"]["dictionary"],
            bundle["accounting"],
        ]
    )


def test_request_fact_actor_is_bound_by_server_and_not_sent_to_writer(session):
    from app.modules.training.prescription_development import build_prescription_writer_context
    from app.modules.training.prescription_validation import validate_development_prescription

    client = create_client(session, "prescription-dev-inputs", "inputs@example.test")
    case = valid_case(client.id)
    data = RequestInputSubmission(
        expected_snapshot_hash=record_hash(case["snapshot"]),
        values={"progression_observed": {"value": True}},
    )
    submit_request_inputs(
        session, case, data, actor_role="client_owner", actor_subject="prescription-dev-inputs"
    )
    row = session.scalar(select(DevelopmentInputConfirmation))
    assert (
        row.snapshot["facts"]["progression_observed"]["source_actor_subject"]
        == "prescription-dev-inputs"
    )
    assert (
        row.snapshot["facts"]["progression_observed"]["confirmed_by_subject"]
        == "prescription-dev-inputs"
    )
    from app.modules.training.prescription_contract import InputSnapshot

    case["snapshot"] = InputSnapshot.model_validate(row.snapshot)
    preflight = validate_development_prescription(
        candidate=None, **{k: v for k, v in case.items() if k != "candidate"}
    )
    context = build_prescription_writer_context(case, preflight, None)
    assert "source_actor_subject" not in context["facts"]["progression_observed"]
    assert "confirmed_by_subject" not in context["facts"]["progression_observed"]


def test_client_cannot_write_instructor_observation_or_onboarding(session):
    client = create_client(session, "prescription-dev-denied", "denied@example.test")
    case = valid_case(client.id)
    requirement = next(
        r for r in case["execution"].input_requirements if r.key == "progression_observed"
    )
    requirement.allowed_actor_roles = ["instructor"]
    for values in (
        {"progression_observed": {"value": True}},
        {"training_goal": {"value": "Changed"}},
    ):
        data = RequestInputSubmission(
            expected_snapshot_hash=record_hash(case["snapshot"]), values=values
        )
        with pytest.raises(PrescriptionRejection, match="authority_not_approved"):
            submit_request_inputs(
                session,
                case,
                data,
                actor_role="client_owner",
                actor_subject="prescription-dev-denied",
            )
    assert session.scalar(select(DevelopmentInputConfirmation)) is None


def test_modality_migration_preserves_existing_rows_and_refuses_lossy_downgrade(migration_engine):
    metadata = MetaData()
    items = Table(
        "training_plan_item",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("sets", Integer, nullable=False),
        Column("rest_seconds", Integer, nullable=False),
    )
    Table("training_adaptation_operation", metadata, Column("id", Integer, primary_key=True))
    migration = runpy.run_path(
        str(Path(__file__).parents[1] / "alembic/versions/20261024_37_prescription_modalities.py")
    )
    with migration_engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(items.insert().values(id=1, sets=3, rest_seconds=90))
        with Operations.context(MigrationContext.configure(connection)):
            migration["upgrade"]()
        assert connection.execute(
            text("SELECT sets, rest_seconds FROM training_plan_item WHERE id=1")
        ).one() == (3, 90)
        assert next(
            c
            for c in inspect(connection).get_columns("training_plan_item")
            if c["name"] == "rest_seconds"
        )["nullable"]
        connection.execute(text("UPDATE training_plan_item SET dose_details='{}' WHERE id=1"))
        with Operations.context(MigrationContext.configure(connection)):
            with pytest.raises(RuntimeError, match="discard"):
                migration["downgrade"]()
