"""Add short-retention client-owned conversational onboarding state.

Revision ID: 20260921_05
Revises: 20260921_04
Create Date: 2026-09-21
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260921_05"
down_revision: str | None = "20260921_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Persist client conversations and expiring raw messages."""
    op.create_table(
        "onboarding_ai_conversation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id"),
    )
    op.create_table(
        "onboarding_ai_message",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("client_request_id", sa.Uuid(), nullable=True),
        sa.Column("reply_to_client_request_id", sa.Uuid(), nullable=True),
        sa.Column("missing_required_fields", sa.Text(), nullable=True),
        sa.Column("completion_ready", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["onboarding_ai_conversation.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id", "sequence", name="uq_onboarding_ai_message_sequence"
        ),
        sa.UniqueConstraint(
            "conversation_id", "client_request_id", name="uq_onboarding_ai_message_request"
        ),
        sa.UniqueConstraint(
            "conversation_id",
            "reply_to_client_request_id",
            name="uq_onboarding_ai_message_reply",
        ),
    )
    op.create_index(
        "ix_onboarding_ai_conversation_raw_expires_at",
        "onboarding_ai_conversation",
        ["raw_expires_at"],
    )


def downgrade() -> None:
    """Remove raw conversational onboarding state."""
    op.drop_index(
        "ix_onboarding_ai_conversation_raw_expires_at",
        table_name="onboarding_ai_conversation",
    )
    op.drop_table("onboarding_ai_message")
    op.drop_table("onboarding_ai_conversation")
