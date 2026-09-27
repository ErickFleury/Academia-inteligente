import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClientAccessReference(Base):
    __tablename__ = "client_access_reference"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("client.id"), unique=True)
    reference_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AccessPassageEvent(Base):
    __tablename__ = "access_passage_event"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("client.id"), nullable=False, index=True
    )
    client_reference_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    checkpoint_id: Mapped[str] = mapped_column(String(200), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="passage_confirmed"
    )
    inconsistency: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default="external")
    state_revision: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OccupancyCorrection(Base):
    __tablename__ = "occupancy_correction"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    adjustment: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    client_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("client.id"), index=True)
    command_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True)
    previous_inside: Mapped[bool | None] = mapped_column(Boolean)
    target_inside: Mapped[bool | None] = mapped_column(Boolean)
    state_revision: Mapped[int | None] = mapped_column(Integer)
    source_kind: Mapped[str] = mapped_column(String(20), nullable=False, server_default="manual")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AccessSourceHeartbeat(Base):
    __tablename__ = "access_source_heartbeat"

    checkpoint_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
