"""Instructor employee administration and durable identity reconciliation."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.clients.models import (
    Account,
    Employee,
    PersonProfile,
)
from app.modules.clients.service import ClientData, ClientValidationError
from app.modules.identity.keycloak_admin import (
    ClientIdentityProvisioner,
    KeycloakAdminClient,
    KeycloakProvisioningError,
)
from app.modules.identity.reconciliation import (
    identity_provisioned,
    lock_account,
    pending_records,
    queue_reconciliation,
    reconcile_account,
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
        identity_provisioned=identity_provisioned(employee.account),
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
        normalized_cnpj = normalize_cnpj(cnpj)
        email_account = session.scalar(select(Account).where(Account.email == data.email))
        cpf_profile = session.scalar(select(PersonProfile).where(PersonProfile.cpf == data.cpf))
        if email_account or cpf_profile:
            if (
                email_account is None
                or cpf_profile is None
                or email_account.id != cpf_profile.account_id
            ):
                raise EmployeeConflictError
            account = lock_account(session, email_account.id)
            if (
                account.employee is not None
                or account.email != data.email
                or account.person_profile.cpf != data.cpf
            ):
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
            account=account, specialization="instructor", cnpj=normalized_cnpj, active=True
        )
        session.add(employee)
        session.flush()
        queue_reconciliation(session, account, employee=True)
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
        account = lock_account(session, employee.account_id)
        if not pending_records(session, account.id):
            queue_reconciliation(session, account, employee=True)
        session.commit()
        try:
            reconcile_account(session, account.id, self.provisioner)
        except KeycloakProvisioningError as error:
            raise EmployeeProvisioningError from error
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
        normalized_cnpj = normalize_cnpj(cnpj) if cnpj_provided else employee.cnpj
        lock_account(session, employee.account_id)
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
        if cnpj_provided:
            employee.cnpj = normalized_cnpj
        if active is not None:
            employee.active = active
        employee.account.account_active = bool(
            (employee.account.client and employee.account.client.active) or employee.active
        )
        queue_reconciliation(session, employee.account, employee=True, refresh_intent=True)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise EmployeeConflictError from error
        if employee.account.keycloak_subject:
            return self.provision_existing(session, employee_id)
        return _summary(employee)

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
