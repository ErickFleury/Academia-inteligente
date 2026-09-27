from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Account, Client
from app.modules.progress.models import ProgressUpdate
from app.modules.social.models import PostImage, SocialProfile
from app.modules.social.service import (
    SocialForbiddenError,
    SocialNotFoundError,
    SocialService,
    SocialValidationError,
)


class ProgressNotFoundError(Exception):
    pass


class ProgressForbiddenError(Exception):
    pass


class ProgressStateError(Exception):
    pass


class ProgressService:
    def client_for_subject(self, session: Session, subject: str) -> Client:
        client = session.scalar(
            select(Client)
            .join(Account)
            .where(
                Account.keycloak_subject == subject,
                Account.account_active,
                Client.active.is_(True),
            )
        )
        if client is None:
            raise ProgressNotFoundError
        return client

    def feed(self, session: Session, subject: str) -> list[tuple[ProgressUpdate, Client]]:
        return [
            (update, session.get(Client, update.client_id))
            for update in SocialService().feed_page(session, subject, None, 50).items
        ]

    def create(
        self,
        session: Session,
        subject: str,
        content: str | None,
        visibility: str,
        images: list[bytes] | None = None,
    ) -> ProgressUpdate:
        text, images = (content or "").strip() or None, images or []
        if not text and not images or len(images) > 4:
            raise ProgressStateError
        client = self.client_for_subject(session, subject)
        profile = SocialService().profile_for_client(session, client.id)
        update = ProgressUpdate(
            client_id=client.id,
            content=text,
            visibility="shared" if profile.visible_to_clients else "private",
        )
        session.add(update)
        session.flush()
        for position, raw in enumerate(images):
            media, media_type, width, height = SocialService().normalize_image(raw)
            session.add(
                PostImage(
                    progress_update_id=update.id,
                    position=position,
                    content=media,
                    media_type=media_type,
                    width=width,
                    height=height,
                )
            )
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
                if not text and not session.scalar(
                    select(PostImage.id).where(PostImage.progress_update_id == update.id)
                ):
                    raise ProgressStateError
                if update.content != text:
                    update.content = text
                    update.edited_at = datetime.now(timezone.utc)
            if visibility is not None:
                profile = SocialService().profile_for_client(session, client.id)
                update.visibility = "shared" if profile.visible_to_clients else "private"
        session.commit()
        session.refresh(update)
        return update

    def moderation(self, session: Session) -> list[tuple[ProgressUpdate, Client]]:
        return list(
            session.execute(
                select(ProgressUpdate, Client)
                .join(Client)
                .join(SocialProfile, SocialProfile.client_id == Client.id)
                .where(SocialProfile.visible_to_clients, ProgressUpdate.deleted_at.is_(None))
                .order_by(ProgressUpdate.created_at.desc(), ProgressUpdate.id.desc())
            ).all()
        )

    def moderate(
        self,
        session: Session,
        update_id: UUID,
        action: str,
        reason: str | None,
        *,
        actor_subject: str,
    ) -> ProgressUpdate:
        try:
            SocialService().moderate(session, actor_subject, "post", update_id, action, reason)
        except SocialNotFoundError:
            raise ProgressNotFoundError from None
        except (SocialForbiddenError, SocialValidationError):
            raise ProgressStateError from None
        return session.get(ProgressUpdate, update_id)
