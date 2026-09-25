"""add anonymous occupancy ledger

Revision ID: 20260925_14
Revises: 20260925_13
Create Date: 2026-09-25
"""

import sqlalchemy as sa

from alembic import op

revision = "20260925_14"
down_revision = "20260925_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_access_reference",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("reference_digest", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
        sa.UniqueConstraint("reference_digest"),
    )
    op.create_table(
        "access_passage_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("client_reference_digest", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("checkpoint_id", sa.String(length=200), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column(
            "event_type", sa.String(length=32), server_default="passage_confirmed", nullable=False
        ),
        sa.Column("inconsistency", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_access_passage_event_client_id", "access_passage_event", ["client_id"])
    op.create_table(
        "occupancy_correction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_subject", sa.String(length=255), nullable=False),
        sa.Column("adjustment", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "access_source_heartbeat",
        sa.Column("checkpoint_id", sa.String(length=200), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("checkpoint_id"),
    )


def downgrade() -> None:
    op.drop_table("access_source_heartbeat")
    op.drop_table("occupancy_correction")
    op.drop_index("ix_access_passage_event_client_id", table_name="access_passage_event")
    op.drop_table("access_passage_event")
    op.drop_table("client_access_reference")
