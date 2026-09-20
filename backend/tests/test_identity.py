import asyncio
import json

from app.main import create_app
from app.modules.identity import router as identity_router
from app.modules.identity.authorization import has_any_role
from app.modules.identity.service import AuthenticatedIdentity, InvalidSessionError


class FakeIdentityProvider:
    def __init__(self, identity: AuthenticatedIdentity | Exception) -> None:
        self.identity = identity

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        if isinstance(self.identity, Exception):
            raise self.identity
        return self.identity


def request(
    app, authorization: str | None = None, path: str = "/identity/me"
) -> tuple[int, dict[str, object]]:
    """Exercise the ASGI app without a live identity provider or HTTP client."""
    sent: list[dict[str, object]] = []
    headers = [] if authorization is None else [(b"authorization", authorization.encode())]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
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


def test_protected_endpoint_rejects_absent_session() -> None:
    status, body = request(create_app())

    assert status == 401
    assert body == {"detail": "Unauthenticated"}


def test_protected_endpoint_returns_authenticated_active_identity(monkeypatch) -> None:
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity(
                subject="user-123", username="active@example.test", roles=("admin",)
            )
        ),
    )

    status, body = request(create_app(), "Bearer valid")

    assert status == 200
    assert body == {
        "subject": "user-123",
        "username": "active@example.test",
        "roles": ["admin"],
    }


def test_expired_or_invalid_session_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        identity_router, "identity_provider", FakeIdentityProvider(InvalidSessionError())
    )
    status, _ = request(create_app(), "Bearer expired")

    assert status == 401


def test_inactive_account_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        identity_router, "identity_provider", FakeIdentityProvider(InvalidSessionError())
    )
    status, _ = request(create_app(), "Bearer inactive")

    assert status == 401


def test_role_policy_matches_only_allowed_roles() -> None:
    client = AuthenticatedIdentity(subject="client-123", username=None, roles=("client",))
    administrator = AuthenticatedIdentity(subject="admin-123", username=None, roles=("admin",))

    assert not has_any_role(client, frozenset({"admin"}))
    assert has_any_role(administrator, frozenset({"admin"}))


def test_client_is_denied_direct_administrative_api_access(monkeypatch) -> None:
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity(
                subject="client-123", username="client@example.test", roles=("client",)
            )
        ),
    )

    status, body = request(create_app(), "Bearer client-token", "/identity/admin")

    assert status == 401
    assert body == {"detail": "Unauthenticated"}


def test_administrator_can_access_administrative_api(monkeypatch) -> None:
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity(
                subject="admin-123", username="admin@example.test", roles=("admin",)
            )
        ),
    )

    status, body = request(create_app(), "Bearer admin-token", "/identity/admin")

    assert status == 200
    assert body == {"authorized": True}
