import asyncio
import json
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_database_session
from app.integrations.ai import AiInterviewTurnResponse, AiOnboardingExtractionResponse
from app.main import create_app
from app.modules.clients.models import Account, Client, PersonProfile
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding import router as onboarding_router
from app.modules.onboarding.conversation_service import OnboardingConversationService
from app.modules.onboarding.draft_service import OnboardingDraftService


class FakeIdentityProvider:
    def __init__(self, identity: AuthenticatedIdentity) -> None:
        self.identity = identity

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        del access_token
        return self.identity


class FakeConversationProvider:
    def interview_turn(self, context: dict[str, object]) -> AiInterviewTurnResponse:
        del context
        return AiInterviewTurnResponse(
            assistant_message="Qual é o seu objetivo de treino?",
            interview_status="in_progress",
        )

    def extract_onboarding(self, context: dict[str, object]) -> AiOnboardingExtractionResponse:
        del context
        return AiOnboardingExtractionResponse(onboarding={})


@pytest.fixture
def database_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def request(
    app: FastAPI,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    *,
    authenticated: bool = True,
) -> tuple[int, dict[str, object]]:
    sent: list[dict[str, object]] = []
    request_body = json.dumps(payload).encode() if payload is not None else b""
    headers = [(b"authorization", b"Bearer test-token")] if authenticated else []
    if payload is not None:
        headers.append((b"content-type", b"application/json"))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": request_body, "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    status_code = next(
        message["status"] for message in sent if message["type"] == "http.response.start"
    )
    body = next(message["body"] for message in sent if message["type"] == "http.response.body")
    return status_code, json.loads(body)


def create_client(session: Session, subject: str, email: str) -> Client:
    client = Client(
        name=email.split("@")[0],
        account=Account(email=email, keycloak_subject=subject, account_active=True),
    )
    client.account.person_profile = PersonProfile(
        first_name=client.name,
        surname="Teste",
        cpf=f"{len(session.scalars(select(Client)).all()):011d}",
        phone="11998765432",
        postal_code="01001000",
        street="Rua de teste",
        number="1",
        neighborhood="Centro",
        city="São Paulo",
        state="SP",
    )
    session.add(client)
    session.commit()
    return client


def app_for(session: Session) -> FastAPI:
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    return app


def test_client_can_access_only_own_draft_and_admin_is_denied(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_client(database_session, "ada-subject", "ada@example.test")
    create_client(database_session, "grace-subject", "grace@example.test")
    app = app_for(database_session)

    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(AuthenticatedIdentity("ada-subject", "ada@example.test", ("client",))),
    )
    saved_status, saved = request(
        app,
        "PATCH",
        "/onboarding/me",
        {"uses_medications": True, "medications": "Medicação privada"},
    )
    assert saved_status == 200
    assert saved["medications"] == "Medicação privada"

    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity("grace-subject", "grace@example.test", ("client",))
        ),
    )
    other_status, other = request(app, "GET", "/onboarding/me")
    assert other_status == 200
    assert other["medications"] is None

    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity("admin-subject", "admin@example.test", ("admin",))
        ),
    )
    denied_status, denied = request(app, "GET", "/onboarding/me")
    assert denied_status == 403
    assert denied == {"detail": "Forbidden"}

    client_id = database_session.scalar(select(Client.id).where(Client.account_id.is_not(None)))
    profile_status, profile = request(app, "GET", f"/clients/{client_id}")
    assert profile_status == 200
    assert "medications" not in profile
    assert "health_conditions" not in profile
    assert "limitations_or_complaints" not in profile
    app.dependency_overrides.clear()


def test_unauthenticated_draft_access_is_rejected(database_session: Session) -> None:
    app = app_for(database_session)
    status_code, body = request(app, "GET", "/onboarding/me", authenticated=False)

    assert status_code == 401
    assert body == {"detail": "Unauthenticated"}
    app.dependency_overrides.clear()


def test_completion_requires_complete_own_draft_and_records_timestamp_atomically(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_client(database_session, "ada-subject", "ada@example.test")
    app = app_for(database_session)
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(AuthenticatedIdentity("ada-subject", "ada@example.test", ("client",))),
    )
    incomplete_status, incomplete = request(app, "POST", "/onboarding/me/completion")
    assert incomplete_status == 422
    assert incomplete["detail"] == "Onboarding is not ready for completion"

    payload = {
        "training_goal": "Ganhar força",
        "training_experience": "beginner",
        "height_cm": 170,
        "weight_kg": "70.50",
        "has_limitations_or_complaints": False,
        "uses_medications": False,
        "has_health_conditions": False,
    }
    assert request(app, "PATCH", "/onboarding/me", payload)[0] == 200
    completed_status, completed = request(app, "POST", "/onboarding/me/completion")
    assert completed_status == 200
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None
    assert request(app, "POST", "/onboarding/me/completion")[0] == 409
    assert request(app, "PATCH", "/onboarding/me", {"training_goal": "Outro"})[0] == 409
    app.dependency_overrides.clear()


def test_client_conversation_is_own_scoped_and_admin_cannot_read_raw_history(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_client(database_session, "ada-subject", "ada@example.test")
    create_client(database_session, "grace-subject", "grace@example.test")
    monkeypatch.setattr(
        onboarding_router,
        "conversation_service",
        OnboardingConversationService(
            provider=FakeConversationProvider(), draft_service=OnboardingDraftService()
        ),
    )
    app = app_for(database_session)
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(AuthenticatedIdentity("ada-subject", "ada@example.test", ("client",))),
    )

    sent_status, sent = request(
        app,
        "POST",
        "/onboarding/conversation/messages",
        {
            "message": "Quero começar.",
            "client_request_id": "00000000-0000-4000-8000-000000000001",
        },
    )
    assert sent_status == 200
    assert sent["messages"][-1]["content"] == "Qual é o seu principal objetivo de treino?"

    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity("grace-subject", "grace@example.test", ("client",))
        ),
    )
    other_status, other = request(app, "GET", "/onboarding/conversation")
    assert other_status == 200
    assert other["messages"] == []

    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity("admin-subject", "admin@example.test", ("admin",))
        ),
    )
    denied_status, denied = request(app, "GET", "/onboarding/conversation")
    assert denied_status == 403
    assert denied == {"detail": "Forbidden"}
    app.dependency_overrides.clear()


def test_ai_cannot_unlock_completion_with_invented_answers(database_session, monkeypatch):
    class FabricatingProvider(FakeConversationProvider):
        def interview_turn(self, context):
            return AiInterviewTurnResponse(
                assistant_message="Tudo pronto!", interview_status="ready"
            )

        def extract_onboarding(self, context):
            return AiOnboardingExtractionResponse(
                onboarding={
                    "training_goal": "Ganhar força",
                    "training_experience": "beginner",
                    "height_cm": 170,
                    "weight_kg": 70,
                    "has_limitations_or_complaints": False,
                    "uses_medications": False,
                    "has_health_conditions": False,
                }
            )

    create_client(database_session, "ada-subject", "ada@example.test")
    app = app_for(database_session)
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(AuthenticatedIdentity("ada-subject", "ada@example.test", ("client",))),
    )
    monkeypatch.setattr(
        onboarding_router,
        "conversation_service",
        OnboardingConversationService(provider=FabricatingProvider()),
    )
    status, response = request(
        app,
        "POST",
        "/onboarding/conversation/messages",
        {
            "message": "Ganhar força",
            "client_request_id": "00000000-0000-4000-8000-000000000002",
        },
    )
    assert status == 200 and not response["completion_ready"]
    assert request(app, "POST", "/onboarding/me/completion")[0] == 422
    _, draft = request(app, "GET", "/onboarding/me")
    assert draft["height_cm"] is None and draft["uses_medications"] is None
    assert draft["status"] == "draft" and draft["completed_at"] is None
    app.dependency_overrides.clear()
