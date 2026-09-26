from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.modules.clients.models import Account, Client
from app.modules.progress.models import ProgressUpdate
from app.modules.social.models import PostComment, PostImage
from app.modules.social.service import SocialService


class ProgressNotFoundError(Exception):
    pass


class ProgressForbiddenError(Exception):
    pass


class ProgressStateError(Exception):
    pass


class ProgressService:
    def client_for_subject(self, session: Session, subject: str) -> Client:
        client = session.scalar(
            select(Client).join(Account).where(Account.keycloak_subject == subject)
        )
        if client is None:
            raise ProgressNotFoundError
        return client

    def feed(self, session: Session, subject: str) -> list[tuple[ProgressUpdate, Client]]:
        client = self.client_for_subject(session, subject)
        return list(
            session.execute(
                select(ProgressUpdate, Client)
                .join(Client)
                .where(
                    ProgressUpdate.deleted_at.is_(None),
                    or_(
                        ProgressUpdate.client_id == client.id,
                        (ProgressUpdate.visibility == "shared")
                        & (ProgressUpdate.moderation_status == "visible"),
                    ),
                )
                .order_by(ProgressUpdate.created_at.desc(), ProgressUpdate.id.desc())
            ).all()
        )

    def create(
        self, session: Session, subject: str, content: str | None, visibility: str, images: list[bytes] | None = None
    ) -> ProgressUpdate:
        text, images = (content or "").strip() or None, images or []
        if not text and not images or len(images) > 4:
            raise ProgressStateError
        update = ProgressUpdate(
            client_id=self.client_for_subject(session, subject).id,
            content=text,
            visibility=visibility,
        )
        session.add(update)
        session.flush()
        for position, raw in enumerate(images):
            media, media_type, width, height = SocialService().normalize_image(raw)
            session.add(PostImage(progress_update_id=update.id, position=position, content=media, media_type=media_type, width=width, height=height))
        session.commit()
        session.refresh(update)
        return update

    def own_change(
        self,
        session: Session,
        subject: str,
        update_id: UUID,
        content: str | None,
        visibility: str | None,
        delete: bool = False,
    ) -> ProgressUpdate:
        client = self.client_for_subject(session, subject)
        update = session.get(ProgressUpdate, update_id)
        if update is None:
            raise ProgressNotFoundError
        if update.client_id != client.id:
            raise ProgressForbiddenError
        if update.deleted_at is not None:
            raise ProgressStateError
        if delete:
            SocialService().delete_post_aggregate(session, update)
        else:
            if content is not None:
                text = content.strip() or None
                if not text and not session.scalar(select(PostImage.id).where(PostImage.progress_update_id == update.id)):
                    raise ProgressStateError
                if update.content != text:
                    update.content = text
                    update.edited_at = datetime.now(timezone.utc)
            if visibility is not None:
                if visibility == "private" and update.visibility == "shared" and session.scalar(select(PostComment.id).where(PostComment.progress_update_id == update.id, PostComment.deleted_at.is_(None))):
                    raise ProgressStateError("Retained comments prevent private visibility")
                update.visibility = visibility
        session.commit()
        session.refresh(update)
        return update

    def moderation(self, session: Session) -> list[tuple[ProgressUpdate, Client]]:
        return list(
            session.execute(
                select(ProgressUpdate, Client)
                .join(Client)
                .where(ProgressUpdate.visibility == "shared", ProgressUpdate.deleted_at.is_(None))
                .order_by(ProgressUpdate.created_at.desc(), ProgressUpdate.id.desc())
            ).all()
        )

    def moderate(
        self, session: Session, update_id: UUID, action: str, reason: str | None
    ) -> ProgressUpdate:
        update = session.get(ProgressUpdate, update_id)
        if update is None:
            raise ProgressNotFoundError
        if update.visibility != "shared" or update.deleted_at is not None:
            raise ProgressStateError
        if action in {"hide", "restore"} and not reason:
            raise ProgressStateError("Moderation reason is required")
        if action == "delete":
            SocialService().delete_post_aggregate(session, update)
        else:
            update.moderation_status = "hidden" if action == "hide" else "visible"
        update.moderation_reason = reason
        session.commit()
        session.refresh(update)
        return update
