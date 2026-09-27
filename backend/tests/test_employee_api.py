from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import select
from test_clients import AsgiClient, client_data
from test_employees import FakeProvisioner

from app.database import get_database_session
from app.modules.clients.models import Account, PersonProfile
from app.modules.employees import router as employee_router
from app.modules.employees.service import EmployeeService
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity

pytest_plugins = ["test_employees"]


@pytest.fixture
def api(session, monkeypatch):
    app = FastAPI()
    app.include_router(employee_router.router)
    app.dependency_overrides[get_database_session] = lambda: session
    app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        subject="admin", username="admin", roles=("admin",)
    )
    monkeypatch.setattr(employee_router, "employee_service", EmployeeService(FakeProvisioner()))
    monkeypatch.setattr(employee_router, "reconcile", lambda _: None)
    return AsgiClient(app)


def test_admin_create_search_view_and_clear_optional_fields(api, session):
    created = api.post("/employees", client_data(cnpj="11222333000181"))
    assert created.status_code == 201
    employee_id = created.json()["id"]
    assert not created.json()["identity_provisioned"]
    assert api.get("/employees", {"query": "Ada"}).json()[0]["id"] == employee_id
    assert api.get(f"/employees/{employee_id}").status_code == 200
    edited = api.patch(f"/employees/{employee_id}", {"complement": None, "cnpj": None})
    assert edited.status_code == 200
    assert edited.json()["complement"] is None and edited.json()["cnpj"] is None
    assert session.scalar(select(PersonProfile)).complement is None


@pytest.mark.parametrize(
    "changes",
    [
        {"cpf": "00000000000"},
        {"email": "invalid"},
        {"phone": "1"},
        {"first_name": None},
        {"state": "invalid"},
        {"cnpj": "11111111111111"},
    ],
)
def test_invalid_edits_are_422_and_preserve_saved_data(api, session, changes):
    employee_id = api.post("/employees", client_data()).json()["id"]
    before = api.get(f"/employees/{employee_id}").json()
    assert api.patch(f"/employees/{employee_id}", changes).status_code == 422
    assert api.get(f"/employees/{employee_id}").json() == before


@pytest.mark.parametrize("role", ["client", "instructor", "employee", "attendant"])
def test_non_admin_cannot_call_any_employee_endpoint(api, role):
    api.app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        subject="user", username="user", roles=(role,)
    )
    employee_id = uuid4()
    for method, path, body in [
        ("GET", "/employees", None),
        ("GET", f"/employees/{employee_id}", None),
        ("POST", "/employees", client_data()),
        ("PATCH", f"/employees/{employee_id}", {"employee_active": False}),
        ("POST", f"/employees/{employee_id}/provision-identity", {}),
    ]:
        assert api.request(method, path, body).status_code == 403


@pytest.mark.parametrize("role", ["admin", "attendant", "employee", "invented"])
def test_specialization_cannot_escalate_permissions(api, role):
    assert api.post("/employees", client_data(specialization=role)).status_code == 422
    employee_id = api.post("/employees", client_data()).json()["id"]
    assert api.patch(f"/employees/{employee_id}", {"specialization": role}).status_code == 422


@pytest.mark.parametrize(
    "changes",
    [
        {"email": "other@example.test"},
        {"cpf": "11144477735"},
        {},
    ],
)
def test_identity_conflicts_do_not_create_partial_accounts(api, session, changes):
    assert api.post("/employees", client_data()).status_code == 201
    assert api.post("/employees", client_data(**changes)).status_code == 409
    assert len(session.scalars(select(Account)).all()) == 1


def test_update_conflict_preserves_identity(api):
    first = api.post("/employees", client_data()).json()
    second = api.post(
        "/employees", client_data(email="other@example.test", cpf="11144477735")
    ).json()
    assert api.patch(f"/employees/{second['id']}", {"email": first["email"]}).status_code == 409
    assert api.get(f"/employees/{second['id']}").json()["email"] == second["email"]
