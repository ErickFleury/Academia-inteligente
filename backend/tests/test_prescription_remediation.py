"""Regression of observed defects against domain code, using exposed synthetic inputs."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from prescription_fixtures import valid_case
from pydantic import ValidationError

from app.modules.training import prescription_authorization as authorization
from app.modules.training.evidence_review import prescription_bundle_hash
from app.modules.training.owner_approval import OwnerApprovalRegistry
from app.modules.training.prescription_budget import CURRENT_BUDGET, AttemptBudget, attempt_budget
from app.modules.training.prescription_contract import (
    DevelopmentExecutionContract,
    NumericRange,
    PrescriptionRejection,
    TypedPrescription,
    record_hash,
)
from app.modules.training.prescription_development import build_prescription_writer_context
from app.modules.training.prescription_math import (
    aerobic_equivalent,
    hold_duration,
    percentage_increase,
    percentage_load,
    round_load,
    scheduled_duration,
)
from app.modules.training.prescription_policy import PolicyCatalog
from app.modules.training.prescription_validation import validate_development_prescription
from app.modules.training.prescription_writer_schema import prescription_writer_schema


def test_authoritative_calculated_load_rejects_the_observed_501_error():
    case = valid_case()
    fact = case["snapshot"].facts["progression_observed"].model_copy(deep=True)
    fact.value = Decimal(50)
    fact.measurement_method = "observed_working_load"
    fact.measurement_unit = "kg"
    fact.exercise_key = fact.variation_key = "fixture"
    fact.measurement_convention = "total_external"
    case["snapshot"].facts["baseline_capacity"] = fact
    raw = case["execution"].model_dump(mode="json")
    raw["input_requirements"].append(
        {"key": "baseline_capacity", "source": "request", "collection_approved": True}
    )
    raw["calculations"] = {
        "load-step": {
            "operation": "percentage_increase",
            "baseline_fact": "baseline_capacity",
            "exercise_key": "fixture",
            "variation_key": "fixture",
            "percent": "2",
            "load_convention": "total_external",
            "rounding": "exact",
        }
    }
    next(r for r in raw["rules"] if r["decision_id"] == "synthetic-intensity")["bounds"][
        "external_load_kg"
    ] = {"minimum": 1, "maximum": 100}
    case["execution"] = DevelopmentExecutionContract.model_validate(raw)
    candidate = case["candidate"].model_dump(mode="json")
    candidate["input_snapshot_sha256"] = record_hash(case["snapshot"])
    candidate["sessions"][0]["items"][0]["calculated_load"] = {
        "calculation_id": "load-step",
        "claimed_kg": "50.1",
    }
    case["candidate"] = TypedPrescription.model_validate(candidate)
    with pytest.raises(PrescriptionRejection, match="calculated_quantity_mismatch") as rejected:
        validate(case)
    assert rejected.value.issues[0]["expected"] == "51"
    case["candidate"].sessions[0].items[0].calculated_load.claimed_kg = Decimal(51)
    result = validate(case)
    assert result["projection"]["items"][0]["load_guidance"] == "51 kg; 2–3 RIR"
    assert result["totals"]["sessions"]["session-a"]["exercises"][0]["external_load_volume_kg"] == {
        "minimum": "306",
        "maximum": "510",
    }


def test_paired_rest_survives_projection_without_per_exercise_rest():
    case = valid_case()
    candidate = case["candidate"].model_dump(mode="json")
    candidate["schema_version"] = 2
    first = candidate["sessions"][0]["items"][0]
    first["rest_seconds"] = None
    first["group"] = {
        "group_id": "pair-1",
        "kind": "pair",
        "rounds": 2,
        "order": 1,
        "rest": {"kind": "after_pair", "seconds": 120},
    }
    second = deepcopy(first)
    second.update(item_id="item-2", exercise_key="second")
    second["group"]["order"] = 2
    candidate["sessions"][0]["items"].append(second)
    catalog = case["catalog"].model_dump(mode="json")
    exercise = deepcopy(catalog["dictionary"]["exercises"][0])
    exercise.update(key="second", label_pt_br="Outro movimento de teste", aliases=[])
    catalog["dictionary"]["exercises"].append(exercise)
    case["catalog"] = PolicyCatalog.model_validate(catalog)
    accounting = case["accounting"].model_dump(mode="json")
    accounting["mappings"].append(
        {"exercise_key": "second", "variation_key": "fixture", "direct_muscles": ["fixture"]}
    )
    from app.modules.training.prescription_accounting import AccountingMethod

    case["accounting"] = AccountingMethod.model_validate(accounting)
    execution = case["execution"].model_dump(mode="json")
    execution["schema_version"] = 2
    next(r for r in execution["rules"] if r["decision_id"] == "synthetic-selection")[
        "allowed_exercises"
    ]["second"] = ["fixture"]
    next(r for r in execution["rules"] if r["decision_id"] == "synthetic-rest")["bounds"][
        "after_pair.seconds"
    ] = {"minimum": 120, "maximum": 120}
    case["execution"] = DevelopmentExecutionContract.model_validate(execution)
    case["candidate"] = TypedPrescription.model_validate(candidate)
    result = validate(case)
    assert all(
        i["rest_seconds"] is None and i["dose_details"]["group"]["rest"]["kind"] == "after_pair"
        for i in result["projection"]["items"]
    )
    assert result["totals"]["sessions"]["session-a"]["working_sets"] == 4


def test_typed_rejection_repairs_once_and_preserves_backend_feedback():
    from training_fixtures import AcceptingTrainingReviewer

    from app.integrations.ai import AiTrainingGenerationResponse
    from app.modules.training.selection import request_selected_training

    calls = []

    def writer(context):
        calls.append(context)
        if len(calls) == 1:
            raise PrescriptionRejection(
                "insufficient_support",
                "parameter_outside_policy",
                issues=[{"field": "rest_seconds", "reason": "parameter_outside_policy"}],
            )
        return AiTrainingGenerationResponse(
            plan={
                "name": "Teste",
                "objective": "Teste",
                "items": [
                    {
                        "exercise_name": "Agachamento",
                        "sets": 2,
                        "repetitions": "3",
                        "load_guidance": "Confortável",
                        "rest_seconds": 30,
                    }
                ],
            }
        )

    result = request_selected_training(
        writer, {}, assess=AcceptingTrainingReviewer().assess_training, repair_domain_errors=True
    )
    assert result.plan["items"] and len(calls) == 2
    assert calls[1]["selection_correction"]["issues"][0]["field"] == "rest_seconds"


def test_missing_input_is_not_repaired_by_inventing_facts():
    from app.modules.training.selection import request_selected_training

    calls = []

    def writer(context):
        calls.append(context)
        raise PrescriptionRejection("missing_input", "measured_baseline_missing")

    with pytest.raises(PrescriptionRejection, match="measured_baseline_missing"):
        request_selected_training(writer, {}, assess=lambda _: None, repair_domain_errors=True)
    assert len(calls) == 1


def validate(case):
    return validate_development_prescription(**case)


def test_observed_numeric_failures_have_backend_oracles():
    assert percentage_increase(50, 2) == Decimal("51")
    assert percentage_load(100, 50) == Decimal("50")
    assert scheduled_duration({"one": 10, "two": 10, "three": 10}, "one", 5) == 35
    assert hold_duration(2, 30, 2) == 120
    result = aerobic_equivalent(
        [
            {"occurrence_id": "a", "start_minutes": 0, "end_minutes": 30, "intensity": "moderate"},
            {"occurrence_id": "b", "start_minutes": 0, "end_minutes": 15, "intensity": "vigorous"},
            {
                "occurrence_id": "b",
                "start_minutes": 15,
                "end_minutes": 25,
                "intensity": "unclassified",
            },
        ],
        2,
    )
    assert result == {
        "moderate_equivalent_minutes": Decimal(60),
        "unclassified_minutes": Decimal(10),
    }
    assert round_load("51", "2.5", "floor") == Decimal(50)
    with pytest.raises(ValueError, match="rounding_policy"):
        round_load(51, 0, "nearest")


@pytest.mark.parametrize("value", [None, True, "NaN", "Infinity", -1])
def test_calculation_never_invents_missing_or_nonfinite_quantities(value):
    with pytest.raises(ValueError):
        percentage_load(value, 50)


def test_aerobic_overlap_is_rejected():
    with pytest.raises(ValueError, match="overlapping"):
        aerobic_equivalent(
            [
                {
                    "occurrence_id": "a",
                    "start_minutes": 0,
                    "end_minutes": 30,
                    "intensity": "moderate",
                },
                {
                    "occurrence_id": "a",
                    "start_minutes": 15,
                    "end_minutes": 30,
                    "intensity": "vigorous",
                },
            ],
            2,
        )


@pytest.mark.parametrize(
    "bound,accepted,rejected",
    [
        ({"minimum": 15, "maximum": None, "minimum_inclusive": False}, 16, 15),
        ({"minimum": None, "maximum": 90, "maximum_inclusive": False}, 89, 90),
        ({"minimum": 180, "maximum": 300}, 180, 160),
        ({"minimum": 0, "maximum": 60, "maximum_inclusive": False}, 59, 60),
    ],
)
def test_explicit_open_and_exclusive_bounds(bound, accepted, rejected):
    value = NumericRange.model_validate(bound)
    assert value.contains(accepted)
    assert not value.contains(rejected)
    assert not value.contains(None)
    assert not value.contains(True)


def test_open_endpoint_flags_and_unknown_rounding_are_not_guessed():
    from app.modules.training.prescription_contract import CalculationDefinition

    with pytest.raises(ValidationError, match="open_endpoint"):
        NumericRange(minimum=15, maximum=None, maximum_inclusive=True)
    with pytest.raises(ValidationError, match="rounding_policy"):
        CalculationDefinition(
            operation="percentage_increase",
            baseline_fact="baseline_capacity",
            exercise_key="fixture",
            variation_key="fixture",
            percent=2,
            load_convention="total_external",
        )


def test_continuous_schema_requires_explicit_rest_and_scopes_unused_models():
    case = mode_case("aerobic")
    preflight = validate_development_prescription(
        candidate=None, **{key: value for key, value in case.items() if key != "candidate"}
    )
    context = build_prescription_writer_context(case, preflight, None)
    schema = prescription_writer_schema(context)
    assert schema["$defs"]["TypedPrescriptionItem"]["properties"]["rest"] == {
        "$ref": "#/$defs/RestPrescription"
    }
    assert schema["$defs"]["RestPrescription"]["properties"]["kind"]["enum"] == ["not_applicable"]
    assert schema["$defs"]["RestPrescription"]["properties"]["seconds"] == {"type": "null"}
    assert "Repetitions" not in schema["$defs"]
    assert schema["properties"]["sessions"]["maxItems"] == 1
    assert schema["$defs"]["AerobicDose"]["properties"]["observation_fact"]["enum"] == [
        "reported_talk_test"
    ]


def test_model_wrong_observation_reference_does_not_request_already_supplied_facts():
    case = mode_case("aerobic")
    case["candidate"].sessions[0].items[0].dose.observation_fact = "progression_observed"
    with pytest.raises(PrescriptionRejection) as rejected:
        validate(case)
    assert rejected.value.category == "insufficient_support"
    assert rejected.value.reason == "invalid_observation_reference"


def mode_case(mode):
    case = valid_case()
    raw = case["execution"].model_dump(mode="json")
    raw["schema_version"] = 2
    by_dimension = {d.dimension: d.id for d in case["catalog"].policies[0].decisions}
    rules = {r["decision_id"]: r for r in raw["rules"]}
    raw["instructions"].update(
        {
            "gentle": {"kind": "relative_load", "text_pt_br": "Intensidade da tarefa revisada."},
            "support": {"kind": "note", "text_pt_br": "Mantenha o apoio indicado."},
            "supervision": {"kind": "note", "text_pt_br": "Realize com a supervisão indicada."},
        }
    )
    raw["instructions"]["progress"].update(unit="seconds", action_key="add_duration")
    rules[by_dimension["intensity"]]["permitted_instruction_keys"] = ["gentle"]
    rules[by_dimension["restrictions"]]["permitted_instruction_keys"] = ["support", "supervision"]
    rules[by_dimension["selection"]]["permitted_values"] = {
        "targets": ["posterior"],
        "sides": ["each_side"],
    }
    volume = rules[by_dimension["volume"]]["bounds"]
    volume.update(
        {
            k: {"minimum": a, "maximum": b}
            for k, a, b in [
                ("duration_minutes", 5, 20),
                ("holds", 2, 2),
                ("hold_seconds", 30, 30),
                ("duration_seconds_per_side", 60, 60),
                ("attempts", 1, 3),
                ("seconds", 5, 10),
                ("repetitions", 5, 5),
            ]
        }
    )
    rules[by_dimension["rest"]]["bounds"].update(
        {
            k + ".seconds": {"minimum": 30, "maximum": 120}
            for k in ("between_holds", "between_attempts", "between_tasks")
        }
    )
    dose = {
        "aerobic": {
            "kind": mode,
            "minutes": "10",
            "intensity": "moderate",
            "observation_fact": "reported_talk_test",
        },
        "flexibility": {
            "kind": mode,
            "holds": 2,
            "hold_seconds": "30",
            "side": "each_side",
            "target": "posterior",
            "intensity_instruction_key": "gentle",
        },
        "balance": {
            "kind": mode,
            "attempts": 3,
            "completed": None,
            "amount": "8",
            "unit": "seconds",
            "side": "each_side",
            "support_instruction_key": "support",
            "supervision_instruction_key": "supervision",
            "intensity_instruction_key": "gentle",
        },
        "functional": {
            "kind": mode,
            "attempts": 1,
            "completed": None,
            "amount": "5",
            "unit": "repetitions",
            "side": "each_side",
            "support_instruction_key": "support",
            "supervision_instruction_key": "supervision",
            "intensity_instruction_key": "gentle",
        },
    }[mode]
    rest_kind = {
        "aerobic": "not_applicable",
        "flexibility": "between_holds",
        "balance": "between_attempts",
        "functional": "between_tasks",
    }[mode]
    candidate = case["candidate"].model_dump(mode="json")
    candidate["schema_version"] = 2
    item = candidate["sessions"][0]["items"][0]
    item.update(
        sets=None,
        intensity=None,
        rest_seconds=None,
        dose=dose,
        rest={"kind": rest_kind, "seconds": None if mode == "aerobic" else 45},
    )
    item["progression"].update(unit="seconds", action_key="add_duration")
    case["catalog"].dictionary.exercises[0].dose_modes = [mode]
    case["accounting"].supported_modes = [mode]
    if mode == "aerobic":
        fact = case["snapshot"].facts["progression_observed"].model_copy(deep=True)
        fact.value = "talk_not_sing"
        case["snapshot"].facts["reported_talk_test"] = fact
        raw["input_requirements"].append(
            {"key": "reported_talk_test", "source": "request", "collection_approved": True}
        )
        rules[by_dimension["intensity"]]["permitted_values"] = {"aerobic_intensity": ["moderate"]}
    case["execution"] = DevelopmentExecutionContract.model_validate(raw)
    candidate["input_snapshot_sha256"] = record_hash(case["snapshot"])
    case["candidate"] = TypedPrescription.model_validate(candidate)
    return case


@pytest.mark.parametrize("mode", ["aerobic", "flexibility", "balance", "functional"])
def test_supported_modalities_validate_and_project_without_resistance_conversion(mode):
    case = mode_case(mode)
    result = validate(case)
    item = result["projection"]["items"][0]
    assert item["sets"] is None
    assert item["dose_details"]["mode"] == mode
    if mode == "aerobic":
        assert item["rest_seconds"] is None
        assert item["dose_details"]["rest"]["kind"] == "not_applicable"
    else:
        assert item["rest_seconds"] == 45
    assert result["modality_totals"]["sessions"]["session-a"]
    assert TypedPrescription.model_validate(result["typed_content"]) == case["candidate"]


def test_continuous_rest_zero_and_unobserved_completion_are_rejected():
    case = mode_case("aerobic")
    case["candidate"].sessions[0].items[0].rest.seconds = 0
    with pytest.raises(PrescriptionRejection, match="reviewed_contract_invalid"):
        validate(case)
    case = mode_case("balance")
    case["candidate"].sessions[0].items[0].dose.completed = 3
    with pytest.raises(PrescriptionRejection, match="completed_attempts_observation"):
        validate(case)


def test_loss_of_control_selects_stop_even_for_a_permissive_candidate():
    case = mode_case("balance")
    fact = case["snapshot"].facts["progression_observed"].model_copy(deep=True)
    fact.value = False
    case["snapshot"].facts["observed_control"] = fact
    raw = case["execution"].model_dump(mode="json")
    raw["input_requirements"].append(
        {"key": "observed_control", "source": "request", "collection_approved": True}
    )
    raw["documented_conflicts"] = [
        {
            "fact_key": "observed_control",
            "expected_value": False,
            "decision_id": "synthetic-restrictions",
            "action": "stop",
        }
    ]
    case["execution"] = DevelopmentExecutionContract.model_validate(raw)
    case["candidate"].input_snapshot_sha256 = record_hash(case["snapshot"])
    with pytest.raises(PrescriptionRejection) as rejected:
        validate(case)
    assert rejected.value.category == "restriction_conflict" and rejected.value.action == "stop"


def test_schema_narrows_exercises_and_rule_links_to_backend_envelope():
    case = valid_case()
    context = {k: v for k, v in case.items() if k != "candidate"}
    preflight = validate_development_prescription(candidate=None, **context)
    writer = build_prescription_writer_context(context, preflight, None)
    schema = prescription_writer_schema(writer)
    properties = schema["$defs"]["TypedPrescriptionItem"]["properties"]
    assert properties["exercise_key"]["enum"] == ["fixture"]
    assert properties["decision_rules"]["properties"]["volume"]["enum"] == ["synthetic-volume"]
    assert properties["calculated_load"] == {"type": "null"}
    assert "progress" in writer["rules"]["instructions"]


def test_nested_budgets_share_counts_and_reset_after_exit():
    with attempt_budget(1) as budget:
        with attempt_budget(999) as nested:
            assert nested is budget
            for _ in range(4):
                nested.call("writer", lambda: None)
        with pytest.raises(PrescriptionRejection, match="budget_exhausted"):
            budget.call("writer", lambda: None)
    assert CURRENT_BUDGET.get() is None
    times = [0]
    budget = AttemptBudget(1, clock=lambda: times[0])
    times[0] = 11
    with pytest.raises(PrescriptionRejection, match="deadline_exhausted"):
        budget.call("focus", lambda: None)


def test_budget_counts_actual_http_calls_and_rejects_late_results():
    times = [0]
    budget = AttemptBudget(1, clock=lambda: times[0])
    budget.call("writer", budget.record_http)
    assert budget.http_counts == {"writer": 1, "review": 0, "focus": 0}
    assert budget.counts["writer"] == 1
    with pytest.raises(PrescriptionRejection, match="budget_exhausted"):
        budget.record_http()

    def late_response():
        budget.record_http()
        times[0] = 11
        return "discarded"

    with pytest.raises(PrescriptionRejection, match="deadline_exhausted"):
        budget.call("review", late_response)
    assert budget.stage_seconds["review"] == 11


def owner_bundle():
    case = valid_case()
    catalog = case["catalog"].model_dump(mode="json")
    components = [*catalog["policies"], catalog["dictionary"]]
    for component in components:
        component.update(
            approval_basis="owner_decision",
            owner_authorization_id="fixture-owner-bundle",
            review_records=[],
        )
    catalog["policies"][0]["branch_id"] = "fixture-branch"
    for decision in catalog["policies"][0]["decisions"]:
        decision["research_rule_ids"] = ["SELECT_RESISTANCE"]
        decision["derivation"] = "owner_derived"
        for reference in decision["evidence"]:
            reference["certainty"] = "not_assessed"
    accounting = case["accounting"].model_dump(mode="json")
    accounting.update(
        approval_basis="owner_decision",
        owner_authorization_id="fixture-owner-bundle",
        review_records=[],
    )
    execution = case["execution"].model_dump(mode="json")
    execution["branch_id"] = "fixture-branch"
    return {"policies": catalog, "accounting": accounting, "execution": {"contracts": [execution]}}


def test_explicit_owner_bundle_authorization_binds_every_dependency(tmp_path, monkeypatch):
    bundle = owner_bundle()
    authorization.validate_bundle(bundle)
    artifacts = {
        key: {"id": key, "sha256": ("a" if key.startswith("source:") else "b") * 64}
        for key in ("source:synthetic", "rule:SELECT_RESISTANCE")
    }
    now = datetime.now(UTC).date()
    owner = OwnerApprovalRegistry(
        decision_id="fixture-decision",
        decided_on=now,
        status="approved",
        instruction="Synthetic owner instruction",
        governance_decision="Synthetic authorization, no professional review",
        artifacts={key: a["sha256"] for key, a in artifacts.items()},
    )
    monkeypatch.setattr(authorization, "load_owner_approval", lambda: owner)
    record = authorization.BundleAuthorization(
        id="fixture-owner-bundle",
        owner_decision_id=owner.decision_id,
        decided_on=now,
        review_due_at=now + timedelta(days=1),
        status="approved",
        bundle_sha256=prescription_bundle_hash(bundle),
        policy_ids=["synthetic"],
        dependency_hashes=owner.artifacts,
    )
    path = tmp_path / "authorizations.json"
    path.write_text(
        authorization.AuthorizationRegistry(authorizations=[record]).model_dump_json(),
        encoding="utf-8",
    )
    monkeypatch.setattr(authorization, "AUTHORIZATION_PATH", path)
    verified = authorization.verify_owner_bundle(bundle, record.id, artifacts=artifacts)
    assert verified["professional_review_performed"] is False
    assert not bundle["policies"]["policies"][0]["review_records"]
    changed = deepcopy(bundle)
    changed["execution"]["contracts"][0]["instructions"]["stop"]["text_pt_br"] = "Changed content"
    with pytest.raises(PrescriptionRejection, match="owner_bundle_authorization"):
        authorization.verify_owner_bundle(changed, record.id, artifacts=artifacts)
    owner.status = "revoked"
    with pytest.raises(PrescriptionRejection):
        authorization.verify_owner_bundle(bundle, record.id, artifacts=artifacts)


def test_owner_does_not_remove_missing_decisions_or_fabricate_human_reviews():
    bundle = owner_bundle()
    bundle["policies"]["policies"][0]["unresolved_decisions"] = [
        "Actual branch still needs a choice"
    ]
    with pytest.raises(ValidationError, match="unresolved"):
        PolicyCatalog.model_validate(bundle["policies"])


def test_all_research_has_readiness_without_automatic_release():
    matrix = authorization.readiness_matrix()
    assert len(matrix["rules"]) == 37
    assert len(matrix["profiles"]) == 11
    assert all(r["owner_accepted"] for r in matrix["rules"])
    assert matrix["enabled_cohorts"] == []
    assert matrix["missing_items"]
