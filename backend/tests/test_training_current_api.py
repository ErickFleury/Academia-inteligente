import asyncio
import json
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_database_session
from app.main import create_app
from app.modules.clients.models import Account, Client
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training.schema import TrainingPlanItemInput, TrainingPlanVersionInput
from app.modules.training.service import TrainingLifecycleService


class FakeIdentityProvider:
    def __init__(self, identity: AuthenticatedIdentity) -> None:
        self.identity = identity

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        del access_token
        return self.identity


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    value = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield value
    finally:
        value.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def create_client(session: Session, subject: str, email: str) -> Client:
    client = Client(
        name=email.split("@")[0],
        account=Account(email=email, keycloak_subject=subject, account_active=True),
    )
    session.add(client)
    session.commit()
    return client


def activate_current_plan(session: Session, client: Client, name: str) -> None:
    lifecycle = TrainingLifecycleService()
    proposal = lifecycle.create_proposal(
        session,
        client_id=client.id,
        data=TrainingPlanVersionInput(
            name=name,
            objective="Ganhar força com consistência",
            items=[
                TrainingPlanItemInput(
                    exercise_name="Agachamento",
                    sets=3,
                    repetitions="8",
                    load_guidance="Carga confortável",
                    rest_seconds=90,
                )
            ],
        ),
        created_by="instructor-subject",
        origin="instructor",
    )
    approved = lifecycle.approve(
        session,
        plan_id=proposal.plan_id,
        version_number=proposal.version_number,
        actor="instructor-subject",
        expected_revision=proposal.revision,
    )
    lifecycle.activate(
        session,
        plan_id=approved.plan_id,
        version_number=approved.version_number,
        expected_revision=approved.revision,
    )


def app_for(session: Session) -> FastAPI:
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    return app


def request(app: FastAPI, authorization: str | None) -> tuple[int, dict[str, object]]:
    sent: list[dict[str, object]] = []
    headers = [] if authorization is None else [(b"authorization", authorization.encode())]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/training/current",
        "raw_path": b"/training/current",
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    body = next(message["body"] for message in sent if message["type"] == "http.response.body")
    return status, json.loads(body)


def set_identity(monkeypatch: pytest.MonkeyPatch, subject: str, roles: tuple[str, ...]) -> None:
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(AuthenticatedIdentity(subject, f"{subject}@example.test", roles)),
    )


def test_current_plan_is_scoped_to_the_authenticated_client_and_survives_reload(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    ada = create_client(session, "ada", "ada@example.test")
    grace = create_client(session, "grace", "grace@example.test")
    activate_current_plan(session, ada, "Força da Ada")
    activate_current_plan(session, grace, "Força da Grace")
    app = app_for(session)
    set_identity(monkeypatch, "ada", ("client",))

    first_status, first = request(app, "Bearer token")
    second_status, second = request(app, "Bearer token")

    assert first_status == second_status == 200
    assert first == second
    assert first["plan"]["name"] == "Força da Ada"
    assert first["plan"]["items"][0]["exercise_name"] == "Agachamento"
    assert "Grace" not in json.dumps(first)
    app.dependency_overrides.clear()


def test_client_without_current_plan_receives_an_empty_response(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_client(session, "ada", "ada@example.test")
    app = app_for(session)
    set_identity(monkeypatch, "ada", ("client",))

    assert request(app, "Bearer token") == (200, {"plan": None})
    app.dependency_overrides.clear()


def test_current_plan_api_rejects_anonymous_and_non_client_roles(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_client(session, "ada", "ada@example.test")
    app = app_for(session)
    assert request(app, None) == (401, {"detail": "Unauthenticated"})
    set_identity(monkeypatch, "admin", ("admin",))
    assert request(app, "Bearer token") == (403, {"detail": "Forbidden"})
    app.dependency_overrides.clear()
