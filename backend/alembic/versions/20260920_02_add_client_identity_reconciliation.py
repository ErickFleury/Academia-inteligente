"""Add durable client identity reconciliation state.

Revision ID: 20260920_02
Revises: 20260920_01
Create Date: 2026-09-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260920_02"
down_revision: str | None = "20260920_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Track incomplete Keycloak/local client identity operations."""
    op.create_table(
        "client_identity_reconciliation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=True),
        sa.Column("keycloak_subject", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("keycloak_subject"),
    )


def downgrade() -> None:
    """Remove reconciliation state."""
    op.drop_table("client_identity_reconciliation")
