"""Memory transaction and stale-session checks using disposable PostgreSQL schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from test_knowledge_postgres import postgres_sessions as postgres_sessions
from test_knowledge_postgres import pytestmark as pytestmark
from test_memory import add, client

from app.modules.memory.service import MemoryChange, MemoryError, MemoryService

service = MemoryService()


def test_memory_changes_roll_back_with_failed_conversational_reply(postgres_sessions):
    with postgres_sessions() as session:
        owner = client(session)
        service.apply(
            session,
            owner,
            0,
            [
                MemoryChange(
                    action="add",
                    category="health_report",
                    text="Tenho dor no joelho.",
                    evidence="Tenho dor no joelho.",
                )
            ],
            event_id=uuid4(),
            occurred_at=datetime.now(UTC),
            message="Tenho dor no joelho.",
        )
        session.rollback()  # Simulate a failed required specialist / reply commit.
    with postgres_sessions() as session:
        state = service.snapshot(session, owner)
        assert state["facts"] == []
        assert state["revision"] == 0


def test_direct_correction_invalidates_inflight_proposal(postgres_sessions):
    with postgres_sessions() as session:
        owner = client(session)
        initial = add(session, owner)
    with postgres_sessions() as inflight:
        old = service.snapshot(inflight, owner)
        with postgres_sessions() as direct:
            service.edit(
                direct,
                owner,
                initial["facts"][0]["id"],
                initial["revision"],
                "Prefiro treinar à noite.",
            )
        with pytest.raises(MemoryError, match="memory_conflict"):
            service.apply(
                inflight,
                owner,
                old["revision"],
                [],
                event_id=uuid4(),
                occurred_at=datetime.now(UTC),
                message="Olá",
            )
        inflight.rollback()
        assert service.snapshot(inflight, owner)["facts"][0]["text"] == "Prefiro treinar à noite."
