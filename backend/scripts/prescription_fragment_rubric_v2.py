"""New, exposed fragment rubric. Historical v1 cases and scores stay untouched.

This version separates the truth of a described fragment from the next action.
Free explanations remain explicitly ungraded; no clinical reliability is inferred.
"""

from copy import deepcopy
from decimal import Decimal
from typing import Literal

from pydantic import Field, StrictBool

from app.modules.training.prescription_contract import record_hash
from app.modules.training.prescription_policy import Record
from scripts.owner_rule_probe_cases import rule_cases

VERSION = "prescription-fragments-2"
UNITS = sorted(
    {
        case["expected"]["unit"]
        for rule in rule_cases()
        for case in rule["cases"]
        if case["expected"]["unit"] is not None
    }
)


class FragmentResultV2(Record):
    case_id: str
    fragment_valid: StrictBool
    required_action: Literal["proceed", "clarify", "stop", "regress", "abstain"]
    value: Decimal | None
    unit: str | None
    explanation_pt_br: str = Field(max_length=400)


def build_suite():
    contexts, oracle = [], {}
    for rule in deepcopy(rule_cases()):
        cases = []
        for case in rule["cases"]:
            old = case["expected"]
            valid = old["decision"] != "reject"
            action = "proceed" if valid else "abstain"
            if old["decision"] == "clarify":
                action = "clarify"
            if rule["rule_id"] == "BALANCE_RECOVERY" and not valid:
                action = "stop"
            identifier = record_hash(
                {"version": VERSION, "scenario": case["scenario_pt_br"], "id": case["case_id"]}
            )[:16]
            oracle[identifier] = {
                "rule_id": rule["rule_id"],
                "fragment_valid": valid,
                "required_action": action,
                "value": old["value"],
                "unit": old["unit"],
            }
            cases.append(
                {
                    "case_id": identifier,
                    "scenario_pt_br": case["scenario_pt_br"],
                    "output_unit": old["unit"],
                }
            )
        contexts.append({"version": VERSION, "rule_id": rule["rule_id"], "cases": cases})
    return contexts, oracle


def response_schema(context):
    item = FragmentResultV2.model_json_schema()
    ids = [c["case_id"] for c in context["cases"]]
    item["properties"]["case_id"]["enum"] = ids
    units = sorted({c["output_unit"] for c in context["cases"] if c["output_unit"] is not None})
    item["properties"]["unit"] = (
        {"anyOf": [{"type": "string", "enum": units}, {"type": "null"}]}
        if units
        else {"type": "null"}
    )
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["results"],
        "properties": {
            "results": {"type": "array", "minItems": len(ids), "maxItems": len(ids), "items": item}
        },
    }


def score_response(response, context, oracle):
    if set(response) != {"results"}:
        raise ValueError("unknown_response_fields")
    rows = [FragmentResultV2.model_validate(row) for row in response["results"]]
    ids = [r.case_id for r in rows]
    if len(ids) != len(set(ids)) or set(ids) != {c["case_id"] for c in context["cases"]}:
        raise ValueError("missing_duplicate_or_unrequested_case")
    results = []
    for row in rows:
        expected = oracle[row.case_id]
        if row.unit is not None and row.unit not in UNITS:
            raise ValueError("unknown_unit_or_string_null")
        numeric = (row.value is None and expected["value"] is None) or (
            row.value is not None
            and expected["value"] is not None
            and row.value == Decimal(str(expected["value"]))
        )
        results.append(
            {
                "case_id": row.case_id,
                "format_valid": True,
                "fragment_matches": row.fragment_valid == expected["fragment_valid"],
                "action_matches": row.required_action == expected["required_action"],
                "quantity_matches": numeric,
                "unit_matches": row.unit == expected["unit"],
                "explanation": "not_graded",
                "source_support": "not_evaluated_by_fragment_test",
            }
        )
    return results
