"""Refresh and retries observe durable chat progress without repeating inference."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import select, update
from test_assistant_postgres import plan_chat as plan_chat
from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_knowledge_postgres import postgres_sessions as postgres_sessions
from test_knowledge_postgres import pytestmark as pytestmark
from test_training_chat import create_client

from app.modules.assistant.runtime import AssistantError
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.models import TrainingAiMessage
from app.modules.training.service import ConcurrentTrainingUpdateError


@pytest.mark.parametrize("plan", [False, True])
def test_refresh_during_inference_recovers_message_and_processing_status(
    postgres_sessions, plan_chat, plan
):
    service, agent = plan_chat if plan else (TrainingChatService(), Agent())
    if not plan:
        service = TrainingChatService(agent)
    with postgres_sessions() as session:
        create_client(session, "other", "other@example.test")
    entered, resume = Event(), Event()

    def hold():
        entered.set()
        assert resume.wait(8)

    agent.hook = hold
    request_id = uuid4()
    message = "Quero criar um novo treino" if plan else "Olá"

    def send():
        with postgres_sessions() as session:
            return service.submit_for_subject(
                session, "owner", message=message, client_request_id=request_id
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(send)
        assert entered.wait(5)
        try:
            with postgres_sessions() as refresh:
                state = service.state_for_subject(refresh, "owner")
                assert state.messages[-1].content == message
                assert state.pending_request.status == "processing"
                assert state.pending_request.client_request_id == request_id
                refresh.rollback()
                other = service.state_for_subject(refresh, "other")
                assert other.messages == [] and other.pending_request is None
            with postgres_sessions() as retry:
                state = service.submit_for_subject(
                    retry, "owner", message=message, client_request_id=request_id
                )
                assert state.pending_request.status == "processing"
        finally:
            resume.set()
        assert task.result(timeout=5).pending_request is None
    with postgres_sessions() as refresh:
        state = service.state_for_subject(refresh, "owner")
        assert len(state.messages) == 2 and state.pending_request is None
    assert [call[0] for call in agent.calls].count("initial_plan" if plan else "training_chat") == 1


@pytest.mark.parametrize("failure", ["provider", "deadline", "unexpected"])
def test_refresh_after_failure_recovers_retry_with_original_uuid(postgres_sessions, failure):
    with postgres_sessions() as session:
        owner(session)
    agent = Agent()
    agent.fail = failure == "provider"

    def fail():
        if failure == "deadline":
            raise AssistantError("deadline_exceeded")
        if failure == "unexpected":
            raise RuntimeError("private provider detail must not be persisted")

    agent.hook = fail
    service = TrainingChatService(agent)
    request_id = uuid4()
    with postgres_sessions() as session:
        with pytest.raises(RuntimeError if failure == "unexpected" else AssistantError):
            service.submit_for_subject(
                session, "owner", message="Olá", client_request_id=request_id
            )
    with postgres_sessions() as refresh:
        state = service.state_for_subject(refresh, "owner")
        assert len(state.messages) == 1
        assert state.pending_request.status == "failed"
        assert state.pending_request.client_request_id == request_id
        assert state.pending_request.failure_code == (
            "deadline_exceeded" if failure == "deadline" else "processing_failed"
        )
    agent.fail = False
    agent.hook = None
    with postgres_sessions() as session:
        service.submit_for_subject(
            session, "owner", message="Ignored retry", client_request_id=request_id
        )
    with postgres_sessions() as refresh:
        assert len(refresh.scalars(select(TrainingAiMessage)).all()) == 2
        assert service.state_for_subject(refresh, "owner").pending_request is None


@pytest.mark.parametrize("clarification", [False, True])
def test_expired_attempt_cannot_overwrite_a_retried_request(postgres_sessions, clarification):
    with postgres_sessions() as session:
        owner(session)
    entered, resume = Event(), Event()
    agent = Agent()
    if clarification:
        from app.modules.assistant.runtime import Clarification

        original = agent.structured

        def clarify(*args, **kwargs):
            result = original(*args, **kwargs)
            if kwargs["role"] == "training_chat":
                result.grounding = "clarification"
                result.clarification = Clarification(
                    reason="missing_client_information",
                    explanation="Preciso esclarecer seu pedido.",
                    next_step="Qual exercício você quer discutir?",
                )
            return result

        agent.structured = clarify

    def hold():
        entered.set()
        assert resume.wait(8)

    agent.hook = hold
    service = TrainingChatService(agent)
    request_id = uuid4()

    def send():
        with postgres_sessions() as session:
            return service.submit_for_subject(
                session, "owner", message="Olá", client_request_id=request_id
            )

    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(send)
        assert entered.wait(5)
        try:
            with postgres_sessions() as session:
                session.execute(
                    update(TrainingAiMessage)
                    .where(TrainingAiMessage.client_request_id == request_id)
                    .values(processing_expires_at=datetime.now(UTC) - timedelta(seconds=1))
                )
                session.commit()
                state = service.state_for_subject(session, "owner")
                assert state.pending_request.status == "failed"
                assert state.pending_request.failure_code == "deadline_exceeded"
            with postgres_sessions() as session:
                TrainingChatService(Agent()).submit_for_subject(
                    session, "owner", message="Ignored retry", client_request_id=request_id
                )
        finally:
            resume.set()
        with pytest.raises((AssistantError, ConcurrentTrainingUpdateError)):
            task.result(timeout=5)
    with postgres_sessions() as session:
        state = service.state_for_subject(session, "owner")
        assert len(state.messages) == 2 and state.pending_request is None


def test_plan_clarification_survives_a_new_database_session(postgres_sessions, rollout):
    from test_training_clarifications import DETAIL, setup_chat

    with postgres_sessions() as session:
        service, agent = setup_chat(session, rollout)
    request_id = uuid4()
    with postgres_sessions() as session:
        state = service.submit_for_subject(
            session, "owner", message="Gere meu treino", client_request_id=request_id
        )
    with postgres_sessions() as session:
        assert service.state_for_subject(session, "owner") == state
        assert state.messages[-1].clarification == {
            **DETAIL,
            "stage": "specialist",
            "initial_plan_requested": True,
        }
        assert (
            service.submit_for_subject(
                session, "owner", message="ignored retry", client_request_id=request_id
            )
            == state
        )
        assert service.state_for_subject(session, "other").messages == []
    assert len(agent.calls) == 2
