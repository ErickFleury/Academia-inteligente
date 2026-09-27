"""Shared-account lifecycle regressions; all provider I/O is in-memory."""

from dataclasses import asdict
from datetime import timedelta

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from test_clients import AsgiClient, FakeIdentityProvider
from test_employees import person
from test_employees import session as session

from app.database import get_database_session
from app.main import create_app
from app.modules.clients import router as client_router
from app.modules.clients.models import (
    Account,
    Client,
    ClientIdentityReconciliation,
    Employee,
    EmployeeIdentityReconciliation,
    PersonProfile,
)
from app.modules.clients.service import (
    ClientIdentityProvisioningError,
    ClientService,
    ClientValidationError,
)
from app.modules.employees.service import EmployeeProvisioningError, EmployeeService
from app.modules.identity import router as identity_router
from app.modules.identity.keycloak_admin import (
    KeycloakAdminClient,
    KeycloakAdminConfig,
    KeycloakIdentityConflictError,
    KeycloakProvisioningError,
)
from app.modules.identity.reconciliation import pending_records
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.progress.models import ProgressUpdate


class MemoryKeycloak(KeycloakAdminClient):
    """Exercise production reconciliation and marker checks, replacing only HTTP."""

    def __init__(self):
        super().__init__(
            KeycloakAdminConfig("http://unused", "test", "fake", "fake", "web", "http://unused")
        )
        self.user = None
        self.roles = {"unmanaged"}
        self.fail_email = False
        self.fail_roles = False
        self.fail_token = False
        self.emails = 0
        self.created = 0
        self.deleted = []
        self.removed_roles = []

    def _access_token(self):
        if self.fail_token:
            raise KeycloakProvisioningError("simulated unavailable provider")
        return "fake"

    def _request(self, method, path, token, payload=None, subject=None):
        if path.endswith("/users") and method == "POST":
            if self.user:
                raise KeycloakIdentityConflictError("duplicate email")
            self.user = dict(payload)
            self.user["id"] = "shared-subject"
            self.created += 1
            return "http://unused/users/shared-subject"
        if "/users?" in path and method == "GET":
            # Real adapter validates the marker returned by this search as well.
            return [self.user] if self.user else []
        if path.endswith("/users/shared-subject"):
            if method == "GET":
                return self.user
            if method == "DELETE":
                self.deleted.append(subject)
                self.user = None
                return None
            self.user.update(payload)
            return None
        if "/execute-actions-email?" in path:
            if self.fail_email:
                raise KeycloakProvisioningError("simulated SMTP failure", subject)
            assert payload == ["UPDATE_PASSWORD"]
            self.emails += 1
            return None
        if path.endswith("/role-mappings/realm"):
            if self.fail_roles:
                raise KeycloakProvisioningError("simulated role failure", subject)
            if method == "GET":
                return [{"name": role} for role in self.roles]
            names = {role["name"] for role in payload}
            if method == "DELETE":
                self.removed_roles.append(names)
                self.roles -= names
            else:
                self.roles |= names
            return None
        if "/roles/" in path:
            return {"name": path.rsplit("/", 1)[1]}
        raise AssertionError((method, path))


def make_employee(session, fake):
    service = EmployeeService(fake)
    employee = service.create(session, person(), None, "instructor")
    service.provision_existing(session, employee.id)
    return service, employee


def make_dual(session, fake):
    employees, employee = make_employee(session, fake)
    clients = ClientService(fake)
    client = clients.create(session, person())
    clients.provision_existing(session, client.id)
    return employees, employee, clients, client


def update_client(service, session, client_id, **changes):
    fields = {key: None for key in asdict(person())}
    fields.update(complement_provided=False, client_active=None)
    fields.update(changes)
    return service.update(session, client_id, **fields)


def test_client_added_to_instructor_is_pending_and_schedules_role_grant(session, monkeypatch):
    from uuid import UUID, uuid4

    fake = MemoryKeycloak()
    make_employee(session, fake)
    clients = ClientService(fake)
    monkeypatch.setattr(client_router, "client_service", clients)
    tasks = BackgroundTasks()
    from biometric_fixtures import SyntheticFaces

    from app.modules.biometrics.config import BiometricConfig
    from app.modules.biometrics.enrollment import EnrollmentService

    enrollment = EnrollmentService(
        BiometricConfig(mode="pilot", api_key="fixture"), SyntheticFaces()
    )
    actor = AuthenticatedIdentity("admin", None, ("admin",))
    stage = enrollment.create(
        session, actor.subject, uuid4(), email=person().email, cpf=person().cpf, role="client"
    )
    stage_id = UUID(stage["session_id"])
    enrollment.capture(session, actor.subject, stage_id, uuid4(), b"synthetic")
    result = client_router.create_client(
        client_router.ClientRegistrationRequest(
            **asdict(person()), command_id=uuid4(), enrollment_session_id=stage_id
        ),
        tasks,
        session,
        actor,
        enrollment,
    )
    assert not result.identity_provisioned
    assert len(tasks.tasks) == 1
    assert clients.provision_existing(session, result.id).identity_provisioned
    assert fake.roles == {"client", "employee", "instructor", "unmanaged"}
    assert fake.created == fake.emails == 1


def test_client_on_inactive_employee_reactivates_only_client(session):
    fake = MemoryKeycloak()
    employees, employee = make_employee(session, fake)
    employees.update(session, employee.id, None, None, False, False, None)
    clients = ClientService(fake)
    client = clients.create(session, person())
    clients.provision_existing(session, client.id)
    assert session.scalar(select(Account)).account_active
    assert not session.scalar(select(Employee)).active
    assert fake.roles == {"client", "unmanaged"}


@pytest.mark.parametrize("employee_first", [True, False])
@pytest.mark.parametrize("retry_employee", [True, False])
def test_partial_first_access_then_other_role_recovers_from_either_endpoint(
    session,
    employee_first,
    retry_employee,
):
    fake = MemoryKeycloak()
    employees, clients = EmployeeService(fake), ClientService(fake)
    fake.fail_email = True
    if employee_first:
        employee = employees.create(session, person(), None, "instructor")
        with pytest.raises(EmployeeProvisioningError):
            employees.provision_existing(session, employee.id)
        client = clients.create(session, person())
    else:
        client = clients.create(session, person())
        with pytest.raises(ClientIdentityProvisioningError):
            clients.provision_existing(session, client.id)
        employee = employees.create(session, person(), None, "instructor")
    account = session.scalar(select(Account))
    marker = pending_records(session, account.id)[0]
    assert marker.keycloak_subject == "shared-subject"
    # An early outage must not discard the external reference.
    fake.fail_token = True
    with pytest.raises(EmployeeProvisioningError):
        employees.provision_existing(session, employee.id)
    assert pending_records(session, account.id)[0].keycloak_subject == "shared-subject"
    fake.fail_token = fake.fail_email = False
    if retry_employee:
        employees.provision_existing(session, employee.id)
    else:
        clients.provision_existing(session, client.id)
    assert account.keycloak_subject == "shared-subject"
    assert not pending_records(session, account.id)
    assert fake.roles == {"client", "employee", "instructor", "unmanaged"}
    assert fake.created == fake.emails == 1
    clients.provision_existing(session, client.id)
    employees.provision_existing(session, employee.id)
    assert fake.emails == 1


@pytest.mark.parametrize("via_employee", [True, False])
def test_local_deactivation_and_shared_update_survive_provider_failure(session, via_employee):
    fake = MemoryKeycloak()
    employees, employee, clients, client = make_dual(session, fake)
    fake.fail_roles = True
    if via_employee:
        with pytest.raises(EmployeeProvisioningError):
            employees.update(
                session,
                employee.id,
                person(email="changed@example.test", surname="Novo"),
                None,
                False,
                False,
                None,
            )
    else:
        with pytest.raises(ClientIdentityProvisioningError):
            update_client(
                clients,
                session,
                client.id,
                email="changed@example.test",
                surname="Novo",
                client_active=False,
            )
    session.expire_all()
    account = session.scalar(select(Account))
    assert account.email == fake.user["email"] == "changed@example.test"
    assert account.person_profile.surname == fake.user["lastName"] == "Novo"
    assert account.client.name == "Maria Novo"
    assert account.account_active
    assert account.employee.active is (not via_employee)
    assert account.client.active is via_employee
    assert pending_records(session, account.id)
    assert not employees.get(session, employee.id).identity_provisioned
    assert not clients.get(session, client.id).identity_provisioned
    fake.fail_roles = False
    # Retry through the OTHER role: no lost name/email intent or duplicate invitation.
    if via_employee:
        clients.provision_existing(session, client.id)
        assert fake.roles == {"client", "unmanaged"}
    else:
        employees.provision_existing(session, employee.id)
        assert fake.roles == {"employee", "instructor", "unmanaged"}
    assert not pending_records(session, account.id)
    assert fake.emails == 1


def test_invalid_cnpj_never_updates_external_or_local_identity(session):
    fake = MemoryKeycloak()
    employees, employee = make_employee(session, fake)
    with pytest.raises(ClientValidationError):
        employees.update(
            session,
            employee.id,
            person(email="changed@example.test"),
            "11111111111111",
            True,
            None,
            None,
        )
    assert session.scalar(select(Account)).email == fake.user["email"] == person().email


@pytest.mark.parametrize("active", [True, False])
@pytest.mark.parametrize("outage", [True, False])
def test_erasing_client_preserves_employee_identity_and_retryable_role_removal(
    session, active, outage
):
    fake = MemoryKeycloak()
    employees, employee, clients, client = make_dual(session, fake)
    session.add(ProgressUpdate(client_id=client.id, content="Client-owned data"))
    session.commit()
    if not active:
        employees.update(session, employee.id, None, None, False, False, None)
    fake.fail_roles = outage
    if outage:
        with pytest.raises(ClientIdentityProvisioningError):
            clients.erase(session, client.id)
    else:
        assert clients.erase(session, client.id)
    session.expire_all()
    account = session.scalar(select(Account))
    assert session.scalar(select(Client)) is None
    assert session.scalar(select(ProgressUpdate)) is None
    assert session.scalar(select(Employee)).id == employee.id
    assert session.scalar(select(PersonProfile)) is not None
    assert account.account_active is active
    assert account.keycloak_subject == "shared-subject"
    assert not fake.deleted
    if outage:
        assert pending_records(session, account.id)
        fake.fail_roles = False
        employees.provision_existing(session, employee.id)
    assert fake.roles == ({"employee", "instructor", "unmanaged"} if active else {"unmanaged"})


@pytest.mark.parametrize(
    "client_active,employee_active", [(True, False), (False, True), (True, True), (False, False)]
)
def test_stale_mixed_identity_keeps_only_locally_active_permissions(
    session, monkeypatch, client_active, employee_active
):
    fake = MemoryKeycloak()
    employees, employee, clients, client = make_dual(session, fake)
    employees.update(session, employee.id, None, None, False, employee_active, None)
    update_client(clients, session, client.id, client_active=client_active)
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity(
                "shared-subject", None, ("client", "employee", "instructor", "default-roles")
            )
        ),
    )
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: session
    api = AsgiClient(app)
    response = api.get("/identity/me")
    if not client_active and not employee_active:
        assert response.status_code == 401
    else:
        assert response.status_code == 200
        assert ("client" in response.body["roles"]) is client_active
        assert ("instructor" in response.body["roles"]) is employee_active
        if not client_active:
            assert api.get("/onboarding/me").status_code == 403
        if not employee_active:
            assert api.get("/instructor/social/feed").status_code == 403
    assert api.get("/identity/admin").status_code in {401, 403}


def test_reconciliation_preserves_desired_and_unmanaged_roles_before_failed_addition():
    fake = MemoryKeycloak()
    fake.roles = {"client", "unmanaged"}
    original = fake._request

    def failing_lookup(method, path, token, payload=None, subject=None):
        if "/roles/" in path:
            raise KeycloakProvisioningError("simulated failure", subject)
        return original(method, path, token, payload, subject)

    fake._request = failing_lookup
    with pytest.raises(KeycloakProvisioningError):
        fake.reconcile_application_roles("shared-subject", {"client", "instructor", "employee"})
    assert fake.roles == {"client", "unmanaged"}
    assert not fake.removed_roles


def test_unknown_external_identity_is_not_adopted_by_email(session):
    fake = MemoryKeycloak()
    fake.user = {"id": "shared-subject", "email": person().email, "attributes": {}}
    employees = EmployeeService(fake)
    employee = employees.create(session, person(), None, "instructor")
    with pytest.raises(EmployeeProvisioningError):
        employees.provision_existing(session, employee.id)
    assert session.scalar(select(Account)).keycloak_subject is None
    assert fake.emails == 0


def test_completion_commit_failure_retains_recovery_record(session, monkeypatch):
    fake = MemoryKeycloak()
    employees, employee = make_employee(session, fake)
    original_commit = session.commit

    def failed_completion():
        if any(
            isinstance(row, (ClientIdentityReconciliation, EmployeeIdentityReconciliation))
            for row in session.deleted
        ):
            raise OperationalError("simulated commit", None, Exception("simulated"))
        original_commit()

    monkeypatch.setattr(session, "commit", failed_completion)
    with pytest.raises(EmployeeProvisioningError):
        employees.update(
            session, employee.id, person(email="changed@example.test"), None, False, None, None
        )
    account = session.scalar(select(Account))
    assert pending_records(session, account.id)
    assert account.email == fake.user["email"] == "changed@example.test"
    monkeypatch.setattr(session, "commit", original_commit)
    assert employees.provision_existing(session, employee.id).identity_provisioned
    assert fake.emails == 1


def test_legacy_conflicting_role_markers_recover_and_pending_email_edit_is_safe(session):
    fake = MemoryKeycloak()
    employees = EmployeeService(fake)
    employee = employees.create(session, person(), None, "instructor")
    fake.fail_email = True
    with pytest.raises(EmployeeProvisioningError):
        employees.provision_existing(session, employee.id)
    account = session.scalar(select(Account))
    # Reproduce the old two-table state, including the copied subject on the wrong marker.
    account.client = Client(name=person().name, active=True)
    session.add(
        ClientIdentityReconciliation(
            account_id=account.id,
            email=account.email,
            operation="link_existing",
            keycloak_subject="shared-subject",
            created_at=pending_records(session, account.id)[0].created_at - timedelta(days=1),
        )
    )
    session.commit()
    employees.update(
        session, employee.id, person(email="changed@example.test"), None, False, None, None
    )
    fake.fail_email = False
    assert ClientService(fake).provision_existing(session, account.client.id).identity_provisioned
    assert fake.user["email"] == "changed@example.test"
    assert fake.created == fake.emails == 1
    assert not pending_records(session, account.id)


def test_linking_employee_preserves_legacy_pending_email_intent(session):
    fake = MemoryKeycloak()
    clients = ClientService(fake)
    client = clients.create(session, person())
    clients.provision_existing(session, client.id)
    account = session.scalar(select(Account))
    session.add(
        ClientIdentityReconciliation(
            account_id=account.id,
            email="requested@example.test",
            operation="email_update",
            keycloak_subject="shared-subject",
        )
    )
    session.commit()
    employees = EmployeeService(fake)
    employee = employees.create(session, person(), None, "instructor")
    employees.provision_existing(session, employee.id)
    assert account.email == fake.user["email"] == "requested@example.test"
    assert fake.emails == 1


def test_pending_client_erasure_preserves_employee_first_access_recovery(session):
    fake = MemoryKeycloak()
    clients = ClientService(fake)
    client = clients.create(session, person())
    fake.fail_email = True
    with pytest.raises(ClientIdentityProvisioningError):
        clients.provision_existing(session, client.id)
    employees = EmployeeService(fake)
    employee = employees.create(session, person(), None, "instructor")
    assert clients.erase(session, client.id)
    fake.fail_email = False
    assert employees.provision_existing(session, employee.id).identity_provisioned
    assert fake.roles == {"employee", "instructor", "unmanaged"}
    assert fake.created == fake.emails == 1
    assert not fake.deleted
