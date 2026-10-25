"""Synthetic Task 47 accounting contracts; no approved clinical/exercise content."""

from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.training.prescription_accounting import (
    AccountingItem,
    AccountingMethod,
    DevelopmentSchedule,
    MuscleAccountingMapping,
    RepetitionCount,
    summarize_development_workload,
)
from app.modules.training.prescription_policy import ExerciseDictionary


def dictionary():
    return ExerciseDictionary(
        version="synthetic-1",
        exercises=[
            {
                "key": "movement",
                "label_pt_br": "Movimento fictício",
                "variations": ["bilateral", "unilateral"],
                "movement": "synthetic",
                "primary_muscles": ["primary", "second-primary"],
            }
        ],
    )


def method(**overrides):
    return AccountingMethod.model_validate(
        {
            "version": "synthetic-1",
            "dictionary_version": "synthetic-1",
            "mappings": [
                {
                    "exercise_key": "movement",
                    "variation_key": "bilateral",
                    "direct_muscles": ["primary", "second-primary"],
                    "indirect_muscles": ["secondary"],
                }
            ],
            **overrides,
        }
    )


def item(**overrides):
    return AccountingItem.model_validate(
        {
            "item_id": "one",
            "session_id": "A",
            "exercise_key": "movement",
            "variation_key": "bilateral",
            "sets": 2,
            "set_role": "working",
            "repetitions": {"minimum": 3, "maximum": 5},
            "repetition_convention": "total",
            "external_load_kg": "10",
            "load_convention": "total_external",
            **overrides,
        }
    )


def summarize(items=None, accounting=None, schedule=None):
    return summarize_development_workload(
        items=[item()] if items is None else items,
        dictionary=dictionary(),
        method=accounting or method(),
        schedule=schedule,
    )


def test_repeated_days_multi_joint_muscles_and_working_sets_are_distinct():
    schedule = DevelopmentSchedule(
        occurrences=[
            {"occurrence_id": "monday", "session_id": "A", "day_index": 0},
            {"occurrence_id": "thursday", "session_id": "A", "day_index": 3},
        ]
    )
    result = summarize(
        [item(), item(item_id="warmup", set_role="warmup", sets=1)], schedule=schedule
    )
    weekly = result["seven_day_totals"]
    assert weekly["working_sets"] == 4 and weekly["warmup_sets"] == 2
    assert weekly["muscles"]["primary"]["direct_sets"] == 4
    assert weekly["muscles"]["second-primary"]["direct_sets"] == 4
    assert weekly["muscles"]["secondary"] == {
        "direct_sets": 0,
        "indirect_sets": 4,
        "weighted_sets": None,
    }
    assert weekly["exercises"][0]["repetitions"] == {"minimum": 12, "maximum": 20}
    assert weekly["exercises"][0]["external_load_volume_kg"] == {
        "minimum": Decimal(120),
        "maximum": Decimal(200),
    }
    assert result["enabled_cohorts"] == []
    assert result["purpose"] == "development_only_accounting"


def test_weekly_context_is_never_inferred_from_a_session_label():
    result = summarize()
    assert result["seven_day_totals"] is None
    assert result["sessions"]["A"]["working_sets"] == 2


def test_explicit_weights_apply_only_to_their_mapped_muscle():
    accounting = method()
    # Deliberately synthetic coefficient, not a real exercise prescription.
    accounting.mappings[0].indirect_weights = {"secondary": Decimal("0.25")}
    result = summarize(accounting=accounting)["sessions"]["A"]["muscles"]
    assert result["secondary"]["weighted_sets"] == Decimal("0.50")
    assert result["primary"]["weighted_sets"] == 2


@pytest.mark.parametrize(
    "field,value",
    [
        ("set_role", "unknown"),
        ("repetition_convention", "per_side"),
        ("repetitions", None),
        ("external_load_kg", None),
        ("load_convention", "per_side"),
    ],
)
def test_unknown_inputs_are_not_zero_or_inferred_multipliers(field, value):
    result = summarize([item(**{field: value})])["sessions"]["A"]
    exercise = result["exercises"][0]
    assert exercise["external_load_volume_kg"] is None
    if field == "set_role":
        assert result["working_sets"] is None and result["muscles"] is None
    if field in ("set_role", "repetition_convention", "repetitions"):
        assert exercise["repetitions"] is None


def test_missing_mapping_is_distinct_from_zero_muscle_work():
    result = summarize(accounting=method(mappings=[]))["sessions"]["A"]
    assert result["working_sets"] == 2
    assert result["muscles"] is None and result["issues"] == ["missing_muscle_mapping"]


def test_missing_one_indirect_weight_does_not_produce_a_partial_weighted_total():
    accounting = method(
        mappings=[
            {
                "exercise_key": "movement",
                "variation_key": "bilateral",
                "direct_muscles": ["primary"],
                "indirect_muscles": ["secondary"],
                "indirect_weights": {"secondary": "0.25"},
            },
            {
                "exercise_key": "movement",
                "variation_key": "unilateral",
                "direct_muscles": ["secondary"],
            },
        ]
    )
    # Missing weighting on a second contribution must invalidate only that
    # weighted muscle total, while retaining separate direct/indirect counts.
    accounting.mappings[1].direct_muscles = ["primary"]
    accounting.mappings[1].indirect_muscles = ["secondary"]
    result = summarize(
        [
            item(),
            item(item_id="two", variation_key="unilateral"),
        ],
        accounting,
    )["sessions"]["A"]["muscles"]["secondary"]
    assert result == {"direct_sets": 0, "indirect_sets": 4, "weighted_sets": None}


def test_variations_keep_their_load_totals_separate():
    result = summarize([item(), item(item_id="two", variation_key="unilateral")])
    assert len(result["sessions"]["A"]["exercises"]) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"exercise_key": "unknown"},
        {"variation_key": "unknown"},
    ],
)
def test_unknown_identity_rejects_development_calculation(change):
    with pytest.raises(ValueError, match="unknown_exercise"):
        summarize([item(**change)])


def test_duplicate_items_and_incomplete_schedules_reject():
    with pytest.raises(ValueError, match="duplicate_accounting_items"):
        summarize([item(), item()])
    with pytest.raises(ValueError, match="coverage_mismatch"):
        summarize(
            schedule=DevelopmentSchedule(
                occurrences=[
                    {"occurrence_id": "one", "session_id": "B", "day_index": 0},
                ]
            )
        )


@pytest.mark.parametrize("day", [-1, 7, True, 1.5])
def test_seven_day_schedule_requires_integer_days(day):
    with pytest.raises(ValidationError):
        DevelopmentSchedule(
            occurrences=[
                {"occurrence_id": "one", "session_id": "A", "day_index": day},
            ]
        )


def test_duplicate_occurrences_reject_without_deduplicating_real_sessions():
    occurrence = {"occurrence_id": "one", "session_id": "A", "day_index": 0}
    with pytest.raises(ValidationError, match="duplicate_schedule"):
        DevelopmentSchedule(occurrences=[occurrence, occurrence])


@pytest.mark.parametrize(
    "change",
    [
        {"indirect_muscles": ["primary"]},
        {"direct_muscles": ["primary", "primary"]},
        {"indirect_weights": {"not-mapped": "0.25"}},
        {"indirect_weights": {"secondary": "NaN"}},
        {"indirect_weights": {"secondary": "1.5"}},
    ],
)
def test_ambiguous_classification_and_invalid_fractional_weights_reject(change):
    value = {
        "exercise_key": "movement",
        "variation_key": "bilateral",
        "direct_muscles": ["primary"],
        "indirect_muscles": ["secondary"],
        **change,
    }
    with pytest.raises(ValidationError):
        MuscleAccountingMapping.model_validate(value)


def test_invalid_repetition_range_and_boolean_sets_reject():
    with pytest.raises(ValidationError):
        RepetitionCount(minimum=5, maximum=3)
    with pytest.raises(ValidationError):
        item(sets=True)


def test_packaged_accounting_has_no_approval_mapping_or_coefficients():
    path = Path(__file__).parents[1] / "app/modules/training/prescription-accounting.json"
    accounting = AccountingMethod.model_validate_json(path.read_text(encoding="utf-8"))
    assert accounting.status == "pending" and not accounting.mappings
    assert not accounting.review_records


def test_revoked_or_mismatched_artifacts_reject_even_in_development():
    with pytest.raises(ValueError, match="version_mismatch"):
        summarize(accounting=method(dictionary_version="other"))
    with pytest.raises(ValueError, match="revoked"):
        summarize(accounting=method(status="revoked"))
