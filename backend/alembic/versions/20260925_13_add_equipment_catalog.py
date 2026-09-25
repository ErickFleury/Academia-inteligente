"""add equipment catalog

Revision ID: 20260925_13
Revises: 20260923_12
Create Date: 2026-09-25
"""

import sqlalchemy as sa

from alembic import op

revision = "20260925_13"
down_revision = "20260923_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equipment_model",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "equipment_unit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("equipment_model_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["equipment_model_id"], ["equipment_model.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equipment_unit_equipment_model_id", "equipment_unit", ["equipment_model_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_equipment_unit_equipment_model_id", table_name="equipment_unit")
    op.drop_table("equipment_unit")
    op.drop_table("equipment_model")
