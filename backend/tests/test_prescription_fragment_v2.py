"""Frozen separate fragment/action oracles and the observed representation failures."""

import pytest

from scripts.owner_rule_probe_cases import rule_cases
from scripts.prescription_fragment_rubric_v2 import build_suite, response_schema, score_response


def test_all_37_rules_have_74_cases_without_leaking_or_rewriting_the_old_key():
    original = rule_cases()
    contexts, oracle = build_suite()
    assert len(contexts) == 37 and len(oracle) == 74
    assert rule_cases() == original
    assert all("expected" not in str(context) for context in contexts)
    for rule in ("SPORT_SPECIFICITY", "RESTRICTIONS"):
        application = next(
            row for row in oracle.values() if row["rule_id"] == rule and row["fragment_valid"]
        )
        assert application["required_action"] == "clarify"


@pytest.mark.parametrize(
    "rule_id, null_index",
    [
        ("AEROBIC_DOSE", 0),
        ("AEROBIC_START_PROGRESS", 0),
        ("FUNCTION_STRUCTURE", 0),
        ("POWER_REPETITIONS", 0),
        ("SELECT_RESISTANCE", 0),
        ("SELECT_RESISTANCE", 1),
        ("SOURCE_ENDURANCE_CIRCUIT", 0),
        ("STRENGTH_DOSE", 0),
    ],
)
def test_observed_string_null_defects_never_match_json_null(rule_id, null_index):
    contexts, oracle = build_suite()
    context = next(c for c in contexts if c["rule_id"] == rule_id)
    rows = [
        {
            "case_id": c["case_id"],
            **{k: v for k, v in oracle[c["case_id"]].items() if k != "rule_id"},
            "explanation_pt_br": "Descrição sintética.",
        }
        for c in context["cases"]
    ]
    row = [r for r in rows if r["unit"] is None][null_index]
    row["unit"] = "null"
    with pytest.raises(ValueError, match="string_null"):
        score_response({"results": rows}, context, oracle)


def test_translated_unit_and_duplicate_ids_are_rejected_separately_from_quantities():
    contexts, oracle = build_suite()
    context = next(c for c in contexts if c["rule_id"] == "ENDURANCE_SETS")
    rows = [
        {
            "case_id": c["case_id"],
            **{k: v for k, v in oracle[c["case_id"]].items() if k != "rule_id"},
            "explanation_pt_br": "Descrição sintética.",
        }
        for c in context["cases"]
    ]
    row = next(r for r in rows if r["unit"] == "repetitions")
    row["unit"] = "repetições"
    with pytest.raises(ValueError, match="unknown_unit"):
        score_response({"results": rows}, context, oracle)
    row["unit"] = "repetitions"
    scores = score_response({"results": rows}, context, oracle)
    assert all(s["quantity_matches"] and s["action_matches"] for s in scores)
    assert all(s["explanation"] == "not_graded" for s in scores)
    with pytest.raises(ValueError, match="duplicate"):
        score_response({"results": [rows[0], rows[0]]}, context, oracle)
    schema = response_schema(context)
    assert schema["properties"]["results"]["maxItems"] == 2
