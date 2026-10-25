"""Frozen exposed owner-RAG runtime check with real public retrieval/local models.

Public-corpus PostgreSQL access is read-only. Synthetic onboarding/proposals are
stored only in disposable in-memory SQLite. No independent evaluation is claimed.
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen
from uuid import uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_training_generation import complete_onboarding, create_client  # noqa: E402

from app.database import Base, SessionLocal  # noqa: E402
from app.integrations.ai import (
    AiProviderError,  # noqa: E402
    training_generation_provider_from_environment,  # noqa: E402
)
from app.modules.knowledge.acquisition import CACHE_PATH, digest, write_json  # noqa: E402
from app.modules.knowledge.models import KnowledgeSource  # noqa: E402
from app.modules.knowledge.service import KnowledgeContext, KnowledgeService  # noqa: E402
from app.modules.training import owner_rag  # noqa: E402
from app.modules.training.chat_service import TrainingChatService  # noqa: E402
from app.modules.training.generation_service import InitialTrainingGenerationService  # noqa: E402
from app.modules.training.models import TrainingPlanVersion  # noqa: E402
from app.modules.training.prescription_budget import CURRENT_STAGE, attempt_budget  # noqa: E402
from app.modules.training.prescription_contract import PrescriptionRejection  # noqa: E402
from app.modules.training.service import TrainingLifecycleService  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", action="store_true", help="Run three goals and two controls")
    parser.add_argument(
        "--schedule-matrix",
        action="store_true",
        help="Optional A/B/C, two-day, default and refusal checks",
    )
    parser.add_argument("--repetitions", type=int, default=1, choices=range(1, 11))
    parser.add_argument(
        "--flexibility-matrix",
        action="store_true",
        help="Flexibility through chat, current intent, optional days and resistance controls",
    )
    parser.add_argument(
        "--case",
        action="append",
        choices=[
            "initial-strength",
            "initial-hypertrophy",
            "initial-muscular-endurance",
            "ambiguous-goal",
            "retrieval-outage",
            "abc-strength",
            "abc-hypertrophy",
            "abc-muscular-endurance",
            "abc-full-body",
            "two-day-hypertrophy",
            "conflicting-schedule",
            "priority-goal",
            "flexibility-plain",
            "flexibility-copied-header",
            "flexibility-one-day",
            "flexibility-three-days",
            "flexibility-negated-goal",
        ],
        help="Run only selected cases; repeat to select more than one (use --matrix for goals)",
    )
    args = parser.parse_args()
    if os.getenv("AI_PROVIDER") != "ollama" or SessionLocal is None:
        raise SystemExit("Configured local Ollama and PostgreSQL are required")
    os.environ["TRAINING_EVIDENCE_MODE"] = "owner_rag"
    approval = owner_rag.authorization()
    provider = training_generation_provider_from_environment()
    with urlopen(provider._config.base_url.rstrip("/") + "/api/tags", timeout=10) as response:
        tags = json.load(response)
    model = next(m for m in tags["models"] if m["name"] == provider._config.model)
    name = "owner-rag-runtime-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    files = [
        "app/modules/training/owner_rag.py",
        "app/modules/training/owner_rag_schema.py",
        "app/modules/training/owner_rag_load.py",
        "app/modules/training/owner_rag_flexibility.py",
        "app/modules/training/request_intent.py",
        "app/modules/training/knowledge_query.py",
        "app/modules/training/owner-rag-exercises.json",
        "app/modules/training/generation_service.py",
        "app/modules/training/chat_service.py",
        "app/modules/training/adaptation_service.py",
        "app/modules/training/selection.py",
        "app/modules/training/prescription_budget.py",
        "app/modules/training/completeness.py",
        "app/modules/training/focus.py",
        "app/integrations/ai.py",
        "app/integrations/ai_diagnostics.py",
        "scripts/probe_owner_rag_runtime.py",
    ]
    hashes = {path: digest((Path(__file__).parents[1] / path).read_bytes()) for path in files}
    cases = [
        {
            "id": "initial-strength",
            "onboarding": {"training_goal": "Ganhar força", "training_experience": "beginner"},
            "repetitions": 1,
            "expected": "reviewable_proposal_without_activation",
            "maximum_writer_http_calls": 4,
            "maximum_review_http_calls": 4,
            "maximum_focus_http_calls": 0,
        }
    ]
    if args.matrix:
        for case_id, goal, experience in [
            ("initial-hypertrophy", "Hipertrofia muscular", "intermediate"),
            ("initial-muscular-endurance", "Resistência muscular", "beginner"),
        ]:
            cases.append(
                {
                    **cases[0],
                    "id": case_id,
                    "onboarding": {"training_goal": goal, "training_experience": experience},
                }
            )
        cases.append(
            {
                "id": "ambiguous-goal",
                "onboarding": {"training_goal": "Força e hipertrofia"},
                "repetitions": 1,
                "expected": "clarification_without_writer_or_save",
                "maximum_model_http_calls": 0,
            }
        )
    cases.append(
        {
            "id": "retrieval-outage",
            "onboarding": {},
            "repetitions": 1,
            "expected": "technical_unavailability_without_writer_or_save",
            "maximum_model_http_calls": 0,
        }
    )
    if args.schedule_matrix:
        if args.matrix:
            parser.error("Use either --matrix or --schedule-matrix")
        positive = {**cases[0], "maximum_focus_http_calls": 2}
        cases = [
            {
                **positive,
                "id": "abc-strength",
                "onboarding": {"training_goal": "Hipertrofia"},
                "request": (
                    "Gere uma ficha de treino de força em três dias diferentes (treinos A, B, C)."
                ),
                "expected_session_labels": list("ABC"),
                "expected_goal_family": "strength",
            },
            {
                **positive,
                "id": "abc-hypertrophy",
                "onboarding": {
                    "training_goal": "Hipertrofia",
                    "training_experience": "intermediate",
                },
                "request": "Gere uma ficha de hipertrofia em três dias, fichas A/B/C.",
                "expected_session_labels": list("ABC"),
                "expected_goal_family": "hypertrophy",
            },
            {
                **positive,
                "id": "abc-muscular-endurance",
                "onboarding": {"training_goal": "Hipertrofia"},
                "request": "Gere treino de resistência muscular em três dias, fichas A/B/C.",
                "expected_session_labels": list("ABC"),
                "expected_goal_family": "muscular_endurance",
            },
            {
                **positive,
                "id": "abc-full-body",
                "onboarding": {},
                "request": "Gere um treino de corpo inteiro para força em três dias, A/B/C.",
                "expected_session_labels": list("ABC"),
                "expected_goal_family": "strength",
            },
            {
                **positive,
                "id": "two-day-hypertrophy",
                "onboarding": {"training_goal": "Hipertrofia"},
                "request": "Gere um treino de hipertrofia em dois dias, fichas A e B.",
                "expected_session_labels": list("AB"),
                "expected_goal_family": "hypertrophy",
            },
            {
                **positive,
                "id": "initial-hypertrophy",
                "onboarding": {"training_goal": "Hipertrofia"},
                "expected_session_labels": ["A"],
                "expected_goal_family": "hypertrophy",
            },
            {
                "id": "ambiguous-goal",
                "onboarding": {},
                "request": "Gere força e hipertrofia em três dias A/B/C.",
                "repetitions": 1,
                "expected": "clarification_without_writer_or_save",
                "maximum_model_http_calls": 0,
            },
            {
                **positive,
                "id": "priority-goal",
                "onboarding": {"training_goal": "Hipertrofia"},
                "request": (
                    "Gere treino de força e hipertrofia em três dias. "
                    "Objetivo principal: hipertrofia."
                ),
                "expected_session_labels": list("ABC"),
                "expected_goal_family": "hypertrophy",
            },
            {
                "id": "conflicting-schedule",
                "onboarding": {},
                "request": "Gere hipertrofia em dois dias com fichas A/B/C.",
                "repetitions": 1,
                "expected": "clarification_without_writer_or_save",
                "maximum_model_http_calls": 0,
            },
            {
                "id": "retrieval-outage",
                "onboarding": {},
                "repetitions": 1,
                "expected": "technical_unavailability_without_writer_or_save",
                "maximum_model_http_calls": 0,
            },
        ]
    if args.flexibility_matrix:
        if args.matrix or args.schedule_matrix:
            parser.error("Use only one matrix option")
        positive = {**cases[0], "maximum_focus_http_calls": 2}
        cases = [
            {
                **positive,
                "id": case_id,
                "onboarding": {"training_goal": "Força e hipertrofia"},
                "entry_point": "chat",
                "request": request,
                "expected_session_labels": labels,
                "expected_goal_family": "mobility_flexibility",
                **(
                    {"history_request": "Gere uma ficha de força e hipertrofia"}
                    if case_id == "flexibility-copied-header"
                    else {}
                ),
            }
            for case_id, request, labels in [
                ("flexibility-plain", "Gere uma ficha de treino de flexibilidade.", ["A"]),
                (
                    "flexibility-copied-header",
                    "Você\nGere uma ficha de treino de flexibilidade.",
                    ["A"],
                ),
                (
                    "flexibility-one-day",
                    "Gere uma ficha de treino de flexibilidade para um dia..",
                    ["A"],
                ),
                (
                    "flexibility-three-days",
                    "Gere uma ficha de flexibilidade em três dias, A/B/C.",
                    list("ABC"),
                ),
                (
                    "flexibility-negated-goal",
                    "Gere uma ficha de flexibilidade, não quero hipertrofia.",
                    ["A"],
                ),
            ]
        ] + [
            {
                **positive,
                "id": "abc-strength",
                "onboarding": {"training_goal": "Hipertrofia"},
                "request": "Gere um treino de força em três dias, A/B/C.",
                "expected_session_labels": list("ABC"),
                "expected_goal_family": "strength",
            },
            {
                **positive,
                "id": "initial-hypertrophy",
                "onboarding": {"training_goal": "Hipertrofia"},
                "expected_session_labels": ["A"],
                "expected_goal_family": "hypertrophy",
            },
            {
                "id": "ambiguous-goal",
                "onboarding": {},
                "entry_point": "chat",
                "request": "Gere um treino de força e flexibilidade",
                "repetitions": 1,
                "expected": "clarification_without_writer_or_save",
                "maximum_model_http_calls": 0,
            },
            {
                "id": "conflicting-schedule",
                "onboarding": {},
                "entry_point": "chat",
                "request": "Gere flexibilidade em dois dias, fichas A/B/C",
                "repetitions": 1,
                "expected": "clarification_without_writer_or_save",
                "maximum_model_http_calls": 0,
            },
            {
                "id": "retrieval-outage",
                "onboarding": {},
                "repetitions": 1,
                "expected": "technical_unavailability_without_writer_or_save",
                "maximum_model_http_calls": 0,
            },
        ]
    if args.case:
        selected = set(args.case)
        if selected - {case["id"] for case in cases}:
            parser.error("Selected cases require --matrix")
        cases = [case for case in cases if case["id"] in selected]
    if args.repetitions > 1:
        cases = [
            {
                **case,
                "base_case_id": case["id"],
                "id": case["id"] + f"-repeat-{number}",
                "repetition": number,
                "repetitions": args.repetitions,
            }
            for case in cases
            for number in range(1, args.repetitions + 1)
        ]
    plan = {
        "name": name,
        "frozen_at": datetime.now(UTC).isoformat(),
        "scope": "exposed_owner_authorized_technical_check",
        "independent_evaluation": False,
        "professional_review_performed": False,
        "authorization_id": approval["decision_id"],
        "configuration": owner_rag.configuration(),
        "model": {"name": model["name"], "digest": model["digest"]},
        "cases": cases,
        "expected_accepted_proposals": sum(
            case["expected"] == "reviewable_proposal_without_activation" for case in cases
        ),
        "expected_load_mode": "qualitative_unmeasured",
        "synthetic_onboarding_defaults": {
            "training_goal": "Ganhar força",
            "training_experience": "beginner",
            "height_cm": 170,
            "weight_kg": "70.50",
            "has_limitations_or_complaints": False,
            "limitations_or_complaints": None,
            "has_health_conditions": False,
            "health_conditions": None,
            "uses_medications": False,
            "medications": None,
        },
        "timeout_seconds": provider._timeout,
        "deadline_seconds_per_case": 10 * provider._timeout,
        "public_retrieval": "actual_PostgreSQL_BGE_M3_maximum_six_passages",
        "persistence": "synthetic_in_memory_sqlite_only",
        "real_client_records_read": False,
        "clinical_accuracy": "not_evaluated",
        "implementation_sha256": hashes,
    }
    write_json(CACHE_PATH / (name + "-plan.json"), plan)
    outputs, retrieved = [], []
    original_text = provider._text

    def capture(body):
        value = original_text(body)
        outputs.append(
            {"case_id": current_case_id, "stage": CURRENT_STAGE.get(), "structured_answer": value}
        )
        write_json(
            CACHE_PATH / (name + "-progress.json"),
            {
                "plan_name": name,
                "outputs": outputs,
                "captured_at": datetime.now(UTC).isoformat(),
                "independent_evaluation": False,
            },
        )
        return value

    provider._text = capture
    original_call = provider._call

    def measured_call(context, instructions, schema, result_type):
        outputs.append(
            {
                "case_id": current_case_id,
                "stage": CURRENT_STAGE.get(),
                "context_characters": len(json.dumps(context, default=str, ensure_ascii=False)),
                "passage_count": len(context.get("knowledge", {}).get("chunks", [])),
                "session_labels": context.get("training_schedule", {}).get("session_labels", []),
                "focus_scope": (context.get("training_focus") or {}).get("scope"),
                "goal_family": context.get("owner_rag_basis", {}).get("goal_family"),
                "correction_issues": context.get("selection_correction", {}).get(
                    "completeness_issues", context.get("selection_correction", {}).get("issues", [])
                ),
                "provided_rule_ids": [
                    rule["id"]
                    for rule in context.get("owner_approved_research", {}).get("rules", [])
                ],
            }
        )
        try:
            return original_call(context, instructions, schema, result_type)
        except AiProviderError as error:
            outputs.append(
                {"stage": CURRENT_STAGE.get(), "provider_failure_category": error.category}
            )
            write_json(
                CACHE_PATH / (name + "-progress.json"),
                {"plan_name": name, "outputs": outputs, "independent_evaluation": False},
            )
            raise

    provider._call = measured_call

    class PublicKnowledge:
        outage = False

        def retrieve(self, isolated, client_id, query):
            if self.outage:
                return KnowledgeContext.empty("unavailable")
            with SessionLocal() as public:
                public.execute(text("SET TRANSACTION READ ONLY"))
                result = KnowledgeService().retrieve(public, client_id, query)
                ids = {chunk["source_id"] for chunk in result.chunks}
                rows = list(
                    public.scalars(
                        select(KnowledgeSource).where(
                            KnowledgeSource.id.in_(ids), KnowledgeSource.client_id.is_(None)
                        )
                    )
                )
                if {row.id for row in rows} != ids:
                    raise ValueError("public_sources_only")
                for row in rows:
                    if isolated.get(KnowledgeSource, row.id) is None:
                        isolated.add(
                            KnowledgeSource(
                                **{
                                    column.name: getattr(row, column.name)
                                    for column in KnowledgeSource.__table__.columns
                                }
                            )
                        )
                isolated.flush()
            retrieved.append(
                [
                    {"source_id": chunk["source_id"], "chunk_id": chunk["chunk_id"]}
                    for chunk in result.chunks
                ]
            )
            return result

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    results = []
    knowledge = PublicKnowledge()
    for case in plan["cases"]:
        current_case_id = case["id"]
        print(json.dumps({"case_started": current_case_id}), flush=True)
        started = time.monotonic()
        with (
            Session(engine, expire_on_commit=False) as session,
            attempt_budget(provider._timeout) as budget,
        ):
            subject = "owner-rag-diagnostic-" + case["id"]
            client = create_client(session, subject, subject + "@example.test")
            complete_onboarding(
                session,
                subject,
                **{**plan["synthetic_onboarding_defaults"], **case["onboarding"]},
            )
            knowledge.outage = case.get("base_case_id", case["id"]) == "retrieval-outage"
            service = InitialTrainingGenerationService(
                provider=provider, knowledge_service=knowledge
            )
            try:
                if case.get("entry_point") == "chat":
                    chat = TrainingChatService(
                        provider=provider, generation_service=service, knowledge_service=knowledge
                    )
                    if case.get("history_request"):
                        chat.submit_for_subject(
                            session,
                            subject,
                            message=case["history_request"],
                            client_request_id=uuid4(),
                        )
                    request_id = uuid4()
                    state = chat.submit_for_subject(
                        session, subject, message=case["request"], client_request_id=request_id
                    )
                    version = TrainingLifecycleService().find_proposal(session, client_id=client.id)
                    if version is None:
                        answer = state.messages[-1].content
                        reason = (
                            "goal_priority_confirmation_required"
                            if "Qual deve ser o principal" in answer
                            else "training_schedule_confirmation_required"
                            if "Confirme quantas fichas" in answer
                            else "unexpected_chat_answer"
                        )
                        raise PrescriptionRejection("missing_input", reason)
                    counts = dict(budget.http_counts)
                    chat.submit_for_subject(
                        session, subject, message=case["request"], client_request_id=request_id
                    )
                    assert counts == budget.http_counts
                else:
                    version = service.generate_for_subject(
                        session, subject, training_request=case.get("request", "")
                    )
                result = {
                    "case_id": case["id"],
                    "status": "proposal",
                    "activated": version.status == "current",
                    "projection": TrainingLifecycleService()
                    .content(session, version)
                    .model_dump(mode="json"),
                    "citations": version.citations,
                    "knowledge_limitations": version.knowledge_limitations,
                }
                from app.modules.training.completeness import split_training_day

                result["session_labels"] = sorted(
                    {
                        split_training_day(i["exercise_name"])[0]
                        for i in result["projection"]["items"]
                    }
                )
                result["goal_family"] = version.citations[0]["owner_rag"]["goal_family"]
            except PrescriptionRejection as error:
                result = {
                    "case_id": case["id"],
                    "status": "rejected",
                    "category": error.category,
                    "reason": error.reason,
                    "issues": error.issues,
                    "proposal_count": len(
                        list(
                            session.scalars(
                                select(TrainingPlanVersion).where(
                                    TrainingPlanVersion.client_id == client.id
                                )
                            )
                        )
                    ),
                }
            except Exception as error:
                result = {
                    "case_id": case["id"],
                    "status": "technical_failure",
                    "exception_type": type(error).__name__,
                }
            result.update(
                proposal_count=len(
                    list(
                        session.scalars(
                            select(TrainingPlanVersion).where(
                                TrainingPlanVersion.client_id == client.id
                            )
                        )
                    )
                ),
                elapsed_seconds=time.monotonic() - started,
                content_corrections=budget.content_corrections,
                stage_calls=dict(budget.counts),
                actual_model_http_calls=dict(budget.http_counts),
                stage_seconds=dict(budget.stage_seconds),
            )
            results.append(result)
            print(
                json.dumps(
                    {
                        "case_finished": current_case_id,
                        "status": result["status"],
                        "reason": result.get("reason"),
                        "elapsed_seconds": result["elapsed_seconds"],
                        "actual_model_http_calls": result["actual_model_http_calls"],
                    }
                ),
                flush=True,
            )
            write_json(
                CACHE_PATH / (name + "-result.json"),
                {
                    "plan_name": name,
                    "results": results,
                    "outputs": outputs,
                    "retrieved": retrieved,
                    "independent_evaluation": False,
                    "professional_review_performed": False,
                },
            )
    engine.dispose()
    unchanged = all(
        digest((Path(__file__).parents[1] / path).read_bytes()) == value
        for path, value in hashes.items()
    )
    report = {
        "plan_name": name,
        "results": results,
        "outputs": outputs,
        "retrieved": retrieved,
        "implementation_unchanged": unchanged,
        "independent_evaluation": False,
        "professional_review_performed": False,
    }
    write_json(CACHE_PATH / (name + "-result.json"), report)
    print(
        json.dumps(
            {
                "plan": name + "-plan.json",
                "result": name + "-result.json",
                "outcomes": [
                    {"id": r["case_id"], "status": r["status"], "reason": r.get("reason")}
                    for r in results
                ],
                "implementation_unchanged": unchanged,
            }
        )
    )


if __name__ == "__main__":
    main()
