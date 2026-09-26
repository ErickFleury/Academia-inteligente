"""add bounded social profile and post interaction persistence

Revision ID: 20260926_17
Revises: 20260925_16
Create Date: 2026-09-26
"""

import sqlalchemy as sa
from alembic import op

revision = "20260926_17"
down_revision = "20260925_16"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("social_profile", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("client_id", sa.Uuid(), nullable=False), sa.Column("nickname", sa.String(40)), sa.Column("biography", sa.String(160)), sa.Column("visible_to_clients", sa.Boolean(), nullable=False, server_default=sa.text("true")), sa.Column("biography_moderation_status", sa.String(16), nullable=False, server_default="visible"), sa.Column("biography_moderation_reason", sa.String(500)), sa.Column("biography_deleted_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.ForeignKeyConstraint(["client_id"], ["client.id"]), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("client_id"))
    op.create_table("profile_image", sa.Column("client_id", sa.Uuid(), nullable=False), sa.Column("content", sa.LargeBinary()), sa.Column("media_type", sa.String(32), nullable=False), sa.Column("width", sa.Integer(), nullable=False), sa.Column("height", sa.Integer(), nullable=False), sa.Column("moderation_status", sa.String(16), nullable=False, server_default="visible"), sa.Column("moderation_reason", sa.String(500)), sa.Column("deleted_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.ForeignKeyConstraint(["client_id"], ["client.id"]), sa.PrimaryKeyConstraint("client_id"))
    op.create_table("client_follow", sa.Column("follower_client_id", sa.Uuid(), nullable=False), sa.Column("followed_client_id", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.CheckConstraint("follower_client_id <> followed_client_id", name="ck_client_follow_not_self"), sa.ForeignKeyConstraint(["followed_client_id"], ["client.id"]), sa.ForeignKeyConstraint(["follower_client_id"], ["client.id"]), sa.PrimaryKeyConstraint("follower_client_id", "followed_client_id"))
    op.create_index("ix_client_follow_followed", "client_follow", ["followed_client_id"])
    op.create_table("post_like", sa.Column("client_id", sa.Uuid(), nullable=False), sa.Column("progress_update_id", sa.Uuid(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.ForeignKeyConstraint(["client_id"], ["client.id"]), sa.ForeignKeyConstraint(["progress_update_id"], ["progress_update.id"]), sa.PrimaryKeyConstraint("client_id", "progress_update_id"))
    op.create_index("ix_post_like_update", "post_like", ["progress_update_id"])
    op.create_table("post_comment", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("progress_update_id", sa.Uuid(), nullable=False), sa.Column("client_id", sa.Uuid(), nullable=False), sa.Column("content", sa.Text()), sa.Column("moderation_status", sa.String(16), nullable=False, server_default="visible"), sa.Column("moderation_reason", sa.String(500)), sa.Column("deleted_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.ForeignKeyConstraint(["client_id"], ["client.id"]), sa.ForeignKeyConstraint(["progress_update_id"], ["progress_update.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_post_comment_update", "post_comment", ["progress_update_id"])
    op.create_index("ix_post_comment_client", "post_comment", ["client_id"])
    op.create_table("social_moderation_audit", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("actor_account_id", sa.Uuid(), nullable=False), sa.Column("target_id", sa.Uuid(), nullable=False), sa.Column("target_type", sa.String(32), nullable=False), sa.Column("action", sa.String(16), nullable=False), sa.Column("reason", sa.String(500)), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.ForeignKeyConstraint(["actor_account_id"], ["account.id"]), sa.PrimaryKeyConstraint("id"))

def downgrade() -> None:
    op.drop_table("social_moderation_audit"); op.drop_index("ix_post_comment_client", table_name="post_comment"); op.drop_index("ix_post_comment_update", table_name="post_comment"); op.drop_table("post_comment"); op.drop_index("ix_post_like_update", table_name="post_like"); op.drop_table("post_like"); op.drop_index("ix_client_follow_followed", table_name="client_follow"); op.drop_table("client_follow"); op.drop_table("profile_image"); op.drop_table("social_profile")
