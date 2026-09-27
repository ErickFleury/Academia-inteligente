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
from app.integrations.cep import CepAddress, PostalCodeNotFoundError, PostalCodeUnavailableError
from app.main import create_app
from app.modules.clients import router as clients_router
from app.modules.clients.models import Account, Client, PersonProfile
from app.modules.clients.service import ClientService
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity


class FakeIdentityProvider:
    def __init__(self, identity: AuthenticatedIdentity) -> None:
        self.identity = identity

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        return self.identity


class FakeProvisioner:
    def __init__(self) -> None:
        self.subjects: dict[str, str] = {}
        self.updated: list[tuple[str, str, str, str]] = []

    def ensure_client_identity(self, email, first_name, surname, reconciliation_id, subject):
        resolved = subject or self.subjects.setdefault(email, f"subject-{len(self.subjects) + 1}")
        self.subjects[email] = resolved
        self.updated.append((resolved, email, first_name, surname))
        return resolved

    def update_client_identity(self, subject, email, first_name, surname):
        self.updated.append((subject, email, first_name, surname))

    def delete_identity(self, subject):
        return None

    def reconcile_application_roles(self, subject, roles):
        return None


class FakeCepLookup:
    def __init__(self, result: CepAddress | Exception) -> None:
        self.result = result

    def lookup(self, postal_code: str) -> CepAddress:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


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
    def __init__(self, app: FastAPI, prepare_registration=None) -> None:
        self.app = app
        self.prepare_registration = prepare_registration

    def request(
        self, method: str, url: str, payload: dict[str, object] | None = None
    ) -> ApiResponse:
        path, _, query = url.partition("?")
        if self.prepare_registration and method == "POST" and path in {"/clients", "/employees"}:
            payload = self.prepare_registration(
                "client" if path == "/clients" else "employee", payload
            )
        body = json.dumps(payload).encode() if payload is not None else b""
        sent: list[dict[str, object]] = []
        headers = [(b"authorization", b"Bearer test-token")]
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
            "query_string": query.encode(),
            "headers": headers,
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

        async def receive() -> dict[str, object]:
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message: dict[str, object]) -> None:
            sent.append(message)

        asyncio.run(self.app(scope, receive, send))
        status_code = next(item["status"] for item in sent if item["type"] == "http.response.start")
        response_body = next(item["body"] for item in sent if item["type"] == "http.response.body")
        return ApiResponse(status_code, json.loads(response_body))

    def post(self, path: str, json: dict[str, object]) -> ApiResponse:
        return self.request("POST", path, json)

    def patch(self, path: str, json: dict[str, object]) -> ApiResponse:
        return self.request("PATCH", path, json)

    def get(self, path: str, params: dict[str, str] | None = None) -> ApiResponse:
        return self.request("GET", f"{path}?{urlencode(params)}" if params else path)


def client_data(**changes: object) -> dict[str, object]:
    data: dict[str, object] = {
        "first_name": "Ada",
        "surname": "Lovelace",
        "email": "ada@example.test",
        "cpf": "529.982.247-25",
        "phone": "(11) 99876-5432",
        "postal_code": "01001-000",
        "street": "Praça da Sé",
        "number": "1",
        "complement": "Sala 2",
        "neighborhood": "Sé",
        "city": "São Paulo",
        "state": "sp",
    }
    data.update(changes)
    return data


def authenticate_as(monkeypatch: pytest.MonkeyPatch, *roles: str) -> None:
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity(subject="test-subject", username="test@example.test", roles=roles)
        ),
    )


@pytest.fixture
def api_client(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> Generator[AsgiClient, None, None]:
    app = create_app()
    monkeypatch.setattr(clients_router, "client_service", ClientService(FakeProvisioner()))
    monkeypatch.setattr(
        clients_router,
        "postal_code_lookup",
        FakeCepLookup(CepAddress("Praça da Sé", "Sé", "São Paulo", "SP")),
    )
    monkeypatch.setattr(clients_router, "reconcile_pending_client_identity", lambda client_id: None)
    app.dependency_overrides[get_database_session] = lambda: database_session
    from biometric_fixtures import prepare_enrolled_registration

    yield AsgiClient(app, prepare_enrolled_registration(app, database_session))
    app.dependency_overrides.clear()


def test_administrator_creates_normalized_authoritative_person_profile(
    monkeypatch, api_client, database_session
) -> None:
    authenticate_as(monkeypatch, "admin")
    response = api_client.post(
        "/clients", client_data(first_name="  Ada ", surname=" Byron  da  Silva ")
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ada Byron da Silva"
    assert body["cpf"] == "52998224725"
    assert body["phone"] == "11998765432"
    assert body["postal_code"] == "01001000"
    profile = database_session.scalar(select(PersonProfile))
    client = database_session.scalar(select(Client))
    assert profile is not None and client is not None
    assert profile.full_name == body["name"]
    assert client.name == profile.full_name
    assert client.active is True


@pytest.mark.parametrize("cpf", ["111.111.111-11", "529.982.247-24"])
def test_invalid_cpf_is_rejected_without_persisting(
    monkeypatch, api_client, database_session, cpf
) -> None:
    authenticate_as(monkeypatch, "admin")
    response = api_client.post("/clients", client_data(cpf=cpf))
    assert response.status_code == 422
    assert database_session.scalars(select(Account)).all() == []


def test_cpf_is_globally_unique(monkeypatch, api_client) -> None:
    authenticate_as(monkeypatch, "admin")
    assert api_client.post("/clients", client_data()).status_code == 201
    response = api_client.post("/clients", client_data(email="other@example.test"))
    assert response.status_code == 409


def test_profile_edit_updates_keycloak_name_and_email_and_client_activity(
    monkeypatch, api_client, database_session
) -> None:
    authenticate_as(monkeypatch, "admin")
    created = api_client.post("/clients", client_data())
    client_id = created.json()["id"]
    assert api_client.post(f"/clients/{client_id}/provision-identity", {}).status_code == 200
    response = api_client.patch(
        f"/clients/{client_id}",
        {
            "surname": "Byron",
            "email": "ada.byron@example.test",
            "complement": None,
            "client_active": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Ada Byron"
    assert response.json()["complement"] is None
    assert response.json()["client_active"] is False
    account = database_session.scalar(select(Account))
    profile = database_session.scalar(select(PersonProfile))
    assert account is not None and profile is not None
    assert account.email == "ada.byron@example.test"
    assert profile.surname == "Byron"
    fake = clients_router.client_service.provisioner
    assert (account.keycloak_subject, "ada.byron@example.test", "Ada", "Byron") in fake.updated


def test_inactive_client_cannot_authenticate_even_when_account_is_active(
    monkeypatch, api_client, database_session
) -> None:
    authenticate_as(monkeypatch, "admin")
    created = api_client.post("/clients", client_data())
    client = database_session.scalar(select(Client))
    client.account.keycloak_subject = "test-subject"
    client.active = False
    database_session.commit()
    authenticate_as(monkeypatch, "client")
    assert api_client.get("/identity/me").status_code == 401
    assert created.status_code == 201


def test_cep_lookup_returns_assistance_and_controlled_failures(monkeypatch, api_client) -> None:
    authenticate_as(monkeypatch, "admin")
    success = api_client.get("/clients/address-lookup", {"postal_code": "01001-000"})
    assert success.status_code == 200
    assert success.json()["city"] == "São Paulo"
    monkeypatch.setattr(
        clients_router, "postal_code_lookup", FakeCepLookup(PostalCodeNotFoundError())
    )
    assert api_client.get("/clients/address-lookup", {"postal_code": "01001000"}).status_code == 404
    monkeypatch.setattr(
        clients_router, "postal_code_lookup", FakeCepLookup(PostalCodeUnavailableError())
    )
    assert api_client.get("/clients/address-lookup", {"postal_code": "01001000"}).status_code == 503
