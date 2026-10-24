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


def test_complementary_technique_search_in_postgres(postgres_sessions):
    from test_knowledge import (
        test_complementary_search_preserves_technique_amid_programming_results,
    )

    provider = FakeEmbedding()
    test_complementary_search_preserves_technique_amid_programming_results(
        (postgres_sessions, KnowledgeService(provider), provider)
    )


def test_focused_technique_embedding_namespace_in_postgres(postgres_sessions):
    from test_knowledge import test_focused_technique_candidates_cannot_mix_embedding_spaces

    provider = FakeEmbedding()
    test_focused_technique_candidates_cannot_mix_embedding_spaces(
        (postgres_sessions, KnowledgeService(provider), provider)
    )


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


def test_duration_query_retrieves_measurements_not_repeated_population_headers(postgres_sessions):
    provider = FakeEmbedding()
    provider.fail = True  # Real PostgreSQL lexical behavior, without semantic luck.
    service = KnowledgeService(provider)
    # Import with embeddings first, then exercise lexical fallback.
    provider.fail = False
    body = (
        "# Jovens de 6 a 17 anos\n"
        + "".join(
            f"## Nota {i}\nJovens de 6 a 17 anos: atividade física para jovens de 6 a 17 anos.\n"
            for i in range(25)
        )
        + "## Duração\nPratique 60 minutos ou mais por dia."
    )
    version = upload(postgres_sessions, service, body=body)
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, version)
    provider.fail = True
    with postgres_sessions() as session:
        refs = service.search(session, "minutos atividade física por dia jovens 6 a 17 anos")
        assert any("60 minutos" in r["content"] for r in refs)


def test_cross_language_semantic_evidence_survives_portuguese_keyword_noise(postgres_sessions):
    from app.integrations.embeddings import EmbeddingConfig

    class BilingualEmbedding:
        config = EmbeddingConfig(dimensions=2)

        def embed(self, texts, *, purpose, timeout=None):
            if purpose == "query":
                return [[1.0, 0.0] for _ in texts]
            return [[0.5, 0.8660254] if "Lat Pulldown" in value else [0.0, 1.0] for value in texts]

    service = KnowledgeService(BilingualEmbedding())
    english = upload(
        postgres_sessions, service, body=("# Lat Pulldown\nLower the bar toward the upper chest.")
    )
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, english)
    noise = upload(
        postgres_sessions,
        service,
        body="\n".join(
            f"# Parte {i}\nCrianças brincam na parte superior da casa." for i in range(8)
        ),
    )
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, noise)
    with postgres_sessions() as session:
        hits = service.search(session, "puxada alta até parte superior do peito")
        assert hits[0]["version_id"] == str(english["id"])
        # Orthogonal embeddings without lexical overlap remain absent.
        assert all("Crianças" not in hit["content"] for hit in service.search(session, "clavícula"))


def test_equal_relevance_uses_document_order_instead_of_random_passage_ids(postgres_sessions):
    from uuid import UUID

    from sqlalchemy import select

    from app.modules.knowledge.models import ReferencePassage

    provider = FakeEmbedding()
    service = KnowledgeService(provider)
    version = upload(
        postgres_sessions,
        service,
        body="\n".join(f"# Ajustes\nBanco etiqueta {i}." for i in range(10)),
    )
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, version)
    with postgres_sessions() as session:
        for passage in session.scalars(select(ReferencePassage)):
            passage.id = UUID(int=100 - passage.position)
        session.commit()
        provider.fail = True
        hits = service.search(session, "banco")
        assert [hit["location"] for hit in hits] == [f"text;passage:{i}" for i in range(1, 6)]


def test_deletion_waits_for_citation_validation_and_invalidates_later_replies(postgres_sessions):
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from time import monotonic, sleep

    from app.modules.knowledge.service import KnowledgeError

    service = KnowledgeService(FakeEmbedding())
    item = upload(postgres_sessions, service)
    service.import_next(postgres_sessions)
    active = activate(postgres_sessions, service, item)
    worker_pid = Queue()

    def erase():
        with postgres_sessions() as session:
            worker_pid.put(session.scalar(text("select pg_backend_pid()")))
            service.delete_source(session, item["source_id"], active["revision"])

    with ThreadPoolExecutor(max_workers=1) as pool, postgres_sessions() as reader:
        refs = service.search(reader, "força")
        service.validate_citations(reader, refs)
        future = pool.submit(erase)
        try:
            pid = worker_pid.get(timeout=5)
            with postgres_sessions() as observer:
                deadline = monotonic() + 3
                while monotonic() < deadline:
                    waiting = observer.scalar(
                        text("select wait_event_type from pg_stat_activity where pid = :pid"),
                        {"pid": pid},
                    )
                    observer.rollback()
                    if waiting == "Lock":
                        break
                    sleep(0.02)
                else:
                    pytest.fail("deletion did not wait for citation validation")
        finally:
            reader.commit()
        future.result(timeout=5)
        with pytest.raises(KnowledgeError, match="reference_conflict"):
            service.validate_citations(reader, refs)
        assert service.search(reader, "força") == []


def test_deleted_import_cannot_publish_vectors_in_postgres(postgres_sessions):
    from sqlalchemy import select

    from app.modules.knowledge.models import ReferencePassage, ReferenceVersion

    provider = FakeEmbedding()
    service = KnowledgeService(provider)
    item = upload(postgres_sessions, service)
    embed = provider.embed

    def deleting_embed(*args, **kwargs):
        with postgres_sessions() as session:
            service.delete_source(session, item["source_id"], item["revision"])
        return embed(*args, **kwargs)

    provider.embed = deleting_embed
    assert service.import_next(postgres_sessions)
    with postgres_sessions() as session:
        assert session.scalars(select(ReferenceVersion)).all() == []
        assert session.scalars(select(ReferencePassage)).all() == []


def test_prescription_search_prioritizes_doses_over_repeated_definitions(postgres_sessions):
    provider = FakeEmbedding()
    service = KnowledgeService(provider)
    version = upload(
        postgres_sessions,
        service,
        body=(
            "\n".join(
                f"# Resistance training {i}\nPrescription terminology: sets repetitions rest. "
                "Sets are groups of repetitions. Rest separates sets."
                for i in range(12)
            )
            + "\n# Resistance training\nPrescription example for a synthetic test only: "
            "2 sets of 8 repetitions; rest 90 seconds between sets."
        ),
    )
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, version)
    with postgres_sessions() as session:
        hits = service.search(session, "resistance training prescription sets repetitions rest")
        assert any("8 repetitions" in hit["content"] for hit in hits[:3])
        definitions = service.search(session, "definition sets repetitions")
        assert "Sets are groups" in definitions[0]["content"]


def test_extra_doses_for_another_population_do_not_displace_requested_group(postgres_sessions):
    service = KnowledgeService(FakeEmbedding())
    version = upload(
        postgres_sessions,
        service,
        body=(
            "# Atividade física para idosos\nDuração frequência intensidade: 150 minutos, "
            "75 minutos, 30 minutos, 2 dias.\n"
            "# Atividade física para adultos\nDuração frequência intensidade: 150 minutos.\n"
            "# Atividade física para crianças\nDuração frequência intensidade: 60 minutos, "
            "30 minutos, 3 dias."
        ),
    )
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, version)
    with postgres_sessions() as session:
        hits = service.search(session, "adultos duração frequência intensidade")
        assert "para adultos" in hits[0]["content"]


def test_plan_search_keeps_an_activity_passage_alongside_dosage(postgres_sessions):
    service = KnowledgeService(FakeEmbedding())
    version = upload(
        postgres_sessions,
        service,
        body=(
            "\n".join(
                f"# Adultos {i}\nAtividade física duração frequência: 150 minutos por semana."
                for i in range(12)
            )
            + "\n# Adultos\nAtividade física: você pode caminhar, correr ou pedalar."
        ),
    )
    service.import_next(postgres_sessions)
    activate(postgres_sessions, service, version)
    with postgres_sessions() as session:
        hits = service.search(
            session, "adultos atividade física duração frequência", include_activity_options=True
        )
        assert any("caminhar" in hit["content"] for hit in hits[:3])
        assert any("150 minutos" in hit["content"] for hit in hits[:3])
