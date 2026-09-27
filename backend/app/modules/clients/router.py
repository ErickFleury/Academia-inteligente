from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_database_session
from app.integrations.cep import (
    CepAddress,
    PostalCodeLookup,
    PostalCodeNotFoundError,
    PostalCodeUnavailableError,
    ViaCepLookup,
)
from app.modules.biometrics.registration import RegistrationService
from app.modules.biometrics.router import Service as EnrollmentServiceDependency
from app.modules.clients.service import (
    ClientIdentityConflictError,
    ClientIdentityProvisioningError,
    ClientService,
    ClientSummary,
    ClientValidationError,
    DuplicateEmailError,
    normalize_postal_code,
    validate_client_data,
)
from app.modules.identity.authorization import require_roles
from app.modules.identity.keycloak_admin import KeycloakProvisioningError
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity

router = APIRouter(prefix="/clients", tags=["clients"])
client_service = ClientService()
postal_code_lookup: PostalCodeLookup = ViaCepLookup()


class ClientCreateRequest(BaseModel):
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


class ClientResponse(BaseModel):
    id: UUID
    person_id: UUID
    name: str
    first_name: str
    surname: str
    email: str
    cpf: str
    phone: str
    postal_code: str
    street: str
    number: str
    complement: str | None
    neighborhood: str
    city: str
    state: str
    client_active: bool
    identity_provisioned: bool
    created_at: str


def response_from_summary(summary: ClientSummary) -> ClientResponse:
    return ClientResponse(
        id=summary.id,
        person_id=summary.person_id,
        name=summary.name,
        first_name=summary.first_name,
        surname=summary.surname,
        email=summary.email,
        cpf=summary.cpf,
        phone=summary.phone,
        postal_code=summary.postal_code,
        street=summary.street,
        number=summary.number,
        complement=summary.complement,
        neighborhood=summary.neighborhood,
        city=summary.city,
        state=summary.state,
        client_active=summary.client_active,
        identity_provisioned=summary.identity_provisioned,
        created_at=summary.created_at.isoformat(),
    )


Administrator = Annotated[
    AuthenticatedIdentity,
    Depends(require_roles(get_authenticated_identity, "admin")),
]
DatabaseSession = Annotated[Session, Depends(get_database_session)]


def reconcile_pending_client_identity(client_id: UUID) -> None:
    """Attempt durable identity reconciliation outside the creation response."""
    if SessionLocal is None:
        return
    session = SessionLocal()
    try:
        client_service.provision_existing(session, client_id)
    except (ClientIdentityConflictError, ClientIdentityProvisioningError):
        # The durable reconciliation record is intentionally retained for an
        # authorized administrator to retry through the explicit API.
        pass
    finally:
        session.close()


class ClientUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    surname: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    cpf: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=32)
    postal_code: str | None = Field(default=None, max_length=16)
    street: str | None = Field(default=None, max_length=200)
    number: str | None = Field(default=None, max_length=40)
    complement: str | None = Field(default=None, max_length=200)
    neighborhood: str | None = Field(default=None, max_length=150)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=2)
    client_active: bool | None = None


class CepAddressResponse(BaseModel):
    street: str | None
    neighborhood: str | None
    city: str | None
    state: str | None


@router.get("/address-lookup", response_model=CepAddressResponse)
def lookup_address(
    postal_code: Annotated[str, Query(max_length=16)], administrator: Administrator
) -> CepAddressResponse:
    """Look up a CEP server-side; callers can always enter every field manually."""
    del administrator
    try:
        address: CepAddress = postal_code_lookup.lookup(normalize_postal_code(postal_code))
    except ClientValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from None
    except PostalCodeNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CEP not found") from None
    except PostalCodeUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="CEP lookup is unavailable"
        ) from None
    return CepAddressResponse(**address.__dict__)


class ClientRegistrationRequest(ClientCreateRequest):
    command_id: UUID
    enrollment_session_id: UUID | None = None


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientRegistrationRequest,
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
    administrator: Administrator,
    enrollment: EnrollmentServiceDependency,
) -> ClientResponse:
    """Persist a client, then reconcile its external identity asynchronously."""
    try:
        client = RegistrationService(enrollment).create(
            session,
            actor=administrator.subject,
            command_id=payload.command_id,
            enrollment_session_id=payload.enrollment_session_id,
            role="client",
            data=validate_client_data(
                **payload.model_dump(exclude={"command_id", "enrollment_session_id"})
            ),
            service=client_service,
        )
        if not client.identity_provisioned:
            background_tasks.add_task(reconcile_pending_client_identity, client.id)
        return response_from_summary(client)
    except ClientValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from None
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already uses this e-mail address",
        ) from None
    except ClientIdentityConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A conflicting Keycloak identity exists"
        ) from None
    except ClientIdentityProvisioningError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Client identity provisioning is pending",
        ) from None


@router.get("", response_model=list[ClientResponse])
def list_clients(
    session: DatabaseSession,
    administrator: Administrator,
    query: Annotated[str | None, Query(max_length=320)] = None,
) -> list[ClientResponse]:
    """List clients, optionally filtering by name or authoritative e-mail."""
    del administrator
    return [response_from_summary(client) for client in client_service.list(session, query)]


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: UUID, session: DatabaseSession, administrator: Administrator
) -> ClientResponse:
    """Return a client only to an authorized administrator."""
    del administrator
    client = client_service.get(session, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return response_from_summary(client)


@router.post("/{client_id}/provision-identity", response_model=ClientResponse)
def provision_client_identity(
    client_id: UUID, session: DatabaseSession, administrator: Administrator
) -> ClientResponse:
    """Reconcile a local client created before Keycloak provisioning existed."""
    del administrator
    try:
        client = client_service.provision_existing(session, client_id)
    except ClientIdentityConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A conflicting Keycloak identity exists"
        ) from None
    except ClientIdentityProvisioningError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Client identity provisioning is pending",
        ) from None
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return response_from_summary(client)


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    payload: ClientUpdateRequest,
    session: DatabaseSession,
    administrator: Administrator,
) -> ClientResponse:
    """Persist validated profile and application-account state changes."""
    del administrator
    try:
        client = client_service.update(
            session,
            client_id,
            first_name=payload.first_name,
            surname=payload.surname,
            email=payload.email,
            cpf=payload.cpf,
            phone=payload.phone,
            postal_code=payload.postal_code,
            street=payload.street,
            number=payload.number,
            complement=payload.complement,
            complement_provided="complement" in payload.model_fields_set,
            neighborhood=payload.neighborhood,
            city=payload.city,
            state=payload.state,
            client_active=payload.client_active,
        )
    except ClientValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from None
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already uses this e-mail address",
        ) from None
    except ClientIdentityConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A conflicting Keycloak identity exists"
        ) from None
    except ClientIdentityProvisioningError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Client identity provisioning is pending",
        ) from None
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return response_from_summary(client)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def erase_client(client_id: UUID, session: DatabaseSession, administrator: Administrator) -> None:
    """Perform the approved irreversible privacy erasure for one client."""
    del administrator
    try:
        erased = client_service.erase(session, client_id)
    except ClientIdentityProvisioningError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Client data erased; shared identity reconciliation is pending",
        ) from None
    except KeycloakProvisioningError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Client identity erasure is temporarily unavailable",
        ) from None
    if not erased:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
