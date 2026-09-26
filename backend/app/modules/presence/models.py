import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProfilePresencePreference(Base):
    __tablename__ = "profile_presence_preference"

    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("client.id"), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ProfilePresenceConsentAudit(Base):
    __tablename__ = "profile_presence_consent_audit"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("client.id"), nullable=False)
    previous_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    new_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
