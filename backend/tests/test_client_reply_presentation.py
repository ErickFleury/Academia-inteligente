"""Client wording hides retrieval mechanics while retaining evidence enforcement."""

from uuid import uuid4

import pytest
from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session

from app.modules.assistant.presentation import client_message
from app.modules.training.chat_service import TrainingChatService


@pytest.mark.parametrize(
    "text",
    [
        "O trecho recuperado menciona subir escadas, mas não sustenta 25 minutos.",
        "As referências não trazem os parâmetros necessários.",
        "Segundo o guia, você pode treinar assim.",
    ],
)
def test_source_process_text_has_plain_language_fallback(text):
    result = client_message(text)
    assert "instrutor" in result
    assert "trecho" not in result
    assert "25 minutos" not in result


def test_evidence_failure_is_still_blocked_without_source_chatter(database_session, rollout):
    owner(database_session)
    agent = Agent(route={"needs_references": True, "query": "subir escadas duração"})
    result = TrainingChatService(agent).submit_for_subject(
        database_session,
        "owner",
        message="Quanto tempo posso subir escadas?",
        client_request_id=uuid4(),
    )
    reply = result.messages[-1]
    assert reply.clarification["reason"] == "insufficient_evidence"
    assert "instrutor" in reply.content
    assert "trecho" not in reply.content
    assert not any(role == "training_chat" for role, _, _ in agent.calls)
