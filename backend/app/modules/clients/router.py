from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.clients.service import (
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
    created_at: str


def response_from_summary(summary: ClientSummary) -> ClientResponse:
    return ClientResponse(
        id=summary.id,
        name=summary.name,
        email=summary.email,
        created_at=summary.created_at.isoformat(),
    )


Administrator = Annotated[
    AuthenticatedIdentity,
    Depends(require_roles(get_authenticated_identity, "admin")),
]
DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreateRequest, session: DatabaseSession, administrator: Administrator
) -> ClientResponse:
    """Create an account/client pair in one transaction."""
    del administrator
    try:
        return response_from_summary(client_service.create(session, payload.name, payload.email))
    except ClientValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from None
    except DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account already uses this e-mail address",
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
