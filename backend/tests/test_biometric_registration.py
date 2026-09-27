from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_biometrics_enrollment import FakeFaces, enrolled_person, stage
from test_clients import AsgiClient, FakeProvisioner, client_data
from test_clients import database_session as database_session

from app.database import get_database_session
from app.main import create_app
from app.modules.biometrics.config import BiometricConfig
from app.modules.biometrics.enrollment import EnrollmentService
from app.modules.biometrics.models import (
    BiometricAudit,
    BiometricCleanupJob,
    BiometricCommand,
    BiometricEnrollment,
    EnrollmentSession,
)
from app.modules.biometrics.router import get_enrollment_service
from app.modules.clients import router as clients_router
from app.modules.clients.models import Account, Client, Employee
from app.modules.clients.service import ClientService
from app.modules.employees import router as employees_router
from app.modules.employees.service import EmployeeService
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity


@pytest.fixture
def api(database_session, monkeypatch):
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: database_session
    app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        "admin", None, ("admin",)
    )
    service = EnrollmentService(BiometricConfig(mode="pilot", api_key="fixture"), FakeFaces())
    app.dependency_overrides[get_enrollment_service] = lambda: service
    monkeypatch.setattr(clients_router, "client_service", ClientService(FakeProvisioner()))
    monkeypatch.setattr(employees_router, "employee_service", EmployeeService(FakeProvisioner()))
    monkeypatch.setattr(clients_router, "reconcile_pending_client_identity", lambda _: None)
    monkeypatch.setattr(employees_router, "reconcile", lambda _: None)
    return AsgiClient(app), service


@pytest.mark.parametrize("path", ["/clients", "/employees"])
def test_both_public_registration_endpoints_reject_missing_enrollment(api, database_session, path):
    http, _ = api
    result = http.post(path, client_data(command_id=str(uuid4())))
    assert result.status_code == 422 and result.json()["detail"] == "enrollment_required"
    assert database_session.scalars(select(Account)).all() == []
    assert database_session.scalars(select(BiometricCommand)).all() == []


@pytest.mark.parametrize("first_role,second_role", [("client", "employee"), ("employee", "client")])
def test_registration_consumes_once_and_second_role_reuses(
    api, database_session, first_role, second_role
):
    http, service = api
    routes = {"client": "/clients", "employee": "/employees"}
    staged = stage(service, database_session, role=first_role)
    command_id = str(uuid4())
    body = client_data(command_id=command_id, enrollment_session_id=str(staged))
    first = http.post(routes[first_role], body)
    assert first.status_code == 201
    assert http.post(routes[first_role], body).json()["id"] == first.json()["id"]
    # A command cannot be replayed with changed personal data.
    assert http.post(routes[first_role], body | {"surname": "Other"}).status_code == 409
    second = http.post(routes[second_role], client_data(command_id=str(uuid4())))
    assert second.status_code == 201
    assert second.json()["person_id"] == first.json()["person_id"]
    assert len(service.provider.enrolled) == 1
    assert len(database_session.scalars(select(Account)).all()) == 1
    assert len(database_session.scalars(select(BiometricEnrollment)).all()) == 1
    assert database_session.get(EnrollmentSession, staged).status == "consumed"


def test_invalid_form_and_wrong_actor_leave_stage_recoverable(api, database_session):
    http, service = api
    staged = stage(service, database_session)
    body = client_data(command_id=str(uuid4()), enrollment_session_id=str(staged))
    assert http.post("/clients", body | {"phone": "1"}).status_code == 422
    http.app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        "another-admin", None, ("admin",)
    )
    assert http.post("/clients", body).status_code == 404
    assert database_session.scalars(select(Account)).all() == []
    assert database_session.get(EnrollmentSession, staged).status == "ready"
    assert database_session.scalar(select(BiometricCleanupJob)) is not None


def test_disabled_mode_never_bypasses_mandatory_enrollment(api, database_session):
    http, _ = api
    http.app.dependency_overrides[get_enrollment_service] = lambda: EnrollmentService(
        BiometricConfig()
    )
    assert http.post("/clients", client_data(command_id=str(uuid4()))).status_code == 503
    assert database_session.scalars(select(Account)).all() == []


def test_full_erasure_removes_local_refs_and_detaches_only_pending_provider_cleanup(
    api, database_session
):
    _, service = api
    person_id = enrolled_person(service, database_session)
    client = database_session.scalar(select(Client).where(Client.account_id == person_id))
    subject = database_session.get(BiometricEnrollment, person_id).subject
    assert ClientService(FakeProvisioner()).erase(database_session, client.id)
    for model in (
        Account,
        EnrollmentSession,
        BiometricEnrollment,
        BiometricCommand,
        BiometricAudit,
    ):
        assert database_session.scalars(select(model)).all() == []
    job = database_session.get(BiometricCleanupJob, subject)
    assert job and job.account_id is None and job.session_id is None
    service.cleanup(database_session)
    assert database_session.scalars(select(BiometricCleanupJob)).all() == []
    assert subject in service.provider.deleted


def test_erasing_client_role_preserves_instructor_enrollment(api, database_session):
    http, service = api
    staged = stage(service, database_session)
    client = http.post(
        "/clients", client_data(command_id=str(uuid4()), enrollment_session_id=str(staged))
    ).json()
    assert http.post("/employees", client_data(command_id=str(uuid4()))).status_code == 201
    person_id = UUID(client["person_id"])
    subject = database_session.get(BiometricEnrollment, person_id).subject
    assert ClientService(FakeProvisioner()).erase(database_session, UUID(client["id"]))
    assert database_session.scalar(select(Employee)).account_id == person_id
    assert database_session.get(BiometricEnrollment, person_id).enabled
    service.cleanup(database_session)
    assert subject not in service.provider.deleted


def test_readiness_checks_shared_identity_without_exposing_capture_material(api, database_session):
    http, service = api
    person_id = enrolled_person(service, database_session)
    result = http.post(
        "/biometrics/enrollment-readiness", {"email": "ada@example.test", "cpf": "529.982.247-25"}
    ).json()
    assert result == {
        "person_id": str(person_id),
        "status": "enabled",
        "revision": 1,
        "cleanup_pending": False,
    }
    http.app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        "instructor", None, ("instructor",)
    )
    assert (
        http.post(
            "/biometrics/enrollment-readiness", {"email": "ada@example.test", "cpf": "52998224725"}
        ).status_code
        == 403
    )
