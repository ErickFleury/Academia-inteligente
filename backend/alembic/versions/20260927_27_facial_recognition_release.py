"""Owned recognition attempts, client state projection, and simulated release."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_27"
down_revision = "20260927_26"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "biometric_client_access_state",
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), primary_key=True),
        sa.Column("inside", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "biometric_recognition_attempt",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor", sa.String(255), nullable=False, index=True),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("checkpoint_id", sa.String(80), nullable=False),
        sa.Column("captures", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("result_code", sa.String(60), nullable=False),
        sa.Column("account_id", sa.Uuid(), sa.ForeignKey("person_profile.account_id"), index=True),
        sa.Column("client_id", sa.Uuid(), sa.ForeignKey("client.id"), index=True),
        sa.Column("enrollment_revision", sa.Integer()),
        sa.Column("state_revision", sa.Integer()),
        sa.Column("capture_command_id", sa.Uuid()),
        sa.Column("capture_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("captures >= 0 AND captures <= 2", name="ck_face_capture_budget"),
        sa.CheckConstraint("direction IN ('entry', 'exit')", name="ck_face_attempt_direction"),
    )
    op.create_table(
        "biometric_release_request",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Uuid(),
            sa.ForeignKey("biometric_recognition_attempt.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("subject_reference", sa.String(80), nullable=False),
        sa.Column("checkpoint_id", sa.String(80), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode = 'simulated'", name="ck_face_release_simulated"),
    )
    for table in ("biometric_command", "biometric_audit"):
        op.add_column(
            table,
            sa.Column(
                "attempt_id",
                sa.Uuid(),
                sa.ForeignKey("biometric_recognition_attempt.id", name=f"fk_{table}_attempt"),
            ),
        )


def downgrade():
    for table in ("biometric_audit", "biometric_command"):
        op.drop_column(table, "attempt_id")
    for table in (
        "biometric_release_request",
        "biometric_recognition_attempt",
        "biometric_client_access_state",
    ):
        op.drop_table(table)
