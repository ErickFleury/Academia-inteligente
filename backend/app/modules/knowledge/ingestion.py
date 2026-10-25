"""Operational corpus proof using the existing atomic bootstrap and real BGE-M3."""

import argparse
import json
import time
from datetime import UTC, datetime
from urllib.request import urlopen

from sqlalchemy import text

from app.database import SessionLocal
from app.integrations.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    OllamaBgeM3EmbeddingProvider,
)
from app.modules.clients import models as client_models  # noqa: F401
from app.modules.knowledge.acquisition import CACHE_PATH, digest, write_json
from app.modules.knowledge.bootstrap import CATALOG_PATH, seed_catalog


class CountingEmbeddings:
    def __init__(self):
        self.provider = OllamaBgeM3EmbeddingProvider()
        self.calls = 0
        self.texts = 0

    def embed(self, texts):
        self.calls += 1
        self.texts += len(texts)
        return self.provider.embed(texts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-name", choices=("s4-indexing", "expansion-indexing"), default="s4-indexing"
    )
    args = parser.parse_args()
    if SessionLocal is None:
        raise SystemExit("DATABASE_URL must be configured")
    raw_catalog = CATALOG_PATH.read_bytes()
    catalog = json.loads(raw_catalog)
    provider = CountingEmbeddings()
    runs = []
    for _ in range(2):
        before_calls, before_texts = provider.calls, provider.texts
        started = time.monotonic()
        with SessionLocal() as session, session.begin():
            if session.get_bind().dialect.name != "postgresql":
                raise SystemExit("Operational proof requires PostgreSQL/pgvector")
            count = seed_catalog(session, provider, catalog)
            vectors = session.execute(
                text(
                    "SELECT count(*), min(public.vector_dims(embedding)), "
                    "max(public.vector_dims(embedding)) FROM knowledge_chunk "
                    "WHERE source_id IN (SELECT id FROM knowledge_source "
                    "WHERE catalog_managed AND client_id IS NULL AND review_status='approved')"
                )
            ).one()
            if tuple(vectors) != (count, EMBEDDING_DIMENSIONS, EMBEDDING_DIMENSIONS):
                raise ValueError("operational_vector_count_or_dimension_mismatch")
            vector_rows = (
                session.execute(
                    text(
                        "SELECT id, source_id, content_hash, embedding_model, "
                        "public.vector_dims(embedding) AS dimensions FROM knowledge_chunk "
                        "WHERE source_id IN (SELECT id FROM knowledge_source "
                        "WHERE catalog_managed AND client_id IS NULL) ORDER BY id"
                    )
                )
                .mappings()
                .all()
            )
        runs.append(
            {
                "chunks": count,
                "embedding_calls": provider.calls - before_calls,
                "embedded_texts": provider.texts - before_texts,
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        )
    if runs[1]["embedded_texts"]:
        raise ValueError("unchanged_second_run_reembedded_content")
    with urlopen(provider.provider.base_url + "/api/tags", timeout=30) as response:
        models = json.loads(response.read(1_000_000))["models"]
    matching = [m for m in models if m["name"].split(":")[0] == EMBEDDING_MODEL]
    if len(matching) != 1:
        raise ValueError("ambiguous_embedding_model_identity")
    report = {
        "version": 1,
        "captured_at": datetime.now(UTC).isoformat(),
        "catalog_sha256": digest(raw_catalog),
        "model": EMBEDDING_MODEL,
        "model_digest": matching[0]["digest"],
        "dimensions": EMBEDDING_DIMENSIONS,
        "runs": runs,
        "vectors": [dict(row) for row in vector_rows],
        "scientific_approval": "pending",
        "enabled_cohorts": [],
    }
    write_json(CACHE_PATH / (args.report_name + ".json"), report)
    print(json.dumps({key: value for key, value in report.items() if key != "vectors"}))


if __name__ == "__main__":
    main()
