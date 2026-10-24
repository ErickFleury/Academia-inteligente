"""A new-plan request rebuilds the sole proposal through grounded generation."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_plan_evidence import passage
from test_training_chat import complete_onboarding
from test_training_lifecycle import data

from app.integrations.ai_budget import current_budget
from app.modules.assistant.runtime import AssistantError
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.service import TrainingLifecycleService


class Rebuilder(Agent):
    followup = "resume"
    ask = False
    health_action = None

    def structured(self, context, instructions, schema, type_, *, role):
        if not hasattr(self, "budgets"):
            self.budgets = []
        self.budgets.append(current_budget.get())
        if role == "orchestrator" and "allowed_specialist" in context:
            if context["allowed_specialist"] == "training_chat":
                self.route = {"plan_action": "rebuild_draft"}
                if context.get("pending_draft_edit"):
                    self.route["draft_followup_action"] = self.followup
                if self.health_action:
                    self.route["health_update"] = {
                        "action": self.health_action,
                        "field": "has_limitations_or_complaints",
                        "kind": "resolved",
                        "present": False,
                        "details": None,
                        "quote": context["current_user_message"],
                    }
            else:
                self.route = {
                    "query": "atividade física adultos duração intensidade",
                    "needs_references": True,
                }
        result = super().structured(context, instructions, schema, type_, role=role)
        if role == "initial_plan" and self.ask:
            return type_.model_validate(
                {
                    "result": None,
                    "citation_ids": [],
                    "grounding": "clarification",
                    "clarification": {
                        "reason": "missing_client_information",
                        "explanation": "",
                        "next_step": "Responder",
                        "missing_fields": ["weekly_availability"],
                    },
                }
            )
        return result


def setup(session, rollout, *, current=False):
    client = owner(session)
    complete_onboarding(session, "owner")
    if current:
        from test_training_chat import create_current_plan

        create_current_plan(session, client)
    draft = TrainingLifecycleService().create_proposal(
        session, client_id=client.id, data=data("Rascunho anterior"), created_by="ai", origin="ai"
    )
    rollout.passages = [passage("Synthetic supported prescription")]
    agent = Rebuilder()
    agent.citations = ["R1"]
    return draft, agent, TrainingChatService(agent)


def submit(service, session, message, request_id=None):
    return service.submit_for_subject(
        session, "owner", message=message, client_request_id=request_id or uuid4()
    )


def test_new_plan_rebuilds_same_draft_and_replay_is_idempotent(database_session, rollout):
    session = database_session
    draft, agent, service = setup(session, rollout)
    submit(TrainingChatService(Agent()), session, "Quero trocar caminhada por escadas.")
    request_id = uuid4()
    result = submit(service, session, "então me faça um novo treino", request_id)
    assert "Refiz seu rascunho" in result.messages[-1].content
    assert draft.revision == 2 and draft.status == "proposal"
    assert session.scalars(select(TrainingPlanVersion)).all() == [draft]
    plan_context = next(context for role, context, _ in agent.calls if role == "initial_plan")
    assert plan_context["draft_rebuild_request"]["request"] == "então me faça um novo treino"
    assert "escadas" not in str(plan_context.get("recent_messages", []))
    assert "editable_training_draft" not in plan_context
    assert plan_context["completed_onboarding"]["limitations_or_complaints"] == "Joelho sensível"
    assert submit(service, session, "então me faça um novo treino", request_id) == result
    assert draft.revision == 2
    assert len(agent.calls) == 4
    assert all(budget is agent.budgets[0] for budget in agent.budgets)
    assert agent.budgets[0].plan is True


def test_confirmed_health_change_resumes_rebuild_with_updated_record(database_session, rollout):
    from test_health_corrections import REPORT

    from app.modules.onboarding.models import Onboarding

    session = database_session
    draft, agent, service = setup(session, rollout)
    agent.health_action = "propose"
    first = submit(service, session, "Refaça meu treino. " + REPORT)
    assert first.messages[-1].clarification["pending_draft_edit"]["operation"] == "rebuild_draft"
    assert draft.revision == 1
    agent.health_action = "confirm"
    result = submit(service, session, "Confirmo a alteração do cadastro.")
    assert "Refiz seu rascunho" in result.messages[-1].content
    plan_context = [context for role, context, _ in agent.calls if role == "initial_plan"][-1]
    assert plan_context["authoritative_health_records"]["has_limitations_or_complaints"] is False
    assert plan_context["completed_onboarding"]["limitations_or_complaints"] is None
    assert session.scalar(select(Onboarding)).has_limitations_or_complaints is False
    assert draft.revision == 2


def test_rebuild_keeps_personal_memory_but_not_old_exercise_target(database_session, rollout):
    from datetime import UTC, datetime

    from app.modules.memory.service import MemoryService

    session = database_session
    draft, agent, service = setup(session, rollout)
    event = uuid4()
    MemoryService().apply(
        session,
        draft.client_id,
        0,
        [],
        event_id=event,
        occurred_at=datetime.now(UTC),
        message="Tenho 19 anos. Subir escadas.",
        answers={
            "age": {
                "question": "Qual é sua idade?",
                "value": 19,
                "source_text": "Tenho 19 anos.",
                "source_event_id": str(event),
            },
            "target_exercise": {
                "question": "Qual exercício?",
                "value": "Subir escadas",
                "source_text": "Subir escadas.",
                "source_event_id": str(event),
            },
        },
    )
    session.commit()
    submit(service, session, "Refaça meu treino")
    context = next(context for role, context, _ in agent.calls if role == "initial_plan")
    assert context["client_answers"]["age"]["value"] == 19
    assert "target_exercise" not in context["client_answers"]
    assert "age" not in context["unanswered_client_fields"]
    assert "escadas" not in str(context["client_memory"])
    review = next(context for _, context, _ in agent.calls if "cited_passages" in context)
    assert "escadas" not in str(review["client_constraints"]["client_memory"])
    assert len(MemoryService.snapshot(session, draft.client_id)["facts"]) == 2


def test_rebuild_requires_completed_onboarding(database_session, rollout):
    from app.modules.onboarding.models import Onboarding

    session = database_session
    draft, agent, service = setup(session, rollout)
    session.scalar(select(Onboarding)).status = "draft"
    session.commit()
    with pytest.raises(AssistantError, match="onboarding_incomplete"):
        submit(service, session, "Refaça meu treino")
    assert draft.revision == 1


def test_rebuild_replaces_old_pending_edit_instead_of_resuming_it(database_session, rollout):
    from test_draft_clarifications import REQUEST, setup_edit

    session = database_session
    draft, editor, service = setup_edit(session, rollout)
    complete_onboarding(session, "owner")
    submit(service, session, REQUEST)
    agent = Rebuilder()
    agent.citations = ["R1"]
    agent.followup = "replace"
    submit(TrainingChatService(agent), session, "Então me faça um novo treino")
    context = next(context for role, context, _ in agent.calls if role == "initial_plan")
    assert context["draft_rebuild_request"]["request"] == "Então me faça um novo treino"
    assert context["pending_draft_edit"] is None
    assert draft.revision == 2


@pytest.mark.parametrize(
    "action,message", [("cancel", "Cancele esse pedido"), ("chat", "Qual é o horário da academia?")]
)
def test_cancel_and_topic_change_stop_rebuild(database_session, rollout, action, message):
    session = database_session
    draft, agent, service = setup(session, rollout)
    agent.ask = True
    submit(service, session, "Refaça meu treino")
    agent.calls.clear()
    agent.followup = action
    agent.citations = []
    result = submit(service, session, message)
    assert draft.revision == 1
    assert all(role != "initial_plan" for role, _, _ in agent.calls)
    assert result.messages[-1].clarification is None
    assert agent.budgets[-1].plan is False


@pytest.mark.parametrize("failure", ["references", "review", "provider"])
def test_unsuccessful_rebuild_preserves_draft(database_session, rollout, failure):
    session = database_session
    draft, agent, service = setup(session, rollout)
    if failure == "references":
        rollout.passages = []
    elif failure == "review":
        agent.review_supported = False
    else:
        agent.fail = True
    if failure == "provider":
        with pytest.raises(AssistantError):
            submit(service, session, "Refaça meu treino")
    else:
        result = submit(service, session, "Refaça meu treino")
        assert result.messages[-1].clarification is not None
        assert "Refiz" not in result.messages[-1].content
    session.refresh(draft)
    assert draft.revision == 1 and draft.name == "Rascunho anterior"


def test_rebuild_never_changes_current_plan(database_session, rollout):
    session = database_session
    draft, agent, service = setup(session, rollout, current=True)
    current = session.scalar(
        select(TrainingPlanVersion).where(TrainingPlanVersion.status == "current")
    )
    before = (current.name, current.objective, current.revision, current.status)
    submit(service, session, "Quero um novo treino")
    session.refresh(current)
    assert (current.name, current.objective, current.revision, current.status) == before
    assert draft.status == "proposal" and draft.revision == 2


def test_concurrent_revision_prevents_rebuild_save(database_session, rollout):
    session = database_session
    draft, agent, service = setup(session, rollout)

    def change_draft():
        draft.name = "Instructor change"
        draft.revision += 1
        session.commit()

    agent.hook = change_draft
    with pytest.raises(AssistantError, match="assistant_state_conflict"):
        submit(service, session, "Quero um novo treino")
    session.refresh(draft)
    assert draft.name == "Instructor change"


def test_rebuild_cannot_use_foreign_draft(database_session, rollout):
    from test_training_chat import create_client

    session = database_session
    draft, agent, service = setup(session, rollout)
    create_client(session, "other", "other@example.test")
    complete_onboarding(session, "other")
    with pytest.raises(AssistantError, match="request_not_authorized"):
        service.submit_for_subject(
            session, "other", message="Quero um novo treino", client_request_id=uuid4()
        )
    assert draft.revision == 1


def test_rebuild_resumes_after_personal_answer_and_reload(database_session, rollout):
    session = database_session
    draft, agent, service = setup(session, rollout)
    agent.ask = True
    first = submit(service, session, "Gere meu plano de treino")
    pending = first.messages[-1].clarification["pending_draft_edit"]
    assert pending["operation"] == "rebuild_draft"
    assert draft.revision == 1
    session.expire_all()
    agent.ask = False
    result = submit(service, session, "3")
    assert "Refiz seu rascunho" in result.messages[-1].content
    plan_context = [context for role, context, _ in agent.calls if role == "initial_plan"][-1]
    assert plan_context["client_answers"]["weekly_availability"]["value"] == 3
    assert plan_context["draft_rebuild_request"]["request"] == "Gere meu plano de treino"
    assert draft.revision == 2
