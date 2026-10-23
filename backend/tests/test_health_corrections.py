"""Confirmed chat corrections update current health without silently changing plans."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_training_chat import complete_onboarding

from app.modules.assistant.runtime import AssistantError
from app.modules.memory.service import MemoryError, MemoryService
from app.modules.onboarding.models import Onboarding, OnboardingAuditEvent
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.models import TrainingAiMessage

REPORT = "Eu não tenho mais dor no joelho; esse problema passou."


class HealthAgent(Agent):
    action = "propose"
    kind = "resolved"
    present = False
    details = None

    def structured(self, context, instructions, schema, type_, *, role):
        if role == "orchestrator" and "allowed_specialist" in context:
            self.route = {
                "health_update": {
                    "action": self.action,
                    "field": "has_limitations_or_complaints",
                    "kind": self.kind,
                    "present": self.present,
                    "details": self.details,
                    "quote": context["current_user_message"],
                }
            }
        return super().structured(context, instructions, schema, type_, role=role)


def setup(session):
    client = owner(session)
    complete_onboarding(session, "owner")
    agent = HealthAgent()
    return client, agent, TrainingChatService(agent)


def submit(service, session, message, request_id=None):
    return service.submit_for_subject(
        session, "owner", message=message, client_request_id=request_id or uuid4()
    )


def test_health_report_requires_confirmation_then_survives_reload(database_session, rollout):
    session = database_session
    client, agent, service = setup(session)
    record = session.scalar(select(Onboarding).where(Onboarding.client_id == client.id))
    completed_at = record.completed_at
    first = submit(service, session, REPORT)
    assert record.has_limitations_or_complaints is True
    assert "Joelho sensível" in first.messages[-1].content
    assert "pending_health_update" in first.messages[-1].clarification
    session.expire_all()
    agent.action = "confirm"
    request_id = uuid4()
    result = submit(service, session, "Pode atualizar meu cadastro, confirmo.", request_id)
    session.refresh(record)
    assert record.has_limitations_or_complaints is False
    assert record.limitations_or_complaints is None
    assert record.completed_at == completed_at
    assert record.status == "completed"
    assert "Atualizei" in result.messages[-1].content
    assert submit(service, session, "Pode atualizar meu cadastro, confirmo.", request_id) == result
    audits = session.scalars(
        select(OnboardingAuditEvent).where(OnboardingAuditEvent.action == "health_report_resolved")
    ).all()
    assert len(audits) == 1
    assert audits[0].client_id == client.id
    assert "joelho" not in (audits[0].changed_fields or "").lower()
    agent.route = {}
    generic = Agent()
    submit(TrainingChatService(generic), session, "Como está meu cadastro?")
    effective = generic.calls[-1][1]["authoritative_health_records"]
    assert effective["has_limitations_or_complaints"] is False
    assert effective["limitations_or_complaints"] is None


@pytest.mark.parametrize(
    "message",
    [
        "Não confirmo.",
        "Sim, mas ainda dói.",
        "Talvez, não tenho certeza.",
        "Sim, ainda tenho dor no joelho.",
        "Posso confirmar?",
        "Não quero atualizar.",
    ],
)
def test_model_confirm_label_cannot_override_uncertainty_or_denial(
    database_session, rollout, message
):
    session = database_session
    client, agent, service = setup(session)
    submit(service, session, REPORT)
    agent.action = "confirm"
    result = submit(service, session, message)
    record = session.scalar(select(Onboarding).where(Onboarding.client_id == client.id))
    assert record.has_limitations_or_complaints is True
    assert "pending_health_update" in result.messages[-1].clarification


def test_cancellation_and_topic_change_discard_pending_permission(database_session, rollout):
    session = database_session
    client, agent, service = setup(session)
    submit(service, session, REPORT)
    agent.action = "cancel"
    result = submit(service, session, "Deixa como estava.")
    assert "pending_health_update" not in result.messages[-1].clarification
    agent.action = "confirm"
    submit(service, session, "Confirmo.")
    assert session.scalar(
        select(Onboarding).where(Onboarding.client_id == client.id)
    ).has_limitations_or_complaints
    agent.action = "propose"
    submit(service, session, REPORT)
    submit(TrainingChatService(Agent()), session, "Qual é o horário da academia?")
    agent.action = "confirm"
    submit(service, session, "Confirmo.")
    assert session.scalar(
        select(Onboarding).where(Onboarding.client_id == client.id)
    ).has_limitations_or_complaints


def test_partial_change_preserves_other_complaints_and_health_categories(database_session, rollout):
    session = database_session
    client, agent, service = setup(session)
    record = session.scalar(select(Onboarding).where(Onboarding.client_id == client.id))
    record.limitations_or_complaints = "Dor no joelho e no ombro"
    record.uses_medications, record.medications = True, "Medicamento informado"
    record.has_health_conditions, record.health_conditions = True, "Condição informada"
    session.commit()
    agent.present, agent.details = True, "Dor no ombro"
    first = submit(service, session, "Meu joelho não dói mais. Continuo com dor no ombro.")
    assert "Vou atualizar para: Dor no ombro" in first.messages[-1].content
    agent.action = "confirm"
    submit(service, session, "Isso mesmo, pode salvar.")
    session.refresh(record)
    assert record.has_limitations_or_complaints is True
    assert record.limitations_or_complaints == "Dor no ombro"
    assert record.medications == "Medicamento informado"
    assert record.health_conditions == "Condição informada"


@pytest.mark.parametrize("change", ["stale", "forgotten", "expired"])
def test_invalidated_health_proposal_cannot_be_confirmed(database_session, rollout, change):
    session = database_session
    client, agent, service = setup(session)
    submit(service, session, REPORT)
    record = session.scalar(select(Onboarding).where(Onboarding.client_id == client.id))
    if change == "stale":
        record.updated_at = datetime.now(UTC) + timedelta(seconds=1)
    elif change == "forgotten":
        # SQLite's server timestamp has second precision; place the original
        # event before the cutoff and the new confirmation after it.
        source = session.scalar(select(TrainingAiMessage).where(TrainingAiMessage.role == "user"))
        source.created_at = datetime.now(UTC) - timedelta(seconds=3)
        client.memory_event_after = datetime.now(UTC) - timedelta(seconds=1)
    else:
        source = session.scalar(select(TrainingAiMessage).where(TrainingAiMessage.role == "user"))
        source.created_at = datetime.now(UTC) - timedelta(days=31)
    session.commit()
    agent.action = "confirm"
    submit(service, session, "Pode atualizar, confirmo.")
    session.refresh(record)
    assert record.has_limitations_or_complaints is True


def test_health_and_reply_roll_back_together_on_finalization_failure(
    database_session, rollout, monkeypatch
):
    session = database_session
    client, agent, service = setup(session)
    submit(service, session, REPORT)
    agent.action = "confirm"

    def fail(*args, **kwargs):
        raise MemoryError("memory_conflict")

    monkeypatch.setattr(MemoryService, "apply", fail)
    with pytest.raises(AssistantError):
        submit(service, session, "Pode atualizar, confirmo.")
    record = session.scalar(select(Onboarding).where(Onboarding.client_id == client.id))
    assert record.has_limitations_or_complaints is True
    assert not session.scalars(
        select(OnboardingAuditEvent).where(OnboardingAuditEvent.action == "health_report_resolved")
    ).all()


def test_generic_mobility_answer_cannot_clear_specific_pain(database_session, rollout):
    session = database_session
    client, agent, service = setup(session)
    result = submit(service, session, "Não tenho limitações.")
    assert "pending_health_update" not in result.messages[-1].clarification
    agent.action = "confirm"
    submit(service, session, "Sim.")
    assert session.scalar(
        select(Onboarding).where(Onboarding.client_id == client.id)
    ).has_limitations_or_complaints


def test_confirmed_correction_has_distinct_audit_kind(database_session, rollout):
    session = database_session
    client, agent, service = setup(session)
    agent.kind = "corrected"
    submit(service, session, "O registro de dor no joelho estava errado, nunca tive essa dor.")
    agent.action = "confirm"
    submit(service, session, "Pode fazer essa alteração do jeito que você descreveu.")
    assert (
        session.scalar(
            select(OnboardingAuditEvent).where(
                OnboardingAuditEvent.client_id == client.id,
                OnboardingAuditEvent.action == "health_report_corrected",
            )
        )
        is not None
    )


def test_foreign_source_cannot_authorize_health_update(database_session, rollout):
    from test_training_chat import create_client

    session = database_session
    client, agent, service = setup(session)
    submit(service, session, REPORT)
    other = create_client(session, "other", "other@example.test")
    complete_onboarding(session, "other")
    TrainingChatService(Agent()).submit_for_subject(
        session, "other", message=REPORT, client_request_id=uuid4()
    )
    events = session.scalars(select(TrainingAiMessage).order_by(TrainingAiMessage.created_at)).all()
    own_reply = next(event for event in events if event.clarification)
    other_source = next(
        event
        for event in events
        if event.role == "user" and event.conversation_id != own_reply.conversation_id
    )
    metadata = dict(own_reply.clarification)
    metadata["pending_health_update"] = {
        **metadata["pending_health_update"],
        "source_event_id": str(other_source.id),
    }
    own_reply.clarification = metadata
    session.commit()
    session.expire_all()
    agent.action = "confirm"
    submit(service, session, "Confirmo.")
    for id_ in [client.id, other.id]:
        assert session.scalar(
            select(Onboarding).where(Onboarding.client_id == id_)
        ).has_limitations_or_complaints


def test_confirmation_resumes_pending_draft_with_updated_health(database_session, rollout):
    from test_draft_clarifications import REQUEST, setup_edit
    from test_training_lifecycle import data

    session = database_session
    draft, _, service = setup_edit(session, rollout)
    complete_onboarding(session, "owner")
    submit(service, session, REQUEST)

    class EditingHealthAgent(HealthAgent):
        def structured(self, context, instructions, schema, type_, *, role):
            output = super().structured(context, instructions, schema, type_, role=role)
            if role == "orchestrator" and "allowed_specialist" in context:
                output.draft_followup_action = "resume"
                output.plan_action = "edit_draft"
                output.needs_references = True
                output.query = "subir escadas"
            if role == "training_chat":
                assert (
                    context["authoritative_health_records"]["has_limitations_or_complaints"]
                    is False
                )
                output.result.draft_update = data("Subir escadas").model_dump(mode="json")
            return output

    agent = EditingHealthAgent()
    agent.citations = ["R1"]
    service = TrainingChatService(agent)
    result = submit(service, session, REPORT)
    assert "pending_draft_edit" in result.messages[-1].clarification
    assert draft.revision == 1
    agent.action = "confirm"
    result = submit(service, session, "Pode atualizar meu cadastro, confirmo.")
    assert draft.revision == 2 and draft.status == "proposal"
    assert "Atualizei seu cadastro de saúde" in result.messages[-1].content
    assert "Atualizei o rascunho" in result.messages[-1].content
    review = [context for _, context, _ in agent.calls if "cited_passages" in context][-1]
    assert (
        review["client_constraints"]["authoritative_health_records"][
            "has_limitations_or_complaints"
        ]
        is False
    )


def test_health_update_preserves_approved_plan(database_session, rollout):
    from test_training_chat import create_current_plan

    from app.modules.training.models import TrainingPlanVersion

    session = database_session
    client, agent, service = setup(session)
    create_current_plan(session, client)
    query = select(
        TrainingPlanVersion.id, TrainingPlanVersion.revision, TrainingPlanVersion.status
    ).where(TrainingPlanVersion.client_id == client.id)
    before = session.execute(query).all()
    submit(service, session, REPORT)
    agent.action = "confirm"
    submit(service, session, "Pode fazer a alteração descrita.")
    assert before == session.execute(query).all()


def test_invented_proposal_evidence_cannot_be_saved(database_session, rollout):
    session = database_session
    client, agent, service = setup(session)
    original = agent.structured

    def forged(*args, **kwargs):
        output = original(*args, **kwargs)
        if kwargs["role"] == "orchestrator":
            output.health_update.quote = "Eu não tenho mais nenhuma dor."
        return output

    agent.structured = forged
    with pytest.raises(AssistantError, match="health_update_invalid"):
        submit(service, session, "Gostaria de conversar sobre minha dor no joelho.")
    record = session.scalar(select(Onboarding).where(Onboarding.client_id == client.id))
    assert record.has_limitations_or_complaints


def test_health_confirmation_does_not_truncate_other_complaints(database_session, rollout):
    session = database_session
    client, agent, service = setup(session)
    record = session.scalar(select(Onboarding).where(Onboarding.client_id == client.id))
    record.limitations_or_complaints = "Dor no joelho. " + "Outra queixa relatada. " * 50
    session.commit()
    previous = record.limitations_or_complaints
    agent.present, agent.details = True, "Outra queixa relatada. " * 50
    result = submit(service, session, REPORT)
    assert previous in result.messages[-1].content
    assert agent.details.strip() in result.messages[-1].content
    assert record.limitations_or_complaints == previous


def test_health_confirmation_resumes_requested_initial_plan(database_session, rollout):
    from test_plan_evidence import passage

    from app.modules.training.generation_service import InitialTrainingGenerationService
    from app.modules.training.models import TrainingPlanVersion

    session = database_session
    client, _, _ = setup(session)
    rollout.passages = [passage("Synthetic supported prescription")]

    class InitialHealthAgent(HealthAgent):
        def structured(self, context, instructions, schema, type_, *, role):
            output = super().structured(context, instructions, schema, type_, role=role)
            if role == "orchestrator" and "allowed_specialist" in context:
                output.query = "atividade física adultos"
                if context["allowed_specialist"] == "initial_plan":
                    output.followup_action = "resume"
                else:
                    output.plan_action = "generate_initial_plan"
            return output

    agent = InitialHealthAgent()
    agent.citations = ["R1"]
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    first = submit(service, session, "Gere meu treino. Não tenho mais dor no joelho.")
    assert "pending_health_update" in first.messages[-1].clarification
    assert first.messages[-1].clarification["initial_plan_requested"] is True
    agent.action = "confirm"
    result = submit(service, session, "Pode fazer a alteração descrita.")
    assert "Criei seu rascunho" in result.messages[-1].content
    assert "Atualizei seu cadastro" in result.messages[-1].content
    assert (
        session.scalar(
            select(TrainingPlanVersion).where(TrainingPlanVersion.client_id == client.id)
        ).status
        == "proposal"
    )
    assert (
        session.scalar(
            select(Onboarding).where(Onboarding.client_id == client.id)
        ).has_limitations_or_complaints
        is False
    )
