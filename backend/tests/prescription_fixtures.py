"""Synthetic development policy/rule/evidence inputs; never runtime artifacts."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from test_prescription_policy import dictionary, policy, reviews

from app.modules.knowledge.acquisition import digest
from app.modules.knowledge.service import KnowledgeContext
from app.modules.training.prescription_accounting import AccountingMethod
from app.modules.training.prescription_contract import (
    DevelopmentExecutionContract,
    InputSnapshot,
    TypedPrescription,
    record_hash,
)
from app.modules.training.prescription_policy import PolicyCatalog


def valid_case(client_id=None):
    owner = client_id or uuid4()
    now = datetime.now(UTC)
    source = {
        "id": "synthetic",
        "title": "Synthetic development fixture",
        "url": "https://example.test/evidence",
        "authors": ["Synthetic fixture"],
        "license": "CC-BY-4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "review_status": "approved",
        "commercial_use_allowed": True,
        "reviewed_at": now.date().isoformat(),
        "review_due_at": (now.date() + timedelta(days=1)).isoformat(),
        "reviewed_by": "synthetic technical reviewer",
        "provenance": {"artifact_sha256": "a" * 64},
        "chunks": [
            {
                "id": "synthetic-1",
                "section": "fixture:1",
                "content": "Synthetic reviewed development evidence, not scientific content.",
            }
        ],
    }
    data = policy()
    for decision in data["decisions"]:
        decision["evidence"][0]["passage_sha256"] = digest(source["chunks"][0]["content"].encode())
    exercise_dictionary = dictionary()
    exercise_dictionary["exercises"][0]["label_pt_br"] = "Agachamento"
    catalog = PolicyCatalog(version="test-1", policies=[data], dictionary=exercise_dictionary)
    accounting = AccountingMethod(
        version="test-1",
        dictionary_version="test-1",
        status="approved",
        review_records=reviews(),
        review_due_at=now.date() + timedelta(days=1),
        mappings=[
            {"exercise_key": "fixture", "variation_key": "fixture", "direct_muscles": ["fixture"]}
        ],
    )
    facts = {
        "training_goal": "fixture",
        "training_experience": "none",
        "uses_medications": True,
        "has_limitations_or_complaints": True,
        "progression_observed": False,
    }
    snapshot = InputSnapshot(
        client_id=owner,
        facts={
            key: {
                "value": value,
                "source": "request" if key == "progression_observed" else "onboarding",
                "source_id": "synthetic-onboarding",
                "source_revision": "1",
                "confirmed_by": "client_owner",
                "observed_at": now,
                "confirmed_at": now,
            }
            for key, value in facts.items()
        },
    )
    rules = [
        {"decision_id": decision["id"], "requires_weekly_context": False}
        for decision in data["decisions"]
    ]
    by_dimension = {
        decision["dimension"]: rule for decision, rule in zip(data["decisions"], rules, strict=True)
    }
    by_dimension["selection"]["allowed_exercises"] = {"fixture": ["fixture"]}
    by_dimension["volume"]["bounds"] = {
        "sets": {"minimum": 1, "maximum": 4},
        "repetitions": {"minimum": 1, "maximum": 10},
        "session_working_sets": {"minimum": 1, "maximum": 4},
        "weekly_working_sets": {"minimum": 1, "maximum": 8},
        "weekly_direct_sets.fixture": {"minimum": 0, "maximum": 8},
        "weekly_indirect_sets.fixture": {"minimum": 0, "maximum": 8},
    }
    # Remove weekly bounds for the session-only fixture. Weekly tests add them explicitly.
    by_dimension["volume"]["bounds"] = {
        key: value
        for key, value in by_dimension["volume"]["bounds"].items()
        if not key.startswith("weekly_")
    }
    by_dimension["intensity"]["bounds"] = {"rir": {"minimum": 1, "maximum": 4}}
    by_dimension["intensity"]["permitted_scale_keys"] = ["synthetic-rir"]
    by_dimension["rest"]["bounds"] = {"rest_seconds": {"minimum": 10, "maximum": 100}}
    by_dimension["progression"]["permitted_instruction_keys"] = ["progress", "stop", "regress"]
    execution = DevelopmentExecutionContract(
        policy_id="synthetic",
        writer_configuration_sha256="c" * 64,
        input_requirements=[
            {
                "key": key,
                "source": "request" if key == "progression_observed" else "onboarding",
                "collection_approved": True,
            }
            for key in facts
        ],
        rules=rules,
        instructions={
            "progress": {
                "kind": "progression",
                "text_pt_br": "Progrida somente na condição revisada.",
                "condition_fact": "progression_observed",
                "action_key": "add_repetitions",
                "unit": "repetitions",
                "amount_bounds": {"minimum": 1, "maximum": 1},
            },
            "stop": {"kind": "stop", "text_pt_br": "Interrompa conforme a condição revisada."},
            "regress": {
                "kind": "regression",
                "text_pt_br": "Retorne à etapa revisada pelo instrutor.",
            },
        },
    )
    candidate = TypedPrescription(
        scope="session_sheet",
        input_snapshot_sha256=record_hash(snapshot),
        policy_version="test-1",
        dictionary_version="test-1",
        accounting_method_version="test-1",
        sessions=[
            {
                "session_id": "session-a",
                "label": "A",
                "items": [
                    {
                        "item_id": "item-1",
                        "exercise_key": "fixture",
                        "variation_key": "fixture",
                        "sets": 2,
                        "dose": {"kind": "repetitions", "minimum": 3, "maximum": 5},
                        "intensity": {
                            "mode": "rir",
                            "minimum": 2,
                            "maximum": 3,
                            "scale_key": "synthetic-rir",
                        },
                        "rest_seconds": 30,
                        "progression": {
                            "instruction_key": "progress",
                            "condition_fact": "progression_observed",
                            "action_key": "add_repetitions",
                            "amount": 1,
                            "unit": "repetitions",
                            "stop_instruction_key": "stop",
                            "regression_instruction_key": "regress",
                        },
                        "decision_rules": {d["dimension"]: d["id"] for d in data["decisions"]},
                    }
                ],
            }
        ],
    )
    chunk = source["chunks"][0]
    evidence = KnowledgeContext(
        (
            {
                **source,
                "source_id": source["id"],
                "chunk_id": chunk["id"],
                "section": chunk["section"],
                "content": chunk["content"],
            },
        ),
        "supported",
        "Synthetic fixture only",
    )
    return {
        "candidate": candidate,
        "snapshot": snapshot,
        "catalog": catalog,
        "execution": execution,
        "accounting": accounting,
        "evidence": evidence,
        "source_catalog": {"version": 1, "sources": [source]},
        "client_id": owner,
    }


def enable_weekly_fixture(case):
    """Explicit synthetic schedule/bounds; not operational policy defaults."""
    from app.modules.training.prescription_contract import DevelopmentSchedule

    case["candidate"].scope = "plan_revision"
    case["candidate"].schedule = DevelopmentSchedule(
        occurrences=[
            {"occurrence_id": "one", "session_id": "session-a", "day_index": 0},
            {"occurrence_id": "two", "session_id": "session-a", "day_index": 3},
        ]
    )
    case["snapshot"].schedule = case["candidate"].schedule.model_copy(deep=True)
    fact = case["snapshot"].facts["progression_observed"].model_copy(deep=True)
    fact.value = True
    case["snapshot"].facts["schedule_confirmed"] = fact
    case["candidate"].input_snapshot_sha256 = record_hash(case["snapshot"])
    raw = case["execution"].model_dump(mode="json")
    raw["input_requirements"].append(
        {
            "key": "schedule_confirmed",
            "source": "request",
            "collection_approved": True,
        }
    )
    for rule in raw["rules"]:
        if rule["decision_id"] == "synthetic-volume":
            rule["bounds"].update(
                {
                    "weekly_working_sets": {"minimum": 1, "maximum": 4},
                    "weekly_direct_sets.fixture": {"minimum": 0, "maximum": 4},
                    "weekly_indirect_sets.fixture": {"minimum": 0, "maximum": 0},
                }
            )
        if rule["decision_id"] == "synthetic-frequency":
            rule["requires_weekly_context"] = True
            rule["bounds"]["sessions_per_seven_days"] = {"minimum": 1, "maximum": 2}
    case["execution"] = DevelopmentExecutionContract.model_validate(raw)
    return case
