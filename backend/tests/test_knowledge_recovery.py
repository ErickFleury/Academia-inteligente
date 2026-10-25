"""Separate runtime fallback, transactional startup failure and safe recovery checks."""

import copy
import os
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from test_clients import AsgiClient
from test_knowledge import FakeEmbeddings, catalog_source
from test_knowledge_postgres import knowledge_sessions as knowledge_sessions
from test_training_lifecycle import client_id, data
from training_fixtures import instructor

from app.database import get_database_session
from app.integrations.embeddings import EmbeddingProviderError
from app.main import create_app
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.knowledge.bootstrap import seed_catalog
from app.modules.knowledge.models import KnowledgeChunk
from app.modules.knowledge.recovery import validate_recovery_catalog
from app.modules.knowledge.service import KnowledgeService


class UnavailableEmbeddings:
    def embed(self, texts):
        raise EmbeddingProviderError("embedding_unavailable")


@pytest.mark.parametrize("change", ["revoked", "removed", "expired", "license"])
def test_last_known_valid_candidate_cannot_restore_invalid_sources(change):
    candidate = {"version": 1, "sources": [catalog_source()]}
    current = copy.deepcopy(candidate)
    if change == "revoked":
        current["sources"][0]["review_status"] = "excluded"
    elif change == "removed":
        current["sources"] = []
    elif change == "expired":
        current["sources"][0]["review_due_at"] = (date.today() - timedelta(days=1)).isoformat()
    else:
        current["sources"][0]["license"] = "CC-BY-NC-4.0"
    with pytest.raises(ValueError):
        validate_recovery_catalog(candidate, current)


def test_compatible_fallback_and_empty_or_stale_candidate():
    candidate = {"version": 1, "sources": [catalog_source()]}
    assert validate_recovery_catalog(candidate, candidate) == 1
    with pytest.raises(ValueError, match="no_valid_recovery"):
        validate_recovery_catalog({"version": 1, "sources": []}, candidate)
    stale = copy.deepcopy(candidate)
    stale["sources"][0]["review_due_at"] = date.today().isoformat()
    with pytest.raises(ValueError, match="invalid"):
        validate_recovery_catalog(stale, candidate)


@pytest.mark.parametrize("remove", [False, True])
def test_fallback_cannot_restore_changed_or_removed_passages(remove):
    candidate = {"version": 1, "sources": [catalog_source()]}
    current = copy.deepcopy(candidate)
    if remove:
        current["sources"][0]["chunks"] = []
    else:
        current["sources"][0]["chunks"][0]["content"] = "Corrected evidence"
    with pytest.raises(ValueError, match="removed_or_changed_passage"):
        validate_recovery_catalog(candidate, current)


@pytest.mark.skipif(os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in")
def test_existing_failed_bootstrap_retains_previous_corpus_then_recovers(knowledge_sessions):
    original = {"version": 1, "sources": [catalog_source(), catalog_source("revoked")]}
    with knowledge_sessions() as session, session.begin():
        seed_catalog(session, FakeEmbeddings(), original)
    changed = copy.deepcopy(original)
    changed["sources"][0]["chunks"][0]["content"] = "Changed text"
    changed["sources"][1]["review_status"] = "excluded"
    with knowledge_sessions() as session:
        with pytest.raises(EmbeddingProviderError), session.begin():
            seed_catalog(session, UnavailableEmbeddings(), changed)
    with knowledge_sessions() as session:
        assert session.get(KnowledgeChunk, "reviewed-1").content != "Changed text"
        assert session.get(KnowledgeChunk, "revoked-1") is not None
        session.rollback()
        with session.begin():
            seed_catalog(session, FakeEmbeddings(), changed)
        assert session.get(KnowledgeChunk, "reviewed-1").content == "Changed text"
        assert session.get(KnowledgeChunk, "revoked-1") is None
    with pytest.raises(ValueError, match="restore"):
        validate_recovery_catalog(original, changed)


@pytest.mark.skipif(os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in")
def test_fresh_database_failed_bootstrap_has_no_usable_corpus(knowledge_sessions):
    catalog = {"version": 1, "sources": [catalog_source()]}
    with knowledge_sessions() as session:
        with pytest.raises(EmbeddingProviderError), session.begin():
            seed_catalog(session, UnavailableEmbeddings(), catalog)
    with knowledge_sessions() as session:
        assert session.scalar(select(func.count()).select_from(KnowledgeChunk)) == 0
        session.rollback()
        with session.begin():
            seed_catalog(session, FakeEmbeddings(), catalog)
        assert session.scalar(select(func.count()).select_from(KnowledgeChunk)) == 1


@pytest.mark.skipif(os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in")
def test_runtime_embedding_outage_does_not_block_manual_api(knowledge_sessions, monkeypatch):
    with knowledge_sessions() as session:
        instructor(session)
        identifier = client_id(session)
        seed_catalog(session, FakeEmbeddings(), {"version": 1, "sources": [catalog_source()]})
        session.commit()
        result = KnowledgeService(UnavailableEmbeddings()).retrieve(session, uuid4(), "força")
        assert result.knowledge_status == "unavailable" and not result.chunks

        class Identity:
            def get_identity(self, token):
                return AuthenticatedIdentity("instructor-1", "instructor", ("instructor",))

        monkeypatch.setattr(identity_router, "identity_provider", Identity())
        app = create_app()
        app.dependency_overrides[get_database_session] = lambda: session
        client = AsgiClient(app)
        assert client.get("/health").status_code == 200
        response = client.post(
            "/training/plans", {**data().model_dump(mode="json"), "client_id": str(identifier)}
        )
        assert response.status_code == 201, response.text
        draft = response.json()
        approval = client.post(
            f"/training/plans/{draft['plan_id']}/versions/1/approve", {"expected_revision": 1}
        )
        assert approval.status_code == 200, approval.text
