"""One local writer/core development probe; no database, release or clinical claim.

Run from the repository root, after starting the existing Ollama service:
Get-Content -Raw docs/tasks/51-prescription-local-writer-probe.py |
  docker compose run --rm -T --no-deps -e DATABASE_URL= -e PYTHONPATH=/app:/app/tests backend python
"""

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

from prescription_fixtures import enable_weekly_fixture, valid_case

from app import database
from app.integrations import ai
from app.modules.knowledge.acquisition import CACHE_PATH, digest, write_json
from app.modules.training.prescription_contract import PrescriptionRejection, record_hash
from app.modules.training.prescription_development import build_prescription_writer_context
from app.modules.training.prescription_validation import validate_development_prescription
from app.modules.training.prescription_writer_schema import prescription_writer_schema

if database.engine is not None or os.getenv("AI_PROVIDER") != "ollama":
    raise SystemExit("Requires DATABASE_URL empty and the configured local Ollama provider")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--scenario", required=True, choices=("session", "confirmed-week"))
args = parser.parse_args()
prefix = "writer-schedule-" + args.scenario
provider = ai.training_generation_provider_from_environment()
with urlopen(provider._config.base_url.rstrip("/") + "/api/tags", timeout=10) as response:
    tags = json.load(response)
model = next(m for m in tags["models"] if m["name"] == provider._config.model)
with urlopen(provider._config.base_url.rstrip("/") + "/api/version", timeout=10) as response:
    server_version = json.load(response)["version"]

case = valid_case()
if args.scenario == "confirmed-week":
    enable_weekly_fixture(case)
revision = case.pop("candidate").expected_revision
owner = case["snapshot"].client_id
case.update(client_id=owner, current_revision=revision)
preflight = validate_development_prescription(candidate=None, **case)
context = {
    **build_prescription_writer_context(case, preflight, revision),
    "training_request": (
        "Gere uma revisão completa do plano sintético, copiando a programação confirmada."
        if args.scenario == "confirmed-week"
        else "Gere uma única sessão sintética sem inventar programação semanal."
    ),
    "required_scope": "plan_revision" if args.scenario == "confirmed-week" else "session_sheet",
    "requested_focus": {"scope": "unspecified", "muscle_groups": []},
    "current_prescription": None,
}
plan = {
    "version": 2,
    "scenario": args.scenario,
    "purpose": "exposed_synthetic_development_probe_not_independent_evaluation",
    "frozen_at": datetime.now(UTC).isoformat(),
    "provider": "ollama",
    "model": model["name"],
    "model_digest": model["digest"],
    "server_version": server_version,
    "maximum_writer_calls": 1,
    "retries": 0,
    "timeout_seconds": provider._timeout,
    "expected_technical_outcome": "typed_candidate_passes_synthetic_fixture_core",
    "input_sha256": record_hash(context),
    "writer_schema_sha256": record_hash(prescription_writer_schema(context)),
    "writer_context_builder_sha256": digest(
        Path("app/modules/training/prescription_development.py").read_bytes()
    ),
    "negative_control": "Reject accepted output after sets exceed its synthetic rule bound",
    "synthetic_fixture_sha256": digest(Path("tests/prescription_fixtures.py").read_bytes()),
    "synthetic_policy_fixture_sha256": digest(
        Path("tests/test_prescription_policy.py").read_bytes()
    ),
    "adapter_sha256": digest(Path("app/integrations/ai.py").read_bytes()),
    "uses_real_corpus_or_embedding_provider": False,
    "database_configured": False,
    "enabled_cohorts": [],
}
write_json(CACHE_PATH / (prefix + "-plan.json"), plan)
requests = []


def observed_transport(request, **kwargs):
    if len(requests) >= plan["maximum_writer_calls"]:
        raise RuntimeError("Development call budget exceeded")
    body = json.loads(request.data)
    requests.append(
        {
            "request_sha256": digest(request.data),
            "instructions_sha256": record_hash(body["messages"][0]["content"]),
            "options": body.get("options", {}),
            "think": body.get("think"),
            "stream": body.get("stream"),
            "timeout_seconds": kwargs.get("timeout"),
        }
    )
    return urlopen(request, **kwargs)


ai.urlopen = observed_transport
started = time.monotonic()
outcome = {}
negative_control = {"status": "not_executed", "reason": "positive_candidate_not_accepted"}
try:
    candidate = provider.generate_prescription(context)
    outcome["typed_candidate_sha256"] = record_hash(candidate)
    result = validate_development_prescription(candidate=candidate, **case)
    outcome.update(
        status="accepted_by_synthetic_core", projection_sha256=result["rendered_content_sha256"]
    )
    changed = candidate.model_copy(deep=True)
    volume_rule_id = changed.sessions[0].items[0].decision_rules["volume"]
    volume_rule = next(r for r in case["execution"].rules if r.decision_id == volume_rule_id)
    changed.sessions[0].items[0].sets = int(volume_rule.bounds["sets"].maximum) + 1
    try:
        validate_development_prescription(candidate=changed, **case)
        negative_control = {"status": "unexpected_acceptance"}
    except PrescriptionRejection as error:
        negative_control = {
            "status": "rejected",
            "category": error.category,
            "reason": error.reason,
        }
except PrescriptionRejection as error:
    outcome.update(
        status="rejected_by_synthetic_core", category=error.category, reason=error.reason
    )
except ai.AiProviderError as error:
    outcome.update(
        status="controlled_provider_failure", category=error.category, retryable=error.retryable
    )
except Exception as error:
    outcome.update(status="probe_failure", error_type=type(error).__name__)

report = {
    "version": 2,
    "captured_at": datetime.now(UTC).isoformat(),
    "purpose": plan["purpose"],
    "frozen_plan_sha256": record_hash(plan),
    "plan": plan,
    "actual_writer_calls": len(requests),
    "requests": requests,
    "elapsed_seconds": round(time.monotonic() - started, 3),
    "outcome": outcome,
    "post_generation_mutation_control": negative_control,
    "saved_or_published_candidates": 0,
    "scientific_approval": "pending",
    "independent_evaluation": "not_executed",
    "limitations": [
        "Implementer-visible toy fixtures are not professional policies or held-out cases.",
        "Retrieval, embeddings, automatic review and authenticated lifecycle were not exercised.",
        "One writer/core call cannot establish supported-cohort acceptance or rejection rates.",
        "No candidate prose, dose or trace is published; the application gate remains disabled.",
    ],
}
write_json(CACHE_PATH / (prefix + "-result.json"), report)
print(json.dumps(report))
