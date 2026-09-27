"""Add instructor employee identities.

Revision ID: 20260927_21
Revises: 20260926_20
"""

import sqlalchemy as sa

from alembic import op

revision = "20260927_21"
down_revision = "20260926_20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column(
            "specialization", sa.String(length=32), server_default="instructor", nullable=False
        ),
        sa.Column("cnpj", sa.String(length=14), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id"),
    )
    op.create_table(
        "employee_identity_reconciliation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("keycloak_subject", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("keycloak_subject"),
    )


def downgrade() -> None:
    op.drop_table("employee_identity_reconciliation")
    op.drop_table("employee")
