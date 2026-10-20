"""Versioned reference ingestion and PostgreSQL hybrid retrieval."""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

revision = "20261019_32"
down_revision = "20260927_31"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
    op.create_table(
        "ai_reference_source",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "ai_reference_version",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("ai_reference_source.id"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(80), nullable=False),
        sa.Column("raw_content", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("error_code", sa.String(60)),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("embedding_fingerprint", sa.String(64)),
        sa.Column("embedding_dimensions", sa.Integer()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("source_id", "number"),
    )
    op.create_index("ix_ai_reference_version_source_id", "ai_reference_version", ["source_id"])
    op.create_index(
        "uq_ai_reference_active_source",
        "ai_reference_version",
        ["source_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.create_table(
        "ai_reference_passage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "version_id", sa.Uuid(), sa.ForeignKey("ai_reference_version.id"), nullable=False
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
        sa.UniqueConstraint("version_id", "position"),
    )
    op.create_index("ix_ai_reference_passage_version_id", "ai_reference_passage", ["version_id"])
    op.execute(
        "CREATE INDEX ix_ai_reference_text ON ai_reference_passage "
        "USING gin(to_tsvector('portuguese'::regconfig, content))"
    )


def downgrade():
    op.drop_table("ai_reference_passage")
    op.drop_table("ai_reference_version")
    op.drop_table("ai_reference_source")
    # The extension may be used by other schemas; do not remove it on downgrade.
