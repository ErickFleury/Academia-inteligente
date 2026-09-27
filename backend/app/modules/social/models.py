"""Social-profile, interaction, and minimized moderation persistence."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SocialProfile(Base):
    __tablename__ = "social_profile"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client.id"), unique=True, nullable=False
    )
    nickname: Mapped[str | None] = mapped_column(String(40))
    biography: Mapped[str | None] = mapped_column(String(160))
    visible_to_clients: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    biography_moderation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="visible"
    )
    biography_moderation_reason: Mapped[str | None] = mapped_column(String(500))
    biography_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ProfileImage(Base):
    __tablename__ = "profile_image"

    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("client.id"), primary_key=True)
    content: Mapped[bytes | None] = mapped_column(LargeBinary)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    moderation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="visible"
    )
    moderation_reason: Mapped[str | None] = mapped_column(String(500))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ClientFollow(Base):
    __tablename__ = "client_follow"
    __table_args__ = (
        CheckConstraint(
            "follower_client_id <> followed_client_id", name="ck_client_follow_not_self"
        ),
    )

    follower_client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client.id"), primary_key=True
    )
    followed_client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ClientFollowRequest(Base):
    __tablename__ = "client_follow_request"
    __table_args__ = (
        CheckConstraint(
            "requester_client_id <> requested_client_id", name="ck_client_follow_request_not_self"
        ),
    )

    requester_client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client.id"), primary_key=True
    )
    requested_client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PostLike(Base):
    __tablename__ = "post_like"

    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("client.id"), primary_key=True)
    progress_update_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("progress_update.id"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PostComment(Base):
    __tablename__ = "post_comment"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    progress_update_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("progress_update.id"), nullable=False, index=True
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client.id"), nullable=False, index=True
    )
    content: Mapped[str | None] = mapped_column(Text)
    moderation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="visible"
    )
    moderation_reason: Mapped[str | None] = mapped_column(String(500))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PostImage(Base):
    __tablename__ = "post_image"
    __table_args__ = (
        CheckConstraint("position >= 0 AND position < 4", name="ck_post_image_position"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    progress_update_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("progress_update.id"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CommentImage(Base):
    __tablename__ = "comment_image"

    comment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("post_comment.id"), primary_key=True
    )
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SocialModerationAudit(Base):
    __tablename__ = "social_moderation_audit"
    __table_args__ = (
        CheckConstraint(
            "actor_account_id IS NOT NULL OR actor_subject IS NOT NULL",
            name="ck_social_moderation_actor",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("account.id"), nullable=True
    )
    actor_subject: Mapped[str | None] = mapped_column(String(255))
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
