"""Permit audited moderation by the OIDC-only bootstrap administrator."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_29"
down_revision = "20260927_28"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("social_moderation_audit", sa.Column("actor_subject", sa.String(255)))
    op.alter_column("social_moderation_audit", "actor_account_id", nullable=True)
    op.create_check_constraint(
        "ck_social_moderation_actor",
        "social_moderation_audit",
        "actor_account_id IS NOT NULL OR actor_subject IS NOT NULL",
    )


def downgrade():
    # Never discard audit records or invent local accounts to satisfy the old schema.
    if op.get_bind().scalar(
        sa.text("SELECT count(*) FROM social_moderation_audit WHERE actor_account_id IS NULL")
    ):
        raise RuntimeError("Cannot downgrade while OIDC-only moderation audit records exist")
    op.drop_constraint("ck_social_moderation_actor", "social_moderation_audit", type_="check")
    op.alter_column("social_moderation_audit", "actor_account_id", nullable=False)
    op.drop_column("social_moderation_audit", "actor_subject")
