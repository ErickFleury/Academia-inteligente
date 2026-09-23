"""Enforce one active training proposal per client.

Revision ID: 20260923_11
Revises: 20260923_10
"""

import sqlalchemy as sa

from alembic import op

revision = "20260923_11"
down_revision = "20260923_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("training_plan_version", sa.Column("client_id", sa.Uuid(), nullable=True))
    op.execute(
        """
        UPDATE training_plan_version
        SET client_id = (
            SELECT client_id
            FROM training_plan
            WHERE training_plan.id = training_plan_version.plan_id
        )
        """
    )
    # Preserve all legacy content while retaining just the newest active draft.
    # Older duplicate drafts become immutable history before the unique index is added.
    op.execute(
        """
        UPDATE training_plan_version
        SET status = 'superseded'
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY client_id
                           ORDER BY created_at DESC, id DESC
                       ) AS position
                FROM training_plan_version
                WHERE status = 'proposal'
            ) AS duplicate_proposals
            WHERE position > 1
        )
        """
    )
    op.create_foreign_key(
        "fk_training_plan_version_client",
        "training_plan_version",
        "client",
        ["client_id"],
        ["id"],
    )
    op.alter_column("training_plan_version", "client_id", nullable=False)
    op.create_index(
        "uq_client_training_plan_proposal",
        "training_plan_version",
        ["client_id"],
        unique=True,
        postgresql_where=sa.text("status = 'proposal'"),
        sqlite_where=sa.text("status = 'proposal'"),
    )


def downgrade() -> None:
    op.drop_index("uq_client_training_plan_proposal", table_name="training_plan_version")
    op.drop_constraint(
        "fk_training_plan_version_client", "training_plan_version", type_="foreignkey"
    )
    op.drop_column("training_plan_version", "client_id")
