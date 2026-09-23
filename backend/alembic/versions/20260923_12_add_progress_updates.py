"""Add controlled client progress updates.

Revision ID: 20260923_12
Revises: 20260923_11
"""

import sqlalchemy as sa

from alembic import op

revision = "20260923_12"
down_revision = "20260923_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "progress_update",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=16), server_default="private", nullable=False),
        sa.Column(
            "moderation_status", sa.String(length=16), server_default="visible", nullable=False
        ),
        sa.Column("moderation_reason", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_progress_update_client_created", "progress_update", ["client_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_progress_update_client_created", table_name="progress_update")
    op.drop_table("progress_update")
