"""Enforce one current training plan for each client.

Revision ID: 20260922_07
Revises: 20260922_06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260922_07"
down_revision: str | None = "20260922_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "training_plan",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    # Existing conflicting data cannot be reconciled by silently selecting one
    # plan; it must be resolved before this client-wide invariant is enforced.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT training_plan.client_id
            FROM training_plan
            JOIN training_plan_version ON training_plan_version.plan_id = training_plan.id
            WHERE training_plan_version.status = 'current'
            GROUP BY training_plan.client_id
            HAVING COUNT(*) > 1
          ) THEN
            RAISE EXCEPTION 'More than one current training plan exists for a client';
          END IF;
        END $$;
        """
    )
    op.execute(
        """
        UPDATE training_plan
        SET is_current = true
        FROM training_plan_version
        WHERE training_plan_version.plan_id = training_plan.id
          AND training_plan_version.status = 'current'
        """
    )
    op.create_index(
        "uq_client_current_training_plan",
        "training_plan",
        ["client_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )


def downgrade() -> None:
    op.drop_index("uq_client_current_training_plan", table_name="training_plan")
    op.drop_column("training_plan", "is_current")
