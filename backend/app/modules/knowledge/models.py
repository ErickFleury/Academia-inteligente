from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PublicVector(Vector):
    """The shared extension lives in public even when tests isolate domain schemas."""

    cache_ok = True

    def get_col_spec(self, **kwargs):
        return "public.vector"


class ReferenceSource(Base):
    __tablename__ = "ai_reference_source"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReferenceVersion(Base):
    __tablename__ = "ai_reference_version"
    __table_args__ = (
        UniqueConstraint("source_id", "number"),
        Index(
            "uq_ai_reference_active_source",
            "source_id",
            unique=True,
            postgresql_where=text("active"),
            sqlite_where=text("active = 1"),
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(ForeignKey("ai_reference_source.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    media_type: Mapped[str] = mapped_column(String(80))
    raw_content: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    error_code: Mapped[str | None] = mapped_column(String(60))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    generation: Mapped[int] = mapped_column(Integer, default=1)
    embedding_fingerprint: Mapped[str | None] = mapped_column(String(64))
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReferencePassage(Base):
    __tablename__ = "ai_reference_passage"
    __table_args__ = (UniqueConstraint("version_id", "position"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(ForeignKey("ai_reference_version.id"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    location: Mapped[str] = mapped_column(String(80))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(PublicVector().with_variant(JSON(), "sqlite"))
