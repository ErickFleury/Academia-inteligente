"""Lifecycle metadata only: no captures, embeddings, or raw provider results."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BiometricLock(Base):
    __tablename__ = "biometric_lock"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    capture_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BiometricEnrollment(Base):
    __tablename__ = "biometric_enrollment"
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("person_profile.account_id"), primary_key=True
    )
    subject: Mapped[str] = mapped_column(String(80), unique=True)
    revision: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean)
    model: Mapped[str] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EnrollmentSession(Base):
    __tablename__ = "biometric_enrollment_session"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    actor: Mapped[str] = mapped_column(String(255))
    identity_binding: Mapped[str] = mapped_column(String(64), index=True)
    role: Mapped[str] = mapped_column(String(20))
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("person_profile.account_id"), index=True
    )
    expected_revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    result_code: Mapped[str] = mapped_column(String(60))
    subject: Mapped[str | None] = mapped_column(String(80), unique=True)
    capture_command_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    capture_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class BiometricCleanupJob(Base):
    __tablename__ = "biometric_cleanup_job"
    subject: Mapped[str] = mapped_column(String(80), primary_key=True)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("person_profile.account_id"), index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("biometric_enrollment_session.id")
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_code: Mapped[str | None] = mapped_column(String(60))


class BiometricCommand(Base):
    """Recoverable command status, separate from append-only audit records."""

    __tablename__ = "biometric_command"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    actor: Mapped[str] = mapped_column(String(255))
    operation: Mapped[str] = mapped_column(String(40))
    fingerprint: Mapped[str] = mapped_column(String(64))
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("person_profile.account_id"), index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("biometric_enrollment_session.id")
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("biometric_recognition_attempt.id")
    )
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BiometricAudit(Base):
    __tablename__ = "biometric_audit"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String(255))
    operation: Mapped[str] = mapped_column(String(40))
    outcome: Mapped[str] = mapped_column(String(60))
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("person_profile.account_id"), index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("biometric_enrollment_session.id")
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("biometric_recognition_attempt.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ClientAccessState(Base):
    __tablename__ = "biometric_client_access_state"
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("client.id"), primary_key=True)
    inside: Mapped[bool] = mapped_column(Boolean)
    revision: Mapped[int] = mapped_column(Integer)
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecognitionAttempt(Base):
    __tablename__ = "biometric_recognition_attempt"
    __table_args__ = (
        CheckConstraint("captures >= 0 AND captures <= 2", name="ck_face_capture_budget"),
        CheckConstraint("direction IN ('entry', 'exit')", name="ck_face_attempt_direction"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    actor: Mapped[str] = mapped_column(String(255), index=True)
    direction: Mapped[str] = mapped_column(String(8))
    checkpoint_id: Mapped[str] = mapped_column(String(80))
    captures: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24))
    result_code: Mapped[str] = mapped_column(String(60))
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("person_profile.account_id"), index=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("client.id"), index=True)
    enrollment_revision: Mapped[int | None] = mapped_column(Integer)
    state_revision: Mapped[int | None] = mapped_column(Integer)
    capture_command_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    capture_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReleaseRequest(Base):
    __tablename__ = "biometric_release_request"
    __table_args__ = (CheckConstraint("mode = 'simulated'", name="ck_face_release_simulated"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("biometric_recognition_attempt.id"), unique=True
    )
    subject_reference: Mapped[str] = mapped_column(String(80))
    checkpoint_id: Mapped[str] = mapped_column(String(80))
    direction: Mapped[str] = mapped_column(String(8))
    mode: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
