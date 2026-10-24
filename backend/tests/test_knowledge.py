from io import BytesIO

import pytest
from pypdf import PdfWriter
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from test_equipment import request

from app.database import Base, get_database_session
from app.integrations.ai import AiProviderError
from app.integrations.document_text import DocumentError, extract_document
from app.integrations.embeddings import EmbeddingConfig
from app.main import create_app
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.knowledge.models import ReferencePassage, ReferenceSource, ReferenceVersion
from app.modules.knowledge.router import get_knowledge_service
from app.modules.knowledge.service import KnowledgeError, KnowledgeService, passages


class FakeEmbedding:
    config = EmbeddingConfig(dimensions=2)

    def __init__(self):
        self.fail = False
        self.calls = []

    def embed(self, texts, *, purpose, timeout=None):
        self.calls.append((texts, purpose))
        if self.fail:
            raise AiProviderError("timeout_or_network", retryable=True)
        return [[1.0, 0.0] if "força" in t.lower() else [0.0, 1.0] for t in texts]


@pytest.fixture
def setup():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    provider = FakeEmbedding()
    yield sessions, KnowledgeService(provider), provider
    engine.dispose()


def upload(sessions, service, source_id=None, body="Orientação de força para iniciantes."):
    with sessions() as session:
        return service.upload(
            session, title="Manual", media_type="text/plain", raw=body.encode(), source_id=source_id
        )


def activate(sessions, service, version):
    with sessions() as session:
        current = next(v for v in service.list(session) if v["id"] == version["id"])
        return service.transition(session, current["id"], "activate", current["revision"])


def test_complementary_search_preserves_technique_amid_programming_results(setup):
    sessions, service, provider = setup
    body = "\n".join(
        f"# Programação {index}\n"
        "Resistance training sets repetitions rest: 3 sets of 8 repetitions."
        for index in range(8)
    )
    body += (
        "\n# Seated Row\nResistance training. Starting Position: sit upright. "
        "Backward Movement: pull the handles toward the torso."
    )
    version = upload(sessions, service, body=body)
    service.import_next(sessions)
    activate(sessions, service, version)
    with sessions() as session:
        ordinary = service.search(session, "resistance training sets repetitions rest")
        assert all("Seated Row" not in row["content"] for row in ordinary)
        focused = service.search(
            session, "resistance training sets repetitions rest", prefer_technique=True
        )
        assert "Seated Row" in focused[0]["content"]
        assert len(focused) == 5
        assert any("Programação" in row["content"] for row in focused)
        provider.fail = True
        assert (
            "Seated Row"
            in service.search(
                session, "resistance training sets repetitions rest", prefer_technique=True
            )[0]["content"]
        )


def test_technique_preference_does_not_add_unmatched_or_withdrawn_sources(setup):
    sessions, service, provider = setup
    general = upload(sessions, service, body="Benefícios da caminhada para adultos.")
    service.import_next(sessions)
    activate(sessions, service, general)
    technique = upload(
        sessions,
        service,
        body="# Seated Row\nStarting Position: sit upright. Backward Movement: pull handles.",
    )
    service.import_next(sessions)
    active = activate(sessions, service, technique)
    provider.fail = True
    with sessions() as session:
        hits = service.search(session, "caminhada adultos", prefer_technique=True)
        assert len(hits) == 1 and hits[0]["version_id"] == str(general["id"])
        service.transition(session, active["id"], "withdraw", active["revision"])
        assert service.search(session, "seated row", prefer_technique=True) == []


def test_import_requires_explicit_activation_and_preserves_citations(setup):
    sessions, service, provider = setup
    version = upload(sessions, service)
    with sessions() as session:
        with pytest.raises(KnowledgeError, match="reference_not_ready"):
            service.transition(session, version["id"], "activate", 1)
    assert service.import_next(sessions)
    with sessions() as session:
        assert service.search(session, "força") == []
        assert service.preview(session, version["id"])[0]["content"].startswith("Orientação")
    activate(sessions, service, version)
    with sessions() as session:
        result = service.search(session, "força")
        assert len(result) == 1
        assert result[0]["version_id"] == str(version["id"])
        assert result[0]["title"] == "Manual"
        assert result[0]["location"] == "text;passage:1"
        service.validate_citations(session, result)


def test_failed_replacement_keeps_previous_version_and_can_retry(setup):
    sessions, service, provider = setup
    first = upload(sessions, service)
    service.import_next(sessions)
    activate(sessions, service, first)
    second = upload(sessions, service, first["source_id"], "Novas orientações de força.")
    provider.fail = True
    service.import_next(sessions)
    with sessions() as session:
        versions = {v["id"]: v for v in service.list(session)}
        assert versions[first["id"]]["active"]
        assert versions[second["id"]]["status"] == "failed"
        assert service.search(session, "força")[0]["version_id"] == str(first["id"])
        service.transition(session, second["id"], "retry", versions[second["id"]]["revision"])
    provider.fail = False
    service.import_next(sessions)
    activate(sessions, service, second)
    with sessions() as session:
        assert {r["version_id"] for r in service.search(session, "força")} == {str(second["id"])}


def test_lowered_pilot_limits_reject_capacity_without_disabling_existing_source(setup, monkeypatch):
    sessions, service, _ = setup
    monkeypatch.setenv("AI_REFERENCE_MAX_ACTIVE_DOCUMENTS", "1")
    first = upload(sessions, service)
    service.import_next(sessions)
    activate(sessions, service, first)
    second = upload(sessions, service)
    service.import_next(sessions)
    with pytest.raises(KnowledgeError, match="reference_capacity"):
        activate(sessions, service, second)
    with sessions() as session:
        assert {r["version_id"] for r in service.search(session, "força")} == {str(first["id"])}
    monkeypatch.setenv("AI_REFERENCE_MAX_CHARACTERS", "10")
    with pytest.raises(DocumentError, match="document_extraction_failed"):
        extract_document(b"This document is longer than the operator limit.", "text/plain")


def test_withdrawn_sources_invalidate_inflight_citations(setup):
    sessions, service, _ = setup
    item = upload(sessions, service)
    service.import_next(sessions)
    active = activate(sessions, service, item)
    with sessions() as old:
        citations = service.search(old, "força")
        old.commit()  # Retain the old identity-map version deliberately.
        with sessions() as other:
            service.transition(other, active["id"], "withdraw", active["revision"])
        with pytest.raises(KnowledgeError, match="reference_conflict"):
            service.validate_citations(old, citations)
    with sessions() as session:
        assert service.search(session, "força") == []


def test_embedding_spaces_are_not_mixed_but_lexical_still_works(setup):
    sessions, service, provider = setup
    item = upload(sessions, service)
    service.import_next(sessions)
    activate(sessions, service, item)
    provider.config = EmbeddingConfig(dimensions=2, revision="new-model")
    with sessions() as session:
        assert service.search(session, "força")  # lexical support remains
        assert service.search(session, "sem correspondência") == []


def test_pending_and_failed_passages_are_never_retrievable(setup):
    sessions, service, provider = setup
    item = upload(sessions, service, body="força " * 5000)
    calls = 0
    original = provider.embed

    def fail_second(texts, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise AiProviderError("timeout_or_network", retryable=True)
        return original(texts, **kwargs)

    provider.embed = fail_second
    service.import_next(sessions)
    with sessions() as session:
        assert session.get(ReferenceVersion, item["id"]).status == "failed"
        assert session.scalars(select(ReferencePassage)).all() == []
        assert service.search(session, "força") == []


def test_old_revision_cannot_withdraw_newly_activated_reference(setup):
    sessions, service, _ = setup
    item = upload(sessions, service)
    service.import_next(sessions)
    activate(sessions, service, item)
    with sessions() as session, pytest.raises(KnowledgeError, match="reference_conflict"):
        service.transition(session, item["id"], "withdraw", item["revision"])


def test_extraction_rejects_scans_invalid_pdf_and_non_utf8():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    raw = BytesIO()
    writer.write(raw)
    for body, media in [
        (raw.getvalue(), "application/pdf"),
        (b"invalid", "application/pdf"),
        (b"\xff", "text/plain"),
    ]:
        with pytest.raises(DocumentError):
            extract_document(body, media)
    assert (
        extract_document("Texto de referência".encode(), "text/plain")[0]["text"]
        == "Texto de referência"
    )


def test_chunking_preserves_all_text_and_bounds_embedding_bytes():
    original = "Não ignore restrições. " * 1000
    chunks = list(passages([{"location": "page:2", "text": original}]))
    assert "".join(p[2].replace(" ", "") for p in chunks) == original.replace(" ", "")
    assert all(len(p[2].encode()) <= 4000 for p in chunks)


@pytest.mark.parametrize("role,expected", [("admin", 200), ("client", 403), ("instructor", 403)])
def test_reference_management_requires_admin(setup, role, expected):
    sessions, service, _ = setup
    app = create_app()
    with sessions() as session:
        app.dependency_overrides[get_database_session] = lambda: session
        app.dependency_overrides[get_knowledge_service] = lambda: service
        app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
            "test", "test@example.test", (role,)
        )
        assert request(app, "GET", "/ai/references")[0] == expected


def test_pdf_chapter_context_survives_page_and_passage_boundaries():
    pages = [
        {"location": "page:1", "text": "ATIVIDADE FÍSICA PARA ADULTOS\n4\nCAPÍTULO\nIntrodução."},
        {
            "location": "page:2",
            "text": "Quanto tempo?\n" + "Pratique ao menos duas vezes por semana. " * 80,
        },
        {
            "location": "page:3",
            "text": "ATIVIDADE FÍSICA PARA IDOSOS\n5\nCAPÍTULO\nOutra orientação.",
        },
    ]
    chunks = list(passages(pages))
    continuation = [p[2] for p in chunks if p[1].startswith("page:2;")]
    assert len(continuation) > 1
    assert all(p.startswith("Seção: ATIVIDADE FÍSICA PARA ADULTOS\n") for p in continuation)
    assert chunks[-1][2].startswith("Seção: ATIVIDADE FÍSICA PARA IDOSOS\n")
    assert all(len(p[2]) <= 1000 for p in chunks)


def test_markdown_sections_are_not_carried_into_the_next_section():
    chunks = list(
        passages([{"location": "text", "text": "# Adultos\nDuas vezes.\n# Idosos\nEquilíbrio."}])
    )
    assert any(p[2].startswith("Seção: Adultos\n") and "Duas vezes." in p[2] for p in chunks)
    assert any(p[2].startswith("Seção: Idosos\n") and "Equilíbrio." in p[2] for p in chunks)
    assert not any("Duas vezes." in p[2] and "Equilíbrio." in p[2] for p in chunks)


def test_nested_markdown_retains_population_and_repeated_text_keeps_conflicts(setup):
    sessions, service, _ = setup
    body = "# Adultos\n## Frequência\nDuas vezes por semana."
    chunks = list(passages([{"location": "text", "text": body}]))
    assert chunks[-1][2].startswith("Seção: Adultos / Frequência\n")
    first = upload(sessions, service, body="# Adultos\nDuas vezes.\n# Adultos\nDuas vezes.")
    service.import_next(sessions)
    activate(sessions, service, first)
    other = upload(sessions, service, body="# Adultos\nTrês vezes.")
    service.import_next(sessions)
    activate(sessions, service, other)
    with sessions() as session:
        refs = service.search(session, "adultos vezes")
        assert len(refs) == 2
        assert len({r["source_id"] for r in refs}) == 2


def test_section_matching_handles_portuguese_singular_and_plural():
    from app.modules.knowledge.service import section_match

    assert section_match("Seção: ATIVIDADE FÍSICA PARA ADULTOS\nOrientação.", "adulto minutos") > 0
    assert section_match("Seção: JOVENS\nOrientação.", "jovem atividade") > 0
    assert section_match("Seção: IDOSOS\nOrientação.", "adultos minutos") == 0


def test_exercise_context_follows_continuation_and_stops_at_next_exercise():
    chunks = list(
        passages(
            [
                {
                    "location": "page:1",
                    "text": "Video 3.1\nFlat Barbell Bench Press\nStarting Position: Lifter\n"
                    "Keep contact with the bench.",
                },
                {
                    "location": "page:2",
                    "text": "Upward Movement\n" + "Keep the contact points stable. " * 60,
                },
                {
                    "location": "page:3",
                    "text": "Racking the bar\nVideo 3.2\nIncline Barbell Bench Press\n"
                    "Starting Position\nAdjust the seat.",
                },
                {"location": "page:4", "text": "Keep the bench inclined."},
                {"location": "page:5", "text": "Part IV\nOther Exercises"},
            ]
        )
    )
    continuation = [content for _, location, content in chunks if location.startswith("page:2;")]
    assert len(continuation) > 1
    assert all(content.startswith("Seção: Flat Barbell Bench Press\n") for content in continuation)
    assert any(
        content.startswith("Seção: Incline Barbell Bench Press\n") and "Adjust the seat." in content
        for _, _, content in chunks
    )
    assert chunks[-2][2].startswith("Seção: Incline Barbell Bench Press\n")
    assert "Bench Press" not in chunks[-1][2]
    assert all(len(content) <= 1000 for _, _, content in chunks)


def test_pdf_word_wrap_is_joined_without_changing_numbers_or_markdown():
    chunks = list(
        passages(
            [
                {
                    "location": "page:1",
                    "text": "Training and hypertrophy. Resistance train-\ning supports muscle "
                    "hyper-\ntrophy. Use 2-3 sets; 30%-70% is a range. "
                    "Five-\npoint contact and single-\njoint exercises.",
                },
                {"location": "text", "text": "Keep the authored spelling: train-\ning."},
            ]
        )
    )
    assert "training" in chunks[0][2] and "hypertrophy" in chunks[0][2]
    assert "2-3 sets; 30%-70%" in chunks[0][2]
    assert "Five-point contact and single-joint" in chunks[0][2]
    assert "train-\ning" in chunks[1][2]


def test_video_mentions_in_contents_do_not_become_exercise_headings():
    chunks = list(
        passages(
            [
                {"location": "page:1", "text": "Video 1.1\nAccess code: example\nContents"},
                {
                    "location": "page:2",
                    "text": "Video 1.10\n1.10\nSplit Jerk\nStarting Position\nInstructions.",
                },
                {"location": "page:3", "text": "Chapter 2\nGeneral guidance"},
            ]
        )
    )
    assert not chunks[0][2].startswith("Seção:")
    assert chunks[1][2].startswith("Seção: Split Jerk\n")
    assert not chunks[2][2].startswith("Seção:")


def test_search_aliases_preserve_variation_original_terms_and_input_bound():
    from app.modules.knowledge.search_terms import expand_search_terms

    query = "Supino inclinado com barra ajudante"
    expanded = expand_search_terms(query)
    assert expanded.startswith(query)
    assert "incline bench press" in expanded and "barbell" in expanded and "spotter" in expanded
    assert "flat" not in expanded and expanded.count("bench press") == 1
    assert expand_search_terms("hipertrofia séries") == "hipertrofia séries hypertrophy sets"
    assert expand_search_terms("modelo Lótus F02") == "modelo Lótus F02"
    assert expand_search_terms("English exercise name") == "English exercise name"
    long_query = "supino " + "x" * 493
    assert expand_search_terms(long_query) == long_query


def test_bibliography_penalty_preserves_prose_and_measurements_cover_both_languages():
    from app.modules.knowledge.service import bibliography_weight, measurement_terms

    assert bibliography_weight("A study (2026) discusses 10 sets weekly.") == 1
    assert bibliography_weight("Training. Journal. 2026;58(4):851. Other. 2024;21:10.") < 1
    assert "weekly" in measurement_terms("frequência semanal")
    assert "semana" in measurement_terms("weekly frequency")
    assert "minute" in measurement_terms("minutos por dia")


@pytest.mark.parametrize("heading", ["About the NSCA", "About the Authors", "References", "Index"])
def test_exercise_context_stops_at_back_matter(heading):
    chunks = list(
        passages(
            [
                {
                    "location": "page:1",
                    "text": "Video 5.9\nDumbbell Renegade Row\nStarting Position\nInstructions.",
                },
                {"location": "page:2", "text": heading + "\nPublication information."},
            ]
        )
    )
    assert chunks[0][2].startswith("Seção: Dumbbell Renegade Row\n")
    assert "Seção:" not in chunks[-1][2]


def test_delete_removes_all_versions_raw_files_and_vectors_but_preserves_other_sources(setup):
    sessions, service, _ = setup
    first = upload(sessions, service)
    service.import_next(sessions)
    activate(sessions, service, first)
    second = upload(sessions, service, first["source_id"])
    service.import_next(sessions)
    activate(sessions, service, second)
    pending = upload(sessions, service, first["source_id"])
    other = upload(sessions, service)
    with sessions() as session:
        citations = service.search(session, "força")
        service.delete_source(session, first["source_id"], pending["revision"])
        assert session.get(ReferenceSource, first["source_id"]) is None
        assert session.scalars(select(ReferencePassage)).all() == []
        assert [v.id for v in session.scalars(select(ReferenceVersion))] == [other["id"]]
        with pytest.raises(KnowledgeError, match="reference_conflict"):
            service.validate_citations(session, citations)


def test_new_upload_invalidates_old_deletion_confirmation(setup):
    sessions, service, _ = setup
    first = upload(sessions, service)
    upload(sessions, service, first["source_id"])
    with sessions() as session, pytest.raises(KnowledgeError, match="reference_conflict"):
        service.delete_source(session, first["source_id"], first["revision"])
    with sessions() as session:
        assert len(session.scalars(select(ReferenceVersion)).all()) == 2


def test_import_cannot_recreate_a_deleted_reference(setup):
    sessions, service, provider = setup
    item = upload(sessions, service)
    original = provider.embed

    def delete_during_embedding(*args, **kwargs):
        with sessions() as session:
            service.delete_source(session, item["source_id"], item["revision"])
        return original(*args, **kwargs)

    provider.embed = delete_during_embedding
    assert service.import_next(sessions)
    with sessions() as session:
        assert service.list(session) == []
        assert session.scalars(select(ReferencePassage)).all() == []


@pytest.mark.parametrize("role,expected", [("admin", 204), ("client", 403), ("instructor", 403)])
def test_reference_deletion_requires_admin(setup, role, expected):
    from test_profile_presence import request as json_request

    sessions, service, _ = setup
    item = upload(sessions, service)
    app = create_app()
    with sessions() as session:
        app.dependency_overrides[get_database_session] = lambda: session
        app.dependency_overrides[get_knowledge_service] = lambda: service
        app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
            "test", "test@example.test", (role,)
        )
        assert (
            json_request(
                app,
                "DELETE",
                f"/ai/references/sources/{item['source_id']}",
                {"revision": item["revision"]},
            )[0]
            == expected
        )
        assert bool(service.list(session)) == (role != "admin")
