"""Add retained training adaptation proposals.

Revision ID: 20260923_09
Revises: 20260922_08
"""

from alembic import op
import sqlalchemy as sa

revision = "20260923_09"
down_revision = "20260922_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "training_adaptation_proposal",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("base_version_id", sa.Uuid(), nullable=False),
        sa.Column("source_client_request_id", sa.Uuid(), nullable=False),
        sa.Column("client_request_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("client_reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("instructor_reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("instructor_id", sa.String(length=255)),
        sa.Column("resulting_version_id", sa.Uuid()),
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
        sa.ForeignKeyConstraint(["client_id"], ["client.id"]),
        sa.ForeignKeyConstraint(["base_version_id"], ["training_plan_version.id"]),
        sa.ForeignKeyConstraint(["resulting_version_id"], ["training_plan_version.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "client_id", "base_version_id", "client_request_id", name="uq_adaptation_request"
        ),
    )
    op.create_table(
        "training_adaptation_operation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(length=16), nullable=False),
        sa.Column("target_position", sa.Integer()),
        sa.Column("exercise_name", sa.String(length=200)),
        sa.Column("sets", sa.Integer()),
        sa.Column("repetitions", sa.String(length=100)),
        sa.Column("load_guidance", sa.String(length=500)),
        sa.Column("rest_seconds", sa.Integer()),
        sa.Column("equipment_requirement", sa.String(length=200)),
        sa.Column("is_existing_exercise", sa.Boolean()),
        sa.ForeignKeyConstraint(["proposal_id"], ["training_adaptation_proposal.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "position", name="uq_adaptation_operation_position"),
    )


def downgrade() -> None:
    op.drop_table("training_adaptation_operation")
    op.drop_table("training_adaptation_proposal")
