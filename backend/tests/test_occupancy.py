import asyncio
import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from training_fixtures import instructor

from app.database import Base, get_database_session
from app.main import create_app
from app.modules.clients.models import Account, Client
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.occupancy.models import AccessPassageEvent
from app.modules.occupancy.service import OccupancyService


class FakeIdentityProvider:
    def __init__(self, roles: tuple[str, ...]):
        self.roles = roles

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        return AuthenticatedIdentity("operator", "operator@example.test", self.roles)


def request(
    app,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, object]:
    body = json.dumps(payload).encode() if payload is not None else b""
    sent: list[dict[str, object]] = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers or [],
        "client": ("test", 1),
        "server": ("test", 80),
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    response = next(message["body"] for message in sent if message["type"] == "http.response.body")
    return status, json.loads(response) if response else None


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


def client(session: Session) -> Client:
    value = Client(
        name="Cliente teste", account=Account(email="client@example.test", account_active=True)
    )
    session.add(value)
    session.commit()
    return value


def test_ledger_is_client_linked_idempotent_and_never_negative(session: Session) -> None:
    service = OccupancyService()
    value = client(session)
    service.register_client_reference(session, value.id, "provider-subject-a")
    occurred = datetime(2026, 9, 25, 12, tzinfo=UTC)
    event, created = service.record_passage(
        session,
        event_id="EVT-1",
        occurred_at=occurred,
        checkpoint_id="main",
        direction="entry",
        event_type="passage_confirmed",
        client_reference="provider-subject-a",
    )
    _, repeated = service.record_passage(
        session,
        event_id="EVT-1",
        occurred_at=occurred,
        checkpoint_id="main",
        direction="entry",
        event_type="passage_confirmed",
        client_reference="provider-subject-a",
    )
    exit_event, _ = service.record_passage(
        session,
        event_id="EVT-2",
        occurred_at=occurred + timedelta(minutes=1),
        checkpoint_id="main",
        direction="exit",
        event_type="passage_confirmed",
        client_reference="provider-subject-a",
    )
    extra_exit, _ = service.record_passage(
        session,
        event_id="EVT-3",
        occurred_at=occurred + timedelta(minutes=2),
        checkpoint_id="main",
        direction="exit",
        event_type="passage_confirmed",
        client_reference="provider-subject-a",
    )
    assert (
        created
        and not repeated
        and event.client_id == value.id
        and exit_event.inconsistency is False
        and extra_exit.inconsistency is True
    )
    assert len(session.scalars(select(AccessPassageEvent)).all()) == 3
    assert service.snapshot(session, occurred + timedelta(minutes=3)).occupancy == 0


def test_heartbeat_staleness_and_corrections_are_reconstructable(session: Session) -> None:
    service = OccupancyService()
    now = datetime(2026, 9, 25, 12, tzinfo=UTC)
    service.record_heartbeat(session, "main", now)
    service.correct(
        session, actor_subject="admin", adjustment=3, reason="Reconciliation", occurred_at=now
    )
    assert service.snapshot(session, now + timedelta(seconds=119)).occupancy == 3
    assert service.snapshot(session, now + timedelta(seconds=119)).status == "current"
    stale = service.snapshot(session, now + timedelta(seconds=121))
    assert stale.occupancy == 3 and stale.status == "stale"


def test_api_authentication_privacy_and_unknown_reference(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = OccupancyService()
    value = client(session)
    service.register_client_reference(session, value.id, "provider-subject-a")
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    monkeypatch.setenv("ACCESS_EVENT_INTEGRATION_SECRET", "integration-secret")
    payload = {
        "event_id": "EVT-1",
        "occurred_at": "2026-09-25T12:00:00Z",
        "checkpoint_id": "main",
        "direction": "entry",
        "event_type": "passage_confirmed",
        "client_reference": "provider-subject-a",
    }
    integration_headers = [
        (b"content-type", b"application/json"),
        (b"x-access-integration-secret", b"integration-secret"),
    ]
    unauthorized, _ = request(app, "POST", "/occupancy/passage-events", payload)
    accepted, body = request(
        app,
        "POST",
        "/occupancy/passage-events",
        payload,
        integration_headers,
    )
    duplicate, duplicate_body = request(
        app,
        "POST",
        "/occupancy/passage-events",
        payload,
        integration_headers,
    )
    unknown_payload = {**payload, "event_id": "EVT-unknown", "client_reference": "unknown"}
    unknown, _ = request(
        app,
        "POST",
        "/occupancy/passage-events",
        unknown_payload,
        integration_headers,
    )
    heartbeat, _ = request(
        app,
        "POST",
        "/occupancy/source-heartbeats",
        {"checkpoint_id": "main", "occurred_at": datetime.now(UTC).isoformat()},
        integration_headers,
    )
    public, snapshot = request(app, "GET", "/occupancy")
    assert unauthorized == 401 and accepted == 201 and body == {"accepted": True, "created": True}
    assert (
        duplicate == 201
        and duplicate_body == {"accepted": True, "created": False}
        and unknown == 422
        and heartbeat == 204
    )
    assert (
        public == 200
        and snapshot["occupancy"] == 1
        and set(snapshot) == {"occupancy", "status", "updated_at"}
    )
    app.dependency_overrides.clear()


def test_only_admin_or_attendant_can_correct(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    headers = [(b"authorization", b"Bearer token"), (b"content-type", b"application/json")]
    instructor(session, "operator")
    monkeypatch.setattr(identity_router, "identity_provider", FakeIdentityProvider(("instructor",)))
    denied, _ = request(
        app, "POST", "/occupancy/admin/corrections", {"adjustment": 1, "reason": "Teste"}, headers
    )
    monkeypatch.setattr(identity_router, "identity_provider", FakeIdentityProvider(("attendant",)))
    accepted, body = request(
        app,
        "POST",
        "/occupancy/admin/corrections",
        {"adjustment": -2, "reason": "Falha da catraca"},
        headers,
    )
    assert denied == 403 and accepted == 201 and body["adjustment"] == -2
    app.dependency_overrides.clear()
