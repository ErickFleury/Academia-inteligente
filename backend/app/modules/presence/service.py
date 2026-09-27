from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Account, Client
from app.modules.occupancy.models import AccessPassageEvent, OccupancyCorrection
from app.modules.occupancy.service import OccupancyService
from app.modules.presence.models import ProfilePresenceConsentAudit, ProfilePresencePreference


class PresenceClientNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class ProfilePresence:
    sharing_enabled: bool
    currently_present: bool


class ProfilePresenceService:
    maximum_presence_duration = timedelta(hours=12)

    def __init__(self, occupancy_service: OccupancyService | None = None) -> None:
        self.occupancy_service = occupancy_service or OccupancyService()

    def client_for_subject(self, session: Session, subject: str) -> Client:
        client = session.scalar(
            select(Client)
            .join(Account)
            .where(
                Account.keycloak_subject == subject, Account.account_active, Client.active.is_(True)
            )
        )
        if client is None:
            raise PresenceClientNotFoundError
        return client

    def get_own(
        self, session: Session, subject: str, now: datetime | None = None
    ) -> ProfilePresence:
        client = self.client_for_subject(session, subject)
        preference = session.get(ProfilePresencePreference, client.id)
        enabled = preference.enabled if preference is not None else False
        return ProfilePresence(
            enabled, enabled and self._is_currently_present(session, client.id, now)
        )

    def set_own(
        self, session: Session, subject: str, enabled: bool, now: datetime | None = None
    ) -> ProfilePresence:
        client = self.client_for_subject(session, subject)
        preference = session.get(ProfilePresencePreference, client.id)
        previous_enabled = preference.enabled if preference is not None else False
        timestamp = now or datetime.now(UTC)
        if preference is None:
            preference = ProfilePresencePreference(
                client_id=client.id,
                enabled=enabled,
                consented_at=timestamp if enabled else None,
            )
            session.add(preference)
        elif preference.enabled != enabled:
            preference.enabled = enabled
            if enabled:
                preference.consented_at = timestamp
        if previous_enabled != enabled:
            session.add(
                ProfilePresenceConsentAudit(
                    client_id=client.id,
                    previous_enabled=previous_enabled,
                    new_enabled=enabled,
                    occurred_at=timestamp,
                )
            )
        session.commit()
        return ProfilePresence(
            enabled, enabled and self._is_currently_present(session, client.id, now)
        )

    def _is_currently_present(self, session: Session, client_id, now: datetime | None) -> bool:
        timestamp = now or datetime.now(UTC)
        if self.occupancy_service.snapshot(session, timestamp).status != "current":
            return False
        latest = session.scalar(
            select(AccessPassageEvent)
            .where(AccessPassageEvent.client_id == client_id)
            .order_by(AccessPassageEvent.occurred_at.desc(), AccessPassageEvent.created_at.desc())
            .limit(1)
        )
        correction = session.scalar(
            select(OccupancyCorrection)
            .where(OccupancyCorrection.client_id == client_id, OccupancyCorrection.adjustment != 0)
            .order_by(OccupancyCorrection.occurred_at.desc(), OccupancyCorrection.created_at.desc())
            .limit(1)
        )
        if correction and (
            latest is None
            or self.occupancy_service._utc(correction.occurred_at)
            >= self.occupancy_service._utc(latest.occurred_at)
        ):
            return bool(
                correction.target_inside
                and self.occupancy_service._utc(correction.occurred_at)
                + self.maximum_presence_duration
                >= self.occupancy_service._utc(timestamp)
            )
        return bool(
            latest
            and latest.direction == "entry"
            and self.occupancy_service._utc(latest.occurred_at) + self.maximum_presence_duration
            >= self.occupancy_service._utc(timestamp)
        )
