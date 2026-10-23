"""Keep compact validated personal answers after chat transcripts expire."""

import sqlalchemy as sa

from alembic import op

revision = "20261023_38"
down_revision = "20261022_37"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("client_memory_fact", sa.Column("answer_data", sa.JSON()))


def downgrade():
    op.drop_column("client_memory_fact", "answer_data")
