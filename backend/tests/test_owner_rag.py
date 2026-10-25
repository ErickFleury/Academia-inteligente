"""Owner-assisted RAG mechanics with synthetic students and fake external adapters."""

import json
from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_training_generation import complete_onboarding, create_client, proposal
from test_training_generation import session as session
from training_fixtures import AcceptingTrainingReviewer, instructor

from app.integrations.ai import AiTrainingGenerationResponse, AiTrainingRequestFocus
from app.modules.knowledge.models import KnowledgeSource
from app.modules.knowledge.service import KnowledgeContext
from app.modules.training import owner_rag
from app.modules.training.evidence_review import current_artifacts
from app.modules.training.generation_service import InitialTrainingGenerationService
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.prescription_contract import PrescriptionRejection
from app.modules.training.service import TrainingLifecycleService


@pytest.fixture
def owner_case(session, monkeypatch):
    monkeypatch.setenv("TRAINING_EVIDENCE_MODE", "owner_rag")
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    source = current_artifacts()["source:nhs-strength"]["data"]
    fields = {column.name for column in KnowledgeSource.__table__.columns}
    data = {key: value for key, value in source.items() if key in fields}
    for key in ("reviewed_at", "review_due_at", "captured_at"):
        if data.get(key):
            data[key] = date.fromisoformat(data[key])
    session.add(KnowledgeSource(**data))
    client = create_client(session, "rag-owner", "rag-owner@example.test")
    complete_onboarding(session, "rag-owner")
    chunk = source["chunks"][0]
    evidence = KnowledgeContext(
        (
            {
                **source,
                "chunk_id": chunk["id"],
                "source_id": source["id"],
                "content": chunk["content"],
                "section": chunk["section"],
            },
        ),
        "supported",
        "Referência de consulta.",
    )

    class Knowledge:
        def retrieve(self, *args):
            return evidence

    class Writer(AcceptingTrainingReviewer):
        calls = 0
        contexts = []

        def analyze_training_request(self, context):
            return AiTrainingRequestFocus(scope="unspecified", muscle_groups=[])

        def generate_training(self, context):
            self.calls += 1
            self.contexts.append(context)
            plan = deepcopy(proposal().plan)
            plan["items"][0]["rest_seconds"] = 180
            plan["items"][0]["load_guidance"] = "Peso corporal"
            return AiTrainingGenerationResponse(
                plan=plan, citations=[chunk["id"]], knowledge_status="supported"
            )

    writer = Writer()
    service = InitialTrainingGenerationService(provider=writer, knowledge_service=Knowledge())
    return client, service, writer, source, evidence


def test_actual_authorization_has_no_independent_or_professional_gate(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    record = owner_rag.authorization()
    assert record["independent_evaluation_required"] is False
    assert record["professional_review_performed"] is False
    assert record["automatic_plan_activation_authorized"] is False


def test_owner_rag_generates_reuses_and_submits_without_compiled_policy_or_seal(
    session, owner_case
):
    client, service, writer, _, _ = owner_case
    draft = service.generate_for_subject(session, "rag-owner")
    assert draft.status == "proposal" and draft.submitted_for_review_at is None
    assert draft.citations[0]["owner_rag"]["compiled_prescription_qualification"] is False
    assert "sem parecer profissional" in draft.knowledge_limitations
    assert writer.contexts[0]["owner_approved_research"]["goal_family"] == "strength"
    assert service.generate_for_subject(session, "rag-owner").id == draft.id
    assert writer.calls == 1
    TrainingLifecycleService().submit_for_review(
        session, subject="rag-owner", version_id=draft.id, expected_revision=draft.revision
    )
    assert draft.submitted_for_review_at is not None
    assert (
        session.scalar(select(TrainingPlanVersion).where(TrainingPlanVersion.status == "current"))
        is None
    )
    assert draft.client_id == client.id


def test_source_revocation_blocks_reuse_and_submission_preserving_saved_draft(session, owner_case):
    _, service, writer, source, _ = owner_case
    draft = service.generate_for_subject(session, "rag-owner")
    original = TrainingLifecycleService().content(session, draft)
    session.get(KnowledgeSource, source["id"]).review_status = "excluded"
    session.commit()
    with pytest.raises(PrescriptionRejection, match="no_longer_eligible"):
        service.generate_for_subject(session, "rag-owner")
    with pytest.raises(PrescriptionRejection):
        TrainingLifecycleService().submit_for_review(
            session, subject="rag-owner", version_id=draft.id, expected_revision=draft.revision
        )
    assert writer.calls == 1 and draft.status == "proposal"
    assert TrainingLifecycleService().content(session, draft) == original
    assert draft.submitted_for_review_at is None


def test_missing_citations_never_persist_a_proposal(session, owner_case):
    _, service, writer, _, _ = owner_case
    original = writer.generate_training
    writer.generate_training = lambda context: original(context).model_copy(
        update={"citations": []}
    )
    with pytest.raises(PrescriptionRejection, match="consultation_citations_required"):
        service.generate_for_subject(session, "rag-owner")
    assert session.scalar(select(TrainingPlanVersion)) is None


def test_authorization_config_changes_cannot_reuse_owner_approval(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "unapproved-model")
    with pytest.raises(PrescriptionRejection, match="current_owner_rag_authorization"):
        owner_rag.authorization()


def test_owner_rag_does_not_derive_an_external_kg_load_from_demographics(session, owner_case):
    _, service, writer, _, _ = owner_case
    original = writer.generate_training

    def faulty(context):
        response = original(context)
        response.plan["items"][0]["load_guidance"] = "Use 10 kg de acordo com sua altura."
        return response

    writer.generate_training = faulty
    with pytest.raises(PrescriptionRejection, match="unmeasured_external_load_generated"):
        service.generate_for_subject(session, "rag-owner")
    assert writer.calls == 2
    assert not getattr(writer, "review_contexts", [])
    assert session.scalar(select(TrainingPlanVersion)) is None


def test_manual_instructor_edit_remains_available_after_source_revocation(session, owner_case):
    _, service, _, source, _ = owner_case
    instructor(session)
    draft = service.generate_for_subject(session, "rag-owner")
    TrainingLifecycleService().submit_for_review(
        session, subject="rag-owner", version_id=draft.id, expected_revision=draft.revision
    )
    session.get(KnowledgeSource, source["id"]).review_status = "excluded"
    session.commit()
    lifecycle = TrainingLifecycleService()
    content = lifecycle.content(session, draft)
    content.name = "Revisão manual"
    revised = lifecycle.revise(
        session,
        plan_id=draft.plan_id,
        version_number=draft.version_number,
        actor="instructor-1",
        data=content,
        expected_revision=draft.revision,
    )
    assert not revised.citations and revised.origin == "ai"


def test_invalid_or_revoked_rag_decision_is_controlled(tmp_path, monkeypatch):
    data = json.loads(owner_rag.AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    data["status"] = "revoked"
    path = tmp_path / "authorization.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(owner_rag, "AUTHORIZATION_PATH", path)
    with pytest.raises(PrescriptionRejection):
        owner_rag.authorization()


@pytest.mark.parametrize(
    "field,invalid",
    [
        ("repetitions", "]"),
        ("exercise_name", "Pull-up com halteres"),
        ("exercise_name", "bodyweight_squat (Dia B)"),
    ],
)
def test_owner_writer_repairs_invalid_representation_and_identity_once(
    session, owner_case, field, invalid
):
    _, service, writer, _, _ = owner_case
    original = writer.generate_training

    def write(context):
        response = original(context)
        if writer.calls == 1:
            response.plan["items"][0][field] = invalid
        return response

    writer.generate_training = write
    draft = service.generate_for_subject(session, "rag-owner")
    assert writer.calls == 2
    assert writer.contexts[1]["selection_correction"]["issues"][0]["field"] == field
    assert (
        TrainingLifecycleService().content(session, draft).items[0].exercise_name
        == "Agachamento com peso corporal (Dia A)"
    )


def test_owner_dictionary_and_minimized_rules_do_not_change_source_quantities(owner_case):
    from app.modules.training.owner_rag_schema import constrain_writer_schema, wire_names

    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {"training_schedule": {"session_labels": []}}, evidence, {"training_goal": "Ganhar força"}
    )
    assert all("Dia A" in name for name in wire_names(context))
    assert len(wire_names(context)) == 12
    assert all("sources" not in rule for rule in context["owner_approved_research"]["rules"])
    rule = next(
        rule
        for rule in context["owner_approved_research"]["rules"]
        if rule["id"] == "STRENGTH_REST"
    )
    assert rule["parameters"][0]["minimum"] == 180
    schema = {
        "type": "object",
        "properties": {"exercise_name": {"type": "string"}, "repetitions": {"type": "string"}},
    }
    constrain_writer_schema(schema, context)
    assert schema["properties"]["exercise_name"]["enum"] == wire_names(context)
    assert "pattern" in schema["properties"]["repetitions"]


def test_owner_chat_generation_and_transport_replay_share_the_saved_rag_proposal(
    session, owner_case
):
    from app.modules.training.chat_service import TrainingChatService

    _, service, writer, _, _ = owner_case
    chat = TrainingChatService(
        provider=writer, generation_service=service, knowledge_service=service._knowledge
    )
    identifier = uuid4()
    state = chat.submit_for_subject(
        session, "rag-owner", message="Monte meu treino", client_request_id=identifier
    )
    assert "Agachamento" in state.messages[-1].content
    chat.submit_for_subject(
        session, "rag-owner", message="Texto de reenvio", client_request_id=identifier
    )
    assert writer.calls == 1
    assert session.scalar(select(TrainingPlanVersion)).citations[0]["owner_rag"]


def test_owner_adaptation_checks_complete_result_and_keeps_current_immutable(session, owner_case):
    from test_training_adaptations import (
        FakeAdaptationProvider,
        adjust_response,
        current_plan,
        source_message,
    )

    from app.modules.training.adaptation_service import TrainingAdaptationService

    client, generation, _, source, _ = owner_case
    base = current_plan(session, client)
    original = TrainingLifecycleService().content(session, base)
    identifier = uuid4()
    source_message(session, client, identifier)
    response = adjust_response().model_copy(
        update={"citations": [source["chunks"][0]["id"]], "knowledge_status": "supported"}
    )
    response.operations[0]["item"]["load_guidance"] = "Peso corporal"
    service = TrainingAdaptationService(
        provider=FakeAdaptationProvider(response), knowledge_service=generation._knowledge
    )
    proposal = service.generate(
        session,
        "rag-owner",
        source_client_request_id=identifier,
        client_request_id=uuid4(),
        reason="Pedido sintético",
    )
    assert proposal.citations[0]["owner_rag"]
    service.client_decide(session, "rag-owner", proposal.id, accept=True)
    draft = session.get(TrainingPlanVersion, proposal.resulting_version_id)
    assert draft.status == "proposal" and base.status == "current"
    assert TrainingLifecycleService().content(session, base) == original
