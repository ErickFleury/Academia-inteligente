"""Administrator-only equipment details and normalized catalog photos."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_30"
down_revision = "20260927_29"
branch_labels = None
depends_on = None


def upgrade():
    for name, length in (("brand", 100), ("manufacturer_model", 100), ("category", 80)):
        op.add_column("equipment_model", sa.Column(name, sa.String(length)))
    for name in ("location", "serial_number"):
        op.add_column("equipment_unit", sa.Column(name, sa.String(120)))
    op.create_table(
        "equipment_image",
        sa.Column(
            "equipment_model_id", sa.Uuid(), sa.ForeignKey("equipment_model.id"), primary_key=True
        ),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("equipment_image")
    for name in ("location", "serial_number"):
        op.drop_column("equipment_unit", name)
    for name in ("brand", "manufacturer_model", "category"):
        op.drop_column("equipment_model", name)
