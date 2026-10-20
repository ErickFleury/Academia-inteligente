"""Supporting-reference identities retained with their owning reply/proposal."""

import sqlalchemy as sa

from alembic import op

revision = "20261019_34"
down_revision = "20261019_33"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("training_ai_message", "training_plan_version", "training_adaptation_proposal"):
        op.add_column(table, sa.Column("reference_citations", sa.JSON()))


def downgrade():
    for table in ("training_ai_message", "training_plan_version", "training_adaptation_proposal"):
        op.drop_column(table, "reference_citations")
