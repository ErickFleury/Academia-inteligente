"""Operational adapters with explicitly synthetic mechanics fixtures, never review claims."""

from copy import deepcopy
from uuid import uuid4

import pytest
from prescription_fixtures import valid_case
from sqlalchemy import select
from test_training_generation import complete_onboarding, create_client
from test_training_generation import session as session
from training_fixtures import AcceptingTrainingReviewer

from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.prescription_contract import PrescriptionRejection, record_hash
from app.modules.training.prescription_development import DevelopmentValidationRecord
from app.modules.training.prescription_runtime import (
    OperationalPrescriptionService,
    writer_configuration,
)


def test_unapproved_packaged_policy_blocks_before_retrieval_or_writer(session):
    client = create_client(session, "operational-owner", "operational-owner@example.test")
    complete_onboarding(session, "operational-owner")

    class Unused:
        def retrieve(self, *args):
            pytest.fail("unapproved policy reached retrieval")

        def generate_prescription(self, *args):
            pytest.fail("unapproved policy reached writer")

    service = OperationalPrescriptionService(
        session=session,
        client_id=client.id,
        subject="operational-owner",
        knowledge_service=Unused(),
    )
    with pytest.raises(PrescriptionRejection, match="approved_goal_policy_required"):
        service.generate_version(Unused())
    assert session.scalar(select(TrainingPlanVersion)) is None


def test_operational_adapter_reuses_typed_validation_and_persistence(session):
    client = create_client(session, "operational-owner", "operational-owner@example.test")
    case = valid_case(client.id)
    case["execution"].purpose = "operational"
    case["execution"].writer_configuration_sha256 = record_hash(writer_configuration())
    service = OperationalPrescriptionService(
        session=session,
        client_id=client.id,
        subject="operational-owner",
        context_supplier=lambda: deepcopy(case),
    )

    class Writer(AcceptingTrainingReviewer):
        def generate_prescription(self, context):
            assert context["input_snapshot_sha256"] == record_hash(case["snapshot"])
            assert len(context["evidence"]["chunks"]) <= 6
            return case["candidate"]

    draft = service.generate_version(Writer())
    record = session.scalar(select(DevelopmentValidationRecord))
    assert draft.status == "proposal" and draft.submitted_for_review_at is None
    assert record.payload["purpose"] == "operational"
    assert record.payload["rendered_content_sha256"] == record_hash(
        service.lifecycle.content(session, draft)
    )


def test_runtime_refuses_development_contract_and_cross_client_access(session):
    client = create_client(session, "operational-owner", "operational-owner@example.test")
    case = valid_case(client.id)
    service = OperationalPrescriptionService(
        session=session,
        client_id=client.id,
        subject="operational-owner",
        context_supplier=lambda: deepcopy(case),
    )
    with pytest.raises(PrescriptionRejection, match="operational_contract_required"):
        service._context(session, client.id)
    with pytest.raises(PermissionError):
        service._boundary(session, uuid4())
    with pytest.raises(PermissionError):
        service.onboarding_snapshot(
            session,
            AuthenticatedIdentity("other", "", ("client",)),
            client_id=client.id,
            required_fields={"training_goal"},
        )


def test_current_writer_configuration_is_checked_even_after_dependency_injection(session):
    client = create_client(session, "operational-owner", "operational-owner@example.test")
    case = valid_case(client.id)
    case["execution"].purpose = "operational"
    case["execution"].writer_configuration_sha256 = "0" * 64
    service = OperationalPrescriptionService(
        session=session,
        client_id=client.id,
        subject="operational-owner",
        context_supplier=lambda: deepcopy(case),
    )
    with pytest.raises(PrescriptionRejection, match="writer_configuration_changed"):
        service._context(session, client.id)


def test_operational_adaptation_validates_acceptance_and_keeps_current_immutable(
    session, monkeypatch
):
    from prescription_fixtures import enable_weekly_fixture
    from test_training_adaptations import source_message
    from training_fixtures import instructor

    from app.modules.training.adaptation_service import TrainingAdaptationService
    from app.modules.training.prescription_development import PrescriptionAdaptationValidation
    from app.modules.training.service import TrainingLifecycleService

    client = create_client(session, "operational-owner", "operational-owner@example.test")
    instructor(session)
    case = valid_case(client.id)
    enable_weekly_fixture(case)
    case["execution"].purpose = "operational"
    case["execution"].writer_configuration_sha256 = record_hash(writer_configuration())
    monkeypatch.setattr(
        OperationalPrescriptionService, "_operational_context", lambda self: deepcopy(case)
    )

    class Writer(AcceptingTrainingReviewer):
        changed = False

        def generate_prescription(self, context):
            candidate = case["candidate"].model_copy(deep=True)
            candidate.expected_revision = context["current_revision"]
            if self.changed:
                candidate.sessions[0].items[0].sets = 1
            return candidate

    writer = Writer()
    runtime = OperationalPrescriptionService(
        session=session,
        client_id=client.id,
        subject="operational-owner",
    )
    base = runtime.generate_version(writer)
    lifecycle = TrainingLifecycleService()
    lifecycle.submit_for_review(
        session, subject="operational-owner", version_id=base.id, expected_revision=base.revision
    )
    lifecycle.approve(
        session,
        plan_id=base.plan_id,
        version_number=base.version_number,
        actor="instructor-1",
        expected_revision=base.revision,
    )
    original = lifecycle.content(session, base)
    source_id = uuid4()
    source_message(session, client, source_id)
    writer.changed = True
    service = TrainingAdaptationService(provider=writer)
    monkeypatch.setenv("TRAINING_PRESCRIPTION_GATE_ENABLED", "true")
    proposal = service.generate(
        session,
        "operational-owner",
        source_client_request_id=source_id,
        client_request_id=uuid4(),
        reason="Pedido sintético de ajuste",
    )
    assert session.get(PrescriptionAdaptationValidation, proposal.id) is not None
    service.client_decide(session, "operational-owner", proposal.id, accept=True)
    draft = session.get(TrainingPlanVersion, proposal.resulting_version_id)
    assert draft.status == "proposal" and draft.submitted_for_review_at is not None
    assert runtime._record(session, draft).kind == "qualified"
    assert lifecycle.content(session, base) == original and base.status == "current"
    case["source_catalog"]["sources"][0]["review_status"] = "excluded"
    with pytest.raises(PrescriptionRejection):
        lifecycle.approve(
            session,
            plan_id=draft.plan_id,
            version_number=draft.version_number,
            actor="instructor-1",
            expected_revision=draft.revision,
        )
    assert base.status == "current" and draft.status == "proposal"
