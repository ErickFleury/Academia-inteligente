"""Health revision transactions against an isolated PostgreSQL database."""

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from test_assistant_runtime import rollout as rollout
from test_health_corrections import REPORT, HealthAgent, setup, submit
from test_health_corrections import (
    test_health_report_requires_confirmation_then_survives_reload as verify_reload,
)
from test_training_review_postgres import sessions as sessions

from app.modules.assistant.runtime import AssistantError
from app.modules.onboarding.models import Onboarding
from app.modules.training.chat_service import TrainingChatService

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


def test_confirmed_health_update_reload_and_retry(sessions, rollout):
    with sessions() as session:
        verify_reload(session, rollout)


def test_concurrent_health_change_invalidates_confirmation(sessions, rollout):
    with sessions() as session:
        client, _, service = setup(session)
        client_id = client.id
        submit(service, session, REPORT)

    class ConcurrentAgent(HealthAgent):
        action = "confirm"

        def structured(self, *args, **kwargs):
            result = super().structured(*args, **kwargs)
            with sessions() as other:
                record = other.scalar(select(Onboarding).where(Onboarding.client_id == client_id))
                record.limitations_or_complaints = "Outra queixa atualizada"
                record.updated_at = datetime.now(UTC)
                other.commit()
            return result

    with sessions() as session:
        with pytest.raises(AssistantError, match="assistant_state_conflict"):
            submit(TrainingChatService(ConcurrentAgent()), session, "Confirmo a alteração.")
    with sessions() as session:
        record = session.scalar(select(Onboarding).where(Onboarding.client_id == client_id))
        assert record.has_limitations_or_complaints is True
        assert record.limitations_or_complaints == "Outra queixa atualizada"
