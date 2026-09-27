"""Lifecycle metadata only: no captures, embeddings, or raw provider results."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Uuid
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
