"""Read-only social projections for active instructor employees."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.clients.models import Client
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.social.models import PostComment
from app.modules.social.router import (
    CommentResponse,
    MediaSummary,
    PostDetailResponse,
    PostResponse,
    ProfileSummary,
)
from app.modules.social.service import (
    SocialForbiddenError,
    SocialNotFoundError,
    SocialService,
    SocialValidationError,
)

router = APIRouter(prefix="/instructor/social", tags=["instructor-social"])
service = SocialService()
DatabaseSession = Annotated[Session, Depends(get_database_session)]
Instructor = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "instructor"))
]


class FeedResponse(BaseModel):
    items: list[PostResponse]
    next_cursor: str | None
    end_reached: bool


def post_response(session: Session, update, author_name: str) -> PostResponse:
    return PostResponse(
        id=update.id,
        author_name=author_name,
        content=update.content or "",
        visibility=update.visibility,
        moderation_status=update.moderation_status,
        moderation_reason=None,
        created_at=update.created_at.isoformat(),
        edited_at=update.edited_at.isoformat() if update.edited_at else None,
        images=[
            MediaSummary(id=item.id, width=item.width, height=item.height)
            for item in service.post_images(session, update.id)
        ],
        like_count=service.like_count(session, update.id),
        comment_count=session.scalar(
            select(func.count())
            .select_from(PostComment)
            .where(
                PostComment.progress_update_id == update.id,
                PostComment.deleted_at.is_(None),
                PostComment.moderation_status == "visible",
            )
        )
        or 0,
        liked_by_viewer=False,
    )


def forbidden_or_missing(exc: Exception) -> HTTPException:
    return HTTPException(
        403 if isinstance(exc, SocialForbiddenError) else 404,
        "Forbidden" if isinstance(exc, SocialForbiddenError) else "Post not found",
    )


@router.get("/feed", response_model=FeedResponse)
def feed(
    session: DatabaseSession, instructor: Instructor, cursor: str | None = None, limit: int = 20
) -> FeedResponse:
    try:
        page = service.instructor_feed_page(session, instructor.subject, cursor, limit)
        return FeedResponse(
            items=[
                post_response(session, item, session.get(Client, item.client_id).name)
                for item in page.items
            ],
            next_cursor=page.next_cursor,
            end_reached=page.end_reached,
        )
    except (SocialForbiddenError, SocialValidationError) as exc:
        raise forbidden_or_missing(exc) from None


@router.get("/posts/{update_id}", response_model=PostDetailResponse)
def detail(update_id: UUID, session: DatabaseSession, instructor: Instructor) -> PostDetailResponse:
    try:
        update, profile, author = service.instructor_post_detail(
            session, instructor.subject, update_id
        )
        comments = service.instructor_comments(session, instructor.subject, update_id, 50)
        return PostDetailResponse(
            post=post_response(session, update, author.name),
            author=ProfileSummary(
                id=profile.id, name=author.name, nickname=profile.nickname, has_image=False
            ),
            like_count=service.like_count(session, update.id),
            liked_by_viewer=False,
            comments=[
                CommentResponse(
                    id=item.id,
                    author=ProfileSummary(
                        id=service.profile_for_client(session, author_client.id).id,
                        name=author_client.name,
                        nickname=service.profile_for_client(session, author_client.id).nickname,
                        has_image=False,
                    ),
                    content=item.content or "",
                    created_at=item.created_at.isoformat(),
                    is_own=False,
                )
                for item, author_client in comments
            ],
        )
    except (SocialForbiddenError, SocialNotFoundError) as exc:
        raise forbidden_or_missing(exc) from None


@router.get("/posts/{update_id}/images/{image_id}")
def image(
    update_id: UUID, image_id: UUID, session: DatabaseSession, instructor: Instructor
) -> Response:
    try:
        update, _, _ = service.instructor_post_detail(session, instructor.subject, update_id)
        item = next(
            (value for value in service.post_images(session, update.id) if value.id == image_id),
            None,
        )
        if item is None:
            raise SocialNotFoundError
        return Response(item.content, media_type=item.media_type)
    except (SocialForbiddenError, SocialNotFoundError) as exc:
        raise forbidden_or_missing(exc) from None
