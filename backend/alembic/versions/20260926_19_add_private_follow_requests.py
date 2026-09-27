"""add private-account follow requests

Revision ID: 20260926_19
Revises: 20260926_18
Create Date: 2026-09-26
"""

import sqlalchemy as sa

from alembic import op

revision = "20260926_19"
down_revision = "20260926_18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_follow_request",
        sa.Column("requester_client_id", sa.Uuid(), nullable=False),
        sa.Column("requested_client_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "requester_client_id <> requested_client_id", name="ck_client_follow_request_not_self"
        ),
        sa.ForeignKeyConstraint(["requester_client_id"], ["client.id"]),
        sa.ForeignKeyConstraint(["requested_client_id"], ["client.id"]),
        sa.PrimaryKeyConstraint("requester_client_id", "requested_client_id"),
    )
    op.create_index(
        "ix_client_follow_request_requested",
        "client_follow_request",
        ["requested_client_id", "created_at"],
    )
    op.execute(
        "UPDATE progress_update AS post SET visibility = CASE WHEN profile.visible_to_clients "
        "THEN 'shared' ELSE 'private' END FROM social_profile AS profile "
        "WHERE profile.client_id = post.client_id AND post.deleted_at IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_client_follow_request_requested", table_name="client_follow_request")
    op.drop_table("client_follow_request")
