"""Inspect readiness or validate an explicitly prepared bundle without approving it.

Examples (repository Compose backend):
  python scripts/compile_prescription_bundle.py --readiness
  python scripts/compile_prescription_bundle.py --bundle /path/bundle.json
Outputs stay in the ignored evidence cache; publication/authorization is explicit.
"""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app.modules.knowledge.acquisition import CACHE_PATH, write_json
from app.modules.training.evidence_review import current_artifacts, prescription_bundle_hash
from app.modules.training.owner_approval import artifact_owner_approval, load_owner_approval
from app.modules.training.prescription_authorization import (
    readiness_matrix,
    required_dependencies,
    validate_bundle,
)


def prepare_authorization_request(bundle):
    catalog, _, _ = validate_bundle(bundle, preparing=True)
    artifacts, owner = current_artifacts(), load_owner_approval()
    dependencies = {}
    for key in sorted(required_dependencies(catalog)):
        artifact = artifacts.get(key)
        if artifact is None or artifact_owner_approval(artifact, owner) is None:
            raise ValueError("current_research_acceptance_required:" + key)
        dependencies[key] = artifact["sha256"]
    return {
        "status": "pending_explicit_owner_authorization",
        "prepared_at": datetime.now(UTC).isoformat(),
        "bundle_sha256": prescription_bundle_hash(bundle),
        "policy_ids": [p.id for p in catalog.policies],
        "dependency_hashes": dependencies,
        "professional_review_performed": False,
        "release_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--readiness", action="store_true")
    group.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    if args.readiness:
        report = readiness_matrix()
        name = "remediation-readiness.json"
    else:
        report = prepare_authorization_request(json.loads(args.bundle.read_text(encoding="utf-8")))
        name = "compiled-bundle-authorization-request.json"
    write_json(CACHE_PATH / name, report)
    print(
        json.dumps(
            {
                "output": name,
                "status": report.get("status", "readiness_only_no_release"),
                "rules": len(report.get("rules", [])),
                "profiles": len(report.get("profiles", [])),
            }
        )
    )


if __name__ == "__main__":
    main()
