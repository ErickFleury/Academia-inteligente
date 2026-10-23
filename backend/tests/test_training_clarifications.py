"""Clarification is a retained answer, never an unsupported plan or failed chat."""

import json
from uuid import uuid4

from sqlalchemy import select
from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_plan_evidence import passage
from test_training_chat import complete_onboarding, create_client

from app.modules.assistant.runtime import Clarification
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.generation_service import InitialTrainingGenerationService
from app.modules.training.models import TrainingAiMessage, TrainingPlanVersion
from app.modules.training.router import training_chat_response

DETAIL = {
    "reason": "missing_client_information",
    "explanation": "Preciso confirmar sua faixa etária para verificar a aplicação das referências.",
    "next_step": "Qual é sua idade?",
}


class ClarifyingAgent(Agent):
    def structured(self, context, instructions, schema, type_, *, role):
        if role == "initial_plan":
            self.calls.append((role, context, instructions))
            self.schemas.append(schema)
            return type_.model_validate(
                {
                    "result": None,
                    "citation_ids": [],
                    "grounding": "clarification",
                    "clarification": DETAIL,
                }
            )
        return super().structured(context, instructions, schema, type_, role=role)


def setup_chat(session, references):
    owner(session)
    complete_onboarding(session, "owner")
    create_client(session, "other", "other@example.test")
    references.passages = [passage("Orientações para adultos; faixa etária necessária.")]
    agent = ClarifyingAgent(route={"query": "prescrição treinamento adultos"})
    return TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    ), agent


def test_plan_clarification_is_saved_refreshable_private_and_idempotent(database_session, rollout):
    service, agent = setup_chat(database_session, rollout)
    request_id = uuid4()
    state = service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=request_id
    )
    assert state.pending_request is None
    reply = state.messages[-1]
    assert reply.role == "assistant"
    assert DETAIL["explanation"] in reply.content and DETAIL["next_step"] in reply.content
    assert reply.clarification == {**DETAIL, "stage": "specialist"}
    assert not reply.reference_citations and not reply.adaptation_suggested
    assert training_chat_response(state).messages[-1].clarification == reply.clarification
    assert database_session.scalar(select(TrainingPlanVersion)) is None
    calls = len(agent.calls)
    database_session.expire_all()
    assert service.state_for_subject(database_session, "owner") == state
    assert (
        service.submit_for_subject(
            database_session, "owner", message="ignored retry", client_request_id=request_id
        )
        == state
    )
    assert len(agent.calls) == calls
    assert service.state_for_subject(database_session, "other").messages == []
    assert len(database_session.scalars(select(TrainingAiMessage)).all()) == 2


def test_answer_to_clarification_can_continue_and_informs_next_explicit_plan_request(
    database_session, rollout
):
    service, agent = setup_chat(database_session, rollout)
    service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    state = service.submit_for_subject(
        database_session, "owner", message="Tenho 35 anos.", client_request_id=uuid4()
    )
    assert state.pending_request is None
    assert len(state.messages) == 4
    assert DETAIL["next_step"] in json.dumps(agent.calls[-1][1], ensure_ascii=False)
    service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    plan_context = next(
        context for role, context, _ in reversed(agent.calls) if role == "initial_plan"
    )
    assert any(m["content"] == "Tenho 35 anos." for m in plan_context["recent_messages"])
    assert database_session.scalar(select(TrainingPlanVersion)) is None


def test_empty_retrieval_returns_explanation_instead_of_failed_request(database_session, rollout):
    service, agent = setup_chat(database_session, rollout)
    rollout.passages = []
    state = service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    assert state.pending_request is None
    assert state.messages[-1].clarification["reason"] == "insufficient_evidence"
    assert state.messages[-1].clarification["stage"] == "retrieval"
    assert "busca" in state.messages[-1].content
    assert "instrutor" in state.messages[-1].content
    assert len(agent.calls) == 1


def test_router_preserves_specific_question_without_generating_or_retrieving(
    database_session, rollout
):
    service, agent = setup_chat(database_session, rollout)
    agent.route = {"specialist": "clarify", "clarification_detail": DETAIL}
    state = service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    assert state.messages[-1].clarification == {**DETAIL, "stage": "router"}
    assert len(agent.calls) == 1 and rollout.queries == []


def test_review_explanation_replaces_rejected_prescription(database_session, rollout):
    service, agent = setup_chat(database_session, rollout)
    original = Agent.structured
    detail = {
        "reason": "conflicting_evidence",
        "explanation": "Os trechos divergem sobre o intervalo de descanso para esta proposta.",
        "next_step": "Consulte o instrutor para definir qual orientação se aplica ao seu caso.",
    }

    def review(context, instructions, schema, type_, *, role):
        result = original(agent, context, instructions, schema, type_, role=role)
        if "cited_passages" in context:
            result.relevant_conflict = True
            result.clarification = Clarification.model_validate(detail)
        return result

    agent.structured = review
    agent.citations = ["R1"]
    state = service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    assert state.messages[-1].clarification == {**detail, "stage": "review"}
    assert "Agachamento" not in state.messages[-1].content
    assert database_session.scalar(select(TrainingPlanVersion)) is None


def test_clarification_logs_category_without_private_explanation(
    database_session, rollout, caplog, monkeypatch
):
    import logging

    # Alembic's migration test configures logging and disables existing loggers.
    monkeypatch.setattr(logging.getLogger("uvicorn.error.ai"), "disabled", False)
    caplog.set_level(logging.INFO, logger="uvicorn.error.ai")
    service, _ = setup_chat(database_session, rollout)
    service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    events = [json.loads(r.message) for r in caplog.records if r.name == "uvicorn.error.ai"]
    assert events[-1]["outcome"] == "clarification"
    assert events[-1]["reason"] == "missing_client_information"
    assert DETAIL["explanation"] not in caplog.text
    assert DETAIL["next_step"] not in caplog.text
    assert "owner@example.test" not in caplog.text


def test_retention_deletes_clarification_with_the_chat_message(database_session, rollout):
    from datetime import UTC, datetime, timedelta

    service, _ = setup_chat(database_session, rollout)
    service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    service.purge_expired_content(database_session, now=datetime.now(UTC) + timedelta(days=31))
    assert database_session.scalar(select(TrainingAiMessage)) is None


def test_non_chat_api_preserves_specific_clarification_payload():
    import asyncio

    from app.main import create_app
    from app.modules.assistant.runtime import AssistantError

    error = AssistantError(
        "assistant_clarification_required", 422, clarification={**DETAIL, "stage": "specialist"}
    )
    handler = create_app().exception_handlers[AssistantError]
    response = asyncio.run(handler(None, error))
    assert response.status_code == 422
    assert json.loads(response.body) == {"detail": error.code, "clarification": error.clarification}


def test_clarification_does_not_apply_proposed_memory_changes(database_session):
    from test_assistant_runtime import report

    from app.modules.memory.models import ClientMemoryFact

    class Uncertain(Agent):
        def structured(self, *args, **kwargs):
            result = super().structured(*args, **kwargs)
            if kwargs["role"] == "training_chat":
                result.grounding = "clarification"
                result.clarification = Clarification.model_validate(DETAIL)
            return result

    owner(database_session)
    service = TrainingChatService(Uncertain(changes=[report()]))
    state = service.submit_for_subject(
        database_session, "owner", message=report()["text"], client_request_id=uuid4()
    )
    assert state.pending_request is None
    assert state.messages[-1].clarification is not None
    assert database_session.scalar(select(ClientMemoryFact)) is None
