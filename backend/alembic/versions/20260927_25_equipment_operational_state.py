"""Independent equipment operational state; inventory quantity is unchanged."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_25"
down_revision = "20260927_24"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "equipment_unit",
        sa.Column("operational_state", sa.String(20), nullable=False, server_default="operational"),
    )
    op.add_column(
        "equipment_unit",
        sa.Column("operational_revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_check_constraint(
        "ck_equipment_operational_state",
        "equipment_unit",
        "operational_state IN ('operational', 'out_of_order')",
    )


def downgrade():
    op.drop_constraint("ck_equipment_operational_state", "equipment_unit", type_="check")
    op.drop_column("equipment_unit", "operational_revision")
    op.drop_column("equipment_unit", "operational_state")
