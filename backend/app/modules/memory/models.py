"""Compact client reports; no indefinite transcript or quoted-source archive."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ClientMemoryFact(Base):
    __tablename__ = "client_memory_fact"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(ForeignKey("client.id"), index=True)
    category: Mapped[str] = mapped_column(String(24))
    text: Mapped[str] = mapped_column(String(400))
    attribution: Mapped[str] = mapped_column(String(24))
    source_event_id: Mapped[UUID | None] = mapped_column(Uuid)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
