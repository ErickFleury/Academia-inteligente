"""Exposed software diagnostic with the configured model and a synthetic envelope.

Not a real-policy/retrieval experiment or independent evaluation. All persistence
uses a disposable in-memory database. Existing probe artifacts are never replaced.
"""

import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_prescription_remediation import mode_case  # noqa: E402
from test_training_generation import create_client  # noqa: E402

from app.database import Base  # noqa: E402
from app.integrations.ai import (  # noqa: E402
    AiProviderError,
    training_generation_provider_from_environment,
)
from app.modules.knowledge.acquisition import CACHE_PATH, write_json  # noqa: E402
from app.modules.training.prescription_budget import CURRENT_STAGE, attempt_budget  # noqa: E402
from app.modules.training.prescription_contract import (  # noqa: E402
    PrescriptionRejection,
    record_hash,
)
from app.modules.training.prescription_runtime import (  # noqa: E402
    OperationalPrescriptionService,
    writer_configuration,
)


def main():
    if os.getenv("AI_PROVIDER") != "ollama":
        raise SystemExit("This diagnostic permits only the configured local Ollama model")
    provider = training_generation_provider_from_environment()
    with urlopen(provider._config.base_url.rstrip("/") + "/api/tags", timeout=10) as response:
        tags = json.load(response)
    model = next(m for m in tags["models"] if m["name"] == provider._config.model)
    case = mode_case("aerobic")
    case["catalog"].dictionary.exercises[0].label_pt_br = "Caminhada"
    case["catalog"].dictionary.exercises[0].movement = "Caminhada contínua"
    case["execution"].purpose = "operational"
    case["execution"].writer_configuration_sha256 = record_hash(writer_configuration())
    name = "remediation-model-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    plan = {
        "name": name,
        "frozen_at": datetime.now(UTC).isoformat(),
        "scope": "exposed_software_diagnostic_synthetic_contract_and_evidence",
        "real_policy_or_retrieval": False,
        "independent_evaluation": False,
        "case": "aerobic_continuous_no_resistance_fields",
        "repetitions": 1,
        "expected": (
            "Reviewable synthetic proposal if the actual model follows the supplied envelope; "
            "all failures retained"
        ),
        "clinical_accuracy": "not_evaluated",
        "explanation": "not_graded_no_free_prose",
        "model": {"name": model["name"], "digest": model["digest"]},
        "writer_configuration": writer_configuration(),
        "timeout_seconds": provider._timeout,
        "deadline_seconds": 10 * provider._timeout,
        "max_http_calls": {"writer": 4, "review": 4, "focus": 0, "total": 8},
        "contract_sha256": record_hash(case["execution"]),
        "dictionary_sha256": record_hash(case["catalog"].dictionary),
        "source_support": "Synthetic fixture; no scientific support claim",
        "implementation_sha256": {
            path: hashlib.sha256((Path(__file__).parents[1] / path).read_bytes()).hexdigest()
            for path in (
                "app/modules/training/prescription_writer_schema.py",
                "app/modules/training/prescription_contract.py",
                "app/modules/training/prescription_validation.py",
                "app/integrations/ai.py",
            )
        },
        "persistence": "in_memory_sqlite_only_no_real_clients_or_release",
    }
    write_json(CACHE_PATH / (name + "-plan.json"), plan)
    outputs = []
    original_text = provider._text

    def capture_structured_text(body):
        value = original_text(body)
        # This probe contains synthetic facts only. Capture only the structured
        # answer, never the provider's separate thinking/reasoning field.
        outputs.append({"stage": CURRENT_STAGE.get(), "structured_answer": value})
        return value

    provider._text = capture_structured_text

    class Recorder:
        def generate_prescription(self, context):
            result = provider.generate_prescription(context)
            outputs.append({"stage": "writer", "result": result.model_dump(mode="json")})
            return result

        def assess_training(self, context):
            result = provider.assess_training(context)
            outputs.append({"stage": "review", "result": result.model_dump(mode="json")})
            return result

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    started = time.monotonic()
    result = {}
    with (
        Session(engine, expire_on_commit=False) as session,
        attempt_budget(provider._timeout) as budget,
    ):
        client = create_client(session, "remediation-diagnostic", "diagnostic@example.test")
        case["client_id"] = case["snapshot"].client_id = client.id
        runtime = OperationalPrescriptionService(
            session=session,
            client_id=client.id,
            subject="remediation-diagnostic",
            context_supplier=lambda: case,
        )
        try:
            version = runtime.generate_version(Recorder())
            result = {
                "status": "accepted_software_fixture_only",
                "projection": runtime.lifecycle.content(session, version).model_dump(mode="json"),
                "activated": False,
            }
        except PrescriptionRejection as error:
            result = {
                "status": "rejected",
                "category": error.category,
                "reason": error.reason,
                "issues": error.issues,
                "next_action": error.action,
            }
        except AiProviderError as error:
            result = {"status": "provider_failure", "reason": error.category}
        finally:
            result.update(
                plan_name=name,
                elapsed_seconds=time.monotonic() - started,
                stage_calls=budget.counts,
                actual_model_http_calls=budget.http_counts,
                stage_seconds=budget.stage_seconds,
                outputs=outputs,
                independent_evaluation=False,
                real_policy_or_retrieval=False,
            )
            write_json(CACHE_PATH / (name + "-result.json"), result)
    engine.dispose()
    print(
        json.dumps(
            {
                "plan": name + "-plan.json",
                "result": name + "-result.json",
                "status": result["status"],
            }
        )
    )


if __name__ == "__main__":
    main()
