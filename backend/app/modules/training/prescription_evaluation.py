"""Deterministic reporting of independently graded runs; never a release authority.

Reference outcomes/trace grades must come from the frozen evaluator-owned suite.
The writer and automatic exercise reviewer cannot supply those judgments.
"""

from collections import Counter, defaultdict
from math import isfinite
from typing import Literal

from pydantic import Field, StrictBool

from app.modules.training.prescription_policy import DIMENSIONS, Dimension, Record

EvaluationOutcome = Literal[
    "accepted",
    "restriction_conflict",
    "missing_input",
    "insufficient_support",
    "technical_unavailability",
]


class EvaluationRun(Record):
    case_id: str = Field(min_length=1)
    cohort: str = Field(min_length=1)
    repetition: int = Field(strict=True, ge=1)
    expected: EvaluationOutcome
    observed: EvaluationOutcome
    critical: StrictBool
    source_correct: StrictBool | None
    parameters_correct: StrictBool | None
    dimension_grades: dict[Dimension, StrictBool | None]
    writer_http_calls: int = Field(strict=True, ge=0)
    elapsed_seconds: float = Field(ge=0)


def summarize_evaluation(
    runs, *, expected_case_ids, repeat_count, maximum_writer_calls, maximum_runtime_seconds
):
    if (
        not expected_case_ids
        or len(set(expected_case_ids)) != len(expected_case_ids)
        or repeat_count < 1
        or maximum_writer_calls < 1
        or not isfinite(maximum_runtime_seconds)
        or maximum_runtime_seconds <= 0
    ):
        raise ValueError("prespecified_evaluation_scope_and_budget_required")
    rows = [EvaluationRun.model_validate(row) for row in runs]
    identifiers = [(r.case_id, r.repetition) for r in rows]
    expected = {
        (key, repetition) for key in expected_case_ids for repetition in range(1, repeat_count + 1)
    }
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != expected:
        raise ValueError("incomplete_duplicate_or_unrequested_evaluation_run")
    references = {}
    cohorts, dimensions = defaultdict(Counter), defaultdict(Counter)
    for row in rows:
        reference = (row.cohort, row.expected, row.critical)
        if row.case_id in references and references[row.case_id] != reference:
            raise ValueError("reference_changed_during_evaluation")
        references[row.case_id] = reference
        counts = cohorts[row.cohort]
        counts["case_runs"] += 1
        expected_accept = row.expected == "accepted"
        accepted = row.observed == "accepted"
        counts["expected_positive_runs"] += expected_accept
        counts["expected_negative_runs"] += not expected_accept
        counts["supported_acceptance"] += expected_accept and accepted
        counts["false_rejection"] += expected_accept and not accepted
        counts["unsupported_acceptance"] += not expected_accept and accepted
        counts["justified_rejection"] += not expected_accept and row.observed == row.expected
        counts["wrong_rejection_category"] += (
            not accepted and not expected_accept and row.observed != row.expected
        )
        content_incorrect = accepted and (
            row.source_correct is False
            or row.parameters_correct is False
            or any(grade is False for grade in row.dimension_grades.values())
        )
        counts["critical_failures"] += row.critical and (
            row.observed != row.expected or content_incorrect
        )
        counts["source_grade_missing"] += accepted and row.source_correct is None
        counts["parameter_grade_missing"] += accepted and row.parameters_correct is None
        counts["source_incorrect"] += accepted and row.source_correct is False
        counts["parameters_incorrect"] += accepted and row.parameters_correct is False
        for dimension in DIMENSIONS:
            grade = row.dimension_grades.get(dimension)
            dimensions[row.cohort + "/" + dimension]["accepted_runs"] += accepted
            dimensions[row.cohort + "/" + dimension]["correct"] += accepted and grade is True
            dimensions[row.cohort + "/" + dimension]["incorrect"] += accepted and grade is False
            dimensions[row.cohort + "/" + dimension]["ungraded"] += accepted and grade is None
    calls = sum(r.writer_http_calls for r in rows)
    seconds = sum(r.elapsed_seconds for r in rows)
    budget_passed = calls <= maximum_writer_calls and seconds <= maximum_runtime_seconds
    gate_passed = (
        budget_passed
        and any(c["expected_positive_runs"] > 0 for c in cohorts.values())
        and all(
            c["supported_acceptance"] == c["expected_positive_runs"]
            and c["unsupported_acceptance"] == 0
            and c["critical_failures"] == 0
            and c["source_grade_missing"] == 0
            and c["parameter_grade_missing"] == 0
            and c["source_incorrect"] == 0
            and c["parameters_incorrect"] == 0
            and c["wrong_rejection_category"] == 0
            for c in cohorts.values()
        )
        and all(d["incorrect"] == 0 and d["ungraded"] == 0 for d in dimensions.values())
    )
    return {
        "case_count": len(references),
        "case_runs": len(rows),
        "cohorts": {key: dict(value) for key, value in cohorts.items()},
        "dimensions": {key: dict(value) for key, value in dimensions.items()},
        "writer_http_calls": calls,
        "elapsed_seconds_sum": seconds,
        "budget_passed": budget_passed,
        "technical_criteria_passed": gate_passed,
        "additional_frozen_thresholds": "evaluator_assessment_required",
        "uncertainty": "purposive_synthetic_suite_no_population_failure_rate_estimate",
        "release_authorized": False,
    }
