"""Offline coverage/oracle integrity of the exposed local model experiment."""

import importlib
import json
from pathlib import Path

import pytest
from sqlalchemy import select
from test_training_generation import complete_onboarding, create_client
from test_training_generation import session as session

from app.modules.training.evidence_review import current_artifacts
from app.modules.training.generation_service import InitialTrainingGenerationService
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.owner_approval import load_owner_approval
from app.modules.training.prescription_contract import PrescriptionRejection


@pytest.fixture
def harness(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts"))
    return importlib.import_module("probe_all_owner_rules")


def test_every_current_approved_rule_has_application_and_counterexample(harness):
    artifacts = current_artifacts()
    batches, oracle = harness.build_batches(artifacts, load_owner_approval())
    expected = {a["id"][5:] for a in artifacts.values() if a["kind"] == "rule_proposal"}
    assert {case["rule_id"] for case in oracle.values()} == expected
    assert len(oracle) == 2 * len(expected) == 74
    assert len(batches) == 13
    for rule_id in expected:
        assert {c["case_id"].split(":")[1] for c in oracle.values() if c["rule_id"] == rule_id} == {
            "application",
            "counterexample",
        }


def test_expected_answers_and_case_kind_are_not_sent_to_model(harness):
    batches, _ = harness.build_batches(current_artifacts(), load_owner_approval())
    for batch in batches:
        for rule in batch["rules"]:
            for case in rule["cases"]:
                assert set(case) == {"case_id", "scenario_pt_br", "output_unit"}
                assert len(case["case_id"]) == 16
                int(case["case_id"], 16)
        assert "expected" not in json.dumps(batch)


def test_wrong_quantity_or_unit_does_not_pass_even_with_correct_acceptance(harness):
    batches, oracle = harness.build_batches(current_artifacts(), load_owner_approval())
    batch = batches[0]
    records = [
        {
            "case_id": case["case_id"],
            **oracle[case["case_id"]]["expected"],
            "explanation_pt_br": "Resposta sintética.",
        }
        for rule in batch["rules"]
        for case in rule["cases"]
    ]
    response = harness.ProbeResponse(results=records)
    assert all(result["passed"] for result in harness.score_response(response, batch, oracle))
    positive = next(result for result in response.results if result.value is not None)
    positive.unit = "wrong_unit"
    assert not all(result["passed"] for result in harness.score_response(response, batch, oracle))
    positive.unit = oracle[positive.case_id]["expected"]["unit"]
    positive.value += 1
    assert not all(result["passed"] for result in harness.score_response(response, batch, oracle))


def test_missing_duplicate_and_unrequested_responses_are_invalid(harness):
    batches, oracle = harness.build_batches(current_artifacts(), load_owner_approval())
    batch = batches[0]
    records = [
        {
            "case_id": case["case_id"],
            **oracle[case["case_id"]]["expected"],
            "explanation_pt_br": "Resposta sintética.",
        }
        for rule in batch["rules"]
        for case in rule["cases"]
    ]
    for changed in (
        records[:-1],
        records + records[:1],
        [{**records[0], "case_id": "unlisted"}, *records[1:]],
    ):
        with pytest.raises(ValueError, match="missing_duplicate_or_unrequested_case"):
            harness.score_response(harness.ProbeResponse(results=changed), batch, oracle)


def test_changed_or_revoked_rule_cannot_enter_probe(harness):
    artifacts, registry = current_artifacts(), load_owner_approval()
    first_rule = next(a for a in artifacts.values() if a["kind"] == "rule_proposal")
    first_rule["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="current_owner_rule_approval_required"):
        harness.build_batches(artifacts, registry)
    registry.status = "revoked"
    with pytest.raises(ValueError, match="current_owner_rule_approval_required"):
        harness.build_batches(current_artifacts(), registry)


def test_diagnostic_selection_keeps_original_oracles_and_limits_response_ids(harness):
    artifacts, registry = current_artifacts(), load_owner_approval()
    _, all_oracles = harness.build_batches(artifacts, registry)
    batches, selected = harness.build_batches(
        artifacts, registry, size=1, selected_rule_ids=["RESISTANCE_EFFORT"]
    )
    assert len(batches) == 1 and len(selected) == 2
    assert all(all_oracles[key] == case for key, case in selected.items())
    schema = harness.response_schema(batches[0])
    assert schema["properties"]["results"]["minItems"] == 2
    assert schema["properties"]["results"]["maxItems"] == 2
    assert set(schema["$defs"]["FragmentResult"]["properties"]["case_id"]["enum"]) == set(selected)
    with pytest.raises(ValueError, match="unknown_or_empty_rule_selection"):
        harness.build_batches(artifacts, registry, selected_rule_ids=["unlisted"])


@pytest.mark.parametrize(
    "goal",
    [
        "Força",
        "Hipertrofia",
        "Emagrecimento",
        "Condicionamento cardiorrespiratório",
        "Resistência muscular",
        "Potência",
        "Mobilidade e flexibilidade",
        "Equilíbrio",
        "Autonomia funcional",
        "Saúde geral",
        "Desempenho esportivo",
    ],
)
def test_qualified_generation_with_actual_packaged_rules_reports_missing_contracts(
    session, monkeypatch, goal
):
    monkeypatch.setenv("TRAINING_PRESCRIPTION_GATE_ENABLED", "true")
    create_client(session, "rule-probe-owner", "rule-probe-owner@example.test")
    complete_onboarding(
        session,
        "rule-probe-owner",
        training_goal=goal,
        has_limitations_or_complaints=False,
        limitations_or_complaints=None,
        has_health_conditions=False,
        health_conditions=None,
    )

    class NoExternalCall:
        def retrieve(self, *args, **kwargs):
            pytest.fail("Incomplete executable policy must block before retrieval")

        def generate_prescription(self, *args, **kwargs):
            pytest.fail("Incomplete executable policy must block before generation")

    adapter = NoExternalCall()
    service = InitialTrainingGenerationService(provider=adapter, knowledge_service=adapter)
    with pytest.raises(PrescriptionRejection) as rejected:
        service.generate_for_subject(session, "rule-probe-owner")
    assert rejected.value.category == "insufficient_support"
    assert rejected.value.reason == "approved_goal_policy_required"
    assert session.scalar(select(TrainingPlanVersion)) is None
