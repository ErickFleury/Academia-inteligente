"""Add client-owned, expiring training assistant conversations.

Revision ID: 20260922_08
Revises: 20260922_07
"""

import sqlalchemy as sa

from alembic import op

revision = "20260922_08"
down_revision = "20260922_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_ai_conversation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("client_id"),
    )
    op.create_index(
        "ix_training_ai_conversation_raw_expires_at",
        "training_ai_conversation",
        ["raw_expires_at"],
    )
    op.create_table(
        "training_ai_message",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("client_request_id", sa.Uuid(), nullable=True),
        sa.Column("reply_to_client_request_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["training_ai_conversation.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_training_ai_message_sequence"),
        sa.UniqueConstraint(
            "conversation_id", "client_request_id", name="uq_training_ai_message_request"
        ),
        sa.UniqueConstraint(
            "conversation_id", "reply_to_client_request_id", name="uq_training_ai_message_reply"
        ),
    )


def downgrade() -> None:
    op.drop_table("training_ai_message")
    op.drop_index(
        "ix_training_ai_conversation_raw_expires_at", table_name="training_ai_conversation"
    )
    op.drop_table("training_ai_conversation")
