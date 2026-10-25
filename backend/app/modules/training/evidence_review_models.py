"""Append-only professional judgments and instructor-owned synthetic evaluation seals."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EvidenceJudgment(Base):
    __tablename__ = "training_evidence_judgment"
    __table_args__ = (
        UniqueConstraint("reviewer_subject", "request_id", name="uq_evidence_review_request"),
        UniqueConstraint("supersedes_id", name="uq_evidence_review_successor"),
        Index(
            "uq_evidence_review_current_person",
            "artifact_id",
            "artifact_sha256",
            "reviewer_subject",
            unique=True,
            postgresql_where=text("is_current"),
            sqlite_where=text("is_current"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(Uuid)
    artifact_id: Mapped[str] = mapped_column(String(180), index=True)
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    reviewer_subject: Mapped[str] = mapped_column(String(255))
    reviewer_name: Mapped[str] = mapped_column(String(301))
    function: Mapped[str] = mapped_column(String(32))
    decision: Mapped[str] = mapped_column(String(32))
    request_sha256: Mapped[str] = mapped_column(String(64))
    supersedes_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("training_evidence_judgment.id")
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class EvidenceSeal(Base):
    __tablename__ = "training_evidence_seal"
    __table_args__ = (
        UniqueConstraint("custodian_subject", "request_id", name="uq_evidence_seal_request"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(Uuid)
    custodian_subject: Mapped[str] = mapped_column(String(255), index=True)
    custodian_name: Mapped[str] = mapped_column(String(301))
    request_sha256: Mapped[str] = mapped_column(String(64))
    protocol: Mapped[dict] = mapped_column(JSON)
    artifact_hashes: Mapped[dict] = mapped_column(JSON)
    attestations: Mapped[dict] = mapped_column(JSON)
    case_count: Mapped[int] = mapped_column(Integer)
    payload_sha256: Mapped[str] = mapped_column(String(64))
    private_cases: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
