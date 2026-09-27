"""Stable professional attribution and equipment references on the sole draft."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_22"
down_revision = "20260927_21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    # Never silently discard or choose among legacy review authorities.
    pending = connection.scalar(
        sa.text(
            "SELECT count(*) FROM training_adaptation_proposal "
            "WHERE status = 'pending_instructor_review'"
        )
    )
    approved = connection.scalar(
        sa.text("SELECT count(*) FROM training_plan_version WHERE status = 'approved'")
    )
    if pending or approved:
        raise RuntimeError(
            "Resolve legacy pending adaptations/approved-only versions before upgrading "
            "training review; no records were deleted"
        )
    op.add_column(
        "training_plan_version", sa.Column("responsible_employee_id", sa.Uuid(), nullable=True)
    )
    op.add_column(
        "training_plan_version", sa.Column("responsible_name", sa.String(301), nullable=True)
    )
    op.create_foreign_key(
        "fk_training_responsible_employee",
        "training_plan_version",
        "employee",
        ["responsible_employee_id"],
        ["id"],
    )
    # Legacy attribution is left intact. Do not invent a historical name from a
    # mutable present-day profile; new approvals always set both fields.
    op.add_column(
        "training_plan_item", sa.Column("equipment_requirement", sa.String(200), nullable=True)
    )
    op.add_column("training_plan_item", sa.Column("equipment_model_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_training_item_equipment",
        "training_plan_item",
        "equipment_model",
        ["equipment_model_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_training_item_equipment", "training_plan_item", type_="foreignkey")
    op.drop_column("training_plan_item", "equipment_model_id")
    op.drop_column("training_plan_item", "equipment_requirement")
    op.drop_constraint(
        "fk_training_responsible_employee", "training_plan_version", type_="foreignkey"
    )
    op.drop_column("training_plan_version", "responsible_name")
    op.drop_column("training_plan_version", "responsible_employee_id")
