from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.clients.models import Client
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.progress.models import ProgressUpdate
from app.modules.progress.service import (
    ProgressForbiddenError,
    ProgressNotFoundError,
    ProgressService,
    ProgressStateError,
)

router = APIRouter(prefix="/progress", tags=["progress"])
service = ProgressService()
ClientUser = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "client"))
]
Administrator = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "admin"))
]
DatabaseSession = Annotated[Session, Depends(get_database_session)]


class UpdateInput(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    visibility: Literal["private", "shared"] = "private"


class UpdatePatch(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=2000)
    visibility: Literal["private", "shared"] | None = None


class ModerationInput(BaseModel):
    action: Literal["hide", "restore", "delete"]
    reason: str | None = Field(default=None, max_length=500)


class UpdateResponse(BaseModel):
    id: UUID
    author_name: str
    content: str
    visibility: str
    moderation_status: str
    moderation_reason: str | None
    is_own: bool = False
    created_at: datetime
    updated_at: datetime


def response(update: ProgressUpdate, client: Client, is_own: bool = False) -> UpdateResponse:
    return UpdateResponse(
        id=update.id,
        author_name=client.name,
        content=update.content or "",
        visibility=update.visibility,
        moderation_status=update.moderation_status,
        moderation_reason=update.moderation_reason,
        is_own=is_own,
        created_at=update.created_at,
        updated_at=update.updated_at,
    )


def own_response(session: Session, update: ProgressUpdate) -> UpdateResponse:
    return response(update, session.get(Client, update.client_id), True)


def error(error: Exception) -> HTTPException:
    if isinstance(error, ProgressNotFoundError):
        return HTTPException(401, "Authenticated client not found")
    if isinstance(error, ProgressForbiddenError):
        return HTTPException(403, "Forbidden")
    if isinstance(error, ProgressStateError):
        return HTTPException(409, "Progress update cannot be changed")
    return HTTPException(404, "Progress update not found")


@router.get("", response_model=list[UpdateResponse])
def list_feed(session: DatabaseSession, client: ClientUser) -> list[UpdateResponse]:
    try:
        own = service.client_for_subject(session, client.subject).id
        return [
            response(update, author, update.client_id == own)
            for update, author in service.feed(session, client.subject)
        ]
    except ProgressNotFoundError as exc:
        raise error(exc) from None


@router.post("", response_model=UpdateResponse, status_code=status.HTTP_201_CREATED)
def create_update(
    payload: UpdateInput, session: DatabaseSession, client: ClientUser
) -> UpdateResponse:
    try:
        return own_response(
            session,
            service.create(session, client.subject, payload.content.strip(), payload.visibility),
        )
    except ProgressNotFoundError as exc:
        raise error(exc) from None


@router.patch("/{update_id}", response_model=UpdateResponse)
def patch_update(
    update_id: UUID, payload: UpdatePatch, session: DatabaseSession, client: ClientUser
) -> UpdateResponse:
    try:
        return own_response(
            session,
            service.own_change(
                session,
                client.subject,
                update_id,
                payload.content.strip() if payload.content else None,
                payload.visibility,
            ),
        )
    except (ProgressNotFoundError, ProgressForbiddenError, ProgressStateError) as exc:
        raise error(exc) from None


@router.delete("/{update_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_update(update_id: UUID, session: DatabaseSession, client: ClientUser) -> None:
    try:
        service.own_change(session, client.subject, update_id, None, None, delete=True)
    except (ProgressNotFoundError, ProgressForbiddenError, ProgressStateError) as exc:
        raise error(exc) from None


@router.get("/moderation/updates", response_model=list[UpdateResponse])
def moderated_updates(session: DatabaseSession, admin: Administrator) -> list[UpdateResponse]:
    del admin
    return [response(update, author) for update, author in service.moderation(session)]


@router.post("/moderation/updates/{update_id}", response_model=UpdateResponse)
def moderate_update(
    update_id: UUID, payload: ModerationInput, session: DatabaseSession, admin: Administrator
) -> UpdateResponse:
    del admin
    try:
        return own_response(
            session,
            service.moderate(
                session,
                update_id,
                payload.action,
                payload.reason.strip() if payload.reason else None,
            ),
        )
    except (ProgressNotFoundError, ProgressStateError) as exc:
        raise error(exc) from None
