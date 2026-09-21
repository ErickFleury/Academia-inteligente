import asyncio
import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_database_session
from app.main import create_app
from app.modules.clients.models import Account, Client
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding import router as onboarding_router
from app.modules.onboarding.models import OnboardingInvitation
from app.modules.onboarding.service import (
    INVITATION_PURPOSE,
    ClientInvitationUnavailableError,
    InvitationDeliveryError,
    OnboardingInvitationService,
    hash_token,
)


class FakeIdentityProvider:
    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        del access_token
        return AuthenticatedIdentity(
            subject="admin-subject", username="admin@example.test", roles=("admin",)
        )


class FakeEmailSender:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.messages: list[tuple[str, str, str]] = []

    def send(self, *, recipient: str, subject: str, body: str) -> None:
        if self.fail:
            raise OSError("mail relay unavailable")
        self.messages.append((recipient, subject, body))


class AsgiClient:
    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def post(self, path: str) -> tuple[int, dict[str, object]]:
        return self.request("POST", path)

    def get(self, path: str) -> tuple[int, dict[str, object]]:
        return self.request("GET", path)

    def request(self, method: str, path: str) -> tuple[int, dict[str, object]]:
        sent: list[dict[str, object]] = []
        parsed = urlsplit(path)
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": parsed.path,
            "raw_path": parsed.path.encode(),
            "query_string": parsed.query.encode(),
            "headers": [(b"authorization", b"Bearer admin-token")],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, object]) -> None:
            sent.append(message)

        asyncio.run(self.app(scope, receive, send))
        status_code = next(
            message["status"] for message in sent if message["type"] == "http.response.start"
        )
        body = next(message["body"] for message in sent if message["type"] == "http.response.body")
        return status_code, json.loads(body)


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


def create_client(session: Session, email: str, *, active: bool = True) -> Client:
    client = Client(
        name=email.split("@")[0],
        account=Account(
            email=email,
            keycloak_subject=f"subject-{email}",
            account_active=active,
        ),
    )
    session.add(client)
    session.commit()
    return client


def raw_token(sender: FakeEmailSender) -> str:
    link = next(part for part in sender.messages[-1][2].split() if part.startswith("http"))
    return parse_qs(urlsplit(link).query)["token"][0]


def test_unexpired_token_is_client_bound_and_passive_validation_does_not_consume(
    database_session: Session,
) -> None:
    client = create_client(database_session, "ada@example.test")
    other_client = create_client(database_session, "grace@example.test")
    sender = FakeEmailSender()
    now = datetime(2026, 9, 20, tzinfo=UTC)
    service = OnboardingInvitationService(
        sender=sender,
        clock=lambda: now,
        token_factory=lambda _: "valid-token",
        invitation_url="https://app.example.test/onboarding",
    )

    summary = service.issue(database_session, client.id)
    token = raw_token(sender)
    invitation = database_session.scalar(select(OnboardingInvitation))

    assert summary.delivery_status == "sent"
    assert summary.expires_at == now + timedelta(hours=24)
    assert invitation is not None
    assert invitation.token_hash == hash_token(token)
    assert token not in invitation.__dict__.values()
    assert service.validate_for_client(database_session, token, client.id) is not None
    assert service.validate_for_client(database_session, token, other_client.id) is None
    assert invitation.redeemed_at is None


def test_expired_and_already_used_tokens_are_rejected(database_session: Session) -> None:
    client = create_client(database_session, "ada@example.test")
    sender = FakeEmailSender()
    clock = [datetime(2026, 9, 20, tzinfo=UTC)]
    service = OnboardingInvitationService(
        sender=sender, clock=lambda: clock[0], token_factory=lambda _: "single-use-token"
    )
    service.issue(database_session, client.id)
    token = raw_token(sender)

    assert service.consume_after_valid_redemption(database_session, token, client.id) is True
    assert service.validate_for_client(database_session, token, client.id) is None
    assert service.consume_after_valid_redemption(database_session, token, client.id) is False

    clock[0] += timedelta(hours=25)
    expired_sender = FakeEmailSender()
    expired_service = OnboardingInvitationService(
        sender=expired_sender,
        clock=lambda: datetime(2026, 9, 20, tzinfo=UTC),
        token_factory=lambda _: "expired-token",
    )
    expired_service.issue(database_session, client.id)
    assert (
        service.validate_for_client(database_session, raw_token(expired_sender), client.id) is None
    )


def test_access_status_is_passive_and_distinguishes_expired_from_invalid(
    database_session: Session,
) -> None:
    client = create_client(database_session, "ada@example.test")
    sender = FakeEmailSender()
    clock = [datetime(2026, 9, 20, tzinfo=UTC)]
    service = OnboardingInvitationService(
        sender=sender, clock=lambda: clock[0], token_factory=lambda _: "access-token"
    )
    service.issue(database_session, client.id)
    token = raw_token(sender)

    assert service.validate_access(database_session, token).status == "valid"
    assert service.validate_access(database_session, "malformed-token").status == "invalid"
    assert service.validate_for_client(database_session, token, client.id) is not None

    clock[0] += timedelta(hours=24)
    assert service.validate_access(database_session, token).status == "expired"


def test_access_api_passively_validates_and_only_explicit_redemption_consumes(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = create_client(database_session, "ada@example.test")
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield database_session

    app.dependency_overrides[get_database_session] = override_database_session
    sender = FakeEmailSender()
    service = OnboardingInvitationService(sender=sender, token_factory=lambda _: "web-access-token")
    monkeypatch.setattr(onboarding_router, "invitation_service", service)
    service.issue(database_session, client.id)
    token = raw_token(sender)
    api_client = AsgiClient(app)

    status_code, body = api_client.get(f"/onboarding/access?token={token}")
    assert status_code == 200
    assert body == {"status": "valid"}
    assert database_session.scalar(select(OnboardingInvitation)).redeemed_at is None

    redeemed_status, redeemed_body = api_client.post(
        f"/onboarding/access/redemptions?token={token}"
    )
    assert redeemed_status == 200
    assert redeemed_body == {"status": "redeemed"}
    assert database_session.scalar(select(OnboardingInvitation)).redeemed_at is not None

    reused_status, reused_body = api_client.get(f"/onboarding/access?token={token}")
    assert reused_status == 200
    assert reused_body == {"status": "invalid"}
    invalid_status, invalid_body = api_client.get("/onboarding/access?token=wrong-token")
    assert invalid_status == 200
    assert invalid_body == {"status": "invalid"}
    app.dependency_overrides.clear()


def test_resend_invalidates_previous_unused_token_and_keeps_newest_valid(
    database_session: Session,
) -> None:
    client = create_client(database_session, "ada@example.test")
    sender = FakeEmailSender()
    tokens = iter(("first-token", "newest-token"))
    service = OnboardingInvitationService(
        sender=sender,
        clock=lambda: datetime(2026, 9, 20, tzinfo=UTC),
        token_factory=lambda _: next(tokens),
    )

    service.issue(database_session, client.id)
    first = raw_token(sender)
    service.issue(database_session, client.id)
    newest = raw_token(sender)
    invitations = database_session.scalars(select(OnboardingInvitation)).all()
    first_invitation = next(item for item in invitations if item.token_hash == hash_token(first))

    assert len(invitations) == 2
    assert first_invitation.invalidated_at is not None
    assert service.validate_for_client(database_session, first, client.id) is None
    assert service.validate_for_client(database_session, newest, client.id) is not None


def test_failed_delivery_is_persisted_as_failure_not_success(database_session: Session) -> None:
    client = create_client(database_session, "ada@example.test")
    service = OnboardingInvitationService(
        sender=FakeEmailSender(fail=True), token_factory=lambda _: "undelivered-token"
    )

    with pytest.raises(InvitationDeliveryError):
        service.issue(database_session, client.id)

    invitation = database_session.scalar(select(OnboardingInvitation))
    assert invitation is not None
    assert invitation.purpose == INVITATION_PURPOSE
    assert invitation.delivery_status == "failed"
    assert invitation.sent_at is None
    assert invitation.failure_recorded_at is not None
    assert invitation.token_hash == hash_token("undelivered-token")


def test_unprovisioned_or_inactive_client_cannot_receive_an_invitation(
    database_session: Session,
) -> None:
    unprovisioned = Client(
        name="legacy",
        account=Account(email="legacy@example.test", account_active=True),
    )
    inactive = create_client(database_session, "inactive@example.test", active=False)
    database_session.add(unprovisioned)
    database_session.commit()
    service = OnboardingInvitationService(sender=FakeEmailSender())

    with pytest.raises(ClientInvitationUnavailableError):
        service.issue(database_session, unprovisioned.id)
    with pytest.raises(ClientInvitationUnavailableError):
        service.issue(database_session, inactive.id)

    assert database_session.scalars(select(OnboardingInvitation)).all() == []


def test_admin_api_issues_invitation_and_returns_controlled_delivery_failure(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = create_client(database_session, "ada@example.test")
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield database_session

    app.dependency_overrides[get_database_session] = override_database_session
    monkeypatch.setattr(identity_router, "identity_provider", FakeIdentityProvider())
    sender = FakeEmailSender()
    monkeypatch.setattr(
        onboarding_router, "invitation_service", OnboardingInvitationService(sender=sender)
    )
    api_client = AsgiClient(app)

    status_code, body = api_client.post(f"/onboarding/clients/{client.id}/invitations")

    assert status_code == 201
    assert body["delivery_status"] == "sent"
    assert "token" not in body

    monkeypatch.setattr(
        onboarding_router,
        "invitation_service",
        OnboardingInvitationService(sender=FakeEmailSender(fail=True)),
    )
    failed_status, failed_body = api_client.post(f"/onboarding/clients/{client.id}/invitations")

    assert failed_status == 503
    assert failed_body == {"detail": "Onboarding invitation delivery failed"}
    latest = database_session.scalars(
        select(OnboardingInvitation).order_by(OnboardingInvitation.issued_at.desc())
    ).first()
    assert latest is not None and latest.delivery_status == "failed"
    app.dependency_overrides.clear()
