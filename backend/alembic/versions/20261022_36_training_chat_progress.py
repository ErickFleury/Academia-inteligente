"""Persist bounded processing ownership with retained training-chat messages."""

import sqlalchemy as sa

from alembic import op

revision = "20261022_36"
down_revision = "20261019_35"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("training_ai_message", sa.Column("processing_token", sa.Uuid()))
    op.add_column(
        "training_ai_message", sa.Column("processing_expires_at", sa.DateTime(timezone=True))
    )
    op.add_column("training_ai_message", sa.Column("failure_code", sa.String(64)))


def downgrade():
    for column in ("failure_code", "processing_expires_at", "processing_token"):
        op.drop_column("training_ai_message", column)
