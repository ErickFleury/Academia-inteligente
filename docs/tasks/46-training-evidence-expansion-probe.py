"""Public-corpus technical probes; not prescription feasibility or evaluation."""

import json
import time
from datetime import UTC, datetime
from uuid import uuid4

from app.database import SessionLocal
from app.integrations.embeddings import OllamaBgeM3EmbeddingProvider
from app.modules.clients import models as client_models  # noqa: F401
from app.modules.knowledge.acquisition import CACHE_PATH, digest, write_json
from app.modules.knowledge.bootstrap import CATALOG_PATH
from app.modules.knowledge.service import MAX_CHUNKS, KnowledgeService

QUERIES = [
    ("singer-rest-2024", "Inter-set rest interval duration muscle hypertrophy"),
    ("iversen-time-efficient-2021", "Time-efficient resistance training minimum dose supersets"),
    (
        "schumann-concurrent-2022",
        "Concurrent aerobic resistance training compatibility interference",
    ),
    ("ingram-stretch-mechanisms-2025", "Stretching mechanisms flexibility range of motion"),
    (
        "smart-isometric-hypertension-2023",
        "Isometric exercise training hypertension blood pressure",
    ),
    ("su-diabetes-exercise-2026", "Diabetes exercise medication hypoglycemia precautions"),
    ("lafontant-body-fat-2025", "Exercise body fat percentage aerobic resistance training"),
    ("bao-depp-2026", "DEPP exercise prescription protocol database methods limitations"),
    ("price-asthma-2025", "Asthma exercise training bronchoconstriction precautions"),
]

service = KnowledgeService(OllamaBgeM3EmbeddingProvider())
results = []
for source_id, query in QUERIES:
    started = time.monotonic()
    with SessionLocal() as session:
        context = service.retrieve(session, uuid4(), query)
    assert len(context.chunks) <= MAX_CHUNKS
    results.append(
        {
            "query": query,
            "target_source_id": source_id,
            "target_retrieved": any(c["source_id"] == source_id for c in context.chunks),
            "status": context.knowledge_status,
            "selected_passages": [
                {"source_id": c["source_id"], "chunk_id": c["chunk_id"]} for c in context.chunks
            ],
            "context_characters": sum(len(c["content"]) for c in context.chunks),
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    )

indexing = json.loads((CACHE_PATH / "expansion-indexing.json").read_text())
report = {
    "version": 1,
    "captured_at": datetime.now(UTC).isoformat(),
    "purpose": "development_only_public_corpus_technical_probes",
    "catalog_sha256": digest(CATALOG_PATH.read_bytes()),
    "embedding_model": indexing["model"],
    "model_digest": indexing["model_digest"],
    "final_passage_limit": MAX_CHUNKS,
    "queries": results,
    "target_hits": sum(result["target_retrieved"] for result in results),
    "reviewed_development_cases": 0,
    "dimension_coverage": "not_assessed",
    "scientific_approval": "pending",
    "enabled_cohorts": [],
    "limitations": [
        "Queries were authored and observed by the implementer, with known source topics.",
        "Target retrieval is a technical smoke check, not independent relevance judgment.",
        "No prescription, clinical applicability or six-passage dimension coverage was evaluated.",
        "No writing model was invoked and no client plan was created or activated.",
    ],
}
write_json(CACHE_PATH / "expansion-retrieval.json", report)
print(json.dumps(report))
