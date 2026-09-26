"""Policy and query boundary for authenticated social projections and interactions."""

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.clients.models import Account, Client
from app.modules.presence.models import ProfilePresencePreference
from app.modules.presence.service import ProfilePresenceService
from app.modules.progress.models import ProgressUpdate
from app.modules.social.models import (
    ClientFollow,
    PostComment,
    CommentImage,
    PostImage,
    PostLike,
    ProfileImage,
    SocialModerationAudit,
    SocialProfile,
)


class SocialNotFoundError(Exception):
    pass


class SocialForbiddenError(Exception):
    pass


class SocialStateError(Exception):
    pass


class SocialValidationError(Exception):
    pass


@dataclass(frozen=True)
class ProfileView:
    profile: SocialProfile
    client: Client
    is_owner: bool
    follower_count: int
    following_count: int
    is_following: bool
    currently_present: bool


@dataclass(frozen=True)
class CursorPage:
    items: list[ProgressUpdate]
    next_cursor: str | None
    end_reached: bool


class SocialService:
    page_size_maximum = 50
    image_size_maximum = 5 * 1024 * 1024

    def __init__(self, presence_service: ProfilePresenceService | None = None) -> None:
        self.presence_service = presence_service or ProfilePresenceService()

    def client_for_subject(self, session: Session, subject: str) -> Client:
        client = session.scalar(
            select(Client)
            .join(Account)
            .where(Account.keycloak_subject == subject, Account.account_active)
        )
        if client is None:
            raise SocialNotFoundError
        return client

    def profile_for_client(self, session: Session, client_id: UUID) -> SocialProfile:
        profile = session.scalar(select(SocialProfile).where(SocialProfile.client_id == client_id))
        if profile is None:
            profile = SocialProfile(client_id=client_id)
            session.add(profile)
            session.commit()
            session.refresh(profile)
        return profile

    def own_profile(self, session: Session, subject: str) -> ProfileView:
        client = self.client_for_subject(session, subject)
        return self._view(session, self.profile_for_client(session, client.id), client, client)

    def viewer_profile(self, session: Session, subject: str, profile_id: UUID) -> ProfileView:
        viewer = self.client_for_subject(session, subject)
        profile = session.get(SocialProfile, profile_id)
        if profile is None:
            raise SocialNotFoundError
        target = session.get(Client, profile.client_id)
        if target is None:
            raise SocialNotFoundError
        if target.id != viewer.id and not profile.visible_to_clients:
            raise SocialForbiddenError
        return self._view(session, profile, target, viewer)

    def profile_shell(self, session: Session, subject: str, profile_id: UUID) -> tuple[ProfileView, bool]:
        """Return the deliberately minimal shell for a hidden profile."""
        viewer = self.client_for_subject(session, subject)
        profile = session.get(SocialProfile, profile_id)
        target = session.get(Client, profile.client_id) if profile else None
        if profile is None or target is None: raise SocialNotFoundError
        if target.id != viewer.id and not profile.visible_to_clients:
            return ProfileView(profile, target, False, 0, 0, False, False), True
        return self._view(session, profile, target, viewer), False

    def update_own(
        self,
        session: Session,
        subject: str,
        nickname: str | None,
        biography: str | None,
        visible: bool | None,
    ) -> ProfileView:
        client = self.client_for_subject(session, subject)
        profile = self.profile_for_client(session, client.id)
        if nickname is not None:
            profile.nickname = self._plain(nickname, 40, "Nickname")
        if biography is not None:
            profile.biography = self._plain(biography, 160, "Biography")
            profile.biography_deleted_at = None
            profile.biography_moderation_status = "visible"
            profile.biography_moderation_reason = None
        if visible is not None:
            profile.visible_to_clients = visible
        session.commit()
        session.refresh(profile)
        return self._view(session, profile, client, client)

    @staticmethod
    def _plain(value: str, maximum: int, field: str) -> str | None:
        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) > maximum:
            raise SocialValidationError(f"{field} is too long")
        return normalized

    def save_image(self, session: Session, subject: str, raw: bytes) -> ProfileImage:
        client = self.client_for_subject(session, subject)
        content, media_type, width, height = self.normalize_image(raw)
        image = session.get(ProfileImage, client.id)
        if image is None:
            image = ProfileImage(
                client_id=client.id,
                content=content,
                media_type=media_type,
                width=width,
                height=height,
            )
            session.add(image)
        else:
            image.content, image.media_type, image.width, image.height = (
                content,
                media_type,
                width,
                height,
            )
            image.deleted_at = None
            image.moderation_status = "visible"
            image.moderation_reason = None
        session.commit()
        session.refresh(image)
        return image

    def remove_image(self, session: Session, subject: str) -> None:
        image = session.get(ProfileImage, self.client_for_subject(session, subject).id)
        if image is not None:
            session.delete(image)
            session.commit()

    def image_for_viewer(self, session: Session, subject: str, profile_id: UUID) -> ProfileImage:
        view = self.viewer_profile(session, subject, profile_id)
        image = session.get(ProfileImage, view.client.id)
        if (
            image is None
            or image.content is None
            or (not view.is_owner and image.moderation_status != "visible")
        ):
            raise SocialNotFoundError
        return image

    def normalize_image(self, raw: bytes) -> tuple[bytes, str, int, int]:
        if not raw or len(raw) > self.image_size_maximum:
            raise SocialValidationError("Image size is invalid")
        try:
            with Image.open(BytesIO(raw)) as source:
                if getattr(source, "n_frames", 1) != 1 or source.format not in {
                    "JPEG",
                    "PNG",
                    "WEBP",
                }:
                    raise SocialValidationError("Unsupported image")
                source.verify()
            with Image.open(BytesIO(raw)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((1024, 1024))
                output = BytesIO()
                image.save(output, format="WEBP", quality=88, method=6)
                return output.getvalue(), "image/webp", image.width, image.height
        except (UnidentifiedImageError, OSError, ValueError) as error:
            raise SocialValidationError("Invalid image") from error

    def _cursor(self, value: str | None) -> tuple[datetime, UUID] | None:
        if not value:
            return None
        try:
            decoded = base64.urlsafe_b64decode(value.encode() + b"=" * (-len(value) % 4))
            data = json.loads(decoded)
            timestamp = datetime.fromisoformat(data["t"])
            if timestamp.tzinfo is None:
                raise ValueError
            return timestamp, UUID(data["i"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            raise SocialValidationError("Invalid cursor") from None

    @staticmethod
    def _encode_cursor(item: ProgressUpdate) -> str:
        payload = json.dumps({"t": item.created_at.isoformat(), "i": str(item.id)}, separators=(",", ":"))
        return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    def feed_page(self, session: Session, subject: str, cursor: str | None, limit: int) -> CursorPage:
        self.client_for_subject(session, subject)
        marker = self._cursor(cursor)
        statement = select(ProgressUpdate).where(
            ProgressUpdate.visibility == "shared",
            ProgressUpdate.moderation_status == "visible",
            ProgressUpdate.deleted_at.is_(None),
        )
        if marker:
            timestamp, identifier = marker
            statement = statement.where(or_(ProgressUpdate.created_at < timestamp, and_(ProgressUpdate.created_at == timestamp, ProgressUpdate.id < identifier)))
        items = list(session.scalars(statement.order_by(ProgressUpdate.created_at.desc(), ProgressUpdate.id.desc()).limit(self._limit(limit) + 1)).all())
        has_more = len(items) > self._limit(limit)
        items = items[: self._limit(limit)]
        return CursorPage(items, self._encode_cursor(items[-1]) if has_more and items else None, not has_more)

    def post_images(self, session: Session, update_id: UUID) -> list[PostImage]:
        return list(session.scalars(select(PostImage).where(PostImage.progress_update_id == update_id).order_by(PostImage.position)).all())

    def comment_image(self, session: Session, comment_id: UUID) -> CommentImage | None:
        return session.get(CommentImage, comment_id)

    def replace_post_images(self, session: Session, subject: str, update_id: UUID, raw_images: list[bytes]) -> ProgressUpdate:
        update, view = self.post_detail(session, subject, update_id)
        if not view.is_owner:
            raise SocialForbiddenError
        if len(raw_images) > 4:
            raise SocialValidationError("Too many images")
        normalized = [self.normalize_image(raw) for raw in raw_images]
        if not (update.content or normalized):
            raise SocialValidationError("Post requires content or image")
        session.query(PostImage).filter(PostImage.progress_update_id == update.id).delete()
        for position, (content, media_type, width, height) in enumerate(normalized):
            session.add(PostImage(progress_update_id=update.id, position=position, content=content, media_type=media_type, width=width, height=height))
        update.edited_at = datetime.now(UTC)
        session.commit(); session.refresh(update)
        return update

    def replace_comment_image(self, session: Session, subject: str, comment_id: UUID, raw: bytes | None) -> PostComment:
        comment = session.get(PostComment, comment_id)
        if comment is None: raise SocialNotFoundError
        if comment.client_id != self.client_for_subject(session, subject).id: raise SocialForbiddenError
        image = self.comment_image(session, comment.id)
        if raw is None:
            if image: session.delete(image)
            if not comment.content: raise SocialValidationError("Comment requires content or image")
        else:
            content, media_type, width, height = self.normalize_image(raw)
            if image: image.content, image.media_type, image.width, image.height = content, media_type, width, height
            else: session.add(CommentImage(comment_id=comment.id, content=content, media_type=media_type, width=width, height=height))
        comment.edited_at = datetime.now(UTC); session.commit(); session.refresh(comment)
        return comment

    def follow(
        self, session: Session, subject: str, profile_id: UUID, following: bool
    ) -> ProfileView:
        viewer = self.client_for_subject(session, subject)
        view = self.viewer_profile(session, subject, profile_id)
        if view.is_owner:
            raise SocialStateError
        if following:
            if session.get(ClientFollow, (viewer.id, view.client.id)) is None:
                session.add(
                    ClientFollow(follower_client_id=viewer.id, followed_client_id=view.client.id)
                )
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()
        else:
            edge = session.get(ClientFollow, (viewer.id, view.client.id))
            if edge is not None:
                session.delete(edge)
                session.commit()
        return self.viewer_profile(session, subject, profile_id)

    def profiles(
        self,
        session: Session,
        subject: str,
        profile_id: UUID,
        direction: str,
        offset: int,
        limit: int,
    ) -> list[ProfileView]:
        owner = self.viewer_profile(session, subject, profile_id)
        statement = select(SocialProfile, Client).join(Client)
        if direction == "followers":
            statement = statement.join(
                ClientFollow, ClientFollow.follower_client_id == Client.id
            ).where(ClientFollow.followed_client_id == owner.client.id)
        else:
            statement = statement.join(
                ClientFollow, ClientFollow.followed_client_id == Client.id
            ).where(ClientFollow.follower_client_id == owner.client.id)
        viewer = self.client_for_subject(session, subject)
        return [
            self._view(session, profile, client, viewer)
            for profile, client in session.execute(
                statement.join(Account)
                .where(Account.account_active, SocialProfile.visible_to_clients)
                .order_by(Client.name)
                .offset(offset)
                .limit(self._limit(limit))
            ).all()
        ]

    def profile_posts(
        self, session: Session, subject: str, profile_id: UUID, offset: int, limit: int
    ) -> list[ProgressUpdate]:
        view = self.viewer_profile(session, subject, profile_id)
        statement = select(ProgressUpdate).where(
            ProgressUpdate.client_id == view.client.id, ProgressUpdate.deleted_at.is_(None)
        )
        if not view.is_owner:
            statement = statement.where(
                ProgressUpdate.visibility == "shared", ProgressUpdate.moderation_status == "visible"
            )
        return list(
            session.scalars(
                statement.order_by(ProgressUpdate.created_at.desc(), ProgressUpdate.id.desc())
                .offset(offset)
                .limit(self._limit(limit))
            ).all()
        )

    def post_detail(
        self, session: Session, subject: str, update_id: UUID
    ) -> tuple[ProgressUpdate, ProfileView]:
        viewer = self.client_for_subject(session, subject)
        update = session.get(ProgressUpdate, update_id)
        if update is None or update.deleted_at is not None:
            raise SocialNotFoundError
        profile = self.profile_for_client(session, update.client_id)
        author = session.get(Client, update.client_id)
        if author is None:
            raise SocialNotFoundError
        allowed = update.client_id == viewer.id or (
            update.visibility == "shared"
            and update.moderation_status == "visible"
        )
        if not allowed:
            raise SocialForbiddenError
        return update, self._view(session, profile, author, viewer)

    def like(
        self, session: Session, subject: str, update_id: UUID, liked: bool
    ) -> tuple[ProgressUpdate, ProfileView]:
        update, view = self.post_detail(session, subject, update_id)
        viewer = self.client_for_subject(session, subject)
        if not (update.visibility == "shared" and update.moderation_status == "visible"):
            raise SocialForbiddenError
        edge = session.get(PostLike, (viewer.id, update.id))
        if liked and edge is None:
            session.add(PostLike(client_id=viewer.id, progress_update_id=update.id))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
        elif not liked and edge is not None:
            session.delete(edge)
            session.commit()
        return self.post_detail(session, subject, update_id)

    def comments(
        self, session: Session, subject: str, update_id: UUID, offset: int, limit: int
    ) -> list[tuple[PostComment, Client]]:
        update, view = self.post_detail(session, subject, update_id)
        statement = (
            select(PostComment, Client)
            .join(Client)
            .where(PostComment.progress_update_id == update.id, PostComment.deleted_at.is_(None))
        )
        if not view.is_owner:
            statement = statement.where(PostComment.moderation_status == "visible")
        return list(
            session.execute(
                statement.order_by(PostComment.created_at.desc(), PostComment.id.desc()).offset(offset).limit(self._limit(limit))
            ).all()
        )

    def add_comment(
        self, session: Session, subject: str, update_id: UUID, content: str | None, raw_image: bytes | None = None
    ) -> PostComment:
        update, _ = self.post_detail(session, subject, update_id)
        if update.visibility != "shared" or update.moderation_status != "visible":
            raise SocialForbiddenError
        text = self._plain(content, 2000, "Comment")
        if text is None and raw_image is None:
            raise SocialValidationError("Comment is required")
        comment = PostComment(
            progress_update_id=update.id,
            client_id=self.client_for_subject(session, subject).id,
            content=text,
        )
        session.add(comment)
        if raw_image is not None:
            media, media_type, width, height = self.normalize_image(raw_image)
            session.flush()
            session.add(CommentImage(comment_id=comment.id, content=media, media_type=media_type, width=width, height=height))
        session.commit()
        session.refresh(comment)
        return comment

    def edit_comment(self, session: Session, subject: str, comment_id: UUID, content: str | None) -> PostComment:
        comment = session.get(PostComment, comment_id)
        if comment is None: raise SocialNotFoundError
        if comment.client_id != self.client_for_subject(session, subject).id: raise SocialForbiddenError
        text = self._plain(content or "", 2000, "Comment")
        if text is None and self.comment_image(session, comment.id) is None:
            raise SocialValidationError("Comment requires content or image")
        if comment.content != text:
            comment.content, comment.edited_at = text, datetime.now(UTC)
            session.commit(); session.refresh(comment)
        return comment

    def delete_comment(self, session: Session, subject: str, comment_id: UUID) -> None:
        comment = session.get(PostComment, comment_id)
        if comment is None:
            raise SocialNotFoundError
        if comment.client_id != self.client_for_subject(session, subject).id:
            raise SocialForbiddenError
        comment.content = None
        image = self.comment_image(session, comment.id)
        if image is not None: session.delete(image)
        comment.deleted_at = datetime.now(UTC)
        session.commit()

    def moderate(
        self,
        session: Session,
        actor_account_id: UUID,
        target_type: str,
        target_id: UUID,
        action: str,
        reason: str | None,
    ) -> None:
        if action in {"hide", "restore"} and not reason:
            raise SocialValidationError("Reason is required")
        target = (
            session.get(PostComment, target_id)
            if target_type == "comment"
            else (
                session.get(SocialProfile, target_id)
                if target_type == "biography"
                else (session.get(ProgressUpdate, target_id) if target_type == "post" else session.get(ProfileImage, target_id))
            )
        )
        if target is None:
            raise SocialNotFoundError
        if action == "delete":
            if target_type == "biography":
                target.biography = None
                target.biography_deleted_at = datetime.now(UTC)
            elif target_type == "image":
                session.delete(target)
            elif target_type == "post":
                self.delete_post_aggregate(session, target)
            else:
                target.content = None
                image = self.comment_image(session, target.id)
                if image is not None: session.delete(image)
                target.deleted_at = datetime.now(UTC)
        else:
            target.moderation_status = "hidden" if action == "hide" else "visible"
            target.moderation_reason = reason
        session.add(
            SocialModerationAudit(
                actor_account_id=actor_account_id,
                target_id=target_id,
                target_type=target_type,
                action=action,
                reason=reason,
            )
        )
        session.commit()

    def delete_post_aggregate(self, session: Session, update: ProgressUpdate) -> None:
        """Remove child content while retaining only the approved post tombstone."""
        comment_ids = select(PostComment.id).where(PostComment.progress_update_id == update.id)
        session.query(CommentImage).filter(CommentImage.comment_id.in_(comment_ids)).delete(synchronize_session=False)
        session.query(PostComment).filter(PostComment.progress_update_id == update.id).delete(synchronize_session=False)
        session.query(PostImage).filter(PostImage.progress_update_id == update.id).delete(synchronize_session=False)
        session.query(PostLike).filter(PostLike.progress_update_id == update.id).delete(synchronize_session=False)
        update.content = None
        update.deleted_at = datetime.now(UTC)

    def like_count(self, session: Session, update_id: UUID) -> int:
        return (
            session.scalar(
                select(func.count())
                .select_from(PostLike)
                .where(PostLike.progress_update_id == update_id)
            )
            or 0
        )

    def is_liked(self, session: Session, client_id: UUID, update_id: UUID) -> bool:
        return session.get(PostLike, (client_id, update_id)) is not None

    def _limit(self, value: int) -> int:
        return min(max(value, 1), self.page_size_maximum)

    def _view(
        self, session: Session, profile: SocialProfile, client: Client, viewer: Client
    ) -> ProfileView:
        follower_count = (
            session.scalar(
                select(func.count())
                .select_from(ClientFollow)
                .where(ClientFollow.followed_client_id == client.id)
            )
            or 0
        )
        following_count = (
            session.scalar(
                select(func.count())
                .select_from(ClientFollow)
                .where(ClientFollow.follower_client_id == client.id)
            )
            or 0
        )
        preference = session.get(ProfilePresencePreference, client.id)
        present = bool(
            preference
            and preference.enabled
            and self.presence_service._is_currently_present(session, client.id, None)
        )
        return ProfileView(
            profile,
            client,
            client.id == viewer.id,
            follower_count,
            following_count,
            session.get(ClientFollow, (viewer.id, client.id)) is not None,
            present,
        )
