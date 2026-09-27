"""Face identification, separate client eligibility policy, and simulated release."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from app.modules.biometrics.config import BiometricConfig, BiometricError
from app.modules.biometrics.enrollment import aware, command, lock_biometrics, utcnow
from app.modules.biometrics.models import (
    BiometricAudit,
    BiometricCommand,
    BiometricEnrollment,
    ClientAccessState,
    RecognitionAttempt,
    ReleaseRequest,
)
from app.modules.biometrics.provider import CompreFaceProvider, FaceProvider, single_face
from app.modules.biometrics.release import (
    SimulatedTurnstileReleaseAdapter,
    TurnstileReleaseAdapter,
    TurnstileReleaseRequest,
)
from app.modules.clients.models import Client
from app.modules.occupancy.models import AccessPassageEvent

CHECKPOINT = "pilot-webcam"


def owned_attempt(session, identifier, actor):
    row = session.get(RecognitionAttempt, identifier, populate_existing=True)
    if row is None or row.actor != actor:
        raise BiometricError("attempt_not_found", 404)
    return row


def access_state(session, client_id):
    """Initialize from existing confirmed passage history, never from recognition."""
    state = session.get(ClientAccessState, client_id, populate_existing=True)
    if state is None:
        passages = session.scalars(
            select(AccessPassageEvent)
            .where(AccessPassageEvent.client_id == client_id)
            .order_by(AccessPassageEvent.occurred_at, AccessPassageEvent.created_at)
        ).all()
        latest = passages[-1] if passages else None
        state = ClientAccessState(
            client_id=client_id,
            inside=bool(latest and latest.direction == "entry"),
            revision=len(passages),
            changed_at=latest.occurred_at if latest else None,
        )
        session.add(state)
        session.flush()
    return state


def attempt_result(session, row):
    expired = aware(row.expires_at) <= utcnow() and row.status not in {"confirmed", "canceled"}
    release = session.scalar(select(ReleaseRequest).where(ReleaseRequest.attempt_id == row.id))
    client = session.get(Client, row.client_id, populate_existing=True) if row.client_id else None
    return {
        "attempt_id": str(row.id),
        "direction": row.direction,
        "status": "expired" if expired else row.status,
        "result_code": "attempt_expired" if expired else row.result_code,
        "captures": row.captures,
        "expires_at": aware(row.expires_at).isoformat(),
        "client_id": str(row.client_id) if row.client_id else None,
        "client_name": client.name if client else None,
        "release_request_id": str(release.id) if release else None,
        "release_mode": release.mode if release else None,
        "can_retry": not expired and row.status == "rejected" and row.captures < 2,
    }


def record_access_audit(session, row, operation, outcome):
    session.add(
        BiometricAudit(
            actor=row.actor,
            operation=operation,
            outcome=outcome,
            account_id=row.account_id,
            attempt_id=row.id,
            created_at=utcnow(),
        )
    )


def invalidate_enrollment_attempts(session, account_id, code="enrollment_changed"):
    for row in session.scalars(
        select(RecognitionAttempt).where(
            RecognitionAttempt.account_id == account_id,
            RecognitionAttempt.status.in_(["authorized", "capturing", "rejected"]),
        )
    ):
        row.status = "canceled"
        row.result_code = code
        row.updated_at = utcnow()
        record_access_audit(session, row, "access_invalidated", code)


def access_policy(client, enrollment, state, direction):
    if enrollment is None or not enrollment.enabled:
        return "enrollment_unavailable"
    if client is None:
        return "staff_only"
    if direction == "entry" and not client.active:
        return "client_inactive"
    if direction == "entry" and state.inside:
        return "already_inside"
    if direction == "exit" and not state.inside:
        return "already_outside"
    return "authorized"


class AccessService:
    def __init__(
        self,
        config: BiometricConfig,
        provider: FaceProvider | None = None,
        release: TurnstileReleaseAdapter | None = None,
    ):
        self.config = config
        self.provider = provider or CompreFaceProvider(config)
        self.release = release or SimulatedTurnstileReleaseAdapter()

    def create(self, session, actor, command_id, direction):
        self.config.require_pilot()
        if direction not in {"entry", "exit"}:
            raise BiometricError("direction_invalid", 422)
        lock_biometrics(session)
        cmd, replay = command(session, command_id, actor, "access_attempt", [direction])
        if replay:
            return attempt_result(session, owned_attempt(session, command_id, actor))
        for previous in session.scalars(
            select(RecognitionAttempt).where(
                RecognitionAttempt.actor == actor,
                RecognitionAttempt.status.in_(
                    ["awaiting_capture", "capturing", "rejected", "authorized"]
                ),
            )
        ):
            previous.status = "canceled"
            previous.result_code = "attempt_superseded"
            record_access_audit(session, previous, "access_cancel", "attempt_superseded")
        row = RecognitionAttempt(
            id=command_id,
            actor=actor,
            direction=direction,
            checkpoint_id=CHECKPOINT,
            captures=0,
            status="awaiting_capture",
            result_code="capture_required",
            created_at=utcnow(),
            updated_at=utcnow(),
            expires_at=utcnow() + timedelta(minutes=15),
        )
        session.add(row)
        session.flush()
        cmd.attempt_id = row.id
        cmd.result = attempt_result(session, row)
        record_access_audit(session, row, "access_attempt", "created")
        session.commit()
        return cmd.result

    def cancel(self, session, actor, attempt_id, command_id):
        lock_biometrics(session)
        row = owned_attempt(session, attempt_id, actor)
        cmd, replay = command(
            session, command_id, actor, "access_cancel", [attempt_id], account_id=row.account_id
        )
        if replay:
            return attempt_result(session, row)
        cmd.attempt_id = row.id
        if row.status != "confirmed":
            row.status = "canceled"
            row.result_code = "attempt_canceled"
            row.updated_at = utcnow()
            record_access_audit(session, row, "access_cancel", "attempt_canceled")
        cmd.result = attempt_result(session, row)
        session.commit()
        return cmd.result

    def capture(self, session, actor, attempt_id, command_id, image):
        self.config.require_pilot()
        lock_biometrics(session)
        row = owned_attempt(session, attempt_id, actor)
        cmd, replay = command(
            session, command_id, actor, "access_capture", [attempt_id], account_id=row.account_id
        )
        if replay:
            return attempt_result(session, row)
        if aware(row.expires_at) <= utcnow():
            raise BiometricError("attempt_expired", 409)
        if row.status not in {"awaiting_capture", "rejected"} or row.captures >= 2:
            raise BiometricError("attempt_not_capturable", 409)
        cmd.attempt_id = row.id
        row.captures += 1
        row.status = "capturing"
        row.result_code = "processing"
        row.capture_command_id = command_id
        row.capture_until = utcnow() + timedelta(seconds=30)
        row.updated_at = utcnow()
        cmd.result = attempt_result(session, row)
        session.commit()
        subject, failure = None, None
        try:
            face = single_face(self.provider.inspect(image), self.config)
            if not face.candidates:
                failure = "unknown_face"
            elif face.candidates[0].similarity < self.config.match_threshold:
                failure = "match_below_threshold"
            elif len(face.candidates) > 1 and (
                face.candidates[0].similarity - face.candidates[1].similarity
                < self.config.ambiguity_margin
            ):
                failure = "ambiguous_face"
            else:
                subject = face.candidates[0].subject
        except BiometricError as error:
            failure = error.code
        lock_biometrics(session)
        row = owned_attempt(session, attempt_id, actor)
        cmd = session.get(BiometricCommand, command_id, populate_existing=True)
        if row.capture_command_id != command_id or row.status != "capturing":
            cmd.result = attempt_result(session, row)
            session.commit()
            return cmd.result
        if aware(row.capture_until) <= utcnow() or aware(row.expires_at) <= utcnow():
            failure = "capture_interrupted"
        enrollment = (
            session.scalar(
                select(BiometricEnrollment)
                .where(
                    BiometricEnrollment.subject == subject, BiometricEnrollment.enabled.is_(True)
                )
                .execution_options(populate_existing=True)
            )
            if subject
            else None
        )
        if not failure and enrollment is None:
            failure = "unknown_face"
        if failure:
            row.status = "rejected" if row.captures < 2 else "failed"
            row.result_code = failure
        else:
            row.account_id = enrollment.account_id
            row.enrollment_revision = enrollment.revision
            client = session.scalar(
                select(Client)
                .where(Client.account_id == row.account_id)
                .execution_options(populate_existing=True)
            )
            row.client_id = client.id if client else None
            state = access_state(session, client.id) if client else None
            row.state_revision = state.revision if state else None
            decision = access_policy(client, enrollment, state, row.direction)
            row.result_code = decision
            row.status = "authorized" if decision == "authorized" else "denied"
            if decision == "authorized":
                request = TurnstileReleaseRequest(
                    release_request_id=uuid4(),
                    recognition_attempt_id=row.id,
                    occurred_at=utcnow(),
                    checkpoint_id=row.checkpoint_id,
                    direction=row.direction,
                    subject_reference=enrollment.subject,
                )
                # TURNSTILE_RELEASE_REQUESTED: no external call in the pilot adapter.
                mode = self.release.request_release(request)
                if mode != "simulated":
                    raise BiometricError("release_mode_invalid", 503)
                session.add(
                    ReleaseRequest(
                        id=request.release_request_id,
                        attempt_id=row.id,
                        subject_reference=request.subject_reference,
                        checkpoint_id=request.checkpoint_id,
                        direction=request.direction,
                        mode=mode,
                        occurred_at=request.occurred_at,
                    )
                )
                row.expires_at = utcnow() + timedelta(seconds=30)
            cmd.account_id = row.account_id
        row.updated_at = utcnow()
        record_access_audit(session, row, "access_capture", row.result_code)
        session.flush()
        cmd.result = attempt_result(session, row)
        session.commit()
        return cmd.result


def recover_interrupted_attempts(session):
    """Called under the same metadata lock by startup/periodic cleanup."""
    now = utcnow()
    for row in session.scalars(
        select(RecognitionAttempt).where(
            RecognitionAttempt.status.in_(
                ["capturing", "awaiting_capture", "rejected", "authorized"]
            )
        )
    ):
        interrupted = row.status == "capturing" and aware(row.capture_until) <= now
        expired = aware(row.expires_at) <= now
        if interrupted or expired:
            row.status = "expired" if expired else "rejected" if row.captures < 2 else "failed"
            row.result_code = "attempt_expired" if expired else "capture_interrupted"
            row.updated_at = now
            if row.capture_command_id:
                cmd = session.get(BiometricCommand, row.capture_command_id)
                cmd.result = attempt_result(session, row)
            record_access_audit(session, row, "access_recovery", row.result_code)
