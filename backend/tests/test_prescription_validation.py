"""Isolated positive/negative rule tests; no held-out or real clinical approvals."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from prescription_fixtures import enable_weekly_fixture, valid_case
from pydantic import ValidationError

from app.modules.knowledge.service import KnowledgeContext
from app.modules.training.prescription_contract import (
    PrescriptionRejection,
    RestrictionConflict,
    TypedPrescription,
    record_hash,
)
from app.modules.training.prescription_validation import validate_development_prescription


def test_complete_supported_synthetic_proposal_passes_despite_health_disclosures():
    case = valid_case()
    result = validate_development_prescription(**case)
    assert result["prescription_eligibility"] == "eligible"
    assert len(result["trace"]) == 7
    assert result["scope"] == "session_sheet"
    assert result["totals"]["seven_day_totals"] is None
    row = result["projection"]["items"][0]
    assert row["sets"] == 2 and row["repetitions"] == "3–5"
    assert row["load_guidance"] == "2–3 RIR" and row["rest_seconds"] == 30
    assert result["rendered_content_sha256"] == record_hash(result["projection"])
    assert case["snapshot"].facts["uses_medications"].value is True
    assert case["snapshot"].facts["has_limitations_or_complaints"].value is True


@pytest.mark.parametrize(
    "change,reason",
    [
        (lambda c: c.update(evidence=KnowledgeContext.empty()), "evidence"),
        (lambda c: c.update(evidence=KnowledgeContext.empty("outdated")), "expired"),
        (lambda c: c.update(client_id=uuid4()), "owner"),
        (lambda c: c["candidate"].sessions[0].items[0].decision_rules.pop("rest"), "dimension"),
        (lambda c: c["candidate"].sessions[0].items[0].__setattr__("sets", 10), "outside_policy"),
        (
            lambda c: c["candidate"].sessions[0].items[0].__setattr__("exercise_key", "invented"),
            "unknown_exercise",
        ),
        (
            lambda c: c["candidate"].sessions[0].items[0].decision_rules.update(volume="invented"),
            "decision_rule",
        ),
        (lambda c: c["source_catalog"]["sources"][0].update(license="CC-BY-NC-4.0"), "source"),
        (lambda c: c["source_catalog"]["sources"][0].update(review_status="excluded"), "source"),
        (
            lambda c: c["source_catalog"]["sources"][0]["provenance"].update(
                artifact_sha256="f" * 64
            ),
            "source",
        ),
        (
            lambda c: c["source_catalog"]["sources"][0]["chunks"][0].update(
                content="Altered evidence"
            ),
            "source",
        ),
        (lambda c: c["source_catalog"]["sources"][0].update(client_id=str(uuid4())), "source"),
        (lambda c: c["candidate"].__setattr__("policy_version", "old"), "version"),
        (lambda c: c["candidate"].__setattr__("expected_revision", 2), "stale_revision"),
    ],
)
def test_mandatory_checks_cannot_be_overridden_by_supported_citations(change, reason):
    case = valid_case()
    change(case)
    with pytest.raises(PrescriptionRejection, match=reason):
        validate_development_prescription(**case)


def test_technical_outage_is_distinct_from_missing_support():
    case = valid_case()
    case["evidence"] = KnowledgeContext.empty("unavailable")
    with pytest.raises(PrescriptionRejection) as failure:
        validate_development_prescription(**case)
    assert failure.value.category == "technical_unavailability"


@pytest.mark.parametrize(
    "change",
    [
        lambda fact: fact.__setattr__("confirmed_at", None),
        lambda fact: fact.__setattr__("conflict", True),
        lambda fact: fact.__setattr__("valid_until", datetime.now(UTC) - timedelta(seconds=1)),
        lambda fact: fact.__setattr__("source", "request"),
    ],
)
def test_stale_unconfirmed_conflicting_and_wrong_authority_facts_reject(change):
    case = valid_case()
    change(case["snapshot"].facts["training_goal"])
    case["candidate"].input_snapshot_sha256 = record_hash(case["snapshot"])
    with pytest.raises(PrescriptionRejection) as failure:
        validate_development_prescription(**case)
    assert failure.value.category == "missing_input"


def test_documented_conflict_requires_a_specific_reviewed_restriction_rule():
    case = valid_case()
    case["execution"].documented_conflicts = [
        RestrictionConflict(
            **{
                "fact_key": "uses_medications",
                "expected_value": True,
                "decision_id": "synthetic-restrictions",
            }
        )
    ]
    # Construct through validation rather than relying on assignment coercion.
    case["execution"] = type(case["execution"]).model_validate(case["execution"].model_dump())
    with pytest.raises(PrescriptionRejection) as failure:
        validate_development_prescription(**case)
    assert failure.value.category == "restriction_conflict"


def test_writer_cannot_add_alternate_prescriptive_prose_or_untyped_dose():
    raw = valid_case()["candidate"].model_dump(mode="json")
    raw["sessions"][0]["items"][0]["notes"] = "Do ten extra sets"
    with pytest.raises(ValidationError):
        TypedPrescription.model_validate(raw)
    raw["sessions"][0]["items"][0].pop("notes")
    raw["sessions"][0]["items"][0]["dose"] = {"kind": "repetitions", "minimum": True, "maximum": 5}
    with pytest.raises(ValidationError):
        TypedPrescription.model_validate(raw)


def test_unknown_progression_and_note_instructions_reject():
    for field in ("progression", "note"):
        case = valid_case()
        item = case["candidate"].sessions[0].items[0]
        if field == "progression":
            item.progression.amount = Decimal(99)
        else:
            item.note_instruction_keys = ["invented-dose"]
        with pytest.raises(PrescriptionRejection):
            validate_development_prescription(**case)


def test_plan_revision_requires_actual_schedule_and_checks_complete_week_totals():
    case = valid_case()
    case["candidate"].scope = "plan_revision"
    with pytest.raises(PrescriptionRejection, match="weekly_schedule_missing"):
        validate_development_prescription(**case)
    enable_weekly_fixture(case)
    result = validate_development_prescription(**case)
    assert result["totals"]["seven_day_totals"]["working_sets"] == 4
    case["candidate"].sessions[0].items[0].sets = 3
    with pytest.raises(PrescriptionRejection, match="outside_policy"):
        validate_development_prescription(**case)


def test_same_content_with_changed_confirmed_inputs_cannot_replay_old_snapshot():
    case = valid_case()
    case["snapshot"].facts["uses_medications"].value = False
    with pytest.raises(PrescriptionRejection, match="input_snapshot_changed"):
        validate_development_prescription(**case)


def test_unused_alternative_rule_does_not_require_irrelevant_extra_passages():
    case = valid_case()
    extra = case["catalog"].policies[0].decisions[0].model_copy(deep=True)
    extra.id = "unused-alternative"
    extra.evidence[0].passage_id = "not-retrieved-alternative"
    case["catalog"].policies[0].decisions.append(extra)
    rule = case["execution"].rules[0].model_copy(deep=True)
    rule.decision_id = extra.id
    case["execution"].rules.append(rule)
    assert validate_development_prescription(**case)["prescription_eligibility"] == "eligible"


@pytest.mark.parametrize(
    "change",
    [
        lambda source: source.update(reviewed_at="not-a-date"),
        lambda source: source.update(commercial_use_allowed="false"),
        lambda source: source.update(chunks=None),
    ],
)
def test_malformed_source_permissions_and_extraction_are_controlled_rejections(change):
    case = valid_case()
    change(case["source_catalog"]["sources"][0])
    with pytest.raises(PrescriptionRejection):
        validate_development_prescription(**case)


def test_seven_context_passages_cannot_bypass_the_six_passage_limit():
    case = valid_case()
    original = case["evidence"].chunks[0]
    case["evidence"] = KnowledgeContext(
        tuple({**original, "chunk_id": f"passage-{index}"} for index in range(7)), "supported", ""
    )
    with pytest.raises(PrescriptionRejection, match="excessive_evidence"):
        validate_development_prescription(**case)


def test_onboarding_cannot_be_claimed_as_the_source_of_an_unavailable_age_fact():
    case = valid_case()
    raw = case["snapshot"].model_dump(mode="json")
    raw["facts"]["adult_eligibility"] = {**raw["facts"]["uses_medications"], "value": True}
    with pytest.raises(ValidationError, match="not_available_in_onboarding"):
        type(case["snapshot"]).model_validate(raw)
