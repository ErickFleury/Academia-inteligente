"""add canonical equipment model references to adaptation operations

Revision ID: 20260925_16
Revises: 20260925_15
Create Date: 2026-09-25
"""

import sqlalchemy as sa

from alembic import op

revision = "20260925_16"
down_revision = "20260925_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "training_adaptation_operation",
        sa.Column("equipment_model_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_training_adaptation_operation_equipment_model",
        "training_adaptation_operation",
        "equipment_model",
        ["equipment_model_id"],
        ["id"],
    )
    op.create_index(
        "ix_training_adaptation_operation_equipment_model_id",
        "training_adaptation_operation",
        ["equipment_model_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_training_adaptation_operation_equipment_model_id",
        table_name="training_adaptation_operation",
    )
    op.drop_constraint(
        "fk_training_adaptation_operation_equipment_model",
        "training_adaptation_operation",
        type_="foreignkey",
    )
    op.drop_column("training_adaptation_operation", "equipment_model_id")
