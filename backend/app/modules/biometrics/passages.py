"""Only explicit simulated passage or a reasoned correction changes occupancy."""

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.modules.biometrics.access import (
    CHECKPOINT,
    access_policy,
    access_state,
    invalidate_enrollment_attempts,
    owned_attempt,
    record_access_audit,
)
from app.modules.biometrics.config import BiometricError
from app.modules.biometrics.enrollment import audit, aware, command, digest, lock_biometrics, utcnow
from app.modules.biometrics.models import BiometricEnrollment, ReleaseRequest
from app.modules.clients.models import Account, Client
from app.modules.occupancy.models import (
    AccessPassageEvent,
    AccessSourceHeartbeat,
    OccupancyCorrection,
)
from app.modules.occupancy.service import OccupancyService


def lock_client(session, client_id):
    account_id = session.scalar(select(Client.account_id).where(Client.id == client_id))
    if account_id is None:
        raise BiometricError("client_not_found", 404)
    session.scalar(select(Account).where(Account.id == account_id).with_for_update())
    client = session.get(Client, client_id, populate_existing=True)
    if client is None:
        raise BiometricError("client_not_found", 404)
    return client


def state_result(client, state):
    return {
        "client_id": str(client.id),
        "client_name": client.name,
        "inside": state.inside,
        "revision": state.revision,
        "client_active": client.active,
    }


class PassageService:
    def __init__(self, config, provider):
        self.config = config
        self.provider = provider

    def state(self, session, client_id):
        client = lock_client(session, client_id)
        lock_biometrics(session)
        result = state_result(client, access_state(session, client.id))
        session.commit()
        return result

    def confirm(self, session, actor, attempt_id, command_id):
        self.config.require_pilot()
        attempt = owned_attempt(session, attempt_id, actor)
        if attempt.client_id is None:
            raise BiometricError("passage_not_authorized", 409)
        client = lock_client(session, attempt.client_id)
        lock_biometrics(session)
        attempt = owned_attempt(session, attempt_id, actor)
        cmd, replay = command(
            session,
            command_id,
            actor,
            "passage_confirm",
            [attempt_id],
            account_id=client.account_id,
        )
        if replay:
            session.commit()
            return cmd.result
        cmd.attempt_id = attempt.id
        event_id = "pilot:" + str(attempt.id)
        existing = session.scalar(
            select(AccessPassageEvent).where(AccessPassageEvent.event_id == event_id)
        )
        state = access_state(session, client.id)
        if attempt.status == "confirmed" and existing is not None:
            cmd.result = {
                "status": "confirmed",
                "attempt_id": str(attempt.id),
                "passage_event_id": str(existing.id),
                "state": state_result(client, state),
                "occupancy": OccupancyService().snapshot(session).occupancy,
            }
            session.commit()
            return cmd.result
        if attempt.status != "authorized" or aware(attempt.expires_at) <= utcnow():
            raise BiometricError("passage_not_authorized", 409)
        enrollment = session.get(BiometricEnrollment, client.account_id, populate_existing=True)
        release = session.scalar(
            select(ReleaseRequest).where(ReleaseRequest.attempt_id == attempt.id)
        )
        if (
            not enrollment
            or not enrollment.enabled
            or release is None
            or enrollment.revision != attempt.enrollment_revision
            or enrollment.subject != release.subject_reference
        ):
            raise BiometricError("enrollment_changed", 409)
        if state.revision != attempt.state_revision:
            raise BiometricError("state_changed", 409)
        policy = access_policy(client, enrollment, state, attempt.direction)
        if policy != "authorized":
            raise BiometricError(policy, 409)
        now = utcnow()
        state.inside = attempt.direction == "entry"
        state.revision += 1
        state.changed_at = now
        passage = AccessPassageEvent(
            id=uuid5(NAMESPACE_URL, "academia:" + event_id),
            event_id=event_id,
            client_id=client.id,
            client_reference_digest=digest(enrollment.subject),
            occurred_at=now,
            checkpoint_id=CHECKPOINT,
            direction=attempt.direction,
            event_type="passage_confirmed",
            source_kind="simulated",
            state_revision=state.revision,
            inconsistency=False,
        )
        session.add(passage)
        attempt.status = "confirmed"
        attempt.result_code = "passage_confirmed"
        attempt.updated_at = now
        record_access_audit(session, attempt, "passage_confirm", "passage_confirmed")
        session.flush()
        cmd.result = {
            "status": "confirmed",
            "attempt_id": str(attempt.id),
            "passage_event_id": str(passage.id),
            "state": state_result(client, state),
            "occupancy": OccupancyService().snapshot(session).occupancy,
        }
        session.commit()
        return cmd.result

    def correct(self, session, actor, command_id, client_id, inside, expected_revision, reason):
        self.config.require_pilot()
        reason = reason.strip()
        if not reason or len(reason) > 1000 or type(inside) is not bool:
            raise BiometricError("correction_invalid", 422)
        client = lock_client(session, client_id)
        lock_biometrics(session)
        cmd, replay = command(
            session,
            command_id,
            actor,
            "state_correction",
            [client_id, inside, expected_revision, reason],
            account_id=client.account_id,
        )
        if replay:
            session.commit()
            return cmd.result
        state = access_state(session, client.id)
        if state.revision != expected_revision:
            raise BiometricError("state_changed", 409)
        previous = state.inside
        adjustment = int(inside) - int(previous)
        now = utcnow()
        if adjustment:
            state.inside = inside
            state.revision += 1
            state.changed_at = now
        correction = OccupancyCorrection(
            actor_subject=actor,
            client_id=client.id,
            command_id=command_id,
            previous_inside=previous,
            target_inside=inside,
            state_revision=state.revision,
            source_kind="simulated",
            adjustment=adjustment,
            reason=reason,
            occurred_at=now,
        )
        session.add(correction)
        invalidate_enrollment_attempts(session, client.account_id, "state_corrected")
        audit(
            session,
            actor,
            "state_correction",
            "corrected" if adjustment else "unchanged",
            client.account_id,
        )
        session.flush()
        cmd.result = {
            "status": "corrected" if adjustment else "unchanged",
            "correction_id": str(correction.id),
            "state": state_result(client, state),
            "occupancy": OccupancyService().snapshot(session).occupancy,
        }
        session.commit()
        return cmd.result

    def heartbeat(self, session, actor, command_id):
        self.config.require_pilot()
        self.provider.ready()  # includes API and recognition worker, not just the open browser
        lock_biometrics(session)
        cmd, replay = command(session, command_id, actor, "pilot_heartbeat", [CHECKPOINT])
        if replay:
            session.commit()
            return cmd.result
        now = utcnow()
        row = session.get(AccessSourceHeartbeat, CHECKPOINT)
        if row is None:
            session.add(
                AccessSourceHeartbeat(checkpoint_id=CHECKPOINT, occurred_at=now, received_at=now)
            )
        else:
            row.occurred_at = now
            row.received_at = now
        cmd.result = {"status": "current", "occurred_at": now.isoformat()}
        session.commit()
        return cmd.result
