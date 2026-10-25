"""Development-only technical probe; not reviewed cohort feasibility or evaluation."""

import json
import time
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select

from app.database import SessionLocal
from app.integrations.embeddings import EMBEDDING_MODEL, OllamaBgeM3EmbeddingProvider
from app.modules.clients import models as client_models  # noqa: F401
from app.modules.knowledge.acquisition import CACHE_PATH, SOURCE_ID, digest, write_json
from app.modules.knowledge.bootstrap import CATALOG_PATH
from app.modules.knowledge.models import KnowledgeChunk
from app.modules.knowledge.service import MAX_CHUNKS, KnowledgeService


def main():
    if SessionLocal is None:
        raise SystemExit("DATABASE_URL must be configured")
    query = "Resistance training dosage strength volume intensity duration untrained limitations"
    started = time.monotonic()
    with SessionLocal() as session:
        indexed = session.scalars(
            select(KnowledgeChunk.id).where(KnowledgeChunk.source_id == SOURCE_ID)
        ).all()
        result = KnowledgeService(OllamaBgeM3EmbeddingProvider()).retrieve(session, uuid4(), query)
    report = {
        "version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "purpose": "development_only_technical_probe",
        "catalog_sha256": digest(CATALOG_PATH.read_bytes()),
        "embedding_model": EMBEDDING_MODEL,
        "query": query,
        "indexed_source_passages": indexed,
        "selected_passages": [c["chunk_id"] for c in result.chunks],
        "selected_source_passages": [
            c["chunk_id"] for c in result.chunks if c["source_id"] == SOURCE_ID
        ],
        "final_passage_limit": MAX_CHUNKS,
        "status": result.knowledge_status,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "context_characters": sum(len(c["content"]) for c in result.chunks),
        "reviewed_development_cases": 0,
        "dimension_coverage": "not_assessed",
        "enabled_cohorts": [],
        "remaining_gate": "Reviewed cases/rules/inputs and sealed evaluation are absent.",
    }
    write_json(CACHE_PATH / "development-retrieval.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
