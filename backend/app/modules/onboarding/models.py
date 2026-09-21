"""Persistence models owned by the onboarding module."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OnboardingInvitation(Base):
    """A one-time, client-bound onboarding invitation without a raw token."""

    __tablename__ = "onboarding_invitation"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("client.id"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_status: Mapped[str] = mapped_column(String(16), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Onboarding(Base):
    """Client-owned structured onboarding, separated from ordinary profile data."""

    __tablename__ = "onboarding"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client.id"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft")
    training_goal: Mapped[str | None] = mapped_column(String(500))
    training_experience: Mapped[str | None] = mapped_column(String(16))
    height_cm: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    has_limitations_or_complaints: Mapped[bool | None] = mapped_column(Boolean)
    limitations_or_complaints: Mapped[str | None] = mapped_column(Text)
    uses_medications: Mapped[bool | None] = mapped_column(Boolean)
    medications: Mapped[str | None] = mapped_column(Text)
    has_health_conditions: Mapped[bool | None] = mapped_column(Boolean)
    health_conditions: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OnboardingAuditEvent(Base):
    """Non-sensitive audit evidence for allowed onboarding operations."""

    __tablename__ = "onboarding_audit_event"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    onboarding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("onboarding.id"), nullable=False
    )
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("client.id"), nullable=False)
    actor_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("account.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_fields: Mapped[str | None] = mapped_column(String(1000))
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
