"""add opt-in profile presence preference

Revision ID: 20260925_15
Revises: 20260925_14
Create Date: 2026-09-25
"""

import sqlalchemy as sa

from alembic import op

revision = "20260925_15"
down_revision = "20260925_14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profile_presence_preference",
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("client_id"),
    )
    op.create_table(
        "profile_presence_consent_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("previous_enabled", sa.Boolean(), nullable=False),
        sa.Column("new_enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_profile_presence_consent_audit_client_id",
        "profile_presence_consent_audit",
        ["client_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_profile_presence_consent_audit_client_id", table_name="profile_presence_consent_audit")
    op.drop_table("profile_presence_consent_audit")
    op.drop_table("profile_presence_preference")
