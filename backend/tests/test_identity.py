import asyncio
import json

from app.main import create_app
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity, InvalidSessionError


class FakeIdentityProvider:
    def __init__(self, identity: AuthenticatedIdentity | Exception) -> None:
        self.identity = identity

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        if isinstance(self.identity, Exception):
            raise self.identity
        return self.identity


def request(app, authorization: str | None = None) -> tuple[int, dict[str, object]]:
    """Exercise the ASGI app without a live identity provider or HTTP client."""
    sent: list[dict[str, object]] = []
    headers = [] if authorization is None else [(b"authorization", authorization.encode())]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/identity/me",
        "raw_path": b"/identity/me",
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
                subject="user-123", username="active@example.test", roles=("client",)
            )
        ),
    )

    status, body = request(create_app(), "Bearer valid")

    assert status == 200
    assert body == {
        "subject": "user-123",
        "username": "active@example.test",
        "roles": ["client"],
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
