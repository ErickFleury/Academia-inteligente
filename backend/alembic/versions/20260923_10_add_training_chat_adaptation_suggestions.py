"""Persist non-binding training-chat adaptation suggestions.

Revision ID: 20260923_10
Revises: 20260923_09
"""

import sqlalchemy as sa

from alembic import op

revision = "20260923_10"
down_revision = "20260923_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "training_ai_message",
        sa.Column(
            "adaptation_suggested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("training_ai_message", sa.Column("adaptation_reason", sa.Text()))


def downgrade() -> None:
    op.drop_column("training_ai_message", "adaptation_reason")
    op.drop_column("training_ai_message", "adaptation_suggested")
