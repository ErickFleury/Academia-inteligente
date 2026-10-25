"""Draft contract checks; synthetic approvals are never packaged runtime policies."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.modules.training.prescription_policy import (
    DIMENSIONS,
    ExerciseDictionary,
    HumanReview,
    ParameterBound,
    PolicyCatalog,
    PrescriptionPolicy,
)


def reviews():
    return [
        HumanReview(
            identity="synthetic-" + role,
            role=role,
            competence="Synthetic fixture only",
            conflicts="Synthetic none",
            independent=True,
            reviewed_at=datetime.now(UTC).date(),
            artifact_sha256="a" * 64,
            record_locator="fixture:" + role,
        )
        for role in ("methodological", "professional")
    ]


def policy():
    evidence = {
        "source_id": "synthetic",
        "passage_id": "synthetic-1",
        "artifact_sha256": "a" * 64,
        "passage_sha256": "b" * 64,
        "locator": "fixture:1",
        "appraisal_record": "fixture:2",
        "outcome": "synthetic outcome",
        "certainty": "low",
        "certainty_rationale": "Synthetic demonstration, no scientific claim",
    }
    return {
        "id": "synthetic",
        "version": "test-1",
        "status": "approved",
        "goal_family": "fixture",
        "exact_goal_mappings": ["fixture"],
        "experience_levels": ["none"],
        "population": "synthetic",
        "restriction_interactions": "synthetic none",
        "dictionary_version": "test-1",
        "accounting_method_version": "test-1",
        "accounting_method": "Synthetic set count",
        "review_due_at": datetime.now(UTC).date() + timedelta(days=1),
        "review_records": reviews(),
        "decisions": [
            {
                "id": "synthetic-" + dimension,
                "dimension": dimension,
                "evidence": [evidence],
                "finding": "Synthetic",
                "interpretation": "Synthetic",
                "derivation": "professionally_derived",
                "adoption": "adapt",
                "compatibility_and_currency": "Synthetic",
                "benefits_harms_burdens": "Synthetic",
                "preferences_feasibility_alternatives": "Synthetic",
                "limitations": ["Not real evidence"],
                "conditions": ["Fixture only"],
                "conflict_resolution": "Synthetic no conflict",
            }
            for dimension in sorted(DIMENSIONS)
        ],
    }


def dictionary():
    return {
        "version": "test-1",
        "status": "approved",
        "review_records": reviews(),
        "exercises": [
            {
                "key": "fixture",
                "label_pt_br": "Movimento fictício",
                "aliases": ["Alias"],
                "variations": ["fixture"],
                "movement": "fixture",
                "primary_muscles": ["fixture"],
            }
        ],
    }


def test_packaged_policy_has_no_approval_dictionary_or_enabled_scope():
    path = Path(__file__).parents[1] / "app/modules/training/prescription-policies.json"
    catalog = PolicyCatalog.model_validate_json(path.read_text(encoding="utf-8"))
    assert all(p.status == "pending" and not p.decisions for p in catalog.policies)
    assert catalog.dictionary.status == "pending" and not catalog.dictionary.exercises
    assert not any(p.exact_goal_mappings for p in catalog.policies)


def test_synthetic_complete_conditional_low_certainty_record_roundtrips():
    result = PrescriptionPolicy.model_validate(policy())
    assert PrescriptionPolicy.model_validate_json(result.model_dump_json()) == result
    assert result.decisions[0].evidence[0].certainty == "low"


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda p: p.update(review_records=[]), "independent"),
        (
            lambda p: p["review_records"][1].__setattr__(
                "identity", p["review_records"][0].identity
            ),
            "independent",
        ),
        (lambda p: p.update(review_due_at=datetime.now(UTC).date()), "expired"),
        (lambda p: p["decisions"].pop(), "dimensions"),
        (
            lambda p: p["decisions"][0]["evidence"][0].update(certainty="not_assessed"),
            "not_assessed",
        ),
        (lambda p: p.update(unresolved_decisions=["Unknown input"]), "unresolved"),
    ],
)
def test_missing_review_coverage_and_stale_records_cannot_be_approved(change, reason):
    value = policy()
    change(value)
    with pytest.raises(ValidationError, match=reason):
        PrescriptionPolicy.model_validate(value)


@pytest.mark.parametrize(
    "unit,minimum,maximum,inputs",
    [
        ("kg", 1, 2, []),
        ("percent_1rm", 1, 2, []),
        ("sets", 1.5, 2, []),
        ("seconds", 2, 1, []),
        ("rir", -1, 2, []),
        ("kg", 1, float("inf"), ["baseline"]),
    ],
)
def test_units_ranges_and_baseline_dependencies(unit, minimum, maximum, inputs):
    with pytest.raises(ValidationError):
        ParameterBound(
            parameter="fixture",
            unit=unit,
            minimum=minimum,
            maximum=maximum,
            method="fixture",
            required_input_keys=inputs,
        )


def test_dictionary_alias_ambiguity_and_unapproved_bundle():
    value = dictionary()
    value["exercises"].append({**value["exercises"][0], "key": "other"})
    with pytest.raises(ValidationError, match="ambiguous"):
        ExerciseDictionary.model_validate(value)
    value = dictionary()
    value["status"] = "pending"
    with pytest.raises(ValidationError, match="dictionary_not_approved"):
        PolicyCatalog(version="test-1", policies=[policy()], dictionary=value)


def test_conflicting_goal_mapping_rejected_without_automatic_choice():
    other = policy()
    other["id"] = "other"
    with pytest.raises(ValidationError, match="conflicting_goal"):
        PolicyCatalog(version="test-1", policies=[policy(), other], dictionary=dictionary())


def test_unapproved_input_or_unknown_experience_cannot_be_in_approved_policy():
    value = policy()
    value["experience_levels"] = ["expert"]
    with pytest.raises(ValidationError):
        PrescriptionPolicy.model_validate(value)
    value = policy()
    value["decisions"][0]["required_inputs"] = [
        {
            "key": "adult_eligibility",
            "representation": "boolean",
            "authority": "pending",
            "source_locator": "pending",
            "confirmer_role": "client_owner",
            "timestamps": "confirmation required",
            "validity_rule": "pending",
            "permitted_audience": ["client_owner", "instructor"],
            "conflict_action": "clarify",
            "missing_action": "unsupported",
            "collection_approved": False,
        }
    ]
    with pytest.raises(ValidationError, match="input_authority"):
        PrescriptionPolicy.model_validate(value)
