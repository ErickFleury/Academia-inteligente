"""Structured answers read as client statements, without repeating the question."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from test_clients import database_session as database_session
from test_memory import client

from app.modules.memory.models import ClientMemoryFact
from app.modules.memory.service import MemoryService, readable_answer


def test_existing_structured_health_memory_displays_statement(database_session):
    session = database_session
    client_id = client(session)
    question = "A dor no joelho dificulta ou piora quando você sobe escadas?"
    value = "não tenho mais dor nos joelhos"
    original = f"{question} {value}"
    now = datetime.now(UTC)
    fact = ClientMemoryFact(
        id=uuid4(),
        client_id=client_id,
        category="health_report",
        text=original,
        attribution="client_report",
        reported_at=now,
        updated_at=now,
        answer_data={"field": "current_limitation_impact", "question": question, "value": value},
    )
    session.add(fact)
    session.commit()
    snapshot = MemoryService.snapshot(session, client_id)
    assert snapshot["facts"][0]["text"] == "Não tenho mais dor nos joelhos."
    assert snapshot["facts"][0]["answer_data"] == fact.answer_data
    assert snapshot["facts"][0]["reported_at"] == now.isoformat()
    assert snapshot["facts"][0]["attribution"] == "client_report"
    assert fact.text == original  # Reading does not rewrite sensitive saved data.


@pytest.mark.parametrize("value", ["não", "nenhum", 19, 60, "Talvez eu tenha dor."])
def test_context_dependent_answers_keep_question_and_units(value):
    original = f"Pergunta com contexto? {value}"
    assert readable_answer({"value": value}, original) == original


def test_manual_memory_text_is_displayed_verbatim():
    assert readable_answer(None, "meu texto editado") == "meu texto editado"


def test_new_structured_memory_stores_readable_statement(database_session):
    session = database_session
    client_id = client(session)
    event_id = uuid4()
    value = "não tenho mais dor nos joelhos"
    MemoryService().apply(
        session,
        client_id,
        0,
        [],
        event_id=event_id,
        occurred_at=datetime.now(UTC),
        message=value,
        answers={
            "current_limitation_impact": {
                "question": "A dor dificulta subir escadas?",
                "value": value,
                "source_text": value,
                "source_event_id": str(event_id),
            },
        },
    )
    session.commit()
    fact = session.query(ClientMemoryFact).one()
    assert fact.text == "Não tenho mais dor nos joelhos."
    assert fact.answer_data["value"] == value
