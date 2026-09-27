"""Concurrent interview turns must preserve verified state and request idempotency."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_onboarding_conversations import CurrentMessageProvider, scope_for
from test_training_review_postgres import sessions as sessions

from app.modules.onboarding.conversation_service import OnboardingConversationService
from app.modules.onboarding.models import OnboardingAiMessage

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


@pytest.mark.parametrize("duplicate", [False, True])
def test_parallel_turns_keep_both_facts_without_duplicate_replies(sessions, duplicate):
    with sessions() as session:
        drafts, scope = scope_for(session)
    ready = Barrier(2)
    request = uuid4()

    def send(index):
        with sessions() as session:
            field, message, value = (
                ("height_cm", "Tenho 180 cm", 180)
                if duplicate or index == 0
                else ("weight_kg", "Peso 80 kg", 80)
            )
            provider = CurrentMessageProvider([], [{field: value}])
            service = OnboardingConversationService(provider, drafts)
            ready.wait(timeout=10)
            service.submit(
                session, scope, message=message, client_request_id=request if duplicate else uuid4()
            )
            return len(provider.extraction_contexts)

    with ThreadPoolExecutor(max_workers=2) as pool:
        calls = list(pool.map(send, range(2)))
    with sessions() as session:
        state = OnboardingConversationService(CurrentMessageProvider([], []), drafts).state(
            session, scope
        )
        assert state.known_answers.height_cm == 180
        assert state.known_answers.weight_kg == (None if duplicate else 80)
        assert len(session.scalars(select(OnboardingAiMessage)).all()) == (2 if duplicate else 4)
        assert sum(calls) == (1 if duplicate else 2)
