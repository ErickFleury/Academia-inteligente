"""Explicit local-model evaluation, separate from the controlled-provider test suite.

Creates and always drops its own random PostgreSQL schema. Never reads client
records from the application schema. Outputs only committed synthetic fixtures.
Run with python -m scripts.evaluate_assistant --output /app/evaluation.json.
"""

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import app.main  # noqa: F401 -- register all application tables
from app.database import Base
from app.integrations.ai import AiProviderError
from app.integrations.embeddings import HttpEmbeddingProvider
from app.modules.assistant.runtime import AssistantError, AssistantRun
from app.modules.clients.models import Account, Client
from app.modules.knowledge.service import KnowledgeService
from app.modules.training.models import TrainingAiConversation, TrainingAiMessage


def review_worksheet(report):
    lines = [
        "# Synthetic assistant claim review",
        "",
        "Human review pending. Use the rubric in docs/ai-rag-evaluation.md.",
        "Do not treat the runtime's own review as an independent quality score.",
        "",
        "For each case, split the answer into substantive claims, check the cited",
        "passages, record counts and flag missing conditions or relevant conflicts.",
        "",
    ]
    for row in report["cases"]:
        lines.extend(
            [
                f"## {row['id']} — {row['kind']}",
                "",
                row["question"],
                "",
                f"Outcome: {row.get('status', 'retrieval only')}; "
                f"{row.get('seconds', '—')} seconds.",
                "",
                "Delivered answer:",
                "",
                row.get("answer", {}).get(
                    "assistant_message", row.get("error", "No answer requested")
                ),
                "",
                "Cited evidence:",
                "",
            ]
        )
        for reference in row.get("citations", []):
            lines.extend(
                [
                    f"- **{reference['title']}**, version {reference['version']}, "
                    f"{reference['location']}",
                    "",
                    "> " + reference["content"].replace("\n", "\n> "),
                    "",
                ]
            )
        if not row.get("citations"):
            lines.extend(["No citations delivered.", ""])
        lines.extend(
            [
                "Human verdict: pending. Substantive claims: __. Supported claims: __.",
                "Critical issue / omitted condition / explanation: __.",
                "",
            ]
        )
    return "\n".join(lines)


class LexicalOnly:
    def __init__(self, provider):
        self.config = provider.config

    def embed(self, *args, **kwargs):
        raise AiProviderError("evaluation_lexical_baseline", retryable=False)


def run(args):
    if (
        os.getenv("AI_PROVIDER", "ollama") != "ollama"
        or os.getenv("AI_EMBEDDING_PROVIDER", "ollama") != "ollama"
    ):
        raise SystemExit("This benchmark is local-only; explicitly select both Ollama adapters.")
    fixture_bytes = Path(__file__).with_name("assistant_eval_fixtures.json").read_bytes()
    fixtures = json.loads(fixture_bytes)
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "synthetic_only": True,
        "generation_model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        "embedding_model": os.getenv("AI_EMBEDDING_MODEL", "embeddinggemma"),
        "embedding_gpu_layers": os.getenv("AI_EMBEDDING_GPU_LAYERS", "0"),
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "documents": fixtures["documents"],
        "cases": [],
    }
    output = Path(args.output)
    if output.exists() or output.with_suffix(".review.md").exists():
        raise SystemExit("Choose a new output path; previous evaluation evidence is immutable.")

    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    schema = "eval_assistant_" + uuid4().hex
    admin = create_engine(os.environ["DATABASE_URL"])
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"options": f"-csearch_path={schema} -clock_timeout=5000"},
    )
    try:
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine, expire_on_commit=False)
        embeddings = HttpEmbeddingProvider()
        knowledge = KnowledgeService(embeddings)
        lexical = KnowledgeService(LexicalOnly(embeddings))
        sources = {}
        started = monotonic()
        for document in fixtures["documents"]:
            with sessions() as session:
                version = knowledge.upload(
                    session,
                    title=document["title"],
                    media_type="text/plain",
                    raw=document["text"].encode(),
                )
            knowledge.import_next(sessions)
            with sessions() as session:
                knowledge.transition(session, version["id"], "activate", version["revision"])
            sources[str(version["source_id"])] = document["id"]
        report["index_seconds"] = round(monotonic() - started, 3)
        print(f"Indexed {len(sources)} synthetic sources", flush=True)
        for case in fixtures["cases"]:
            if args.case and case["id"] not in args.case:
                continue
            row = {**case, "kind": case.get("kind", "answerable")}
            with sessions() as session:
                started = monotonic()
                refs = knowledge.search(session, case["question"])
                row["hybrid_seconds"] = round(monotonic() - started, 3)
                row["hybrid"] = [sources[r["source_id"]] for r in refs]
                row["lexical"] = [
                    sources[r["source_id"]] for r in lexical.search(session, case["question"])
                ]
                if args.answers:
                    client = Client(
                        name="Synthetic evaluation client",
                        account=Account(email=f"{uuid4().hex}@example.test", account_active=True),
                    )
                    session.add(client)
                    session.flush()
                    conversation = TrainingAiConversation(client_id=client.id)
                    session.add(conversation)
                    session.flush()
                    source = TrainingAiMessage(
                        conversation_id=conversation.id,
                        role="user",
                        content=case["question"],
                        sequence=1,
                        client_request_id=uuid4(),
                    )
                    session.add(source)
                    session.commit()
                    agent = AssistantRun(
                        session, client.id, "training_chat", source=source, knowledge=knowledge
                    )
                    started = monotonic()
                    try:
                        agent.prepare(
                            {
                                "current_user_message": case["question"],
                                "current_training_plan": None,
                                "editable_training_draft": None,
                                "onboarding_completed": True,
                                "rules": {"may_update_ai_draft": False},
                            }
                        )
                        answer = agent.specialist()
                        agent.finalize()
                        row["answer"] = answer.model_dump(mode="json")
                        row["citations"] = [
                            {**ref, "fixture_source": sources[ref["source_id"]]}
                            for ref in agent.citations
                        ]
                        row["status"] = "success"
                    except (AssistantError, AiProviderError) as error:
                        row["status"] = "controlled_failure"
                        row["error"] = str(error)
                    finally:
                        session.rollback()
                    row["seconds"] = round(monotonic() - started, 3)
                    row["route"] = agent.route.model_dump(mode="json") if agent.route else None
                    row["routed_sources"] = [sources[r["source_id"]] for r in agent.references]
                    row["budget"] = {
                        key: getattr(agent.budget, key)
                        for key in ("calls", "retrievals", "input_tokens", "output_tokens")
                    }
            report["cases"].append(row)
            save()
            print(
                json.dumps({k: row[k] for k in ("id", "hybrid", "status", "seconds") if k in row}),
                flush=True,
            )
        answerable = [r for r in report["cases"] if r["expected"] and r["kind"] != "conflict"]
        report["retrieval"] = {
            "answerable_cases": len(answerable),
            **{
                method + "_recall_at_5": sum(
                    bool(set(r["expected"]) & set(r[method][:5])) for r in answerable
                )
                / len(answerable)
                if answerable
                else None
                for method in ("lexical", "hybrid")
            },
        }
        report["completed_at"] = datetime.now(UTC).isoformat()
        save()
        output.with_suffix(".review.md").write_text(review_worksheet(report))
        print(json.dumps(report["retrieval"]), flush=True)
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--answers", action="store_true")
    parser.add_argument("--case", action="append", help="Run selected case IDs for diagnosis only")
    run(parser.parse_args())
