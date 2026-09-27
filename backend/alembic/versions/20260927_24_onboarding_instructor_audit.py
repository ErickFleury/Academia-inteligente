"""Attribute instructor onboarding access without retaining sensitive values."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_24"
down_revision = "20260927_23"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "onboarding_audit_event", sa.Column("actor_employee_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_onboarding_actor_employee",
        "onboarding_audit_event",
        "employee",
        ["actor_employee_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_onboarding_actor_employee", "onboarding_audit_event", type_="foreignkey")
    op.drop_column("onboarding_audit_event", "actor_employee_id")
