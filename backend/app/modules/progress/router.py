from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import Response as BinaryResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
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
from app.modules.social.models import PostComment, SocialProfile
from app.modules.social.service import (
    SocialForbiddenError,
    SocialNotFoundError,
    SocialService,
    SocialValidationError,
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
    content: str | None = Field(default=None, max_length=2000)
    visibility: Literal["private", "shared"] = "private"


class UpdatePatch(BaseModel):
    content: str | None = Field(default=None, max_length=2000)
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
    author_profile_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None = None
    like_count: int = 0
    liked_by_viewer: bool = False
    comment_count: int = 0
    image_count: int = 0
    images: list["MediaResponse"] = []


class MediaResponse(BaseModel):
    id: UUID
    width: int
    height: int


class FeedResponse(BaseModel):
    items: list[UpdateResponse]
    next_cursor: str | None
    end_reached: bool


def response(
    update: ProgressUpdate,
    client: Client,
    is_own: bool = False,
    author_profile_id: UUID | None = None,
    session: Session | None = None,
    viewer_client_id: UUID | None = None,
) -> UpdateResponse:
    return UpdateResponse(
        id=update.id,
        author_name=client.name,
        content=update.content or "",
        visibility=update.visibility,
        moderation_status=update.moderation_status,
        moderation_reason=update.moderation_reason,
        is_own=is_own,
        author_profile_id=author_profile_id,
        created_at=update.created_at,
        updated_at=update.updated_at,
        edited_at=update.edited_at,
        like_count=SocialService().like_count(session, update.id) if session else 0,
        liked_by_viewer=SocialService().is_liked(session, viewer_client_id, update.id)
        if session and viewer_client_id
        else False,
        comment_count=(
            session.scalar(
                select(func.count())
                .select_from(PostComment)
                .where(
                    PostComment.progress_update_id == update.id,
                    PostComment.deleted_at.is_(None),
                    PostComment.moderation_status == "visible",
                )
            )
            or 0
        )
        if session
        else 0,
        image_count=len(images := SocialService().post_images(session, update.id))
        if session
        else 0,
        images=[
            MediaResponse(id=image.id, width=image.width, height=image.height) for image in images
        ]
        if session
        else [],
    )


def own_response(session: Session, update: ProgressUpdate) -> UpdateResponse:
    return response(
        update,
        session.get(Client, update.client_id),
        True,
        session=session,
        viewer_client_id=update.client_id,
    )


def error(error: Exception) -> HTTPException:
    if isinstance(error, SocialValidationError):
        return HTTPException(422, "Imagem inválida")
    if isinstance(error, ProgressNotFoundError):
        return HTTPException(401, "Authenticated client not found")
    if isinstance(error, ProgressForbiddenError):
        return HTTPException(403, "Forbidden")
    if isinstance(error, ProgressStateError):
        return HTTPException(
            409, "A publicação não pode ser alterada; comentários retidos impedem torná-la privada."
        )
    return HTTPException(404, "Progress update not found")


@router.get("", response_model=FeedResponse)
def list_feed(
    session: DatabaseSession, client: ClientUser, cursor: str | None = None, limit: int = 20
) -> FeedResponse:
    try:
        page = SocialService().feed_page(session, client.subject, cursor, limit)
        viewer = SocialService().client_for_subject(session, client.subject)
        return FeedResponse(
            items=[
                response(
                    update,
                    session.get(Client, update.client_id),
                    update.client_id == viewer.id,
                    profile.id if profile else None,
                    session,
                    viewer.id,
                )
                for update in page.items
                for profile in [
                    session.scalar(
                        select(SocialProfile).where(SocialProfile.client_id == update.client_id)
                    )
                    or SocialService().profile_for_client(session, update.client_id)
                ]
            ],
            next_cursor=page.next_cursor,
            end_reached=page.end_reached,
        )
    except (ProgressNotFoundError, SocialValidationError) as exc:
        raise error(exc) from None


@router.post("/create", response_model=UpdateResponse, status_code=status.HTTP_201_CREATED)
def create_update(
    payload: UpdateInput, session: DatabaseSession, client: ClientUser
) -> UpdateResponse:
    try:
        return own_response(
            session,
            service.create(session, client.subject, payload.content, payload.visibility),
        )
    except ProgressNotFoundError as exc:
        raise error(exc) from None


@router.post("/image-only", response_model=UpdateResponse, status_code=status.HTTP_201_CREATED)
def create_image_only(
    raw: bytes = Body(...),
    visibility: Literal["private", "shared"] = "private",
    session: DatabaseSession = None,
    client: ClientUser = None,
) -> UpdateResponse:
    try:
        return own_response(
            session, service.create(session, client.subject, None, visibility, [raw])
        )
    except (ProgressNotFoundError, ProgressStateError, SocialValidationError) as exc:
        raise error(exc) from None


@router.post("", response_model=UpdateResponse, status_code=status.HTTP_201_CREATED)
def create_update_root(
    payload: UpdateInput, session: DatabaseSession, client: ClientUser
) -> UpdateResponse:
    return create_update(payload, session, client)


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


@router.put("/{update_id}/images/{position}", response_model=UpdateResponse)
def replace_image(
    update_id: UUID,
    position: int,
    raw: bytes = Body(...),
    session: DatabaseSession = None,
    client: ClientUser = None,
) -> UpdateResponse:
    """Replace the ordered media set by addressing its position; bytes never enter JSON."""
    if position < 0 or position > 3:
        raise HTTPException(422, "Invalid image position")
    try:
        current = SocialService().post_images(session, update_id)
        values = [item.content for item in current]
        while len(values) <= position:
            values.append(b"")
        values[position] = raw
        updated = SocialService().replace_post_images(
            session, client.subject, update_id, [value for value in values if value]
        )
        return own_response(session, updated)
    except (
        ProgressNotFoundError,
        SocialForbiddenError,
        SocialNotFoundError,
        SocialValidationError,
    ) as exc:
        raise error(exc) from None


@router.delete("/{update_id}/images/{image_id}", response_model=UpdateResponse)
def delete_image(
    update_id: UUID,
    image_id: UUID,
    session: DatabaseSession,
    client: ClientUser,
) -> UpdateResponse:
    try:
        return own_response(
            session,
            SocialService().remove_post_image(session, client.subject, update_id, image_id),
        )
    except (SocialForbiddenError, SocialNotFoundError, SocialValidationError) as exc:
        raise error(exc) from None


@router.get("/{update_id}/images/{image_id}")
def post_image(update_id: UUID, image_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        update, _ = SocialService().post_detail(session, client.subject, update_id)
        image = next(
            (
                item
                for item in SocialService().post_images(session, update.id)
                if item.id == image_id
            ),
            None,
        )
        if image is None:
            raise SocialNotFoundError
        return BinaryResponse(image.content, media_type=image.media_type)
    except (SocialNotFoundError, SocialForbiddenError) as exc:
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
