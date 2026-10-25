"""Owner decisions stay distinct from human reviews and bind exact research versions."""

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from test_training_lifecycle import session as session
from test_training_review import api as api

from app.modules.training import evidence_review, owner_approval
from app.modules.training.owner_approval import (
    OwnerApprovalRegistry,
    approved_research_context,
    artifact_owner_approval,
)


def registry(artifact):
    return OwnerApprovalRegistry(
        decision_id="synthetic-owner-decision",
        decided_on=datetime.now(UTC).date(),
        status="approved",
        instruction="Synthetic owner instruction for software testing.",
        governance_decision="Owner basis, no professional review.",
        artifacts={artifact["id"]: artifact["sha256"]},
    )


def test_owner_approval_does_not_complete_independent_human_review(session, monkeypatch):
    artifact = next(iter(evidence_review.current_artifacts().values()))
    decision = registry(artifact)
    monkeypatch.setattr(owner_approval, "load_owner_approval", lambda: decision)
    result = evidence_review.artifact_out(session, artifact, details=True)
    assert result["owner_approval"]["authority"] == "project_owner"
    assert result["owner_approval"]["professional_review_performed"] is False
    assert result["judgments"] == []
    assert result["independence_complete"] is False


def test_instructor_api_exposes_owner_basis_without_creating_judgments(api):
    http, _ = api
    response = http.get("/training/evidence-review/artifacts")
    assert response.status_code == 200
    sources = [a for a in response.json() if a["kind"] == "source"]
    assert sources and all(a["owner_approval"]["authority"] == "project_owner" for a in sources)
    detail = http.get("/training/evidence-review/artifacts/" + sources[0]["id"]).json()
    assert detail["owner_approval"]["professional_review_performed"] is False
    assert detail["judgments"] == []
    assert detail["independence_complete"] is False


def test_changed_unlisted_and_revoked_artifacts_are_not_approved():
    artifact = next(iter(evidence_review.current_artifacts().values()))
    decision = registry(artifact)
    assert artifact_owner_approval(artifact, decision)
    assert artifact_owner_approval({**artifact, "sha256": "0" * 64}, decision) is None
    assert artifact_owner_approval({**artifact, "id": "source:unlisted"}, decision) is None
    decision.status = "revoked"
    assert artifact_owner_approval(artifact, decision) is None


def test_missing_or_corrupt_owner_registry_never_grants_approval(tmp_path, monkeypatch):
    path = tmp_path / "approval.json"
    monkeypatch.setattr(owner_approval, "APPROVAL_PATH", path)
    assert owner_approval.load_owner_approval() is None
    path.write_text('{"artifacts": {}}', encoding="utf-8")
    assert owner_approval.load_owner_approval() is None
    path.write_bytes(b"\xff\xfe\xff")
    assert owner_approval.load_owner_approval() is None


def test_owner_decision_cannot_claim_professional_review_or_approve_incomplete_bundle():
    artifact = next(iter(evidence_review.current_artifacts().values()))
    data = registry(artifact).model_dump(mode="json")
    with pytest.raises(ValidationError):
        OwnerApprovalRegistry.model_validate({**data, "professional_review_performed": True})
    with pytest.raises(ValidationError, match="owner_source_rule_scope_required"):
        OwnerApprovalRegistry.model_validate(
            {**data, "artifacts": {"prescription-bundle": "a" * 64}}
        )
    with pytest.raises(ValidationError, match="future_owner_decision"):
        OwnerApprovalRegistry.model_validate(
            {**data, "decided_on": (datetime.now(UTC).date() + timedelta(days=1)).isoformat()}
        )


def test_all_current_sources_and_proposed_rules_have_explicit_owner_approval():
    artifacts = evidence_review.current_artifacts()
    sources_and_rules = [a for a in artifacts.values() if a["kind"] in ("source", "rule_proposal")]
    assert sources_and_rules
    assert all(artifact_owner_approval(a) for a in sources_and_rules)
    assert artifact_owner_approval(artifacts["prescription-bundle"]) is None
    # Authorization must not mutate licensing, certainty or unresolved research.
    context = approved_research_context("hypertrophy")
    assert context["qualified_operational_policy"] is False
    assert context["approval"]["professional_review_performed"] is False
    assert context["profile"]["unresolved"]


def test_changed_rule_or_its_applicability_invalidates_generation_context(monkeypatch):
    artifacts = evidence_review.current_artifacts()
    changed = deepcopy(artifacts)
    context = approved_research_context("hypertrophy")
    changed["rule:" + context["rules"][0]["id"]]["sha256"] = "0" * 64
    monkeypatch.setattr(evidence_review, "current_artifacts", lambda: changed)
    with pytest.raises(ValueError, match="current_owner_rule_approval_required"):
        approved_research_context("hypertrophy")


def test_unknown_research_goal_is_not_silently_mapped_to_an_approved_family():
    with pytest.raises(ValueError, match="unsupported_research_goal_family"):
        approved_research_context("unlisted mixed goal")


def test_approval_keeps_exact_packaged_license_and_source_status():
    artifacts = evidence_review.current_artifacts()
    catalog = json.loads(evidence_review.CATALOG_PATH.read_text(encoding="utf-8"))
    for source in catalog["sources"]:
        assert artifacts["source:" + source["id"]]["data"] == source
