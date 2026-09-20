import asyncio
import json
from collections.abc import Generator
from dataclasses import dataclass
from urllib.parse import urlencode

import pytest
from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_database_session
from app.main import create_app
from app.modules.clients.models import Account, Client
from app.modules.clients.service import ClientService, ClientValidationError
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity


class FakeIdentityProvider:
    def __init__(self, identity: AuthenticatedIdentity) -> None:
        self.identity = identity

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        return self.identity


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


@dataclass
class ApiResponse:
    status_code: int
    body: object

    def json(self) -> object:
        return self.body


class AsgiClient:
    def __init__(self, app: FastAPI) -> None:
        self.app = app

    def post(self, path: str, json: dict[str, object]) -> ApiResponse:
        return self.request("POST", path, json)

    def patch(self, path: str, json: dict[str, object]) -> ApiResponse:
        return self.request("PATCH", path, json)

    def get(self, path: str, params: dict[str, str] | None = None) -> ApiResponse:
        query_string = f"?{urlencode(params)}" if params else ""
        return self.request("GET", f"{path}{query_string}")

    def request(
        self, method: str, url: str, payload: dict[str, object] | None = None
    ) -> ApiResponse:
        path, _, query_string = url.partition("?")
        request_body = json.dumps(payload).encode() if payload else b""
        sent: list[dict[str, object]] = []
        headers = [(b"authorization", b"Bearer test-token")]
        if payload:
            headers.append((b"content-type", b"application/json"))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": query_string.encode(),
            "headers": headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": request_body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            sent.append(message)

        asyncio.run(self.app(scope, receive, send))
        status_code = next(
            message["status"] for message in sent if message["type"] == "http.response.start"
        )
        body = next(message["body"] for message in sent if message["type"] == "http.response.body")
        return ApiResponse(status_code=status_code, body=json.loads(body))


@pytest.fixture
def api_client(database_session: Session) -> Generator[AsgiClient, None, None]:
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield database_session

    app.dependency_overrides[get_database_session] = override_database_session
    yield AsgiClient(app)
    app.dependency_overrides.clear()


def authenticate_as(monkeypatch: pytest.MonkeyPatch, *roles: str) -> None:
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity(subject="test-subject", username="test@example.test", roles=roles)
        ),
    )


def test_client_validation_rejects_invalid_data_without_persisting(
    monkeypatch: pytest.MonkeyPatch, api_client: AsgiClient, database_session: Session
) -> None:
    authenticate_as(monkeypatch, "admin")

    response = api_client.post("/clients", json={"name": "   ", "email": "invalid"})

    assert response.status_code == 422
    assert response.json() == {"detail": "Name is required"}
    assert database_session.scalars(select(Account)).all() == []
    assert database_session.scalars(select(Client)).all() == []


def test_client_service_validates_e_mail_address(database_session: Session) -> None:
    with pytest.raises(ClientValidationError, match="valid e-mail"):
        ClientService().create(database_session, "Ada Lovelace", "not-an-email")

    assert database_session.scalars(select(Account)).all() == []
    assert database_session.scalars(select(Client)).all() == []


def test_administrator_creates_client_and_normalizes_account_email(
    monkeypatch: pytest.MonkeyPatch, api_client: AsgiClient, database_session: Session
) -> None:
    authenticate_as(monkeypatch, "admin")

    response = api_client.post(
        "/clients", json={"name": "  Ada   Lovelace ", "email": " ADA@EXAMPLE.TEST "}
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body, dict)
    assert body["name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.test"
    assert body["id"]
    account = database_session.scalar(select(Account))
    client = database_session.scalar(select(Client))
    assert account is not None and client is not None
    assert client.account_id == account.id
    assert account.keycloak_subject is None
    assert account.account_active is True


def test_duplicate_email_is_rejected_for_inactive_account(
    monkeypatch: pytest.MonkeyPatch, api_client: AsgiClient, database_session: Session
) -> None:
    database_session.add(Account(email="ada@example.test", account_active=False))
    database_session.commit()
    authenticate_as(monkeypatch, "admin")

    response = api_client.post(
        "/clients", json={"name": "Ada Lovelace", "email": "ADA@example.test"}
    )

    assert response.status_code == 409
    assert database_session.scalars(select(Account)).all()[0].email == "ada@example.test"
    assert database_session.scalars(select(Client)).all() == []


def test_administrator_lists_searches_and_reads_client_detail(
    monkeypatch: pytest.MonkeyPatch, api_client: AsgiClient
) -> None:
    authenticate_as(monkeypatch, "admin")
    first = api_client.post("/clients", json={"name": "Ada Lovelace", "email": "ada@example.test"})
    api_client.post("/clients", json={"name": "Grace Hopper", "email": "grace@example.test"})

    listed = api_client.get("/clients")
    search_by_name = api_client.get("/clients", params={"query": "hopper"})
    search_by_email = api_client.get("/clients", params={"query": "ada@example"})
    detail = api_client.get(f"/clients/{first.json()['id']}")

    assert listed.status_code == 200
    assert [client["name"] for client in listed.json()] == ["Ada Lovelace", "Grace Hopper"]
    assert [client["email"] for client in search_by_name.json()] == ["grace@example.test"]
    assert [client["name"] for client in search_by_email.json()] == ["Ada Lovelace"]
    assert detail.status_code == 200
    assert detail.json()["email"] == "ada@example.test"


def test_client_role_cannot_access_client_records(
    monkeypatch: pytest.MonkeyPatch, api_client: AsgiClient
) -> None:
    authenticate_as(monkeypatch, "client")

    create_response = api_client.post(
        "/clients", json={"name": "Ada Lovelace", "email": "ada@example.test"}
    )
    list_response = api_client.get("/clients")
    detail_response = api_client.get("/clients/00000000-0000-0000-0000-000000000001")

    assert create_response.status_code == 403
    assert list_response.status_code == 403
    assert detail_response.status_code == 403


def test_administrator_updates_profile_and_state_with_persistence(
    monkeypatch: pytest.MonkeyPatch, api_client: AsgiClient, database_session: Session
) -> None:
    authenticate_as(monkeypatch, "admin")
    created = api_client.post(
        "/clients", json={"name": "Ada Lovelace", "email": "ada@example.test"}
    )
    assert created.status_code == 201
    created_body = created.json()
    assert isinstance(created_body, dict)
    client_id = created_body["id"]
    created_at = created_body["created_at"]

    updated = api_client.patch(
        f"/clients/{client_id}",
        json={"name": "  Ada   Byron ", "email": "ada.byron@example.test", "account_active": False},
    )
    reloaded = api_client.get(f"/clients/{client_id}")

    assert updated.status_code == 200
    assert updated.json()["name"] == "Ada Byron"
    assert updated.json()["email"] == "ada.byron@example.test"
    assert updated.json()["account_active"] is False
    assert reloaded.json()["created_at"] == created_at
    account = database_session.scalar(select(Account))
    client = database_session.scalar(select(Client))
    assert account is not None and client is not None
    assert account.account_active is False
    assert client.name == "Ada Byron"


def test_deactivated_linked_account_is_rejected_as_unauthenticated(
    monkeypatch: pytest.MonkeyPatch, api_client: AsgiClient, database_session: Session
) -> None:
    account = Account(
        email="deactivated@example.test",
        keycloak_subject="test-subject",
        account_active=False,
    )
    database_session.add(Client(name="Deactivated Client", account=account))
    database_session.commit()
    authenticate_as(monkeypatch, "client")

    response = api_client.get("/clients")

    assert response.status_code == 401
    assert database_session.scalar(select(Client)) is not None


def test_update_rejects_invalid_fields_without_partial_changes(
    monkeypatch: pytest.MonkeyPatch, api_client: AsgiClient
) -> None:
    authenticate_as(monkeypatch, "admin")
    created = api_client.post(
        "/clients", json={"name": "Ada Lovelace", "email": "ada@example.test"}
    )
    client_id = created.json()["id"]

    response = api_client.patch(
        f"/clients/{client_id}", json={"name": "Changed", "email": "invalid"}
    )
    reloaded = api_client.get(f"/clients/{client_id}")

    assert response.status_code == 422
    assert reloaded.json()["name"] == "Ada Lovelace"
    assert reloaded.json()["email"] == "ada@example.test"
