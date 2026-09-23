from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.clients.models import Account, Client
from app.modules.progress.models import ProgressUpdate


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
                .order_by(ProgressUpdate.created_at.desc())
            ).all()
        )

    def create(
        self, session: Session, subject: str, content: str, visibility: str
    ) -> ProgressUpdate:
        update = ProgressUpdate(
            client_id=self.client_for_subject(session, subject).id,
            content=content,
            visibility=visibility,
        )
        session.add(update)
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
            update.content = None
            update.deleted_at = datetime.now(timezone.utc)
        else:
            if content is not None:
                update.content = content
            if visibility is not None:
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
                .order_by(ProgressUpdate.created_at.desc())
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
        if action == "delete":
            update.content = None
            update.deleted_at = datetime.now(timezone.utc)
        else:
            update.moderation_status = "hidden" if action == "hide" else "visible"
        update.moderation_reason = reason
        session.commit()
        session.refresh(update)
        return update
