import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.clients.models import Client
from app.modules.occupancy.models import (
    AccessPassageEvent,
    AccessSourceHeartbeat,
    ClientAccessReference,
    OccupancyCorrection,
)


class OccupancyError(Exception):
    pass


class UnknownClientReferenceError(OccupancyError):
    pass


class ConflictingEventError(OccupancyError):
    pass


class InvalidCorrectionError(OccupancyError):
    pass


@dataclass(frozen=True)
class OccupancySnapshot:
    occupancy: int
    status: str
    updated_at: datetime | None


class OccupancyService:
    heartbeat_freshness = timedelta(seconds=120)

    @staticmethod
    def digest(reference: str) -> str:
        return hashlib.sha256(reference.strip().encode()).hexdigest()

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    def register_client_reference(
        self, session: Session, client_id: UUID, reference: str
    ) -> ClientAccessReference:
        if not reference.strip():
            raise UnknownClientReferenceError
        if session.get(Client, client_id) is None:
            raise UnknownClientReferenceError
        record = ClientAccessReference(
            client_id=client_id, reference_digest=self.digest(reference), active=True
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def record_passage(
        self,
        session: Session,
        *,
        event_id: str,
        occurred_at: datetime,
        checkpoint_id: str,
        direction: str,
        event_type: str,
        client_reference: str,
    ) -> tuple[AccessPassageEvent, bool]:
        digest = self.digest(client_reference)
        existing = session.scalar(
            select(AccessPassageEvent).where(AccessPassageEvent.event_id == event_id)
        )
        if existing:
            if not self._matches(
                existing, digest, occurred_at, checkpoint_id, direction, event_type
            ):
                raise ConflictingEventError
            return existing, False
        reference = session.scalar(
            select(ClientAccessReference).where(
                ClientAccessReference.reference_digest == digest,
                ClientAccessReference.active.is_(True),
            )
        )
        if reference is None:
            raise UnknownClientReferenceError
        event = AccessPassageEvent(
            event_id=event_id,
            client_id=reference.client_id,
            client_reference_digest=digest,
            occurred_at=occurred_at,
            checkpoint_id=checkpoint_id,
            direction=direction,
            event_type=event_type,
        )
        try:
            session.add(event)
            session.flush()
            event.inconsistency = (
                direction == "exit" and self._occupancy_before(session, occurred_at, event.id) == 0
            )
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.scalar(
                select(AccessPassageEvent).where(AccessPassageEvent.event_id == event_id)
            )
            if existing and self._matches(
                existing, digest, occurred_at, checkpoint_id, direction, event_type
            ):
                return existing, False
            raise ConflictingEventError from None
        session.refresh(event)
        return event, True

    def record_heartbeat(self, session: Session, checkpoint_id: str, occurred_at: datetime) -> None:
        heartbeat = session.get(AccessSourceHeartbeat, checkpoint_id)
        if heartbeat is None:
            session.add(AccessSourceHeartbeat(checkpoint_id=checkpoint_id, occurred_at=occurred_at))
        elif self._utc(occurred_at) > self._utc(heartbeat.occurred_at):
            heartbeat.occurred_at = occurred_at
        session.commit()

    def correct(
        self,
        session: Session,
        *,
        actor_subject: str,
        adjustment: int,
        reason: str,
        occurred_at: datetime,
    ) -> OccupancyCorrection:
        if adjustment == 0 or not reason.strip():
            raise InvalidCorrectionError
        correction = OccupancyCorrection(
            actor_subject=actor_subject,
            adjustment=adjustment,
            reason=reason.strip(),
            occurred_at=occurred_at,
        )
        session.add(correction)
        session.commit()
        session.refresh(correction)
        return correction

    def snapshot(self, session: Session, now: datetime | None = None) -> OccupancySnapshot:
        now = now or datetime.now(UTC)
        events = list(session.scalars(select(AccessPassageEvent)))
        corrections = list(session.scalars(select(OccupancyCorrection)))
        count = self._calculate(events, corrections)
        latest_event = max((self._utc(item.occurred_at) for item in events), default=None)
        latest_correction = max((self._utc(item.occurred_at) for item in corrections), default=None)
        updated_at = max(
            (item for item in (latest_event, latest_correction) if item is not None), default=None
        )
        latest_heartbeat = session.scalar(
            select(AccessSourceHeartbeat.occurred_at)
            .order_by(AccessSourceHeartbeat.occurred_at.desc())
            .limit(1)
        )
        status = (
            "current"
            if latest_heartbeat
            and self._utc(latest_heartbeat) >= self._utc(now) - self.heartbeat_freshness
            else "stale"
        )
        return OccupancySnapshot(count, status, self._utc(updated_at) if updated_at else None)

    def _occupancy_before(self, session: Session, occurred_at: datetime, event_id: UUID) -> int:
        events = [
            item for item in session.scalars(select(AccessPassageEvent)) if item.id != event_id
        ]
        corrections = list(session.scalars(select(OccupancyCorrection)))
        return self._calculate(events, corrections, cutoff=occurred_at)

    def _matches(
        self,
        event: AccessPassageEvent,
        digest: str,
        occurred_at: datetime,
        checkpoint_id: str,
        direction: str,
        event_type: str,
    ) -> bool:
        return (
            event.client_reference_digest,
            self._utc(event.occurred_at),
            event.checkpoint_id,
            event.direction,
            event.event_type,
        ) == (digest, self._utc(occurred_at), checkpoint_id, direction, event_type)

    @staticmethod
    def _calculate(
        events: list[AccessPassageEvent],
        corrections: list[OccupancyCorrection],
        cutoff: datetime | None = None,
    ) -> int:
        changes = [
            (OccupancyService._utc(item.occurred_at), 0, 1 if item.direction == "entry" else -1)
            for item in events
        ]
        changes += [
            (OccupancyService._utc(item.occurred_at), 1, item.adjustment) for item in corrections
        ]
        count = 0
        for when, _, adjustment in sorted(changes):
            if cutoff is not None and when >= OccupancyService._utc(cutoff):
                continue
            count = max(0, count + adjustment)
        return count
