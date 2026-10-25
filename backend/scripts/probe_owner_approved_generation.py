"""Bounded local generation with owner-approved research and read-only public retrieval.

Run with: docker compose run --rm -T --no-deps backend
  python scripts/probe_owner_approved_generation.py
No real-client reads, lifecycle writes, professional signatures or rollout changes.
"""

import json
import os
import time
from datetime import UTC, datetime
from urllib.request import urlopen
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import text

from app.database import SessionLocal
from app.integrations import ai
from app.modules.knowledge.acquisition import CACHE_PATH, write_json
from app.modules.knowledge.service import KnowledgeCitationError, KnowledgeService
from app.modules.training.completeness import (
    IncompleteTrainingPlanError,
    normalize_training_resources,
    training_review_context,
    validate_assessment,
    validate_exercise_names,
    validate_requested_sessions,
)
from app.modules.training.evidence_review import current_artifacts
from app.modules.training.knowledge_query import retrieve_training_knowledge
from app.modules.training.owner_approval import (
    approved_research_context,
    artifact_owner_approval,
    load_owner_approval,
)
from app.modules.training.prescription_contract import record_hash
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.selection import (
    RedundantTrainingExerciseError,
    validate_exercise_selection,
)

PREFIX = "owner-approved-generation-2026-10-24"
SCENARIOS = [
    ("hypertrophy", "hipertrofia", "beginner"),
    ("strength", "força", "intermediate"),
]


def main():
    if os.getenv("AI_PROVIDER") != "ollama":
        raise SystemExit("This development probe permits only the configured local Ollama provider")
    provider = ai.training_generation_provider_from_environment()
    with urlopen(provider._config.base_url.rstrip("/") + "/api/tags", timeout=10) as response:
        tags = json.load(response)
    model = next(m for m in tags["models"] if m["name"] == provider._config.model)
    registry, artifacts = load_owner_approval(), current_artifacts()
    if registry is None:
        raise SystemExit("Current owner approval registry is required")
    contexts = []
    for family, goal, experience in SCENARIOS:
        onboarding = {
            "training_goal": goal,
            "training_experience": experience,
            "height_cm": 175,
            "weight_kg": 75,
            "has_limitations_or_complaints": False,
            "limitations_or_complaints": None,
            "uses_medications": False,
            "medications": None,
            "has_health_conditions": False,
            "health_conditions": None,
        }
        request = (
            f"Gere uma única ficha de corpo inteiro para {goal}, sem superset ou circuito. "
            "Use exercícios livres, sem máquinas. Não invente dias da semana ou cargas em kg."
        )
        # The only database access is public-corpus retrieval. This random ID
        # belongs to no actual student; no student/account table is queried.
        with SessionLocal() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            evidence = retrieve_training_knowledge(
                KnowledgeService(), session, uuid4(), request, onboarding
            )
        if not evidence.chunks or any(
            artifact_owner_approval(artifacts["source:" + c["source_id"]], registry) is None
            for c in evidence.chunks
        ):
            raise SystemExit("Current owner-approved eligible retrieval is required")
        context = {
            "training_request": request,
            "training_focus": {"scope": "full_body", "muscle_groups": [], "goal": goal},
            "training_schedule": {"session_labels": []},
            "active_equipment_models": [],
            "completed_onboarding": onboarding,
            "owner_approved_research": approved_research_context(family),
            "knowledge": evidence.as_context(),
            "proposal_rules": {
                "must_not_approve_or_activate": True,
                "synthetic_development_only": True,
                "professional_review_performed": False,
                "qualified_operational_policy": False,
            },
        }
        contexts.append((family, context, evidence))
    plan = {
        "purpose": "owner_approved_research_development_not_independent_evaluation",
        "frozen_at": datetime.now(UTC).isoformat(),
        "owner_decision_id": registry.decision_id,
        "registry_sha256": record_hash(registry),
        "provider": "ollama",
        "model": model["name"],
        "model_digest": model["digest"],
        "maximum_model_calls": 4,
        "maximum_generation_calls_per_case": 1,
        "maximum_assessment_calls_per_case": 1,
        "timeout_seconds_per_call": provider._timeout,
        "retries": 0,
        "cases": [{"goal_family": f, "context_sha256": record_hash(c)} for f, c, _ in contexts],
        "checks": ["schema", "exercise_names", "duplicates", "citations", "automatic_review"],
        "dose_policy_validation": "not_available_incomplete_executable_contracts",
        "no_student_lifecycle_writes": True,
        "release_authorized_by_probe": False,
    }
    write_json(CACHE_PATH / (PREFIX + "-plan.json"), plan)
    calls = []

    def observed_transport(request, **kwargs):
        if len(calls) >= plan["maximum_model_calls"]:
            raise RuntimeError("Frozen local model call budget exceeded")
        calls.append({"request_sha256": record_hash(json.loads(request.data))})
        return urlopen(request, **kwargs)

    ai.urlopen = observed_transport
    results = []
    for family, context, evidence in contexts:
        started = time.monotonic()
        result = {
            "goal_family": family,
            "retrieved_passages": [
                {"source_id": c["source_id"], "chunk_id": c["chunk_id"]} for c in evidence.chunks
            ],
            "owner_approved_rule_ids": [
                r["id"] for r in context["owner_approved_research"]["rules"]
            ],
            "professional_review_performed": False,
            "qualified_prescription": False,
        }
        try:
            response = provider.generate_training(context)
            candidate = normalize_training_resources(
                TrainingPlanVersionInput.model_validate(response.plan)
            )
            validate_exercise_names(candidate)
            validate_exercise_selection(candidate)
            validate_requested_sessions(candidate, context)
            citations = evidence.resolve_citations(response.citations, response.knowledge_status)
            if citations.knowledge_status != "supported" or not citations.citations:
                raise KnowledgeCitationError("applicable_citations_required")
            review_context = training_review_context(candidate, context)
            assessment = provider.assess_training(review_context)
            result["automatic_assessment"] = assessment.model_dump(mode="json")
            validate_assessment(assessment, review_context)
            if any(item.equipment_model_id is not None for item in candidate.items):
                raise ValueError("unavailable_machine_reference")
            result.update(
                status="generation_and_automatic_checks_passed",
                development_plan=candidate.model_dump(mode="json"),
                citations=citations.citations,
                knowledge_limitations=citations.knowledge_limitations,
            )
        except ai.AiProviderError as error:
            result.update(status="controlled_provider_failure", reason=error.category)
        except IncompleteTrainingPlanError as error:
            result.update(status="rejected_by_automatic_checks", issues=error.issues)
        except (
            ValidationError,
            KnowledgeCitationError,
            RedundantTrainingExerciseError,
            ValueError,
        ) as error:
            result.update(status="rejected_by_automatic_checks", error_type=type(error).__name__)
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        results.append(result)
        # Preserve every attempt even if a later call is interrupted.
        write_json(
            CACHE_PATH / (PREFIX + "-result.json"),
            {
                "plan": plan,
                "results": results,
                "actual_model_calls": len(calls),
                "requests": calls,
                "saved_student_plans": 0,
                "activated_student_plans": 0,
                "independent_evaluation_performed": False,
                "limitations": [
                    "Only two implementer-exposed synthetic development cases, one run each.",
                    "Research rules have owner approval, without professional appraisal.",
                    "Automatic checks do not validate numeric research-rule compliance.",
                    "Incomplete executable contracts still block typed qualification.",
                ],
            },
        )
        print(
            json.dumps({key: result[key] for key in ("goal_family", "status", "elapsed_seconds")}),
            flush=True,
        )


if __name__ == "__main__":
    main()
