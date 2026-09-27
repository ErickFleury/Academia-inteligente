"""add social feed media, edit state, and cursor indexes

Revision ID: 20260926_18
Revises: 20260926_17
Create Date: 2026-09-26
"""

import sqlalchemy as sa

from alembic import op

revision = "20260926_18"
down_revision = "20260926_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("progress_update", sa.Column("edited_at", sa.DateTime(timezone=True)))
    op.add_column("post_comment", sa.Column("edited_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_progress_update_feed_cursor",
        "progress_update",
        ["visibility", "moderation_status", "deleted_at", "created_at", "id"],
    )
    op.create_index(
        "ix_post_comment_cursor",
        "post_comment",
        ["progress_update_id", "deleted_at", "moderation_status", "created_at", "id"],
    )
    op.create_table(
        "post_image",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("progress_update_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("position >= 0 AND position < 4", name="ck_post_image_position"),
        sa.ForeignKeyConstraint(["progress_update_id"], ["progress_update.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("progress_update_id", "position", name="uq_post_image_position"),
    )
    op.create_index("ix_post_image_update", "post_image", ["progress_update_id"])
    op.create_table(
        "comment_image",
        sa.Column("comment_id", sa.Uuid(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["comment_id"], ["post_comment.id"]),
        sa.PrimaryKeyConstraint("comment_id"),
    )


def downgrade() -> None:
    op.drop_table("comment_image")
    op.drop_index("ix_post_image_update", table_name="post_image")
    op.drop_table("post_image")
    op.drop_index("ix_post_comment_cursor", table_name="post_comment")
    op.drop_index("ix_progress_update_feed_cursor", table_name="progress_update")
    op.drop_column("post_comment", "edited_at")
    op.drop_column("progress_update", "edited_at")
