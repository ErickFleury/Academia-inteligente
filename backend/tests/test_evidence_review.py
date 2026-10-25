"""Synthetic human-review records and confidential custody; no real approvals."""

import runpy
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from prescription_fixtures import valid_case
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import OperationalError
from test_prescription_migration import migration_engine as migration_engine
from test_training_generation import create_client
from test_training_lifecycle import session as session
from test_training_review import api as api
from training_fixtures import instructor

from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training import evidence_review as service
from app.modules.training.evidence_review_models import EvidenceJudgment, EvidenceSeal
from app.modules.training.prescription_contract import PrescriptionRejection, record_hash
from app.modules.training.prescription_policy import HumanReview

ROOT = "/training/evidence-review"


@pytest.fixture
def artifacts(monkeypatch):
    items = {
        "source:synthetic": {
            "id": "source:synthetic",
            "kind": "source",
            "title": "Fonte sintética de teste",
            "data": {"version": 1, "text": "Exposed software fixture, not scientific evidence."},
            "missing_items": [],
            "sections": [{"label": "Trecho fictício", "text": "Conteúdo fictício."}],
        },
        "prescription-bundle": {
            "id": "prescription-bundle",
            "kind": "prescription_bundle",
            "title": "Contrato incompleto",
            "data": {"policies": []},
            "missing_items": ["Faltam regras revisadas."],
            "sections": [],
        },
    }
    for item in items.values():
        item["sha256"] = record_hash(item["data"])
    monkeypatch.setattr(service, "current_artifacts", lambda: deepcopy(items))
    return items


def judgment(artifacts, **changes):
    return {
        "request_id": str(uuid4()),
        "expected_artifact_sha256": artifacts["source:synthetic"]["sha256"],
        "function": "methodological",
        "decision": "approved",
        "scope": "Escopo exclusivamente sintético deste teste.",
        "method_and_version": "Instrumento fictício v1",
        "rationale": "Julgamento fictício para testar persistência e autorização.",
        "competence": "Declaração fictícia",
        "conflicts": "Sem conflito neste teste fictício.",
        "judgments": [
            {
                "domain": "Domínio fictício",
                "judgment": "Avaliado no teste",
                "source_locator": "fixture:1",
            }
        ],
        "outcomes": [
            {
                "outcome": "Desfecho fictício",
                "certainty": "low",
                "rationale": "Justificativa fictícia.",
            }
        ],
        "personally_performed": True,
        "independent_assessment": True,
        "review_due_at": (datetime.now(UTC).date() + timedelta(days=30)).isoformat(),
        **changes,
    }


def seal(artifacts, **changes):
    return {
        "request_id": str(uuid4()),
        "artifact_hashes": {"source:synthetic": artifacts["source:synthetic"]["sha256"]},
        "protocol": {
            "title": "Protocolo fictício de teste",
            "scope": "Escopo sintético",
            "methods": "Método fictício",
            "decision_thresholds": "Critério definido somente para este teste de software.",
            "repeat_count": 1,
            "maximum_writer_calls": 1,
            "maximum_runtime_seconds": 10,
        },
        "cases": [
            {
                "case_id": "case-1",
                "cohort": "synthetic",
                "scenario": "Private exposed fixture case",
                "reference_judgment": "Private fixture reference answer",
                "critical": True,
            }
        ],
        "synthetic_only": True,
        "independent_and_unexposed": True,
        "understands_no_release": True,
        **changes,
    }


def test_two_distinct_active_instructors_can_review_exact_artifacts(session, api, artifacts):
    http, identity = api
    first = judgment(artifacts)
    posted = http.post(ROOT + "/artifacts/source:synthetic/judgments", first)
    assert posted.status_code == 200
    assert posted.json()["reviewer_name"] == "Instrutor Silva"
    replay = http.post(ROOT + "/artifacts/source:synthetic/judgments", first)
    assert replay.json()["id"] == posted.json()["id"]
    assert session.scalar(select(func.count()).select_from(EvidenceJudgment)) == 1
    assert (
        http.post(
            ROOT + "/artifacts/source:synthetic/judgments",
            judgment(artifacts, function="professional"),
        ).status_code
        == 409
    )
    identity.identity = AuthenticatedIdentity("instructor-2", "", ("instructor",))
    second = http.post(
        ROOT + "/artifacts/source:synthetic/judgments", judgment(artifacts, function="professional")
    )
    assert second.status_code == 200
    assert http.get(ROOT + "/artifacts/source:synthetic").json()["independence_complete"]
    assert http.get(ROOT + "/artifacts").json()[0]["content"] is None


@pytest.mark.parametrize("role", ["client", "admin", "attendant"])
def test_non_instructors_cannot_read_or_register_reviews(session, api, artifacts, role):
    http, identity = api
    subject = "instructor-1"
    if role == "client":
        subject = "review-client"
        create_client(session, subject, "review-client@example.test")
    identity.identity = AuthenticatedIdentity(subject, "", (role,))
    assert http.get(ROOT + "/artifacts").status_code == 403
    assert (
        http.post(ROOT + "/artifacts/source:synthetic/judgments", judgment(artifacts)).status_code
        == 403
    )
    assert http.post(ROOT + "/seals", seal(artifacts)).status_code == 403


def test_local_role_and_caller_identity_cannot_be_forged(session, api, artifacts):
    http, identity = api
    identity.identity = AuthenticatedIdentity("unlinked", "", ("instructor",))
    assert http.get(ROOT + "/artifacts").status_code == 401
    identity.identity = AuthenticatedIdentity("instructor-1", "", ("instructor",))
    assert (
        http.post(
            ROOT + "/artifacts/source:synthetic/judgments",
            judgment(artifacts, reviewer_subject="instructor-2"),
        ).status_code
        == 422
    )
    instructor(session).active = False
    session.commit()
    assert http.get(ROOT + "/artifacts").status_code == 401


def test_stale_incomplete_unassessed_and_unattested_approvals_are_rejected(api, artifacts):
    http, _ = api
    assert (
        http.post(
            ROOT + "/artifacts/source:synthetic/judgments",
            judgment(artifacts, expected_artifact_sha256="0" * 64),
        ).status_code
        == 409
    )
    body = judgment(artifacts, expected_artifact_sha256=artifacts["prescription-bundle"]["sha256"])
    assert http.post(ROOT + "/artifacts/prescription-bundle/judgments", body).status_code == 422
    body["decision"] = "changes_requested"
    assert http.post(ROOT + "/artifacts/prescription-bundle/judgments", body).status_code == 200
    assert (
        http.post(
            ROOT + "/artifacts/source:synthetic/judgments",
            judgment(artifacts, personally_performed=False),
        ).status_code
        == 422
    )
    body = judgment(artifacts)
    body["outcomes"][0]["certainty"] = "not_assessed"
    assert http.post(ROOT + "/artifacts/source:synthetic/judgments", body).status_code == 422


def test_disagreement_requires_a_distinct_adjudicator_and_exact_review_references(
    session, api, artifacts
):
    http, identity = api
    first = http.post(ROOT + "/artifacts/source:synthetic/judgments", judgment(artifacts)).json()
    identity.identity = AuthenticatedIdentity("instructor-2", "", ("instructor",))
    second = http.post(
        ROOT + "/artifacts/source:synthetic/judgments",
        judgment(artifacts, function="professional", decision="changes_requested"),
    ).json()
    assert not http.get(ROOT + "/artifacts/source:synthetic").json()["independence_complete"]
    instructor(session, "instructor-3", "Terceira")
    identity.identity = AuthenticatedIdentity("instructor-3", "", ("instructor",))
    body = judgment(
        artifacts, function="adjudicator", resolves_judgment_ids=[first["id"], str(uuid4())]
    )
    assert http.post(ROOT + "/artifacts/source:synthetic/judgments", body).status_code == 422
    body["resolves_judgment_ids"] = [first["id"], second["id"]]
    assert http.post(ROOT + "/artifacts/source:synthetic/judgments", body).status_code == 200
    assert http.get(ROOT + "/artifacts/source:synthetic").json()["independence_complete"]


def test_confidential_cases_are_visible_only_to_the_actual_custodian(session, api, artifacts):
    http, identity = api
    data = seal(artifacts)
    created = http.post(ROOT + "/seals", data)
    assert created.status_code == 200
    identifier = created.json()["id"]
    assert "cases" not in created.json() and created.json()["can_read_cases"]
    assert all(created.json()["attestations"].values())
    assert http.post(ROOT + "/seals", data).json()["id"] == identifier
    assert session.scalar(select(func.count()).select_from(EvidenceSeal)) == 1
    own = http.get(ROOT + f"/seals/{identifier}/cases")
    assert own.json()["cases"] == data["cases"]
    identity.identity = AuthenticatedIdentity("instructor-2", "", ("instructor",))
    public = http.get(ROOT + "/seals")
    assert public.status_code == 200 and not public.json()[0]["can_read_cases"]
    assert "Private fixture reference answer" not in str(public.json())
    assert "Private exposed fixture case" not in str(public.json())
    assert http.get(ROOT + f"/seals/{identifier}/cases").status_code == 404
    assert http.get(ROOT + f"/seals/{uuid4()}/cases").status_code == 404


def test_seal_replay_drift_stale_artifact_and_invalid_budget_are_rejected(api, artifacts):
    http, _ = api
    data = seal(artifacts)
    assert http.post(ROOT + "/seals", data).status_code == 200
    data["cases"][0]["reference_judgment"] = "Different reference answer"
    assert http.post(ROOT + "/seals", data).status_code == 409
    data = seal(artifacts, artifact_hashes={"source:synthetic": "0" * 64})
    assert http.post(ROOT + "/seals", data).status_code == 409
    data = seal(artifacts)
    data["protocol"]["repeat_count"] = 2
    assert http.post(ROOT + "/seals", data).status_code == 422
    assert (
        http.post(ROOT + "/seals", seal(artifacts, independent_and_unexposed=False)).status_code
        == 422
    )


def test_sealed_payload_integrity_is_checked_before_retrieval(session, api, artifacts):
    http, _ = api
    created = http.post(ROOT + "/seals", seal(artifacts)).json()
    row = session.scalar(select(EvidenceSeal))
    row.private_cases = [{"case_id": "tampered"}]
    session.commit()
    result = http.get(ROOT + f"/seals/{created['id']}/cases")
    assert result.status_code == 503
    assert result.json() == {"detail": "sealed_payload_integrity_error"}
    assert "tampered" not in str(result.json())


def test_protocol_is_reviewable_without_loading_or_disclosing_sealed_cases(api, artifacts):
    http, identity = api
    created = http.post(ROOT + "/seals", seal(artifacts)).json()
    identity.identity = AuthenticatedIdentity("instructor-2", "", ("instructor",))
    identifier = "seal-protocol:" + created["id"]
    listing = http.get(ROOT + "/artifacts")
    assert listing.status_code == 200
    assert identifier in {item["id"] for item in listing.json()}
    detail = http.get(ROOT + "/artifacts/" + identifier)
    assert detail.status_code == 200
    public = detail.json()
    assert public["kind"] == "evaluation_protocol"
    assert "cases" not in public["content"]
    assert "reference_judgment" not in str(public)
    review = judgment(artifacts, expected_artifact_sha256=public["sha256"])
    assert http.post(ROOT + "/artifacts/" + identifier + "/judgments", review).status_code == 200
    assert http.get(ROOT + f"/seals/{created['id']}/cases").status_code == 404


def test_review_replacement_preserves_original_and_cannot_change_independent_function(
    session, api, artifacts
):
    http, _ = api
    first = http.post(ROOT + "/artifacts/source:synthetic/judgments", judgment(artifacts)).json()
    replacement = judgment(
        artifacts, decision="changes_requested", supersedes_judgment_id=first["id"]
    )
    invalid = {**replacement, "function": "professional"}
    assert http.post(ROOT + "/artifacts/source:synthetic/judgments", invalid).status_code == 409
    result = http.post(ROOT + "/artifacts/source:synthetic/judgments", replacement)
    assert result.status_code == 200 and result.json()["is_current"]
    original = http.get(ROOT + f"/judgments/{first['id']}").json()
    assert not original["is_current"] and not original["can_supersede"]
    assert original["decision"] == "approved" and original["assessment"] == first["assessment"]
    assert session.scalar(select(func.count()).select_from(EvidenceJudgment)) == 2
    stale = {**replacement, "request_id": str(uuid4())}
    assert http.post(ROOT + "/artifacts/source:synthetic/judgments", stale).status_code == 409


def test_approval_needs_a_future_review_deadline_and_expiry_does_not_fall_back_to_old_reviews(
    session, api, artifacts
):
    http, identity = api
    assert (
        http.post(
            ROOT + "/artifacts/source:synthetic/judgments", judgment(artifacts, review_due_at=None)
        ).status_code
        == 422
    )
    expired = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    assert (
        http.post(
            ROOT + "/artifacts/source:synthetic/judgments",
            judgment(artifacts, review_due_at=expired),
        ).status_code
        == 422
    )
    assert (
        http.post(ROOT + "/artifacts/source:synthetic/judgments", judgment(artifacts)).status_code
        == 200
    )
    identity.identity = AuthenticatedIdentity("instructor-2", "", ("instructor",))
    assert (
        http.post(
            ROOT + "/artifacts/source:synthetic/judgments",
            judgment(artifacts, function="professional"),
        ).status_code
        == 200
    )
    assert http.get(ROOT + "/artifacts/source:synthetic").json()["independence_complete"]
    row = session.scalar(
        select(EvidenceJudgment).where(EvidenceJudgment.function == "professional")
    )
    row.payload = {**row.payload, "review_due_at": expired}
    session.commit()
    assert not http.get(ROOT + "/artifacts/source:synthetic").json()["independence_complete"]


def test_database_failures_rollback_and_never_disclose_private_payload(
    session, api, artifacts, monkeypatch
):
    http, _ = api
    with monkeypatch.context() as patch:
        patch.setattr(
            session,
            "commit",
            lambda: (_ for _ in ()).throw(
                OperationalError(
                    "INSERT seal", {"private": "PRIVATE-REFERENCE"}, Exception("outage")
                )
            ),
        )
        response = http.post(ROOT + "/seals", seal(artifacts))
    assert response.status_code == 503
    assert response.json() == {"detail": "review_storage_unavailable"}
    assert "PRIVATE-REFERENCE" not in str(response.json())
    assert session.scalar(select(func.count()).select_from(EvidenceSeal)) == 0


def test_pilot_reset_refuses_to_erase_review_or_custody_records(session, api, artifacts):
    from scripts.reset_facial_pilot import clear_database, table_counts

    http, _ = api
    assert http.post(ROOT + "/seals", seal(artifacts)).status_code == 200
    before = table_counts(session)
    with pytest.raises(RuntimeError, match="Review/custody records exist"):
        clear_database(session, set())
    assert table_counts(session) == before


def test_new_independent_reviewers_can_renew_expired_approvals_without_erasing_history(
    session, api, artifacts
):
    http, identity = api
    assert (
        http.post(ROOT + "/artifacts/source:synthetic/judgments", judgment(artifacts)).status_code
        == 200
    )
    identity.identity = AuthenticatedIdentity("instructor-2", "", ("instructor",))
    assert (
        http.post(
            ROOT + "/artifacts/source:synthetic/judgments",
            judgment(artifacts, function="professional"),
        ).status_code
        == 200
    )
    for row in session.scalars(select(EvidenceJudgment)):
        row.payload = {**row.payload, "review_due_at": "2000-01-01"}
    session.commit()
    assert not http.get(ROOT + "/artifacts/source:synthetic").json()["independence_complete"]
    for subject, function in (("instructor-3", "methodological"), ("instructor-4", "professional")):
        instructor(session, subject, subject)
        identity.identity = AuthenticatedIdentity(subject, "", ("instructor",))
        assert (
            http.post(
                ROOT + "/artifacts/source:synthetic/judgments",
                judgment(artifacts, function=function),
            ).status_code
            == 200
        )
    assert http.get(ROOT + "/artifacts/source:synthetic").json()["independence_complete"]
    assert session.scalar(select(func.count()).select_from(EvidenceJudgment)) == 4


def test_actual_registry_exposes_no_ready_executable_bundle():
    artifacts = service.current_artifacts()
    assert not artifacts["prescription-bundle"]["missing_items"] == []
    assert any(a["kind"] == "source" and not a["missing_items"] for a in artifacts.values())
    proposals = [a for a in artifacts.values() if a["kind"] == "rule_proposal"]
    assert len(proposals) == 37
    assert all(a["data"]["runtime_eligible"] is False for a in proposals)


def test_bundle_digest_excludes_approval_bookkeeping_but_binds_clinical_content():
    case = valid_case()
    bundle = {
        "policies": case["catalog"].model_dump(mode="json"),
        "execution": {"contracts": [case["execution"].model_dump(mode="json")]},
        "accounting": case["accounting"].model_dump(mode="json"),
    }
    original = service.prescription_bundle_hash(bundle)
    changed = deepcopy(bundle)
    changed["policies"]["policies"][0]["status"] = "pending"
    changed["policies"]["policies"][0]["review_records"] = []
    assert service.prescription_bundle_hash(changed) == original
    changed["policies"]["policies"][0]["population"] = "Different synthetic population"
    assert service.prescription_bundle_hash(changed) != original


def test_runtime_cannot_reuse_superseded_or_forged_review_links_or_extend_human_deadlines(
    session, api, artifacts
):
    http, identity = api
    target = artifacts["prescription-bundle"]
    target["missing_items"] = []  # Explicitly synthetic, structurally ready test artifact.
    first = http.post(
        ROOT + "/artifacts/prescription-bundle/judgments",
        judgment(
            artifacts,
            expected_artifact_sha256=target["sha256"],
        ),
    ).json()
    identity.identity = AuthenticatedIdentity("instructor-2", "", ("instructor",))
    second = http.post(
        ROOT + "/artifacts/prescription-bundle/judgments",
        judgment(
            artifacts,
            expected_artifact_sha256=target["sha256"],
            function="professional",
        ),
    ).json()
    reviews = [HumanReview.model_validate(r["human_review_record"]) for r in (first, second)]
    deadline = datetime.now(UTC).date() + timedelta(days=30)
    service.require_current_runtime_reviews(session, [(reviews, deadline)])
    forged = [reviews[0].model_copy(update={"identity": "forged-person"}), reviews[1]]
    with pytest.raises(PrescriptionRejection, match="professional_review_not_current"):
        service.require_current_runtime_reviews(session, [(forged, deadline)])
    with pytest.raises(PrescriptionRejection, match="professional_review_scope_or_deadline"):
        service.require_current_runtime_reviews(session, [(reviews, deadline + timedelta(days=1))])
    identity.identity = AuthenticatedIdentity("instructor-1", "", ("instructor",))
    assert (
        http.post(
            ROOT + "/artifacts/prescription-bundle/judgments",
            judgment(
                artifacts,
                expected_artifact_sha256=target["sha256"],
                decision="changes_requested",
                supersedes_judgment_id=first["id"],
            ),
        ).status_code
        == 200
    )
    with pytest.raises(PrescriptionRejection, match="professional_contract_review_required"):
        service.require_current_runtime_reviews(session, [(reviews, deadline)])


def test_custody_migration_is_empty_reversible_and_preserves_existing_data(migration_engine):
    migration = runpy.run_path(
        str(Path(__file__).parents[1] / "alembic/versions/20261024_36_evidence_review_custody.py")
    )
    with migration_engine.begin() as connection:
        connection.execute(text("CREATE TABLE retained_review_data (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO retained_review_data VALUES (1)"))
        with Operations.context(MigrationContext.configure(connection)):
            migration["upgrade"]()
        for table in ("training_evidence_judgment", "training_evidence_seal"):
            assert connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() == 0
            assert inspect(connection).get_unique_constraints(table)
        with Operations.context(MigrationContext.configure(connection)):
            migration["downgrade"]()
        assert connection.execute(text("SELECT id FROM retained_review_data")).scalar_one() == 1
