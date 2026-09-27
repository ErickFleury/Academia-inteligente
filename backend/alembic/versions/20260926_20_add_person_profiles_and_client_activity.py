"""Add authoritative person profiles and client-specific activity.

Revision ID: 20260926_20
Revises: 20260926_19
Create Date: 2026-09-26
"""

import sqlalchemy as sa

from alembic import op

revision = "20260926_20"
down_revision = "20260926_19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person_profile",
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("surname", sa.String(length=200), nullable=False),
        sa.Column("cpf", sa.String(length=11), nullable=False),
        sa.Column("phone", sa.String(length=11), nullable=False),
        sa.Column("postal_code", sa.String(length=8), nullable=False),
        sa.Column("street", sa.String(length=200), nullable=False),
        sa.Column("number", sa.String(length=40), nullable=False),
        sa.Column("complement", sa.String(length=200), nullable=True),
        sa.Column("neighborhood", sa.String(length=150), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
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
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.PrimaryKeyConstraint("account_id"),
        sa.UniqueConstraint("cpf"),
    )
    op.create_index("ix_person_profile_cpf", "person_profile", ["cpf"], unique=False)
    op.add_column(
        "client",
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.alter_column("client", "active", server_default=None)


def downgrade() -> None:
    op.drop_column("client", "active")
    op.drop_index("ix_person_profile_cpf", table_name="person_profile")
    op.drop_table("person_profile")
