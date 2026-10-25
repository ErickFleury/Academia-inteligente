"""Persist exact-revision prescription validation and scoped input confirmations.

No policies, approvals or historical qualification are fabricated by migration.
Internal table names preserve the already tested isolated service mapping.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261023_35"
down_revision = "20261017_34"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "training_prescription_adaptation_validation",
        sa.Column(
            "proposal_id",
            sa.Uuid(),
            sa.ForeignKey("training_adaptation_proposal.id"),
            primary_key=True,
        ),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("base_content_sha256", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_training_prescription_adaptation_validation_client_id",
        "training_prescription_adaptation_validation",
        ["client_id"],
    )
    op.create_table(
        "training_prescription_development_validation",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "version_id", sa.Uuid(), sa.ForeignKey("training_plan_version.id"), nullable=False
        ),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("entry_point", sa.String(32), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_training_prescription_development_validation_client_id",
        "training_prescription_development_validation",
        ["client_id"],
    )
    op.create_index(
        "ix_training_prescription_development_validation_request_id",
        "training_prescription_development_validation",
        ["request_id"],
    )
    op.create_table(
        "training_prescription_development_confirmation",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), nullable=False),
        sa.Column("origin_sha256", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_training_prescription_development_confirmation_client_id",
        "training_prescription_development_confirmation",
        ["client_id"],
    )
    op.create_index(
        "ix_training_prescription_development_confirmation_origin_sha256",
        "training_prescription_development_confirmation",
        ["origin_sha256"],
    )


def downgrade():
    op.drop_table("training_prescription_adaptation_validation")
    op.drop_table("training_prescription_development_confirmation")
    op.drop_table("training_prescription_development_validation")
