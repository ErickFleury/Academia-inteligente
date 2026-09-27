"""Internal simulated provenance and person-specific occupancy corrections."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_28"
down_revision = "20260927_27"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "access_passage_event",
        sa.Column("source_kind", sa.String(20), nullable=False, server_default="external"),
    )
    op.add_column("access_passage_event", sa.Column("state_revision", sa.Integer()))
    op.add_column(
        "occupancy_correction",
        sa.Column(
            "client_id",
            sa.Uuid(),
            sa.ForeignKey("client.id", name="fk_occupancy_correction_client"),
        ),
    )
    op.create_index("ix_occupancy_correction_client_id", "occupancy_correction", ["client_id"])
    op.add_column("occupancy_correction", sa.Column("command_id", sa.Uuid()))
    op.create_unique_constraint(
        "uq_occupancy_correction_command_id", "occupancy_correction", ["command_id"]
    )
    op.add_column("occupancy_correction", sa.Column("previous_inside", sa.Boolean()))
    op.add_column("occupancy_correction", sa.Column("target_inside", sa.Boolean()))
    op.add_column("occupancy_correction", sa.Column("state_revision", sa.Integer()))
    op.add_column(
        "occupancy_correction",
        sa.Column("source_kind", sa.String(20), nullable=False, server_default="manual"),
    )


def downgrade():
    for column in (
        "source_kind",
        "state_revision",
        "target_inside",
        "previous_inside",
        "command_id",
        "client_id",
    ):
        op.drop_column("occupancy_correction", column)
    op.drop_column("access_passage_event", "state_revision")
    op.drop_column("access_passage_event", "source_kind")
