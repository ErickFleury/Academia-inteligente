"""Instructor employee administration and durable identity reconciliation."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.clients.models import (
    Account,
    ClientIdentityReconciliation,
    Employee,
    EmployeeIdentityReconciliation,
    PersonProfile,
)
from app.modules.clients.service import ClientData, ClientValidationError
from app.modules.identity.keycloak_admin import (
    ClientIdentityProvisioner,
    KeycloakAdminClient,
    KeycloakProvisioningError,
)


class EmployeeConflictError(Exception):
    pass


class EmployeeProvisioningError(Exception):
    pass


def normalize_cnpj(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    cnpj = "".join(character for character in value if character.isdigit())
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        raise ClientValidationError("A valid CNPJ is required")
    for size in (12, 13):
        weights = (
            (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
            if size == 12
            else (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
        )
        digit = 11 - sum(int(item) * weight for item, weight in zip(cnpj[:size], weights)) % 11
        if (0 if digit >= 10 else digit) != int(cnpj[size]):
            raise ClientValidationError("A valid CNPJ is required")
    return cnpj


@dataclass(frozen=True)
class EmployeeSummary(ClientData):
    id: UUID
    cnpj: str | None
    specialization: str
    employee_active: bool
    identity_provisioned: bool
    created_at: datetime


def _summary(employee: Employee) -> EmployeeSummary:
    profile = employee.account.person_profile
    if profile is None:
        raise ClientValidationError("Employee personal data is unavailable")
    return EmployeeSummary(
        first_name=profile.first_name,
        surname=profile.surname,
        email=employee.account.email,
        cpf=profile.cpf,
        phone=profile.phone,
        postal_code=profile.postal_code,
        street=profile.street,
        number=profile.number,
        complement=profile.complement,
        neighborhood=profile.neighborhood,
        city=profile.city,
        state=profile.state,
        id=employee.id,
        cnpj=employee.cnpj,
        specialization=employee.specialization,
        employee_active=employee.active,
        identity_provisioned=employee.account.keycloak_subject is not None,
        created_at=employee.created_at,
    )


class EmployeeService:
    def __init__(self, provisioner: ClientIdentityProvisioner | None = None) -> None:
        self.provisioner = provisioner or KeycloakAdminClient()

    def create(
        self, session: Session, data: ClientData, cnpj: str | None, specialization: str
    ) -> EmployeeSummary:
        if specialization != "instructor":
            raise ClientValidationError("Only instructor specialization is allowed")
        email_account = session.scalar(select(Account).where(Account.email == data.email))
        cpf_profile = session.scalar(select(PersonProfile).where(PersonProfile.cpf == data.cpf))
        if email_account or cpf_profile:
            if (
                email_account is None
                or cpf_profile is None
                or email_account.id != cpf_profile.account_id
            ):
                raise EmployeeConflictError
            account = email_account
            if account.employee is not None:
                raise EmployeeConflictError
            account.account_active = True
        else:
            account = Account(email=data.email, account_active=True)
            account.person_profile = PersonProfile(
                first_name=data.first_name,
                surname=data.surname,
                cpf=data.cpf,
                phone=data.phone,
                postal_code=data.postal_code,
                street=data.street,
                number=data.number,
                complement=data.complement,
                neighborhood=data.neighborhood,
                city=data.city,
                state=data.state,
            )
        employee = Employee(
            account=account, specialization="instructor", cnpj=normalize_cnpj(cnpj), active=True
        )
        session.add(employee)
        session.flush()
        session.add(EmployeeIdentityReconciliation(email=data.email, account_id=account.id))
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise EmployeeConflictError from error
        return _summary(employee)

    def list(self, session: Session, query: str | None = None) -> list[EmployeeSummary]:
        statement = select(Employee).options(
            joinedload(Employee.account).joinedload(Account.person_profile)
        )
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            statement = (
                statement.join(Employee.account)
                .join(Account.person_profile)
                .where(
                    or_(
                        Account.email.ilike(pattern),
                        PersonProfile.first_name.ilike(pattern),
                        PersonProfile.surname.ilike(pattern),
                    )
                )
            )
        return [
            _summary(item)
            for item in session.scalars(statement.order_by(Employee.created_at)).all()
        ]

    def get(self, session: Session, employee_id: UUID) -> EmployeeSummary | None:
        employee = self._employee(session, employee_id)
        return _summary(employee) if employee else None

    def provision_existing(self, session: Session, employee_id: UUID) -> EmployeeSummary | None:
        employee = self._employee(session, employee_id)
        if employee is None:
            return None
        pending = session.scalar(
            select(EmployeeIdentityReconciliation).where(
                EmployeeIdentityReconciliation.account_id == employee.account_id
            )
        )
        if pending is None:
            pending = EmployeeIdentityReconciliation(
                email=employee.account.email, account_id=employee.account_id
            )
            session.add(pending)
            session.commit()
        profile = employee.account.person_profile
        client_pending = session.scalar(
            select(ClientIdentityReconciliation).where(
                ClientIdentityReconciliation.account_id == employee.account_id
            )
        )
        if employee.account.keycloak_subject:
            try:
                self.provisioner.update_client_identity(
                    employee.account.keycloak_subject,
                    employee.account.email,
                    profile.first_name,
                    profile.surname,
                )
                self.provisioner.reconcile_application_roles(
                    employee.account.keycloak_subject, self._roles(employee)
                )
            except KeycloakProvisioningError as error:
                raise EmployeeProvisioningError from error
            session.delete(pending)
            if client_pending:
                session.delete(client_pending)
            session.commit()
            return _summary(employee)
        reconciliation_id = client_pending.id if client_pending else pending.id
        try:
            subject = self.provisioner.ensure_employee_identity(
                employee.account.email,
                profile.first_name,
                profile.surname,
                reconciliation_id,
                pending.keycloak_subject
                or (client_pending.keycloak_subject if client_pending else None),
                self._roles(employee),
                True,
            )
        except KeycloakProvisioningError as error:
            pending.keycloak_subject = error.subject
            if client_pending:
                client_pending.keycloak_subject = error.subject
            session.commit()
            raise EmployeeProvisioningError from error
        employee.account.keycloak_subject = subject
        session.delete(pending)
        if client_pending:
            session.delete(client_pending)
        session.commit()
        return _summary(employee)

    def update(
        self,
        session: Session,
        employee_id: UUID,
        data: ClientData | None,
        cnpj: str | None,
        cnpj_provided: bool,
        active: bool | None,
        specialization: str | None,
    ) -> EmployeeSummary | None:
        employee = self._employee(session, employee_id)
        if employee is None:
            return None
        if specialization is not None and specialization != "instructor":
            raise ClientValidationError("Only instructor specialization is allowed")
        profile = employee.account.person_profile
        if data:
            other = session.scalar(
                select(PersonProfile).where(
                    PersonProfile.cpf == data.cpf, PersonProfile.account_id != employee.account_id
                )
            )
            other_account = session.scalar(
                select(Account).where(
                    Account.email == data.email, Account.id != employee.account_id
                )
            )
            if other or other_account:
                raise EmployeeConflictError
            profile.first_name, profile.surname, profile.cpf, profile.phone = (
                data.first_name,
                data.surname,
                data.cpf,
                data.phone,
            )
            profile.postal_code, profile.street, profile.number, profile.complement = (
                data.postal_code,
                data.street,
                data.number,
                data.complement,
            )
            profile.neighborhood, profile.city, profile.state, employee.account.email = (
                data.neighborhood,
                data.city,
                data.state,
                data.email,
            )
            if employee.account.client:
                employee.account.client.name = data.name
            if employee.account.keycloak_subject:
                try:
                    self.provisioner.update_client_identity(
                        employee.account.keycloak_subject, data.email, data.first_name, data.surname
                    )
                except KeycloakProvisioningError as error:
                    session.rollback()
                    raise EmployeeProvisioningError from error
        if cnpj_provided:
            employee.cnpj = normalize_cnpj(cnpj)
        if active is not None:
            employee.active = active
        if employee.account.keycloak_subject:
            try:
                self.provisioner.reconcile_application_roles(
                    employee.account.keycloak_subject, self._roles(employee)
                )
            except KeycloakProvisioningError as error:
                session.rollback()
                raise EmployeeProvisioningError from error
        employee.account.account_active = bool(
            (employee.account.client and employee.account.client.active) or employee.active
        )
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise EmployeeConflictError from error
        return _summary(employee)

    @staticmethod
    def _roles(employee: Employee) -> set[str]:
        roles: set[str] = set()
        if employee.account.client and employee.account.client.active:
            roles.add("client")
        if employee.active:
            roles.update({"employee", "instructor"})
        return roles

    @staticmethod
    def _employee(session: Session, employee_id: UUID) -> Employee | None:
        return session.scalar(
            select(Employee)
            .options(
                joinedload(Employee.account).joinedload(Account.person_profile),
                joinedload(Employee.account).joinedload(Account.client),
            )
            .where(Employee.id == employee_id)
        )
