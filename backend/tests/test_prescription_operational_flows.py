"""Authenticated runtime paths using explicitly synthetic policies and providers."""

from copy import deepcopy
from uuid import uuid4

import pytest
from prescription_fixtures import enable_weekly_fixture, valid_case
from sqlalchemy import select
from test_training_generation import complete_onboarding, create_client
from test_training_generation import session as session
from test_training_review import api as api
from training_fixtures import AcceptingTrainingReviewer, instructor

from app.integrations.ai import AiTrainingRequestFocus
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.models import TrainingAiMessage, TrainingPlanVersion
from app.modules.training.prescription_contract import PrescriptionRejection, record_hash
from app.modules.training.prescription_runtime import (
    OperationalPrescriptionService,
    writer_configuration,
)


@pytest.fixture
def operational(session, monkeypatch):
    client = create_client(session, "operational-owner", "operational-owner@example.test")
    complete_onboarding(session, "operational-owner")
    professional = instructor(session)
    case = valid_case(client.id)
    enable_weekly_fixture(case)
    case["execution"].purpose = "operational"
    case["execution"].writer_configuration_sha256 = record_hash(writer_configuration())
    monkeypatch.setattr(
        OperationalPrescriptionService, "_operational_context", lambda self: deepcopy(case)
    )
    monkeypatch.setenv("TRAINING_PRESCRIPTION_GATE_ENABLED", "true")

    class Writer(AcceptingTrainingReviewer):
        calls = 0

        def analyze_training_request(self, context):
            return AiTrainingRequestFocus(scope="unspecified", muscle_groups=[])

        def generate_prescription(self, context):
            self.calls += 1
            result = case["candidate"].model_copy(deep=True)
            result.expected_revision = context["current_revision"]
            return result

        def training_chat(self, context):
            pytest.fail("free-form chat cannot bypass typed prescription validation")

    return client, case, Writer(), professional


def test_real_chat_path_persists_typed_result_and_revalidates_transport_replays(
    session, operational
):
    client, case, writer, _ = operational
    chat = TrainingChatService(provider=writer)
    request_id = uuid4()
    state = chat.submit_for_subject(
        session, "operational-owner", message="Monte meu treino", client_request_id=request_id
    )
    draft = session.scalar(select(TrainingPlanVersion))
    assert draft.status == "proposal" and writer.calls == 1
    assert "Agachamento" in state.messages[-1].content
    chat.submit_for_subject(
        session,
        "operational-owner",
        message="Texto de reenvio diferente",
        client_request_id=request_id,
    )
    assert writer.calls == 1
    original_revision = draft.revision
    case["source_catalog"]["sources"][0]["review_status"] = "excluded"
    with pytest.raises(PrescriptionRejection):
        chat.submit_for_subject(
            session, "operational-owner", message="Monte meu treino", client_request_id=request_id
        )
    assert writer.calls == 1 and draft.revision == original_revision


def test_rejected_chat_attempt_keeps_only_the_client_message(session, operational):
    _, case, writer, _ = operational
    case["candidate"].sessions[0].items[0].sets = 99
    chat = TrainingChatService(provider=writer)
    with pytest.raises(PrescriptionRejection):
        chat.submit_for_subject(
            session, "operational-owner", message="Monte meu treino", client_request_id=uuid4()
        )
    assert session.scalar(select(TrainingPlanVersion)) is None
    messages = list(session.scalars(select(TrainingAiMessage)))
    assert len(messages) == 1 and messages[0].role == "user"


def test_automatic_review_rejects_without_overriding_evidence_or_saving(session, operational):
    from app.integrations.ai import AiTrainingPlanAssessment

    client, _, writer, _ = operational
    writer.assess_training = lambda context: AiTrainingPlanAssessment(
        sessions=[
            {
                "label": "A",
                "complete": False,
                "issues": ["restriction_not_respected"],
            }
        ]
    )
    runtime = OperationalPrescriptionService(
        session=session, client_id=client.id, subject="operational-owner"
    )
    with pytest.raises(PrescriptionRejection, match="exercise_review_rejected"):
        runtime.generate_version(writer)
    assert writer.calls == 2
    assert session.scalar(select(TrainingPlanVersion)) is None


def test_revocation_during_automatic_review_discards_the_candidate(session, operational):
    client, case, writer, _ = operational
    original_review = writer.assess_training

    def revoke(context):
        case["source_catalog"]["sources"][0]["review_status"] = "excluded"
        return original_review(context)

    writer.assess_training = revoke
    runtime = OperationalPrescriptionService(
        session=session, client_id=client.id, subject="operational-owner"
    )
    with pytest.raises(PrescriptionRejection):
        runtime.generate_version(writer)
    assert session.scalar(select(TrainingPlanVersion)) is None


def test_review_api_enforces_ownership_active_instructor_and_private_trace(
    session, operational, api
):
    client, case, writer, professional = operational
    runtime = OperationalPrescriptionService(
        session=session, client_id=client.id, subject="operational-owner"
    )
    draft = runtime.generate_version(writer)
    http, identity = api
    identity.identity = AuthenticatedIdentity("operational-owner", "", ("client",))
    own = http.get(f"/training/drafts/{draft.id}/prescription")
    assert own.status_code == 200 and own.json()["outcome"]["status"] == "accepted"
    assert "trace" not in own.json()["outcome"]["prescription"]
    create_client(session, "other-client", "other-client@example.test")
    identity.identity = AuthenticatedIdentity("other-client", "", ("client",))
    assert http.get(f"/training/drafts/{draft.id}/prescription").status_code == 404
    runtime.lifecycle.submit_for_review(
        session, subject="operational-owner", version_id=draft.id, expected_revision=draft.revision
    )
    identity.identity = AuthenticatedIdentity("instructor-1", "", ("instructor",))
    review = http.get(f"/training/pending/{draft.id}/prescription")
    assert review.status_code == 200 and review.json()["submitted_for_review"]
    assert review.json()["outcome"]["prescription"]["trace"]
    assert "input_snapshot" not in str(review.json())
    professional.active = False
    session.commit()
    assert http.get(f"/training/pending/{uuid4()}/prescription").status_code == 401
    assert (
        http.post(
            f"/training/pending/{draft.id}/prescription/assume-manual",
            {"expected_revision": draft.revision, "reason": "Revisão sintética"},
        ).status_code
        == 401
    )
