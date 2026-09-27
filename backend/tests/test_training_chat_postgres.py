"""Training chat requests serialize per client without repeating provider side effects."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_training_chat import FakeProvider, complete_onboarding, create_client
from test_training_chat_generation import service_for
from test_training_review_postgres import sessions as sessions

from app.integrations.ai import AiTrainingChatResponse
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.models import TrainingAiMessage, TrainingPlanVersion

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


@pytest.mark.parametrize("duplicate", [False, True])
def test_concurrent_turns_preserve_order_and_idempotency(sessions, duplicate):
    with sessions() as session:
        create_client(session, "ada", "ada@example.test")
    barrier = Barrier(2)
    request_id = uuid4()

    def send(index):
        with sessions() as session:
            provider = FakeProvider(AiTrainingChatResponse(assistant_message="Entendido."))
            barrier.wait(timeout=10)
            TrainingChatService(provider).submit_for_subject(
                session,
                "ada",
                message=f"Relato {index}",
                client_request_id=request_id if duplicate else uuid4(),
            )
            return provider.calls

    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = list(pool.map(send, range(2)))
    with sessions() as session:
        messages = session.scalars(
            select(TrainingAiMessage).order_by(TrainingAiMessage.sequence)
        ).all()
        assert len(messages) == (2 if duplicate else 4)
        assert [item.role for item in messages] == ["user", "assistant"] * (1 if duplicate else 2)
        assert sum(calls) == (1 if duplicate else 2)


@pytest.mark.parametrize("duplicate", [False, True])
def test_concurrent_initial_generation_creates_one_draft_and_commits_its_reply(sessions, duplicate):
    with sessions() as session:
        create_client(session, "ada", "ada@example.test")
        complete_onboarding(session, "ada")
    barrier = Barrier(2)
    request_id = uuid4()

    def send(index):
        service, _, provider = service_for()
        with sessions() as session:
            barrier.wait(timeout=10)
            service.submit_for_subject(
                session,
                "ada",
                message="Gere meu treino",
                client_request_id=request_id if duplicate else uuid4(),
            )
            return provider.calls

    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = list(pool.map(send, range(2)))
    with sessions() as session:
        versions = session.scalars(select(TrainingPlanVersion)).all()
        assert len(versions) == 1 and versions[0].status == "proposal"
        assert sum(calls) == 1
        messages = session.scalars(
            select(TrainingAiMessage).order_by(TrainingAiMessage.sequence)
        ).all()
        assert len(messages) == (2 if duplicate else 4)
        assert "Criei seu rascunho" in messages[1].content
        if not duplicate:
            assert "já está disponível" in messages[3].content
