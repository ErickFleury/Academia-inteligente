"""Add structured client onboarding and non-sensitive audit evidence.

Revision ID: 20260921_04
Revises: 20260920_03
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_04"
down_revision: str | None = "20260920_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create separate structured onboarding and audit tables."""
    op.create_table(
        "onboarding",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("training_goal", sa.String(length=500), nullable=True),
        sa.Column("training_experience", sa.String(length=16), nullable=True),
        sa.Column("height_cm", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("has_limitations_or_complaints", sa.Boolean(), nullable=True),
        sa.Column("limitations_or_complaints", sa.Text(), nullable=True),
        sa.Column("uses_medications", sa.Boolean(), nullable=True),
        sa.Column("medications", sa.Text(), nullable=True),
        sa.Column("has_health_conditions", sa.Boolean(), nullable=True),
        sa.Column("health_conditions", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_table(
        "onboarding_audit_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("onboarding_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("actor_account_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("changed_fields", sa.String(length=1000), nullable=True),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["actor_account_id"], ["account.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.ForeignKeyConstraint(["onboarding_id"], ["onboarding.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Remove onboarding data in reverse dependency order."""
    op.drop_table("onboarding_audit_event")
    op.drop_table("onboarding")
