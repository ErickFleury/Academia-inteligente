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
from app.modules.knowledge.models import ReferencePassage, ReferenceVersion
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
