"""Preserve typed dose details and explicitly inapplicable quantities."""

import sqlalchemy as sa

from alembic import op

revision = "20261024_37"
down_revision = "20261024_36"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("training_plan_item", "training_adaptation_operation"):
        op.add_column(table, sa.Column("dose_details", sa.JSON(), nullable=True))
    with op.batch_alter_table("training_plan_item") as batch:
        batch.alter_column("sets", existing_type=sa.Integer(), nullable=True)
        batch.alter_column("rest_seconds", existing_type=sa.Integer(), nullable=True)


def downgrade():
    connection = op.get_bind()
    if connection.scalar(
        sa.text(
            "SELECT COUNT(*) FROM training_plan_item WHERE sets IS NULL OR rest_seconds IS NULL"
        )
    ):
        raise RuntimeError("Cannot discard inapplicable modality quantities")
    for table in ("training_plan_item", "training_adaptation_operation"):
        if connection.scalar(
            sa.text(f"SELECT COUNT(*) FROM {table} WHERE dose_details IS NOT NULL")
        ):
            raise RuntimeError("Cannot discard existing modality records")
    with op.batch_alter_table("training_plan_item") as batch:
        batch.alter_column("sets", existing_type=sa.Integer(), nullable=False)
        batch.alter_column("rest_seconds", existing_type=sa.Integer(), nullable=False)
    for table in ("training_plan_item", "training_adaptation_operation"):
        op.drop_column(table, "dose_details")
