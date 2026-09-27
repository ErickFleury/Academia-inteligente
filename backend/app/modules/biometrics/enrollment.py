"""Durable staging and atomic enrollment changes, independent of HTTP/provider shape."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.biometrics.config import BiometricConfig, BiometricError
from app.modules.biometrics.models import (
    BiometricAudit,
    BiometricCleanupJob,
    BiometricCommand,
    BiometricEnrollment,
    BiometricLock,
    EnrollmentSession,
)
from app.modules.biometrics.provider import CompreFaceProvider, FaceProvider, single_face
from app.modules.clients.models import Account, Client, PersonProfile
from app.modules.clients.service import (
    ClientValidationError,
    email_pattern,
    normalize_cpf,
    normalize_email,
)
from app.modules.occupancy.models import ClientAccessReference


def utcnow():
    return datetime.now(UTC)


def audit(session, actor, operation, outcome, account_id=None, session_id=None):
    session.add(
        BiometricAudit(
            actor=actor,
            operation=operation,
            outcome=outcome,
            account_id=account_id,
            session_id=session_id,
            created_at=utcnow(),
        )
    )


def aware(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def identity_binding(email: str, cpf: str) -> str:
    email = normalize_email(email)
    if len(email) > 320 or not email_pattern.fullmatch(email):
        raise BiometricError("identity_invalid", 422)
    try:
        return digest(email + "\n" + normalize_cpf(cpf))
    except ClientValidationError:
        raise BiometricError("identity_invalid", 422) from None


def lock_biometrics(session: Session) -> BiometricLock:
    # Seeded by migration. Serializes short metadata writes across API workers,
    # including first enrollment, where no per-person enrollment row exists yet.
    row = session.scalar(
        select(BiometricLock)
        .where(BiometricLock.id == 1)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise BiometricError("biometrics_unavailable", 503)
    return row


def enrollment_status(session: Session, account_id: UUID) -> dict:
    if session.get(PersonProfile, account_id) is None:
        raise BiometricError("person_not_found", 404)
    enrollment = session.get(BiometricEnrollment, account_id, populate_existing=True)
    pending = (
        session.scalar(
            select(BiometricCleanupJob.subject)
            .where(BiometricCleanupJob.account_id == account_id)
            .limit(1)
        )
        is not None
    )
    return {
        "person_id": str(account_id),
        "status": "enabled" if enrollment and enrollment.enabled else "missing_or_revoked",
        "revision": enrollment.revision if enrollment else 0,
        "cleanup_pending": pending,
    }


def session_status(row: EnrollmentSession) -> dict:
    expired = aware(row.expires_at) <= utcnow() and row.status != "consumed"
    return {
        "session_id": str(row.id),
        "status": "expired" if expired else row.status,
        "result_code": "session_expired" if expired else row.result_code,
        "expires_at": aware(row.expires_at).isoformat(),
    }


def owned_session(session, session_id, actor) -> EnrollmentSession:
    row = session.get(EnrollmentSession, session_id, populate_existing=True)
    if row is None or row.actor != actor:
        raise BiometricError("session_not_found", 404)
    return row


def command(session, command_id, actor, operation, payload, *, account_id=None, session_id=None):
    fingerprint = digest(json.dumps(payload, sort_keys=True, default=str))
    existing = session.get(BiometricCommand, command_id, populate_existing=True)
    if existing:
        if (existing.actor, existing.operation, existing.fingerprint) != (
            actor,
            operation,
            fingerprint,
        ):
            raise BiometricError("command_conflict", 409)
        return existing, True
    row = BiometricCommand(
        id=command_id,
        actor=actor,
        operation=operation,
        fingerprint=fingerprint,
        account_id=account_id,
        session_id=session_id,
        result={"status": "processing"},
        created_at=utcnow(),
    )
    session.add(row)
    return row, False


def sync_access_reference(session: Session, enrollment: BiometricEnrollment):
    client = session.scalar(select(Client).where(Client.account_id == enrollment.account_id))
    if client is None:
        return
    reference = session.scalar(
        select(ClientAccessReference).where(ClientAccessReference.client_id == client.id)
    )
    if reference is None:
        reference = ClientAccessReference(client_id=client.id)
        session.add(reference)
    reference.reference_digest = digest(enrollment.subject)
    reference.active = enrollment.enabled


class EnrollmentService:
    def __init__(self, config: BiometricConfig, provider: FaceProvider | None = None):
        self.config = config
        self.provider = provider or CompreFaceProvider(config)

    def create(
        self,
        session: Session,
        actor: str,
        command_id: UUID,
        *,
        email: str,
        cpf: str,
        role: str,
        person_id: UUID | None = None,
        expected_revision: int = 0,
    ):
        self.config.require_pilot()
        binding = identity_binding(email, cpf)
        if role not in {"client", "employee", "replacement"}:
            raise BiometricError("enrollment_role_invalid", 422)
        lock_biometrics(session)
        cmd, replay = command(
            session,
            command_id,
            actor,
            "enrollment_session",
            [binding, role, person_id, expected_revision],
        )
        if replay:
            return session_status(owned_session(session, command_id, actor))
        account = session.scalar(
            select(Account)
            .join(PersonProfile)
            .where(Account.email == normalize_email(email), PersonProfile.cpf == normalize_cpf(cpf))
        )
        # Reject a conflicting identity before sending anything to the provider.
        email_owner = session.scalar(
            select(Account.id).where(Account.email == normalize_email(email))
        )
        cpf_owner = session.scalar(
            select(PersonProfile.account_id).where(PersonProfile.cpf == normalize_cpf(cpf))
        )
        if (email_owner or cpf_owner) and (account is None):
            raise BiometricError("identity_conflict", 409)
        if person_id is not None and (account is None or account.id != person_id):
            raise BiometricError("identity_conflict", 409)
        if role == "replacement" and person_id is None:
            raise BiometricError("person_required", 422)
        enrollment = session.get(BiometricEnrollment, account.id) if account else None
        revision = enrollment.revision if enrollment else 0
        if revision != expected_revision:
            raise BiometricError("enrollment_stale", 409)
        row = EnrollmentSession(
            id=command_id,
            actor=actor,
            identity_binding=binding,
            role=role,
            account_id=account.id if account else None,
            expected_revision=revision,
            status="awaiting_capture",
            result_code="capture_required",
            created_at=utcnow(),
            expires_at=utcnow() + timedelta(minutes=15),
        )
        session.add(row)
        session.flush()
        cmd.session_id = row.id
        cmd.account_id = row.account_id
        cmd.result = session_status(row)
        audit(session, actor, "enrollment_session", "created", row.account_id, row.id)
        session.commit()
        return cmd.result

    def capture(
        self, session: Session, actor: str, session_id: UUID, command_id: UUID, image: bytes
    ):
        self.config.require_pilot()
        gate = lock_biometrics(session)
        row = owned_session(session, session_id, actor)
        cmd, replay = command(
            session,
            command_id,
            actor,
            "enrollment_capture",
            [session_id],
            account_id=row.account_id,
            session_id=row.id,
        )
        if replay:
            return cmd.result
        if aware(row.expires_at) <= utcnow():
            raise BiometricError("session_expired", 409)
        if row.status not in {"awaiting_capture", "rejected"}:
            raise BiometricError("session_not_capturable", 409)
        if gate.capture_until and aware(gate.capture_until) > utcnow():
            raise BiometricError("capture_in_progress", 409)
        subject = "face-" + uuid4().hex
        row.subject = subject
        row.status = "capturing"
        row.result_code = "processing"
        row.capture_command_id = command_id
        row.capture_until = utcnow() + timedelta(seconds=60)
        gate.capture_until = row.capture_until
        # The cleanup intent commits BEFORE any external write; a crash cannot
        # leave an untraceable enrolled subject or silently make it eligible.
        session.add(
            BiometricCleanupJob(
                subject=subject,
                account_id=row.account_id,
                session_id=row.id,
                due_at=max(aware(row.expires_at), row.capture_until),
            )
        )
        cmd.result = session_status(row)
        session.commit()
        failure = None
        try:
            face = single_face(self.provider.inspect(image), self.config)
            if (
                len(face.candidates) > 1
                and face.candidates[0].similarity >= self.config.match_threshold
                and face.candidates[0].similarity - face.candidates[1].similarity
                < self.config.ambiguity_margin
            ):
                raise BiometricError("face_identity_ambiguous", 422)
            current = session.get(BiometricEnrollment, row.account_id) if row.account_id else None
            # Similarity never merges people. Old/current references for this person
            # may be replaced, but an unknown/staged/other person's match is rejected.
            for candidate in face.candidates:
                if candidate.similarity >= self.config.match_threshold and (
                    current is None or candidate.subject != current.subject
                ):
                    raise BiometricError("face_identity_conflict", 422)
            session.rollback()  # do not hold a read transaction during provider I/O
            self.provider.enroll(subject, image)
        except BiometricError as error:
            failure = error.code
        gate = lock_biometrics(session)
        row = owned_session(session, session_id, actor)
        cmd = session.get(BiometricCommand, command_id, populate_existing=True)
        job = session.get(BiometricCleanupJob, subject)
        if row.capture_command_id != command_id:
            # Another explicit capture recovered this session. A late response
            # belongs only to its own command, never to the newer capture/lease.
            cmd.result = {
                "session_id": str(session_id),
                "status": "rejected",
                "result_code": "capture_superseded",
                "expires_at": aware(row.expires_at).isoformat(),
            }
            if job:
                job.due_at = utcnow() + timedelta(seconds=60)
            audit(
                session, actor, "enrollment_capture", "capture_superseded", row.account_id, row.id
            )
            session.commit()
            return cmd.result
        # A resumed request cannot revive an expired/invalidated staging operation.
        if (
            row.status != "capturing"
            or aware(row.expires_at) <= utcnow()
            or aware(row.capture_until) <= utcnow()
            or job is None
        ):
            failure = failure or "session_expired"
        if gate.capture_until == row.capture_until:
            gate.capture_until = None
        row.status = "rejected" if failure else "ready"
        row.result_code = failure or "enrollment_ready"
        if failure and job:
            job.due_at = utcnow() + timedelta(seconds=60)
            job.last_code = failure
        cmd.result = session_status(row)
        audit(session, actor, "enrollment_capture", row.result_code, row.account_id, row.id)
        session.commit()
        return cmd.result

    def attach(
        self,
        session: Session,
        *,
        account_id: UUID,
        email: str,
        cpf: str,
        role: str,
        actor: str,
        session_id: UUID | None,
    ):
        """Participates in the caller's registration transaction; NEVER commits."""
        self.config.require_pilot()
        lock_biometrics(session)
        current = session.get(BiometricEnrollment, account_id, populate_existing=True)
        if session_id is None:
            if current and current.enabled:
                sync_access_reference(session, current)
                return current
            raise BiometricError("enrollment_required", 422)
        row = owned_session(session, session_id, actor)
        if (
            row.identity_binding != identity_binding(email, cpf)
            or row.role != role
            or row.account_id not in {None, account_id}
        ):
            raise BiometricError("enrollment_identity_conflict", 409)
        if row.status != "ready" or aware(row.expires_at) <= utcnow():
            raise BiometricError("enrollment_not_ready", 409)
        if (current.revision if current else 0) != row.expected_revision:
            raise BiometricError("enrollment_stale", 409)
        if current:
            from app.modules.biometrics.access import invalidate_enrollment_attempts

            invalidate_enrollment_attempts(session, account_id)
            self._queue_delete(session, current.subject, account_id)
            current.subject = row.subject
            current.revision += 1
            current.enabled = True
            current.updated_at = utcnow()
            current.model = self.config.model
        else:
            current = BiometricEnrollment(
                account_id=account_id,
                subject=row.subject,
                revision=1,
                enabled=True,
                model=self.config.model,
                updated_at=utcnow(),
            )
            session.add(current)
        job = session.get(BiometricCleanupJob, row.subject)
        if job:
            session.delete(job)
        row.status = "consumed"
        row.result_code = "enrollment_attached"
        row.account_id = account_id
        for cmd in session.scalars(
            select(BiometricCommand).where(BiometricCommand.session_id == row.id)
        ):
            cmd.account_id = account_id
        audit(session, actor, "enrollment_attach", "enabled", account_id, row.id)
        session.flush()
        sync_access_reference(session, current)
        return current

    def replace(self, session, actor, account_id, command_id, session_id, expected_revision):
        self.config.require_pilot()
        lock_biometrics(session)
        cmd, replay = command(
            session,
            command_id,
            actor,
            "enrollment_replace",
            [account_id, session_id, expected_revision],
            account_id=account_id,
        )
        if replay:
            return cmd.result
        account = session.get(Account, account_id, populate_existing=True)
        if account is None or account.person_profile is None:
            raise BiometricError("person_not_found", 404)
        row = owned_session(session, session_id, actor)
        if row.expected_revision != expected_revision:
            raise BiometricError("enrollment_stale", 409)
        self.attach(
            session,
            account_id=account_id,
            email=account.email,
            cpf=account.person_profile.cpf,
            role="replacement",
            actor=actor,
            session_id=session_id,
        )
        session.flush()
        cmd.result = enrollment_status(session, account_id)
        session.commit()
        return cmd.result

    def revoke(self, session, actor, account_id, command_id, expected_revision):
        self.config.require_pilot()
        lock_biometrics(session)
        cmd, replay = command(
            session,
            command_id,
            actor,
            "enrollment_revoke",
            [account_id, expected_revision],
            account_id=account_id,
        )
        if replay:
            return cmd.result
        enrollment = session.get(BiometricEnrollment, account_id, populate_existing=True)
        if enrollment is None:
            raise BiometricError("enrollment_not_found", 404)
        if enrollment.revision != expected_revision:
            raise BiometricError("enrollment_stale", 409)
        enrollment.enabled = False
        from app.modules.biometrics.access import invalidate_enrollment_attempts

        invalidate_enrollment_attempts(session, account_id, "enrollment_revoked")
        enrollment.revision += 1
        enrollment.updated_at = utcnow()
        audit(session, actor, "enrollment_revoke", "disabled", account_id)
        self._queue_delete(session, enrollment.subject, account_id)
        sync_access_reference(session, enrollment)
        session.flush()
        cmd.result = enrollment_status(session, account_id)
        session.commit()
        return cmd.result

    @staticmethod
    def _queue_delete(session, subject, account_id=None):
        if not session.get(BiometricCleanupJob, subject):
            session.add(
                BiometricCleanupJob(subject=subject, account_id=account_id, due_at=utcnow())
            )

    def cleanup(self, session: Session, limit: int = 20):
        from app.modules.biometrics.access import recover_interrupted_attempts

        self.config.require_pilot()
        for _ in range(limit):
            lock_biometrics(session)
            recover_interrupted_attempts(session)
            now = utcnow()
            for row in session.scalars(
                select(EnrollmentSession).where(
                    EnrollmentSession.status.in_(
                        ["awaiting_capture", "capturing", "ready", "rejected"]
                    )
                )
            ):
                expired = aware(row.expires_at) <= now
                interrupted = row.status == "capturing" and aware(row.capture_until) <= now
                if row.status == "capturing" and aware(row.capture_until) > now:
                    continue
                if expired or interrupted:
                    row.status = "expired" if expired else "rejected"
                    row.result_code = "session_expired" if expired else "capture_interrupted"
                    audit(
                        session,
                        "system:biometric-cleanup",
                        "enrollment_cleanup",
                        row.result_code,
                        row.account_id,
                        row.id,
                    )
                    if row.capture_command_id:
                        cmd = session.get(BiometricCommand, row.capture_command_id)
                        cmd.result = session_status(row)
                    if row.subject:
                        job = session.get(BiometricCleanupJob, row.subject)
                        if job:
                            job.due_at = now
            session.flush()
            job = session.scalar(
                select(BiometricCleanupJob)
                .where(BiometricCleanupJob.due_at <= now)
                .order_by(BiometricCleanupJob.due_at)
                .limit(1)
            )
            if job is None:
                session.commit()
                break
            active = session.scalar(
                select(BiometricEnrollment.account_id).where(
                    BiometricEnrollment.subject == job.subject,
                    BiometricEnrollment.enabled.is_(True),
                )
            )
            if active:
                raise BiometricError("cleanup_active_reference", 503)
            try:
                self.provider.delete(job.subject)
            except BiometricError:
                job.attempts = min(job.attempts + 1, 1000)
                job.last_code = "cleanup_pending"
                job.due_at = now + timedelta(seconds=min(60 * 2 ** min(job.attempts, 6), 3600))
            else:
                session.delete(job)
            session.commit()
