from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from fastapi.responses import Response as BinaryResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.clients.models import Account
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.social.models import CommentImage, PostComment, PostImage, ProfileImage
from app.modules.social.service import (
    SocialForbiddenError,
    SocialNotFoundError,
    SocialService,
    SocialStateError,
    SocialValidationError,
)

router = APIRouter(prefix="/social-profiles", tags=["social-profiles"])
service = SocialService()
DatabaseSession = Annotated[Session, Depends(get_database_session)]
ClientUser = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "client"))
]
Administrator = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "admin"))
]


class ProfilePatch(BaseModel):
    nickname: str | None = Field(default=None, max_length=40)
    biography: str | None = Field(default=None, max_length=160)
    visible_to_clients: bool | None = None


class ProfileResponse(BaseModel):
    id: UUID
    name: str
    nickname: str | None
    biography: str | None
    visible_to_clients: bool | None = None
    biography_moderation_status: str | None = None
    biography_moderation_reason: str | None = None
    has_image: bool
    follower_count: int
    following_count: int
    is_following: bool
    follow_requested: bool = False
    pending_follow_request_count: int = 0
    is_owner: bool
    currently_present: bool
    private_shell: bool = False


class ProfileSummary(BaseModel):
    id: UUID
    name: str
    nickname: str | None
    has_image: bool


class PostResponse(BaseModel):
    id: UUID
    author_name: str
    content: str
    visibility: str
    moderation_status: str
    moderation_reason: str | None
    created_at: str
    edited_at: str | None = None
    images: list["MediaSummary"] = []
    like_count: int = 0
    comment_count: int = 0
    liked_by_viewer: bool = False


class MediaSummary(BaseModel):
    id: UUID
    width: int
    height: int


class CommentInput(BaseModel):
    content: str | None = Field(default=None, max_length=2000)


class CommentResponse(BaseModel):
    id: UUID
    author: ProfileSummary
    content: str
    created_at: str
    is_own: bool
    moderation_status: str | None = None
    moderation_reason: str | None = None
    edited_at: str | None = None
    image: MediaSummary | None = None


class PostDetailResponse(BaseModel):
    post: PostResponse
    author: ProfileSummary
    like_count: int
    liked_by_viewer: bool
    comments: list[CommentResponse]


class ModerationInput(BaseModel):
    target_type: Literal["post", "comment", "biography", "image"]
    action: Literal["hide", "restore", "delete"]
    reason: str | None = Field(default=None, max_length=500)


def profile_response(session: Session, view, private_shell: bool = False) -> ProfileResponse:
    image = session.get(ProfileImage, view.client.id)
    own = view.is_owner
    return ProfileResponse(
        id=view.profile.id,
        name=view.client.name,
        nickname=view.profile.nickname,
        biography=None if private_shell else view.profile.biography
        if own or view.profile.biography_moderation_status == "visible"
        else None,
        visible_to_clients=view.profile.visible_to_clients if own else None,
        biography_moderation_status=view.profile.biography_moderation_status if own else None,
        biography_moderation_reason=view.profile.biography_moderation_reason if own else None,
        has_image=bool(image and image.content and (own or image.moderation_status == "visible")),
        follower_count=view.follower_count,
        following_count=view.following_count,
        is_following=view.is_following,
        follow_requested=view.follow_requested,
        pending_follow_request_count=view.pending_follow_request_count if own else 0,
        is_owner=own,
        currently_present=False if private_shell else view.currently_present,
        private_shell=private_shell,
    )


def summary(session: Session, view) -> ProfileSummary:
    image = session.get(ProfileImage, view.client.id)
    return ProfileSummary(
        id=view.profile.id,
        name=view.client.name,
        nickname=view.profile.nickname,
        has_image=bool(image and image.content and image.moderation_status == "visible"),
    )


def post_response(session: Session, update, viewer_client_id: UUID | None = None) -> PostResponse:
    return PostResponse(
        id=update.id,
        author_name="",
        content=update.content or "",
        visibility=update.visibility,
        moderation_status=update.moderation_status,
        moderation_reason=update.moderation_reason,
        created_at=update.created_at.isoformat(),
        edited_at=update.edited_at.isoformat() if update.edited_at else None,
        images=[MediaSummary(id=image.id, width=image.width, height=image.height) for image in service.post_images(session, update.id)],
        like_count=service.like_count(session, update.id),
        comment_count=(session.scalar(select(func.count()).select_from(PostComment).where(PostComment.progress_update_id == update.id, PostComment.deleted_at.is_(None), PostComment.moderation_status == "visible")) or 0),
        liked_by_viewer=service.is_liked(session, viewer_client_id, update.id) if viewer_client_id else False,
    )


def error(exc: Exception) -> HTTPException:
    if isinstance(exc, SocialForbiddenError):
        return HTTPException(403, "Forbidden")
    if isinstance(exc, SocialStateError):
        return HTTPException(409, "Social action cannot be applied")
    if isinstance(exc, SocialValidationError):
        return HTTPException(422, "Invalid social profile data")
    return HTTPException(404, "Social profile resource not found")


@router.get("/me", response_model=ProfileResponse)
def own_profile(session: DatabaseSession, client: ClientUser):
    try:
        return profile_response(session, service.own_profile(session, client.subject))
    except SocialNotFoundError as exc:
        raise error(exc) from None


@router.patch("/me", response_model=ProfileResponse)
def patch_own(payload: ProfilePatch, session: DatabaseSession, client: ClientUser):
    try:
        return profile_response(
            session,
            service.update_own(
                session,
                client.subject,
                payload.nickname,
                payload.biography,
                payload.visible_to_clients,
            ),
        )
    except (SocialNotFoundError, SocialValidationError) as exc:
        raise error(exc) from None


@router.put("/me/image", status_code=status.HTTP_204_NO_CONTENT)
def upload_image(
    raw: bytes = Body(...), session: DatabaseSession = None, client: ClientUser = None
):
    try:
        service.save_image(session, client.subject, raw)
    except (SocialNotFoundError, SocialValidationError) as exc:
        raise error(exc) from None
    return Response(status_code=204)


@router.delete("/me/image", status_code=status.HTTP_204_NO_CONTENT)
def remove_image(session: DatabaseSession, client: ClientUser):
    service.remove_image(session, client.subject)


@router.get("/me/follow-requests", response_model=list[ProfileSummary])
def pending_follow_requests(session: DatabaseSession, client: ClientUser):
    return [summary(session, view) for view in service.follow_requests(session, client.subject)]


@router.put("/me/follow-requests/{requester_profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def accept_follow_request(requester_profile_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        service.decide_follow_request(session, client.subject, requester_profile_id, True)
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None


@router.delete("/me/follow-requests/{requester_profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def reject_follow_request(requester_profile_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        service.decide_follow_request(session, client.subject, requester_profile_id, False)
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
def profile(profile_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        view, private_shell = service.profile_shell(session, client.subject, profile_id)
        return profile_response(session, view, private_shell)
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None


@router.get("/profiles/{profile_id}/image")
def image(profile_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        item = service.image_for_viewer(session, client.subject, profile_id)
        return BinaryResponse(item.content or b"", media_type=item.media_type)
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None


@router.put("/profiles/{profile_id}/follow", response_model=ProfileResponse)
def follow(profile_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        return profile_response(session, service.follow(session, client.subject, profile_id, True))
    except (SocialNotFoundError, SocialForbiddenError, SocialStateError) as exc:
        raise error(exc) from None


@router.delete("/profiles/{profile_id}/follow", response_model=ProfileResponse)
def unfollow(profile_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        return profile_response(session, service.follow(session, client.subject, profile_id, False))
    except (SocialNotFoundError, SocialForbiddenError, SocialStateError) as exc:
        raise error(exc) from None


@router.get("/profiles/{profile_id}/graph/{direction}", response_model=list[ProfileSummary])
def list_graph(
    profile_id: UUID,
    direction: Literal["followers", "following"],
    session: DatabaseSession,
    client: ClientUser,
    offset: int = 0,
    limit: int = 20,
):
    try:
        return [
            summary(session, view)
            for view in service.profiles(
                session, client.subject, profile_id, direction, offset, limit
            )
        ]
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None


@router.get("/profiles/{profile_id}/posts", response_model=list[PostResponse])
def posts(
    profile_id: UUID, session: DatabaseSession, client: ClientUser, offset: int = 0, limit: int = 20
):
    try:
        view = service.viewer_profile(session, client.subject, profile_id)
        viewer = service.client_for_subject(session, client.subject)
        return [
            post_response(session, update, viewer.id).model_copy(update={"author_name": view.client.name})
            for update in service.profile_posts(session, client.subject, profile_id, offset, limit)
        ]
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None


@router.get("/posts/{update_id}", response_model=PostDetailResponse)
def detail(
    update_id: UUID, session: DatabaseSession, client: ClientUser, offset: int = 0, limit: int = 20
):
    try:
        update, author = service.post_detail(session, client.subject, update_id)
        viewer = service.client_for_subject(session, client.subject)
        comments = [
            CommentResponse(
                id=item.id,
                author=summary(
                    session,
                    service.viewer_profile(
                        session, client.subject, service.profile_for_client(session, owner.id).id
                    ),
                ),
                content=item.content or "",
                created_at=item.created_at.isoformat(),
                is_own=item.client_id == viewer.id,
                moderation_status=item.moderation_status if item.client_id == viewer.id else None,
                moderation_reason=item.moderation_reason if item.client_id == viewer.id else None,
                edited_at=item.edited_at.isoformat() if item.edited_at else None,
                image=(MediaSummary(id=item.id, width=image.width, height=image.height) if (image := service.comment_image(session, item.id)) else None),
            )
            for item, owner in service.comments(session, client.subject, update_id, offset, limit)
        ]
        return PostDetailResponse(
            post=post_response(session, update, viewer.id).model_copy(update={"author_name": author.client.name}),
            author=summary(session, author),
            like_count=service.like_count(session, update.id),
            liked_by_viewer=service.is_liked(session, viewer.id, update.id),
            comments=comments,
        )
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None


@router.put("/posts/{update_id}/like", response_model=PostDetailResponse)
def like(update_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        service.like(session, client.subject, update_id, True)
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None
    return detail(update_id, session, client)


@router.delete("/posts/{update_id}/like", response_model=PostDetailResponse)
def unlike(update_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        service.like(session, client.subject, update_id, False)
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None
    return detail(update_id, session, client)


@router.post("/posts/{update_id}/comments", response_model=CommentResponse, status_code=201)
def comment(update_id: UUID, payload: CommentInput, session: DatabaseSession, client: ClientUser):
    try:
        item = service.add_comment(session, client.subject, update_id, payload.content)
        view = service.own_profile(session, client.subject)
        return CommentResponse(
            id=item.id,
            author=summary(session, view),
            content=item.content or "",
            created_at=item.created_at.isoformat(),
            is_own=True,
        )
    except (SocialNotFoundError, SocialForbiddenError, SocialValidationError) as exc:
        raise error(exc) from None


@router.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        service.delete_comment(session, client.subject, comment_id)
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None


@router.patch("/comments/{comment_id}", response_model=CommentResponse)
def patch_comment(comment_id: UUID, payload: CommentInput, session: DatabaseSession, client: ClientUser):
    try:
        item = service.edit_comment(session, client.subject, comment_id, payload.content)
        image = service.comment_image(session, item.id)
        return CommentResponse(id=item.id, author=summary(session, service.own_profile(session, client.subject)), content=item.content or "", created_at=item.created_at.isoformat(), is_own=True, edited_at=item.edited_at.isoformat() if item.edited_at else None, image=MediaSummary(id=item.id, width=image.width, height=image.height) if image else None)
    except (SocialNotFoundError, SocialForbiddenError, SocialValidationError) as exc:
        raise error(exc) from None


@router.put("/comments/{comment_id}/image", status_code=204)
def put_comment_image(comment_id: UUID, raw: bytes = Body(...), session: DatabaseSession = None, client: ClientUser = None):
    try:
        service.replace_comment_image(session, client.subject, comment_id, raw)
    except (SocialNotFoundError, SocialForbiddenError, SocialValidationError) as exc:
        raise error(exc) from None


@router.get("/comments/{comment_id}/image")
def get_comment_image(comment_id: UUID, session: DatabaseSession, client: ClientUser):
    try:
        comment = session.get(PostComment, comment_id)
        if comment is None: raise SocialNotFoundError
        service.post_detail(session, client.subject, comment.progress_update_id)
        image = service.comment_image(session, comment.id)
        if image is None: raise SocialNotFoundError
        return BinaryResponse(image.content, media_type=image.media_type)
    except (SocialNotFoundError, SocialForbiddenError) as exc:
        raise error(exc) from None


@router.post("/moderation", status_code=204)
def moderate(payload: ModerationInput, session: DatabaseSession, admin: Administrator):
    account_id = session.scalar(select(Account.id).where(Account.keycloak_subject == admin.subject))
    if account_id is None:
        raise HTTPException(401, "Authenticated administrator not found")
    try:
        service.moderate(
            session,
            account_id,
            payload.target_type,
            payload.target_id,
            payload.action,
            payload.reason.strip() if payload.reason else None,
        )
    except (SocialNotFoundError, SocialValidationError) as exc:
        raise error(exc) from None
