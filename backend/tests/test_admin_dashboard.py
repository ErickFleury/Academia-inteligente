import asyncio
import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_database_session
from app.main import create_app
from app.modules.clients.models import Account, Client
from app.modules.dashboard.service import DashboardService
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.occupancy.models import AccessPassageEvent
from app.modules.occupancy.service import OccupancyService


class FakeIdentityProvider:
    def __init__(self, roles: tuple[str, ...]):
        self.roles = roles

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        return AuthenticatedIdentity("operator", "operator@example.test", self.roles)


def request(app, path: str, headers: list[tuple[bytes, bytes]] | None = None) -> tuple[int, object]:
    sent: list[dict[str, object]] = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers or [],
        "client": ("test", 1),
        "server": ("test", 80),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    response_status = next(
        message["status"] for message in sent if message["type"] == "http.response.start"
    )
    response_body = next(
        message["body"] for message in sent if message["type"] == "http.response.body"
    )
    return response_status, json.loads(response_body) if response_body else None


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


def client(session: Session, name: str, active: bool = True) -> Client:
    value = Client(name=name, account=Account(email=f"{name}@example.test", account_active=active))
    session.add(value)
    session.commit()
    return value


def entry(
    session: Session, client_id, event_id: str, occurred_at: datetime, direction: str = "entry"
) -> None:
    session.add(
        AccessPassageEvent(
            event_id=event_id,
            client_id=client_id,
            client_reference_digest=f"digest-{event_id}",
            occurred_at=occurred_at,
            checkpoint_id="main",
            direction=direction,
            event_type="passage_confirmed",
        )
    )
    session.commit()


def test_dashboard_derives_active_clients_and_bounded_utc_weekly_confirmed_entries(
    session: Session,
) -> None:
    active = client(session, "active")
    client(session, "inactive", active=False)
    now = datetime(2026, 9, 25, 12, tzinfo=UTC)
    entry(session, active.id, "entry-current-1", datetime(2026, 9, 22, 10, tzinfo=UTC))
    entry(session, active.id, "entry-current-2", datetime(2026, 9, 25, 10, tzinfo=UTC))
    entry(session, active.id, "entry-previous", datetime(2026, 9, 15, 10, tzinfo=UTC))
    entry(session, active.id, "exit-not-attendance", datetime(2026, 9, 24, 10, tzinfo=UTC), "exit")
    entry(session, active.id, "entry-outside-window", now - timedelta(weeks=9))

    service = DashboardService()
    history = service.attendance_history(session, now)

    assert service.active_client_count(session) == 1
    assert [item.week_start.isoformat() for item in history] == [
        "2026-08-03", "2026-08-10", "2026-08-17", "2026-08-24",
        "2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21",
    ]
    assert [item.confirmed_entries for item in history] == [0, 0, 0, 0, 0, 0, 1, 2]


def test_dashboard_api_is_admin_only_and_returns_aggregate_only(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    active = client(session, "active")
    active.account.keycloak_subject = "operator"
    session.commit()
    now = datetime.now(UTC)
    entry(session, active.id, "entry-current", now)
    OccupancyService().record_heartbeat(session, "main", now)
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    headers = [(b"authorization", b"Bearer token")]
    monkeypatch.setattr(identity_router, "identity_provider", FakeIdentityProvider(("client",)))
    for path in (
        "/admin/dashboard/active-clients",
        "/admin/dashboard/attendance",
        "/admin/dashboard/occupancy",
    ):
        status, body = request(app, path, headers)
        assert status == 403 and body == {"detail": "Forbidden"}

    monkeypatch.setattr(identity_router, "identity_provider", FakeIdentityProvider(("admin",)))
    active_status, active_body = request(app, "/admin/dashboard/active-clients", headers)
    attendance_status, attendance_body = request(app, "/admin/dashboard/attendance", headers)
    occupancy_status, occupancy_body = request(app, "/admin/dashboard/occupancy", headers)

    assert active_status == 200 and active_body == {"active_clients": 1}
    assert attendance_status == 200 and set(attendance_body) == {"weeks"}
    assert occupancy_status == 200 and occupancy_body["occupancy"] == 1
    assert occupancy_body["status"] == "current"
    serialized = json.dumps([active_body, attendance_body, occupancy_body])
    assert active.id.hex not in serialized and "client_reference" not in serialized
    app.dependency_overrides.clear()
