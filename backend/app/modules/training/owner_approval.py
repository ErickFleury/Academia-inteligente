"""Exact-version project-owner authorization; never a fabricated scientific review."""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, ValidationError, model_validator

from app.modules.training.prescription_policy import Record

ROOT = Path(__file__).parent
APPROVAL_PATH = ROOT / "owner-evidence-approval.json"
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class OwnerApproval(Record):
    decision_id: str = Field(min_length=1)
    authority: Literal["project_owner"] = "project_owner"
    decided_on: date
    professional_review_performed: Literal[False] = False
    independent_evaluation_performed: Literal[False] = False


class OwnerApprovalRegistry(OwnerApproval):
    schema_version: Literal[1] = 1
    status: Literal["approved", "revoked"]
    instruction: str = Field(min_length=1)
    governance_decision: str = Field(min_length=1)
    artifacts: dict[str, Hash] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_scope(self):
        if self.decided_on > datetime.now(UTC).date():
            raise ValueError("future_owner_decision")
        if any(not key.startswith(("source:", "rule:")) for key in self.artifacts):
            raise ValueError("owner_source_rule_scope_required")
        return self


def load_owner_approval():
    try:
        return OwnerApprovalRegistry.model_validate_json(APPROVAL_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValidationError):
        # An unreadable decision cannot authorize anything. Human-review records
        # and source inspection remain available independently.
        return None


def artifact_owner_approval(artifact, registry=None):
    registry = registry if registry is not None else load_owner_approval()
    if (
        registry is None
        or registry.status != "approved"
        or registry.artifacts.get(artifact["id"]) != artifact["sha256"]
    ):
        return None
    return OwnerApproval.model_validate(
        {key: getattr(registry, key) for key in OwnerApproval.model_fields}
    ).model_dump(mode="json")


def approved_research_context(goal_family):
    """Explicit goal-family research input for development probes, not typed eligibility."""
    from app.modules.training.evidence_review import current_artifacts

    proposals = json.loads((ROOT / "review-rule-candidates.json").read_text(encoding="utf-8"))
    profile = next((p for p in proposals["profiles"] if p["goal_family"] == goal_family), None)
    if profile is None:
        raise ValueError("unsupported_research_goal_family")
    ids = {key for keys in profile["dimensions"].values() for key in keys}
    ids.update(profile.get("accounting", []))
    ids.update(profile.get("protocol_alternatives", []))
    artifacts, registry = current_artifacts(), load_owner_approval()
    rules = [r for r in proposals["rules"] if r["id"] in ids]
    if not rules or any(
        artifact_owner_approval(artifacts["rule:" + rule["id"]], registry) is None for rule in rules
    ):
        raise ValueError("current_owner_rule_approval_required")
    return {
        "approval": artifact_owner_approval(artifacts["rule:" + rules[0]["id"]], registry),
        "goal_family": goal_family,
        "rules": rules,
        "profile": profile,
        "qualified_operational_policy": False,
        "instructions_pt_br": (
            "Estas regras foram aceitas pelo proprietário, sem parecer profissional. "
            "Use somente as regras aplicáveis ao objetivo e aos fatos confirmados. "
            "Não combine alternativas incompatíveis, não invente informações ou parâmetros "
            "para preencher lacunas e não trate referências de RM como repetições com RIR. "
            "Cite somente os trechos realmente fornecidos em knowledge. "
            "O resultado é um teste de desenvolvimento sem validação profissional."
        ),
    }
