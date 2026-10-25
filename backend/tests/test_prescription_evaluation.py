"""Exposed report mechanics, not the independent held-out evaluation payload."""

from copy import deepcopy

import pytest

from app.modules.training.prescription_evaluation import summarize_evaluation
from app.modules.training.prescription_policy import DIMENSIONS


def rows():
    return [
        {
            "case_id": key,
            "cohort": "synthetic",
            "repetition": 1,
            "expected": outcome,
            "observed": outcome,
            "critical": True,
            "source_correct": True if outcome == "accepted" else None,
            "parameters_correct": True if outcome == "accepted" else None,
            "dimension_grades": {key: True for key in DIMENSIONS},
            "writer_http_calls": 1,
            "elapsed_seconds": 1,
        }
        for key, outcome in (("positive", "accepted"), ("negative", "insufficient_support"))
    ]


def report(runs):
    return summarize_evaluation(
        runs,
        expected_case_ids=["positive", "negative"],
        repeat_count=1,
        maximum_writer_calls=4,
        maximum_runtime_seconds=10,
    )


def test_report_requires_positive_controls_and_never_issues_release():
    valid = report(rows())
    assert valid["technical_criteria_passed"] and not valid["release_authorized"]
    abstain = rows()
    abstain[0]["observed"] = "insufficient_support"
    result = report(abstain)
    assert not result["technical_criteria_passed"]
    assert result["cohorts"]["synthetic"]["false_rejection"] == 1
    separate_negative_cohort = rows()
    separate_negative_cohort[1]["cohort"] = "unsupported_profile"
    assert report(separate_negative_cohort)["technical_criteria_passed"]


def test_critical_acceptance_missing_trace_grade_and_budgets_cannot_pass():
    invalid = rows()
    invalid[1]["observed"] = "accepted"
    result = report(invalid)
    assert not result["technical_criteria_passed"]
    assert result["cohorts"]["synthetic"]["unsupported_acceptance"] == 1
    for field in ("source_correct", "parameters_correct"):
        invalid = rows()
        invalid[0][field] = None
        assert not report(invalid)["technical_criteria_passed"]
    invalid = rows()
    invalid[0]["dimension_grades"] = {}
    assert not report(invalid)["technical_criteria_passed"]
    invalid = rows()
    invalid[0]["writer_http_calls"] = 5
    assert not report(invalid)["budget_passed"]


def test_missing_duplicate_or_changed_repeated_references_reject():
    with pytest.raises(ValueError, match="incomplete"):
        report(rows()[:1])
    with pytest.raises(ValueError, match="duplicate"):
        report([rows()[0], rows()[0]])
    runs = rows()
    second = deepcopy(runs)
    for row in second:
        row["repetition"] = 2
    second[0]["expected"] = "missing_input"
    with pytest.raises(ValueError, match="reference_changed"):
        summarize_evaluation(
            runs + second,
            expected_case_ids=["positive", "negative"],
            repeat_count=2,
            maximum_writer_calls=8,
            maximum_runtime_seconds=10,
        )
