"""Bounded administrator history with no biometric material or provider identifiers."""

import base64
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import String, and_, case, cast, func, literal, or_, select, union_all

from app.modules.biometrics.config import BiometricError
from app.modules.biometrics.enrollment import aware, utcnow
from app.modules.biometrics.models import BiometricAudit, BiometricCleanupJob, RecognitionAttempt
from app.modules.clients.models import Client, PersonProfile
from app.modules.occupancy.models import OccupancyCorrection


def event_history(session, *, limit=20, cursor=None, client_id=None, result=None, direction=None):
    audit = (
        select(
            cast(BiometricAudit.id, String).label("id"),
            literal("audit").label("kind"),
            BiometricAudit.created_at.label("occurred_at"),
            BiometricAudit.operation.label("operation"),
            BiometricAudit.outcome.label("result"),
            Client.id.label("client_id"),
            (PersonProfile.first_name + " " + PersonProfile.surname).label("person_name"),
            RecognitionAttempt.direction.label("direction"),
            cast(literal(None), String).label("reason"),
        )
        .select_from(BiometricAudit)
        .outerjoin(PersonProfile, PersonProfile.account_id == BiometricAudit.account_id)
        .outerjoin(Client, Client.account_id == BiometricAudit.account_id)
        .outerjoin(RecognitionAttempt, RecognitionAttempt.id == BiometricAudit.attempt_id)
        .where(BiometricAudit.operation != "state_correction")
    )
    corrections = (
        select(
            cast(OccupancyCorrection.id, String),
            literal("correction"),
            OccupancyCorrection.occurred_at,
            literal("state_correction"),
            case((OccupancyCorrection.adjustment == 0, "unchanged"), else_="corrected"),
            Client.id,
            Client.name,
            case((OccupancyCorrection.target_inside, "entry"), else_="exit"),
            OccupancyCorrection.reason,
        )
        .select_from(OccupancyCorrection)
        .join(Client, Client.id == OccupancyCorrection.client_id)
        .where(OccupancyCorrection.source_kind == "simulated")
    )
    events = union_all(audit, corrections).subquery()
    query = select(events)
    if client_id:
        query = query.where(events.c.client_id == client_id)
    if result:
        query = query.where(events.c.result == result)
    if direction:
        query = query.where(events.c.direction == direction)
    if cursor:
        try:
            payload = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
            timestamp = datetime.fromisoformat(payload["time"])
            identifier, kind = payload["id"], payload["kind"]
            if not isinstance(identifier, str):
                raise ValueError()
            UUID(identifier)
            if timestamp.tzinfo is None or kind not in {"audit", "correction"}:
                raise ValueError()
        except (ValueError, TypeError, KeyError, UnicodeError):
            raise BiometricError("history_cursor_invalid", 422) from None
        query = query.where(
            or_(
                events.c.occurred_at < timestamp,
                and_(events.c.occurred_at == timestamp, events.c.kind < kind),
                and_(
                    events.c.occurred_at == timestamp,
                    events.c.kind == kind,
                    events.c.id < identifier,
                ),
            )
        )
    rows = (
        session.execute(
            query.order_by(
                events.c.occurred_at.desc(), events.c.kind.desc(), events.c.id.desc()
            ).limit(limit + 1)
        )
        .mappings()
        .all()
    )
    items = [dict(row, occurred_at=aware(row["occurred_at"]).isoformat()) for row in rows[:limit]]
    next_cursor = None
    if len(rows) > limit:
        last = items[-1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(
                {"time": last["occurred_at"], "id": last["id"], "kind": last["kind"]}
            ).encode()
        ).decode()
    return {"items": items, "next_cursor": next_cursor}


def provider_status(session, service):
    available = False
    try:
        service.config.require_pilot()
        service.provider.ready()
        available = True
    except BiometricError:
        pass
    pending = session.scalar(
        select(func.count())
        .select_from(BiometricCleanupJob)
        .where(
            or_(BiometricCleanupJob.due_at <= utcnow(), BiometricCleanupJob.last_code.is_not(None))
        )
    )
    return {"mode": service.config.mode, "available": available, "cleanup_pending": pending}
