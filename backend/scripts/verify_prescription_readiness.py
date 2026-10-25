"""Read-only Tasks 46–51 audit; never reads sealed cases or client records.

Run with `python -m scripts.verify_prescription_readiness`. This inventories
public corpus state and protected public seal metadata, not independent results.
"""

import json
from datetime import UTC, datetime

from sqlalchemy import select, text

from app.database import SessionLocal
from app.integrations.embeddings import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL
from app.modules.knowledge.acquisition import CACHE_PATH, digest, write_json
from app.modules.knowledge.bootstrap import CATALOG_PATH
from app.modules.training.evidence_review_models import EvidenceSeal
from app.modules.training.prescription_authorization import readiness_matrix
from app.modules.training.prescription_runtime import writer_configuration


def collect_audit(session):
    if session.get_bind().dialect.name != "postgresql":
        raise ValueError("actual_postgresql_inventory_required")
    session.execute(text("SET TRANSACTION READ ONLY"))
    vectors = session.execute(
        text(
            "SELECT count(*), min(public.vector_dims(k.embedding)), "
            "max(public.vector_dims(k.embedding)) FROM knowledge_chunk k "
            "JOIN knowledge_source s ON s.id=k.source_id WHERE s.catalog_managed "
            "AND s.client_id IS NULL AND s.review_status='approved'"
        )
    ).one()
    sources = (
        session.execute(
            text(
                "SELECT s.id, s.review_status, count(k.id) AS indexed_passages "
                "FROM knowledge_source s LEFT JOIN knowledge_chunk k ON k.source_id=s.id "
                "WHERE s.catalog_managed AND s.client_id IS NULL "
                "GROUP BY s.id, s.review_status ORDER BY s.id"
            )
        )
        .mappings()
        .all()
    )
    # Explicit columns prevent deferred/eager ORM access to private_cases.
    seals = (
        session.execute(
            select(
                EvidenceSeal.id,
                EvidenceSeal.artifact_hashes,
                EvidenceSeal.case_count,
                EvidenceSeal.payload_sha256,
            )
        )
        .mappings()
        .all()
    )
    matrix = readiness_matrix()
    rag = matrix["owner_rag"]
    rag_available = rag["enabled"] and rag["authorized"]
    blockers = (
        [] if rag_available else ["Owner-RAG mode and matching current authorization required."]
    )
    if not vectors[0] or vectors[1:] != (EMBEDDING_DIMENSIONS, EMBEDDING_DIMENSIONS):
        blockers.append("Eligible indexed public corpus with correct dimensions required.")
    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "scope": "tasks_46_51_read_only_readiness",
        "catalog_sha256": digest(CATALOG_PATH.read_bytes()),
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimensions_expected": EMBEDDING_DIMENSIONS,
        "public_vectors": vectors[0],
        "dimensions_min": vectors[1],
        "dimensions_max": vectors[2],
        "public_sources": [dict(row) for row in sources],
        "writer_configuration": writer_configuration(),
        "bundle_sha256": matrix["bundle_sha256"],
        "accepted_research_rules": sum(r["owner_accepted"] for r in matrix["rules"]),
        "compiled_approved_policy_count": sum(
            len(p["compiled_policy_ids"]) for p in matrix["profiles"]
        ),
        "seal_metadata": [{**dict(row), "id": str(row["id"])} for row in seals],
        "private_cases_read": False,
        "client_records_read": False,
        "independent_evaluation": "optional_not_performed",
        "owner_rag": rag,
        "release_authorized": rag_available,
        "release_scope": "owner_assisted_rag_only" if rag_available else "none",
        "compiled_prescription_release_authorized": False,
        "compiled_policy_open_items": matrix["missing_items"],
        "enabled_cohorts": matrix["enabled_cohorts"],
        "blockers": blockers,
    }


def main():
    if SessionLocal is None:
        raise SystemExit("DATABASE_URL is required")
    with SessionLocal() as session:
        report = collect_audit(session)
    name = "tasks-46-51-readiness-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + ".json"
    write_json(CACHE_PATH / name, report)
    print(
        json.dumps(
            {
                "output": name,
                "vectors": report["public_vectors"],
                "accepted_rules": report["accepted_research_rules"],
                "approved_policies": report["compiled_approved_policy_count"],
                "seal_count": len(report["seal_metadata"]),
                "release_authorized": report["release_authorized"],
            }
        )
    )


if __name__ == "__main__":
    main()
