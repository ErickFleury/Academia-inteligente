"""A retry can reuse an earlier own health report without treating retry as consent."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from test_assistant_runtime import Agent
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_health_corrections import REPORT, setup, submit

from app.modules.onboarding.health_updates import HealthUpdate, HealthUpdateError, proposal
from app.modules.onboarding.models import Onboarding
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.models import TrainingAiConversation, TrainingAiMessage


def test_retry_can_propose_health_correction_from_earlier_own_report(database_session, rollout):
    session = database_session
    client, agent, service = setup(session)
    submit(TrainingChatService(Agent()), session, REPORT)
    original = agent.structured

    def use_previous_report(*args, **kwargs):
        result = original(*args, **kwargs)
        if kwargs["role"] == "orchestrator" and result.health_update.action == "propose":
            result.health_update.quote = REPORT
        return result

    agent.structured = use_previous_report
    result = submit(service, session, "tente novamente")
    assert result.pending_request is None
    assert "pending_health_update" in result.messages[-1].clarification
    assert "Joelho sensível" in result.messages[-1].content
    assert (
        session.scalar(
            select(Onboarding).where(Onboarding.client_id == client.id)
        ).has_limitations_or_complaints
        is True
    )
    agent.action = "confirm"
    submit(service, session, "Pode salvar essa correção.")
    assert (
        session.scalar(
            select(Onboarding).where(Onboarding.client_id == client.id)
        ).has_limitations_or_complaints
        is False
    )


@pytest.mark.parametrize(
    "invalid", ["expired", "forgotten", "superseded", "foreign", "assistant", "unavailable"]
)
def test_retry_rejects_unusable_historical_health_report(database_session, rollout, invalid):
    from test_memory import client as new_client

    session = database_session
    client, _, _ = setup(session)
    service = TrainingChatService(Agent())
    submit(service, session, REPORT)
    submit(service, session, "tente novamente")
    original, current = session.scalars(
        select(TrainingAiMessage)
        .where(TrainingAiMessage.role == "user")
        .order_by(TrainingAiMessage.sequence)
    ).all()
    record = session.scalar(select(Onboarding).where(Onboarding.client_id == client.id))
    sources = [{"event_id": str(original.id)}]
    cutoff = None
    if invalid == "expired":
        original.created_at = datetime.now(UTC) - timedelta(days=31)
    elif invalid == "forgotten":
        cutoff = datetime.now(UTC)
    elif invalid == "superseded":
        record.updated_at = datetime.now(UTC) + timedelta(seconds=1)
    elif invalid == "foreign":
        conversation = TrainingAiConversation(client_id=new_client(session, "other"))
        session.add(conversation)
        session.flush()
        original.conversation_id = conversation.id
    elif invalid == "assistant":
        original.role = "assistant"
    elif invalid == "unavailable":
        sources = []
    session.flush()
    update = HealthUpdate(
        action="propose",
        field="has_limitations_or_complaints",
        kind="resolved",
        present=False,
        quote=REPORT,
    )
    with pytest.raises(HealthUpdateError):
        proposal(session, client.id, current, update, sources=sources, cutoff=cutoff)
    assert record.has_limitations_or_complaints is True


@pytest.mark.parametrize(
    "message, quote",
    [
        ("Não tenho dor no joelho.", "tenho dor no joelho."),
        ("Talvez não tenha dor no joelho.", "não tenha dor no joelho."),
    ],
)
def test_health_quote_cannot_drop_negation_or_uncertainty(
    database_session, rollout, message, quote
):
    session = database_session
    client, _, _ = setup(session)
    submit(TrainingChatService(Agent()), session, message)
    source = session.scalar(select(TrainingAiMessage).where(TrainingAiMessage.role == "user"))
    update = HealthUpdate(
        action="propose",
        field="has_limitations_or_complaints",
        kind="resolved",
        present=False,
        quote=quote,
    )
    with pytest.raises(HealthUpdateError):
        proposal(session, client.id, source, update)


def test_whole_message_qualification_survives_sentence_selection(database_session, rollout):
    session = database_session
    client, _, _ = setup(session)
    submit(TrainingChatService(Agent()), session, REPORT + " Mas ainda dói às vezes.")
    source = session.scalar(select(TrainingAiMessage).where(TrainingAiMessage.role == "user"))
    update = HealthUpdate(
        action="propose",
        field="has_limitations_or_complaints",
        kind="resolved",
        present=False,
        quote=REPORT,
    )
    assert proposal(session, client.id, source, update) is None


def test_inconsistent_proposal_asks_again_without_breaking_chat(database_session, rollout, caplog):
    import logging

    session = database_session
    client, agent, service = setup(session)
    agent.details = "Inconsistent synthetic detail while present is false"
    caplog.set_level(logging.INFO, logger="uvicorn.error.ai")
    result = submit(service, session, REPORT)
    assert result.pending_request is None
    assert "pending_health_update" not in result.messages[-1].clarification
    assert "Não alterei" in result.messages[-1].content
    assert (
        session.scalar(
            select(Onboarding).where(Onboarding.client_id == client.id)
        ).has_limitations_or_complaints
        is True
    )
    assert '"reason":"health_update_invalid"' in caplog.text
    assert REPORT not in caplog.text
    assert agent.details not in caplog.text
