from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from test_clients import AsgiClient, FakeIdentityProvider
from test_training_chat import session as session

from app.database import get_database_session
from app.main import create_app
from app.modules.clients.models import Account, Client, ClientIdentityReconciliation
from app.modules.identity import recovery_router
from app.modules.identity import router as identity_router
from app.modules.identity.keycloak_admin import (
    KeycloakAdminClient,
    KeycloakAdminConfig,
    KeycloakIdentityConflictError,
    KeycloakProvisioningError,
)
from app.modules.identity.password_recovery import PasswordRecoveryError, PasswordRecoveryService
from app.modules.identity.service import AuthenticatedIdentity, InvalidSessionError


class Provider:
    def __init__(self):
        self.calls = []
        self.fail = False

    def send_password_recovery_email(self, subject, email):
        self.calls.append((subject, email))
        if self.fail:
            raise KeycloakProvisioningError("sensitive provider detail")


def client(session, subject="ada"):
    value = Client(
        name=subject,
        account=Account(
            email=f"{subject}@example.test",
            keycloak_subject=subject,
            account_active=True,
        ),
    )
    session.add(value)
    session.commit()
    return value


def api(session, monkeypatch, provider, identity):
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: session
    monkeypatch.setattr(identity_router, "identity_provider", FakeIdentityProvider(identity))
    monkeypatch.setattr(recovery_router, "recovery_service", PasswordRecoveryService(provider))
    return AsgiClient(app)


def test_self_recovery_uses_authenticated_subject_not_body_or_other_clients(session, monkeypatch):
    own, other = client(session), client(session, "grace")
    provider = Provider()
    response = api(
        session, monkeypatch, provider, AuthenticatedIdentity("ada", None, ("client",))
    ).post(
        "/identity/me/password-reset",
        {"client_id": str(other.id), "email": "attacker@example.test"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "sent", "expires_in_seconds": 900}
    assert provider.calls == [("ada", own.account.email)]
    assert other.account.password_recovery_requested_at is None


def test_admin_can_send_to_client_but_clients_and_instructors_cannot(session, monkeypatch):
    target = client(session)
    provider = Provider()
    for roles in (("client",), ("instructor",)):
        response = api(
            session, monkeypatch, provider, AuthenticatedIdentity("ada", None, roles)
        ).request("POST", f"/clients/{target.id}/password-reset")
        assert response.status_code in (401, 403)
    assert provider.calls == []
    response = api(
        session, monkeypatch, provider, AuthenticatedIdentity("admin", None, ("admin",))
    ).request("POST", f"/clients/{target.id}/password-reset")
    assert response.status_code == 200 and len(provider.calls) == 1


@pytest.mark.parametrize("state", ["inactive", "unlinked", "pending"])
def test_unavailable_accounts_do_not_send_email(session, state):
    target = client(session)
    if state == "inactive":
        target.account.account_active = False
    elif state == "unlinked":
        target.account.keycloak_subject = None
    else:
        session.add(
            ClientIdentityReconciliation(
                account_id=target.account_id, email=target.account.email, operation="update"
            )
        )
    session.commit()
    provider = Provider()
    with pytest.raises(PasswordRecoveryError) as error:
        PasswordRecoveryService(provider).request_for_client(session, target.id)
    assert error.value.status == 409 and provider.calls == []


def test_admin_and_self_share_persistent_cooldown_even_after_delivery_failure(session):
    target = client(session)
    provider = Provider()
    service = PasswordRecoveryService(provider)
    provider.fail = True
    with pytest.raises(PasswordRecoveryError) as error:
        service.request_for_subject(session, "ada")
    assert error.value.status == 503
    assert "sensitive" not in error.value.code
    with pytest.raises(PasswordRecoveryError) as error:
        service.request_for_client(session, target.id)
    assert error.value.status == 429 and len(provider.calls) == 1
    session.rollback()
    target.account.password_recovery_requested_at = datetime.now(UTC) - timedelta(seconds=61)
    session.commit()
    provider.fail = False
    service.request_for_client(session, target.id)
    assert len(provider.calls) == 2


def test_invalid_session_and_missing_client_are_controlled(session, monkeypatch):
    class Expired:
        def get_identity(self, token):
            raise InvalidSessionError

    provider = Provider()
    http = api(session, monkeypatch, provider, AuthenticatedIdentity("admin", None, ("admin",)))
    assert http.request("POST", f"/clients/{uuid4()}/password-reset").status_code == 404
    monkeypatch.setattr(identity_router, "identity_provider", Expired())
    assert http.request("POST", "/identity/me/password-reset").status_code == 401
    assert provider.calls == []


def test_keycloak_action_has_exact_expiry_and_trusted_redirect(monkeypatch):
    adapter = KeycloakAdminClient(
        KeycloakAdminConfig(
            "http://identity", "academia", "provisioner", "test-secret", "web", "https://gym.test/"
        )
    )
    calls = []
    monkeypatch.setattr(adapter, "_access_token", lambda: "token")

    def request(method, path, token, payload=None, subject=None):
        calls.append((method, path, payload))
        if method == "GET":
            return {"id": "ada", "enabled": True, "email": "ada@example.test"}

    monkeypatch.setattr(adapter, "_request", request)
    adapter.send_password_recovery_email("ada", "ada@example.test")
    method, path, payload = calls[-1]
    assert method == "PUT" and payload == ["UPDATE_PASSWORD"]
    assert parse_qs(urlparse(path).query) == {
        "lifespan": ["900"],
        "client_id": ["web"],
        "redirect_uri": ["https://gym.test/"],
    }
    assert "credentials" not in str(calls)


@pytest.mark.parametrize(
    "user",
    [
        {"id": "ada", "enabled": True, "email": "old@example.test"},
        {"id": "ada", "enabled": False, "email": "ada@example.test"},
        {"id": "other", "enabled": True, "email": "ada@example.test"},
        None,
    ],
)
def test_keycloak_mismatch_never_sends_recovery_to_stale_identity(monkeypatch, user):
    adapter = KeycloakAdminClient()
    calls = []
    monkeypatch.setattr(adapter, "_access_token", lambda: "token")

    def request(method, *args, **kwargs):
        calls.append(method)
        return user

    monkeypatch.setattr(adapter, "_request", request)
    with pytest.raises(KeycloakIdentityConflictError):
        adapter.send_password_recovery_email("ada", "ada@example.test")
    assert calls == ["GET"]
