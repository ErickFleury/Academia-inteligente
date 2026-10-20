"""Match accented and unaccented Portuguese reference terms with the same GIN index."""

from alembic import op

revision = "20261019_35"
down_revision = "20261019_34"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_ai_reference_text", table_name="ai_reference_passage")
    op.execute(
        "CREATE INDEX ix_ai_reference_text ON ai_reference_passage USING gin("
        "to_tsvector('portuguese'::regconfig, translate(lower(content), "
        "'áàâãäéèêëíìîïóòôõöúùûüçñ', 'aaaaaeeeeiiiiooooouuuucn')))"
    )


def downgrade():
    op.drop_index("ix_ai_reference_text", table_name="ai_reference_passage")
    op.execute(
        "CREATE INDEX ix_ai_reference_text ON ai_reference_passage "
        "USING gin(to_tsvector('portuguese'::regconfig, content))"
    )
