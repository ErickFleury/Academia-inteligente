from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_database_session
from app.modules.clients.service import (
    ClientIdentityConflictError,
    ClientIdentityProvisioningError,
    ClientService,
    ClientSummary,
    ClientValidationError,
    DuplicateEmailError,
)
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity

router = APIRouter(prefix="/clients", tags=["clients"])
client_service = ClientService()


class ClientCreateRequest(BaseModel):
    name: str = Field(max_length=200)
    email: str = Field(max_length=320)


class ClientResponse(BaseModel):
    id: UUID
    name: str
    email: str
    account_active: bool
    identity_provisioned: bool
    created_at: str


def response_from_summary(summary: ClientSummary) -> ClientResponse:
    return ClientResponse(
        id=summary.id,
        name=summary.name,
        email=summary.email,
        account_active=summary.account_active,
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
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    account_active: bool | None = None


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreateRequest,
    background_tasks: BackgroundTasks,
    session: DatabaseSession,
    administrator: Administrator,
) -> ClientResponse:
    """Persist a client, then reconcile its external identity asynchronously."""
    del administrator
    try:
        client = client_service.create(session, payload.name, payload.email)
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
            name=payload.name,
            email=payload.email,
            account_active=payload.account_active,
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
