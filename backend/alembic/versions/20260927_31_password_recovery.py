"""Persist an account-wide cooldown for password recovery email requests."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_31"
down_revision = "20260927_30"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "account", sa.Column("password_recovery_requested_at", sa.DateTime(timezone=True))
    )


def downgrade():
    op.drop_column("account", "password_recovery_requested_at")
