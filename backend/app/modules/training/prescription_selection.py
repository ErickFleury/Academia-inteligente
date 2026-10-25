"""Retain the mandatory automatic exercise review after evidence qualification."""

import os

from pydantic import BaseModel, ValidationError

from app.integrations.ai import AiProviderError
from app.integrations.ai_diagnostics import record_retry
from app.modules.training.completeness import IncompleteTrainingPlanError
from app.modules.training.prescription_budget import CURRENT_BUDGET, attempt_budget
from app.modules.training.prescription_contract import (
    PrescriptionRejection,
    TypedPrescription,
    record_hash,
)
from app.modules.training.prescription_validation import validate_development_prescription
from app.modules.training.selection import RedundantTrainingExerciseError, request_selected_training


class ReviewedProjection(BaseModel):
    plan: dict
    result: dict
    citations: list[dict]


def retry_provider(operation, stage="writer"):
    for attempt in range(2):
        try:
            budget = CURRENT_BUDGET.get()
            return budget.call(stage, operation) if budget is not None else operation()
        except AiProviderError as error:
            record_retry(error.category, not attempt and error.retryable)
            if attempt or not error.retryable:
                raise


def prepare_with_selection(runtime, session, client_id, revision, write, prepare, require_complete):
    timeout = float(
        os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")
        if os.getenv("AI_PROVIDER") == "ollama"
        else os.getenv("AI_TIMEOUT_SECONDS", "10")
    )
    with attempt_budget(timeout):
        return _prepare_with_selection(
            runtime, session, client_id, revision, write, prepare, require_complete
        )


def _prepare_with_selection(
    runtime, session, client_id, revision, write, prepare, require_complete
):
    initial = runtime._context(session, client_id)
    initial.pop("candidate", None)
    initial.update(client_id=client_id, current_revision=revision)
    preflight = validate_development_prescription(candidate=None, **initial)
    reviewer = getattr(runtime, "reviewer", None)
    if reviewer is None:
        raise PrescriptionRejection("technical_unavailability", "exercise_review_unavailable")
    context = {
        "training_request": runtime.request,
        "knowledge": preflight["evidence"].as_context(),
        "relevant_onboarding": {
            key: fact.value
            for key, fact in initial["snapshot"].facts.items()
            if fact.source == "onboarding"
        },
    }

    def operation(selected_context):
        def corrected(writer_context):
            return write({**writer_context, **selected_context})

        try:
            result = prepare(
                session, client_id, revision, corrected, require_complete=require_complete
            )
        except ValidationError as error:
            raise PrescriptionRejection(
                "insufficient_support",
                "invalid_typed_candidate",
                issues=[
                    {"field": ".".join(map(str, e["loc"])), "reason": e["type"]}
                    for e in error.errors(include_input=False, include_url=False)
                ],
            ) from None
        except AiProviderError as error:
            if error.category != "malformed_structured_output":
                raise
            raise PrescriptionRejection(
                "insufficient_support",
                "invalid_typed_candidate",
                issues=[{"field": "candidate", "reason": "malformed_structured_output"}],
            ) from None
        candidate = TypedPrescription.model_validate(result["typed_content"])
        context["prescription_modes"] = sorted(
            {item.mode for session in candidate.sessions for item in session.items}
        )
        context["approved_exercises"] = [
            {
                "key": e.key,
                "label_pt_br": e.label_pt_br,
                "movement": e.movement,
                "variations": e.variations,
            }
            for e in initial["catalog"].dictionary.exercises
        ]
        context["training_focus"] = getattr(runtime, "requested_focus", {})
        context["training_schedule"] = {"session_labels": [s.label for s in candidate.sessions]}
        return ReviewedProjection(
            plan=result["projection"], result=result, citations=result["citations"]
        )

    try:
        response = request_selected_training(
            operation,
            context,
            assess=lambda review: retry_provider(lambda: reviewer(review), stage="review"),
            repair_domain_errors=True,
        )
    except (IncompleteTrainingPlanError, RedundantTrainingExerciseError) as error:
        raise PrescriptionRejection(
            "insufficient_support", "exercise_review_rejected", issues=getattr(error, "issues", [])
        ) from None
    if record_hash(response.plan) != response.result["rendered_content_sha256"]:
        raise PrescriptionRejection("insufficient_support", "review_changed_projection")
    # The automatic reviewer cannot authorize revoked support or replace the gate.
    fresh = runtime._context(session, client_id)
    fresh.pop("candidate", None)
    fresh.update(client_id=client_id, current_revision=revision)
    return validate_development_prescription(
        candidate=TypedPrescription.model_validate(response.result["typed_content"]),
        **fresh,
    )
