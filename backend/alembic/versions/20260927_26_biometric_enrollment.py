"""Protected enrollment staging, revisioned lifecycle, and durable cleanup."""

import sqlalchemy as sa

from alembic import op

revision = "20260927_26"
down_revision = "20260927_25"
branch_labels = None
depends_on = None


def person_column(name="account_id", nullable=True):
    return sa.Column(name, sa.Uuid(), sa.ForeignKey("person_profile.account_id"), nullable=nullable)


def upgrade():
    op.create_table(
        "biometric_lock",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("capture_until", sa.DateTime(timezone=True)),
    )
    op.execute("INSERT INTO biometric_lock (id) VALUES (1)")
    op.create_table(
        "biometric_enrollment",
        sa.Column(
            "account_id", sa.Uuid(), sa.ForeignKey("person_profile.account_id"), primary_key=True
        ),
        sa.Column("subject", sa.String(80), nullable=False, unique=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "biometric_enrollment_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("identity_binding", sa.String(64), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        person_column(),
        sa.Column("expected_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("result_code", sa.String(60), nullable=False),
        sa.Column("subject", sa.String(80), unique=True),
        sa.Column("capture_command_id", sa.Uuid()),
        sa.Column("capture_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_index(
        "ix_biometric_enrollment_session_account_id", "biometric_enrollment_session", ["account_id"]
    )
    op.create_table(
        "biometric_cleanup_job",
        sa.Column("subject", sa.String(80), primary_key=True),
        person_column(),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("biometric_enrollment_session.id")),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("last_code", sa.String(60)),
    )
    op.create_index("ix_biometric_cleanup_job_account_id", "biometric_cleanup_job", ["account_id"])
    op.create_table(
        "biometric_command",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("operation", sa.String(40), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        person_column(),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("biometric_enrollment_session.id")),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_biometric_command_account_id", "biometric_command", ["account_id"])
    op.create_table(
        "biometric_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("operation", sa.String(40), nullable=False),
        sa.Column("outcome", sa.String(60), nullable=False),
        person_column(),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("biometric_enrollment_session.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_biometric_audit_account_id", "biometric_audit", ["account_id"])


def downgrade():
    for name in (
        "biometric_audit",
        "biometric_command",
        "biometric_cleanup_job",
        "biometric_enrollment_session",
        "biometric_enrollment",
        "biometric_lock",
    ):
        op.drop_table(name)
