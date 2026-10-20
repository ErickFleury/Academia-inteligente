"""Real vector/full-text queries and migration verification in disposable schemas."""

import os
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from test_knowledge import FakeEmbedding, activate, upload

from alembic import command
from app.database import Base
from app.modules.knowledge.service import KnowledgeService

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


@pytest.fixture
def postgres_sessions():
    schema = "test_knowledge_" + uuid4().hex
    admin = create_engine(os.environ["DATABASE_URL"])
    with admin.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"options": f"-csearch_path={schema} -clock_timeout=5000"},
    )
    try:
        Base.metadata.create_all(engine)
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_vector_and_lexical_queries_use_real_postgres(postgres_sessions):
    provider = FakeEmbedding()
    service = KnowledgeService(provider)
    version = upload(postgres_sessions, service)
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, version)
    with postgres_sessions() as session:
        assert service.search(session, "força")[0]["version_id"] == str(version["id"])
        provider.fail = True
        assert service.search(session, "iniciantes")[0]["version_id"] == str(version["id"])
        assert service.search(session, "Como começar exercícios de força?")[0]["version_id"] == str(
            version["id"]
        )
        assert service.search(session, "orientacao forca")[0]["version_id"] == str(version["id"])
        assert service.search(session, "sem correspondência") == []


def test_portuguese_lexemes_are_not_stemmed_twice(postgres_sessions):
    provider = FakeEmbedding()
    service = KnowledgeService(provider)
    version = upload(postgres_sessions, service, body="Série é um grupo de repetições na ficha.")
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, version)
    provider.fail = True
    with postgres_sessions() as session:
        assert service.search(session, "Qual a diferença entre serie e repeticao?")[0][
            "version_id"
        ] == str(version["id"])


def test_migration_upgrade_and_downgrade_preserve_base_database(monkeypatch):
    original_url = os.environ["DATABASE_URL"]
    schema = "test_migration_" + uuid4().hex
    admin = create_engine(original_url)
    with admin.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        # Keep public available for the vector type, but mask its Alembic marker.
        # Otherwise a migrated base database makes this isolated upgrade a no-op.
        connection.execute(
            text(
                f'CREATE TABLE "{schema}".alembic_version '
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
    url = make_url(original_url).update_query_dict({"options": f"-csearch_path={schema},public"})
    monkeypatch.setenv("DATABASE_URL", url.render_as_string(hide_password=False))
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "head")
        with admin.connect() as connection:
            columns = (
                connection.execute(
                    text(
                        "SELECT udt_name FROM information_schema.columns "
                        "WHERE table_schema=:schema AND table_name='ai_reference_passage' "
                        "AND column_name='embedding'"
                    ),
                    {"schema": schema},
                )
                .scalars()
                .all()
            )
            assert columns == ["vector"]
            assert connection.scalar(text("SHOW server_version")).startswith("18.6")
        command.downgrade(config, "20260927_31")
        with admin.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT to_regclass(:table)"), {"table": f"{schema}.ai_reference_passage"}
                )
                is None
            )
    finally:
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_requested_section_outranks_other_populations(postgres_sessions):
    provider = FakeEmbedding()
    service = KnowledgeService(provider)
    # Identical vocabulary makes the heading the deciding evidence of applicability.
    body = (
        "# Gestantes\nMinutos moderada vigorosa semana. Consulte orientação específica.\n"
        "# Adultos\nMinutos moderada vigorosa semana. Orientação para a população solicitada.\n"
        "# Idosos\nMinutos moderada vigorosa semana. Consulte orientação específica."
    )
    version = upload(postgres_sessions, service, body=body)
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, version)
    with postgres_sessions() as session:
        refs = service.search(session, "minutos moderada vigorosa adultos semana")
        assert refs[0]["content"].startswith("Seção: Adultos\n")
        assert "Gestantes" not in refs[0]["content"]
