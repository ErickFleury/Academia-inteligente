from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_clients import AsgiClient
from test_clients import database_session as database_session
from test_shared_accounts import MemoryKeycloak, make_dual

from app.database import get_database_session
from app.main import create_app
from app.modules.clients.models import Account, Client, Employee
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.memory.models import ClientMemoryFact
from app.modules.memory.service import MemoryChange, MemoryError, MemoryService
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.models import TrainingAiConversation, TrainingAiMessage

service = MemoryService()


def client(session, subject="owner"):
    row = Client(
        name="Owner", account=Account(email=f"{subject}@example.test", keycloak_subject=subject)
    )
    session.add(row)
    session.commit()
    return row.id


def add(session, client_id, text="Prefiro treinar de manhã.", occurred_at=None):
    state = service.snapshot(session, client_id)
    service.apply(
        session,
        client_id,
        state["revision"],
        [MemoryChange(action="add", category="preference", text=text, evidence=text)],
        event_id=uuid4(),
        occurred_at=occurred_at or datetime.now(UTC),
        message=text,
    )
    session.commit()
    return service.snapshot(session, client_id)


def test_memory_is_private_and_roles_cannot_override_owner(database_session):
    session = database_session
    owner = client(session)
    other = client(session, "other")
    original = add(session, owner)
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: session
    http = AsgiClient(app)
    for role in ["admin", "instructor", "attendant"]:
        app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
            "owner", None, (role,)
        )
        assert http.get("/ai/memory").status_code == 403
    app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        "other", None, ("client",)
    )
    assert http.get("/ai/memory").json()["facts"] == []
    status = http.request(
        "PATCH", "/ai/memory/" + original["facts"][0]["id"], {"revision": 0, "text": "Outro relato"}
    ).status_code
    assert status == 404
    assert service.snapshot(session, other)["revision"] == 0
    assert service.snapshot(session, owner)["facts"] == original["facts"]


def test_correction_and_forgetting_block_stale_and_replayed_sources(database_session):
    session = database_session
    owner = client(session)
    before = datetime.now(UTC) - timedelta(days=1)
    state = add(session, owner, occurred_at=before)
    fact_id = state["facts"][0]["id"]
    revised = service.edit(session, owner, fact_id, state["revision"], "Prefiro treinar à tarde.")
    assert revised["facts"][0]["attribution"] == "client_edit"
    with pytest.raises(MemoryError, match="memory_conflict"):
        service.edit(session, owner, fact_id, state["revision"], "Não sobrescrever")
    forgotten = service.edit(session, owner, fact_id, revised["revision"])
    assert forgotten["facts"] == []
    with pytest.raises(MemoryError, match="memory_event_expired"):
        add(session, owner, occurred_at=before)
    assert service.snapshot(session, owner)["facts"] == []
    # A genuinely new report remains allowed; forgetting is not a permanent ban.
    assert len(add(session, owner)["facts"]) == 1


@pytest.mark.parametrize(
    "message,evidence,text",
    [
        ("Minha irmã tem uma condição.", "Tenho uma condição.", "Tenho uma condição."),
        ("Não tenho dor.", "tenho dor.", "tenho dor."),
        ("Talvez eu tenha dor.", "Talvez eu tenha dor.", "Talvez eu tenha dor."),
        ("Tenho dor no joelho.", "Tenho dor no joelho.", "Tenho artrite."),
        (
            "Minha irmã tem uma condição.",
            "Minha irmã tem uma condição.",
            "Minha irmã tem uma condição.",
        ),
    ],
)
def test_proposals_cannot_invent_diagnosis_or_invert_source(
    database_session, message, evidence, text
):
    owner = client(database_session)
    with pytest.raises(MemoryError):
        service.apply(
            database_session,
            owner,
            0,
            [MemoryChange(action="add", category="health_report", text=text, evidence=evidence)],
            event_id=uuid4(),
            occurred_at=datetime.now(UTC),
            message=message,
        )
    assert service.snapshot(database_session, owner)["facts"] == []
    assert service.snapshot(database_session, owner)["revision"] == 0


def test_duplicate_consolidation_and_atomic_capacity_failure(database_session):
    session = database_session
    owner = client(session)
    add(session, owner)
    assert len(add(session, owner)["facts"]) == 1
    now = datetime.now(UTC)
    for i in range(49):
        session.add(
            ClientMemoryFact(
                client_id=owner,
                category="preference",
                text=f"Preferência {i}",
                attribution="client_edit",
                reported_at=now,
                updated_at=now,
            )
        )
    session.commit()
    before = service.snapshot(session, owner)
    with pytest.raises(MemoryError, match="memory_capacity"):
        add(session, owner, "Quero treinar mais.")
    assert service.snapshot(session, owner) == before


def test_transcript_expiration_does_not_expire_memory(database_session):
    session = database_session
    owner = client(session)
    before = datetime.now(UTC) - timedelta(days=31)
    add(session, owner, occurred_at=before)
    conversation = TrainingAiConversation(client_id=owner, raw_expires_at=before)
    session.add(conversation)
    session.flush()
    session.add(
        TrainingAiMessage(
            conversation_id=conversation.id,
            role="user",
            content="Old private text",
            sequence=1,
            created_at=before,
        )
    )
    session.commit()
    TrainingChatService().purge_expired_content(session)
    assert session.scalar(select(TrainingAiMessage)) is None
    assert len(service.snapshot(session, owner)["facts"]) == 1


def test_erasing_shared_client_removes_memory_but_preserves_employee(database_session):
    session = database_session
    fake = MemoryKeycloak()
    _, employee, clients, owner = make_dual(session, fake)
    add(session, owner.id, "Tenho dor no joelho.")
    assert clients.erase(session, owner.id)
    assert session.scalar(select(ClientMemoryFact)) is None
    assert session.scalar(select(Client)) is None
    assert session.scalar(select(Employee)).id == employee.id
    assert not fake.deleted


def test_conversational_forgetting_requires_explicit_instruction(database_session):
    session = database_session
    owner = client(session)
    state = add(session, owner)
    fact_id = state["facts"][0]["id"]

    def forget(message):
        service.apply(
            session,
            owner,
            state["revision"],
            [MemoryChange(action="forget", fact_id=fact_id, evidence=message)],
            event_id=uuid4(),
            occurred_at=datetime.now(UTC),
            message=message,
        )

    with pytest.raises(MemoryError, match="memory_evidence_invalid"):
        forget("Tudo bem.")
    with pytest.raises(MemoryError, match="memory_evidence_invalid"):
        forget("Não esqueça minha preferência de horário.")
    forget("Esqueça minha preferência de horário.")
    session.commit()
    assert service.snapshot(session, owner)["facts"] == []
