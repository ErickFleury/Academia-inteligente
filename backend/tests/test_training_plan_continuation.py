"""An explicit initial-plan request can collect answers without renewed consent."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_plan_evidence import passage
from test_training_chat import complete_onboarding, create_client

from app.integrations.ai_budget import current_budget
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.generation_service import InitialTrainingGenerationService
from app.modules.training.models import TrainingPlanVersion


class CollectingAgent(Agent):
    def __init__(self):
        super().__init__(route={"query": "prescrição exercícios séries repetições"})
        self.citations = ["R1"]
        self.answer_received = False
        self.followup_action = "resume"
        self.plan_calls = 0

    def structured(self, context, instructions, schema, type_, *, role):
        if role == "orchestrator" and "allowed_specialist" in context:
            self.route = {"query": "prescrição exercícios séries repetições"}
            if context.get("resume_initial_plan"):
                self.route["followup_action"] = self.followup_action
        result = super().structured(context, instructions, schema, type_, role=role)
        if role == "initial_plan":
            self.plan_calls += 1
            assert current_budget.get().plan
            if not self.answer_received:
                return type_.model_validate(
                    {
                        "result": None,
                        "citation_ids": [],
                        "grounding": "clarification",
                        "clarification": {
                            "reason": "missing_client_information",
                            "explanation": "",
                            "missing_fields": ["age", "weekly_availability"],
                            "next_step": "Me diga:\n- Qual é sua idade?\n"
                            "- Quantos dias por semana pode treinar?",
                        },
                    }
                )
        return result


def setup(session, references):
    owner(session)
    complete_onboarding(session, "owner")
    references.passages = [passage("Synthetic supported plan fixture.")]
    agent = CollectingAgent()
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    return service, agent


def send(session, service, message, request_id=None, subject="owner"):
    return service.submit_for_subject(
        session, subject, message=message, client_request_id=request_id or uuid4()
    )


def test_all_questions_are_saved_together_and_final_answer_generates_without_confirmation(
    database_session, rollout
):
    service, agent = setup(database_session, rollout)
    first = send(database_session, service, "Gere meu treino")
    assert (
        first.messages[-1].content
        == "- Qual é sua idade?\n- Quantos dias por semana você pode treinar?"
    )
    database_session.expire_all()  # Reload must not lose the original request's continuation.
    agent.answer_received = True
    request_id = uuid4()
    result = send(
        database_session, service, "Tenho 35 anos e posso treinar três dias por semana.", request_id
    )
    assert "Criei seu rascunho" in result.messages[-1].content
    assert "?" not in result.messages[-1].content
    plans = database_session.scalars(select(TrainingPlanVersion)).all()
    assert len(plans) == 1 and plans[0].status == "proposal"
    assert agent.plan_calls == 2
    assert send(database_session, service, "Ignored retry", request_id) == result
    assert agent.plan_calls == 2
    context = next(c for role, c, _ in reversed(agent.calls) if role == "initial_plan")
    assert context["resume_initial_plan"] is True
    assert context["current_user_message"].startswith("Tenho 35 anos")
    assert context["completed_onboarding"]["limitations_or_complaints"] == "Joelho sensível"


def test_partial_answer_keeps_request_pending_without_creating_an_unsupported_plan(
    database_session, rollout
):
    service, agent = setup(database_session, rollout)
    send(database_session, service, "Gere meu treino")
    state = send(database_session, service, "Tenho 35 anos.")
    assert state.messages[-1].content == "Quantos dias por semana você pode treinar?"
    assert state.messages[-1].clarification["initial_plan_requested"] is True
    assert database_session.scalar(select(TrainingPlanVersion)) is None
    assert agent.plan_calls == 2


@pytest.mark.parametrize(
    "action,message",
    [
        ("cancel", "Prefiro deixar esse plano para outra hora."),
        ("chat", "O que significa hipertrofia?"),
    ],
)
def test_cancellation_or_topic_change_does_not_generate(database_session, rollout, action, message):
    service, agent = setup(database_session, rollout)
    send(database_session, service, "Gere meu treino")
    agent.answer_received = True
    agent.followup_action = action
    result = send(database_session, service, message)
    assert result.pending_request is None
    assert agent.plan_calls == 1
    assert database_session.scalar(select(TrainingPlanVersion)) is None
    assert result.messages[-1].clarification is None
    # The next answer cannot revive the earlier request after cancellation/topic change.
    send(database_session, service, "Tenho 35 anos.")
    assert agent.plan_calls == 1


def test_explicit_cancellation_is_enforced_even_if_router_would_resume(database_session, rollout):
    service, agent = setup(database_session, rollout)
    send(database_session, service, "Gere meu treino")
    calls = len(agent.calls)
    result = send(database_session, service, "Cancele meu plano")
    assert "cancelei" in result.messages[-1].content
    assert len(agent.calls) == calls
    assert database_session.scalar(select(TrainingPlanVersion)) is None


def test_unrequested_or_other_client_answer_cannot_generate(database_session, rollout):
    service, agent = setup(database_session, rollout)
    send(database_session, service, "Tenho 35 anos.")
    assert agent.plan_calls == 0
    send(database_session, service, "Gere meu treino")
    create_client(database_session, "other", "other@example.test")
    complete_onboarding(database_session, "other")
    agent.answer_received = True
    send(database_session, service, "Tenho 35 anos.", subject="other")
    assert agent.plan_calls == 1
    assert database_session.scalar(select(TrainingPlanVersion)) is None


def test_evidence_gap_does_not_authorize_automatic_generation_on_a_new_message(
    database_session, rollout
):
    service, agent = setup(database_session, rollout)
    rollout.passages = []
    first = send(database_session, service, "Gere meu treino")
    assert first.messages[-1].clarification["reason"] == "insufficient_evidence"
    agent.answer_received = True
    rollout.passages = [passage("Synthetic reference")]
    send(database_session, service, "Tenho 35 anos.")
    assert agent.plan_calls == 0
    assert database_session.scalar(select(TrainingPlanVersion)) is None


def test_negative_preference_is_an_answer_not_a_cancellation(database_session, rollout):
    service, agent = setup(database_session, rollout)
    send(database_session, service, "Gere meu treino")
    agent.answer_received = True
    result = send(database_session, service, "Não quero treinar três dias, só dois. Tenho 35 anos.")
    assert "Criei seu rascunho" in result.messages[-1].content
    assert agent.plan_calls == 2
