"""Durable client-owned compact memory and non-content replay suppression."""

import sqlalchemy as sa

from alembic import op

revision = "20261019_33"
down_revision = "20261019_32"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "client", sa.Column("memory_revision", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column("client", sa.Column("memory_event_after", sa.DateTime(timezone=True)))
    op.create_table(
        "client_memory_fact",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("text", sa.String(400), nullable=False),
        sa.Column("attribution", sa.String(24), nullable=False),
        sa.Column("source_event_id", sa.Uuid()),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_client_memory_fact_client_id", "client_memory_fact", ["client_id"])


def downgrade():
    op.drop_table("client_memory_fact")
    op.drop_column("client", "memory_event_after")
    op.drop_column("client", "memory_revision")
