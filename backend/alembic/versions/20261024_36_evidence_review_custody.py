"""Persist actual instructor judgments and private synthetic evaluation custody."""

import sqlalchemy as sa

from alembic import op

revision = "20261024_36"
down_revision = "20261023_35"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "training_evidence_judgment",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("artifact_id", sa.String(180), nullable=False),
        sa.Column("artifact_sha256", sa.String(64), nullable=False),
        sa.Column("reviewer_subject", sa.String(255), nullable=False),
        sa.Column("reviewer_name", sa.String(301), nullable=False),
        sa.Column("function", sa.String(32), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("supersedes_id", sa.Uuid(), sa.ForeignKey("training_evidence_judgment.id")),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("reviewer_subject", "request_id", name="uq_evidence_review_request"),
        sa.UniqueConstraint("supersedes_id", name="uq_evidence_review_successor"),
    )
    op.create_index(
        "ix_training_evidence_judgment_artifact_id", "training_evidence_judgment", ["artifact_id"]
    )
    op.create_index(
        "uq_evidence_review_current_person",
        "training_evidence_judgment",
        ["artifact_id", "artifact_sha256", "reviewer_subject"],
        unique=True,
        postgresql_where=sa.text("is_current"),
        sqlite_where=sa.text("is_current"),
    )
    op.create_table(
        "training_evidence_seal",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("custodian_subject", sa.String(255), nullable=False),
        sa.Column("custodian_name", sa.String(301), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("protocol", sa.JSON(), nullable=False),
        sa.Column("artifact_hashes", sa.JSON(), nullable=False),
        sa.Column("attestations", sa.JSON(), nullable=False),
        sa.Column("case_count", sa.Integer(), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("private_cases", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("custodian_subject", "request_id", name="uq_evidence_seal_request"),
    )
    op.create_index(
        "ix_training_evidence_seal_custodian_subject",
        "training_evidence_seal",
        ["custodian_subject"],
    )


def downgrade():
    op.drop_table("training_evidence_seal")
    op.drop_table("training_evidence_judgment")
