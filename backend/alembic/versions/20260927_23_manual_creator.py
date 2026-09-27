"""Retain the local Employee identity for manual draft authorship."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_23"
down_revision = "20260927_22"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "training_plan_version", sa.Column("created_employee_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_training_creator_employee",
        "training_plan_version",
        "employee",
        ["created_employee_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_training_creator_employee", "training_plan_version", type_="foreignkey")
    op.drop_column("training_plan_version", "created_employee_id")
