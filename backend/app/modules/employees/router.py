from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_database_session
from app.modules.biometrics.registration import RegistrationService
from app.modules.biometrics.router import Service as EnrollmentServiceDependency
from app.modules.clients.service import ClientValidationError, validate_client_data
from app.modules.employees.service import (
    EmployeeConflictError,
    EmployeeProvisioningError,
    EmployeeService,
    EmployeeSummary,
)
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity

router = APIRouter(prefix="/employees", tags=["employees"])
employee_service = EmployeeService()
DatabaseSession = Annotated[Session, Depends(get_database_session)]
Administrator = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "admin"))
]


class EmployeeInput(BaseModel):
    first_name: str = Field(max_length=100)
    surname: str = Field(max_length=200)
    email: str = Field(max_length=320)
    cpf: str = Field(max_length=32)
    phone: str = Field(max_length=32)
    postal_code: str = Field(max_length=16)
    street: str = Field(max_length=200)
    number: str = Field(max_length=40)
    complement: str | None = Field(default=None, max_length=200)
    neighborhood: str = Field(max_length=150)
    city: str = Field(max_length=120)
    state: str = Field(max_length=2)
    cnpj: str | None = Field(default=None, max_length=32)
    specialization: str = "instructor"


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    surname: str | None = None
    email: str | None = None
    cpf: str | None = None
    phone: str | None = None
    postal_code: str | None = None
    street: str | None = None
    number: str | None = None
    complement: str | None = None
    neighborhood: str | None = None
    city: str | None = None
    state: str | None = None
    cnpj: str | None = None
    specialization: str | None = None
    employee_active: bool | None = None


class EmployeeResponse(EmployeeInput):
    id: UUID
    person_id: UUID
    name: str
    employee_active: bool
    identity_provisioned: bool
    created_at: str


def response(item: EmployeeSummary) -> EmployeeResponse:
    return EmployeeResponse(
        id=item.id,
        person_id=item.person_id,
        name=item.name,
        first_name=item.first_name,
        surname=item.surname,
        email=item.email,
        cpf=item.cpf,
        phone=item.phone,
        postal_code=item.postal_code,
        street=item.street,
        number=item.number,
        complement=item.complement,
        neighborhood=item.neighborhood,
        city=item.city,
        state=item.state,
        cnpj=item.cnpj,
        specialization=item.specialization,
        employee_active=item.employee_active,
        identity_provisioned=item.identity_provisioned,
        created_at=item.created_at.isoformat(),
    )


def reconcile(employee_id: UUID) -> None:
    if SessionLocal is None:
        return
    session = SessionLocal()
    try:
        employee_service.provision_existing(session, employee_id)
    except EmployeeProvisioningError:
        pass
    finally:
        session.close()


def error(exc: Exception) -> HTTPException:
    if isinstance(exc, ClientValidationError):
        return HTTPException(422, str(exc))
    if isinstance(exc, EmployeeConflictError):
        return HTTPException(409, "An incompatible account already exists")
    return HTTPException(503, "Employee identity provisioning is pending")


class EmployeeRegistrationRequest(EmployeeInput):
    command_id: UUID
    enrollment_session_id: UUID | None = None


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: EmployeeRegistrationRequest,
    tasks: BackgroundTasks,
    session: DatabaseSession,
    admin: Administrator,
    enrollment: EnrollmentServiceDependency,
) -> EmployeeResponse:
    try:
        item = RegistrationService(enrollment).create(
            session,
            actor=admin.subject,
            command_id=payload.command_id,
            enrollment_session_id=payload.enrollment_session_id,
            role="employee",
            data=validate_client_data(
                **payload.model_dump(
                    exclude={"cnpj", "specialization", "command_id", "enrollment_session_id"}
                )
            ),
            service=employee_service,
            cnpj=payload.cnpj,
            specialization=payload.specialization,
        )
    except (ClientValidationError, EmployeeConflictError, EmployeeProvisioningError) as exc:
        raise error(exc) from None
    tasks.add_task(reconcile, item.id)
    return response(item)


@router.get("", response_model=list[EmployeeResponse])
def list_employees(
    session: DatabaseSession,
    admin: Administrator,
    query: Annotated[str | None, Query(max_length=320)] = None,
) -> list[EmployeeResponse]:
    del admin
    return [response(item) for item in employee_service.list(session, query)]


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get(employee_id: UUID, session: DatabaseSession, admin: Administrator) -> EmployeeResponse:
    del admin
    item = employee_service.get(session, employee_id)
    if item is None:
        raise HTTPException(404, "Employee not found")
    return response(item)


@router.post("/{employee_id}/provision-identity", response_model=EmployeeResponse)
def provision(
    employee_id: UUID, session: DatabaseSession, admin: Administrator
) -> EmployeeResponse:
    del admin
    try:
        item = employee_service.provision_existing(session, employee_id)
    except EmployeeProvisioningError as exc:
        raise error(exc) from None
    if item is None:
        raise HTTPException(404, "Employee not found")
    return response(item)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update(
    employee_id: UUID, payload: EmployeeUpdate, session: DatabaseSession, admin: Administrator
) -> EmployeeResponse:
    del admin
    values = payload.model_dump()
    fields = {
        key: values[key]
        for key in (
            "first_name",
            "surname",
            "email",
            "cpf",
            "phone",
            "postal_code",
            "street",
            "number",
            "complement",
            "neighborhood",
            "city",
            "state",
        )
    }
    try:
        data = None
        provided = payload.model_fields_set.intersection(fields)
        if provided:
            existing = employee_service.get(session, employee_id)
            if existing is None:
                raise HTTPException(404, "Employee not found")
            if any(fields[key] is None for key in provided - {"complement"}):
                raise ClientValidationError("Required personal fields cannot be null")
            data = validate_client_data(
                **{
                    key: fields[key] if key in provided else getattr(existing, key)
                    for key in fields
                }
            )
        item = employee_service.update(
            session,
            employee_id,
            data,
            payload.cnpj,
            "cnpj" in payload.model_fields_set,
            payload.employee_active,
            payload.specialization,
        )
    except (ClientValidationError, EmployeeConflictError, EmployeeProvisioningError) as exc:
        raise error(exc) from None
    if item is None:
        raise HTTPException(404, "Employee not found")
    return response(item)
