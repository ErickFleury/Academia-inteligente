"""Validate a local fallback against current revocations before operator recovery."""

import argparse
import json
from datetime import date
from pathlib import Path

from app.modules.knowledge.acquisition import CATALOG_PATH, validate_packaged_source
from app.modules.knowledge.service import ALLOWED_LICENSES


def validate_recovery_catalog(candidate: dict, current: dict, *, today: date | None = None):
    today = today or date.today()
    if candidate.get("version") != 1 or current.get("version") != 1:
        raise ValueError("incompatible_recovery_catalog_version")
    current_sources = {source["id"]: source for source in current["sources"]}
    seen, passages = set(), 0
    for source in candidate["sources"]:
        identifier = source["id"]
        if identifier in seen:
            raise ValueError("duplicate_recovery_source")
        seen.add(identifier)
        if source["review_status"] != "approved":
            continue
        latest = current_sources.get(identifier)
        if not latest or latest["review_status"] != "approved":
            raise ValueError("recovery_would_restore_removed_or_revoked_source")
        for record in (source, latest):
            if (
                record["license"] not in ALLOWED_LICENSES
                or not record["commercial_use_allowed"]
                or not record.get("reviewed_by")
                or not record.get("reviewed_at")
                or not record.get("review_due_at")
                or not date.fromisoformat(record["reviewed_at"])
                <= today
                < date.fromisoformat(record["review_due_at"])
            ):
                raise ValueError("recovery_source_review_or_permission_invalid")
        if source["license"] != latest["license"]:
            raise ValueError("recovery_source_license_changed")
        if source["url"] != latest["url"]:
            raise ValueError("recovery_source_identity_changed")
        latest_chunks = {chunk["id"]: chunk for chunk in latest.get("chunks", [])}
        for chunk in source.get("chunks", []):
            if latest_chunks.get(chunk["id"]) != chunk:
                raise ValueError("recovery_would_restore_removed_or_changed_passage")
        validate_packaged_source(source)
        if not source.get("chunks"):
            raise ValueError("recovery_approved_source_without_passages")
        passages += len(source["chunks"])
    if not passages:
        raise ValueError("no_valid_recovery_corpus")
    return passages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    current = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    count = validate_recovery_catalog(candidate, current)
    print(
        f"Local fallback checks passed: {count} passages; operator currency review still required"
    )


if __name__ == "__main__":
    main()
