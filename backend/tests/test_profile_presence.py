import asyncio
import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_database_session
from app.main import create_app
from app.modules.clients.models import Account, Client
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.occupancy.service import OccupancyService
from app.modules.presence.models import ProfilePresenceConsentAudit
from app.modules.presence.service import ProfilePresenceService


class FakeIdentityProvider:
    def __init__(self, subject: str, roles: tuple[str, ...]):
        self.subject = subject
        self.roles = roles

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        return AuthenticatedIdentity(self.subject, "client@example.test", self.roles)


def request(
    app, method: str, path: str, payload: dict[str, object] | None = None
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
        "headers": [(b"authorization", b"Bearer token"), (b"content-type", b"application/json")],
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


def client(session: Session, subject: str = "client-subject") -> Client:
    value = Client(
        name="Cliente teste",
        account=Account(
            email=f"{subject}@example.test", keycloak_subject=subject, account_active=True
        ),
    )
    session.add(value)
    session.commit()
    return value


def add_entry_and_heartbeat(session: Session, value: Client, now: datetime) -> None:
    occupancy = OccupancyService()
    occupancy.register_client_reference(session, value.id, f"access-{value.id}")
    occupancy.record_passage(
        session,
        event_id=f"entry-{value.id}",
        occurred_at=now,
        checkpoint_id="main",
        direction="entry",
        event_type="passage_confirmed",
        client_reference=f"access-{value.id}",
    )
    occupancy.record_heartbeat(session, "main", now)


def test_presence_is_default_off_and_does_not_change_anonymous_occupancy(session: Session) -> None:
    now = datetime(2026, 9, 25, 12, tzinfo=UTC)
    value = client(session)
    add_entry_and_heartbeat(session, value, now)
    presence = ProfilePresenceService()
    assert presence.get_own(session, "client-subject", now).sharing_enabled is False
    assert presence.get_own(session, "client-subject", now).currently_present is False
    before = OccupancyService().snapshot(session, now).occupancy
    enabled = presence.set_own(session, "client-subject", True, now)
    assert enabled.currently_present is True
    assert OccupancyService().snapshot(session, now).occupancy == before == 1


def test_presence_requires_current_source_entry_and_unexpired_session(session: Session) -> None:
    now = datetime(2026, 9, 25, 12, tzinfo=UTC)
    value = client(session)
    add_entry_and_heartbeat(session, value, now)
    presence = ProfilePresenceService()
    presence.set_own(session, "client-subject", True, now)
    assert presence.get_own(
        session, "client-subject", now + timedelta(seconds=119)
    ).currently_present
    assert not presence.get_own(
        session, "client-subject", now + timedelta(seconds=121)
    ).currently_present
    OccupancyService().record_heartbeat(session, "main", now + timedelta(hours=12))
    assert (
        presence.get_own(
            session, "client-subject", now + timedelta(hours=12, seconds=1)
        ).currently_present
        is False
    )


def test_exit_and_revocation_hide_tag_and_preserve_a_minimal_consent_audit(
    session: Session,
) -> None:
    now = datetime(2026, 9, 25, 12, tzinfo=UTC)
    value = client(session)
    add_entry_and_heartbeat(session, value, now)
    occupancy = OccupancyService()
    presence = ProfilePresenceService()
    presence.set_own(session, "client-subject", True, now)
    occupancy.record_passage(
        session,
        event_id="exit",
        occurred_at=now + timedelta(minutes=5),
        checkpoint_id="main",
        direction="exit",
        event_type="passage_confirmed",
        client_reference=f"access-{value.id}",
    )
    occupancy.record_heartbeat(session, "main", now + timedelta(minutes=5))
    assert not presence.get_own(
        session, "client-subject", now + timedelta(minutes=5)
    ).currently_present
    revoked = presence.set_own(session, "client-subject", False, now + timedelta(minutes=6))
    audits = list(session.scalars(select(ProfilePresenceConsentAudit)))
    assert revoked.sharing_enabled is False and revoked.currently_present is False
    assert [(audit.previous_enabled, audit.new_enabled) for audit in audits] == [
        (False, True),
        (True, False),
    ]
    assert occupancy.snapshot(session, now + timedelta(minutes=6)).occupancy == 0


def test_api_is_client_only_and_returns_only_presence_projection(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = client(session)
    add_entry_and_heartbeat(session, value, datetime.now(UTC))
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    monkeypatch.setattr(
        identity_router, "identity_provider", FakeIdentityProvider("client-subject", ("client",))
    )
    initial_status, initial = request(app, "GET", "/profile-presence/me")
    update_status, updated = request(app, "PATCH", "/profile-presence/me", {"enabled": True})
    monkeypatch.setattr(
        identity_router, "identity_provider", FakeIdentityProvider("operator", ("admin",))
    )
    forbidden_status, _ = request(app, "GET", "/profile-presence/me")
    assert initial_status == 200 and initial == {
        "sharing_enabled": False,
        "currently_present": False,
    }
    assert update_status == 200 and updated == {"sharing_enabled": True, "currently_present": True}
    assert forbidden_status == 403
    app.dependency_overrides.clear()
