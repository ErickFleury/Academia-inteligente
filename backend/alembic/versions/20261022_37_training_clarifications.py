"""Retain structured clarification alongside its client-owned chat reply."""

import sqlalchemy as sa

from alembic import op

revision = "20261022_37"
down_revision = "20261022_36"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("training_ai_message", sa.Column("clarification", sa.JSON()))


def downgrade():
    op.drop_column("training_ai_message", "clarification")
