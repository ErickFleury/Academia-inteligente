"""Compiled bundle authorization and honest readiness of accepted research."""

import json
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator

from app.modules.training.owner_approval import artifact_owner_approval, load_owner_approval
from app.modules.training.prescription_accounting import AccountingMethod
from app.modules.training.prescription_contract import (
    DevelopmentExecutionContract,
    PrescriptionRejection,
)
from app.modules.training.prescription_policy import PolicyCatalog, Record

ROOT = Path(__file__).parent
AUTHORIZATION_PATH = ROOT / "owner-prescription-authorizations.json"


class BundleAuthorization(Record):
    id: str = Field(min_length=1)
    basis: Literal["owner_decision"] = "owner_decision"
    owner_decision_id: str = Field(min_length=1)
    decided_on: date
    review_due_at: date
    status: Literal["approved", "revoked"]
    bundle_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_ids: list[str] = Field(min_length=1)
    dependency_hashes: dict[str, str] = Field(min_length=1)
    professional_review_performed: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self):
        if (
            len(set(self.policy_ids)) != len(self.policy_ids)
            or self.review_due_at <= self.decided_on
        ):
            raise ValueError("invalid_owner_authorization_scope_or_dates")
        return self


class AuthorizationRegistry(Record):
    schema_version: Literal[1] = 1
    authorizations: list[BundleAuthorization] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique(self):
        if len({a.id for a in self.authorizations}) != len(self.authorizations):
            raise ValueError("duplicate_owner_bundle_authorization")
        return self


def validate_bundle(bundle, *, preparing=False):
    document = deepcopy(bundle)
    if preparing:
        # Exercise the complete approved-state validators without publishing or
        # representing a pending document as an actual authorization.
        for component in [
            *document["policies"]["policies"],
            document["policies"]["dictionary"],
            document["accounting"],
        ]:
            if component.get("status") == "revoked":
                raise ValueError("revoked_component_cannot_be_prepared")
            component["status"] = "approved"
    catalog = PolicyCatalog.model_validate(document["policies"])
    accounting = AccountingMethod.model_validate(document["accounting"])
    contracts = [
        DevelopmentExecutionContract.model_validate(c) for c in bundle["execution"]["contracts"]
    ]
    policies = {p.id: p for p in catalog.policies}
    if len({c.policy_id for c in contracts}) != len(contracts) or {
        c.policy_id for c in contracts
    } != set(policies):
        raise ValueError("execution_policy_coverage_mismatch")
    if accounting.dictionary_version != catalog.dictionary.version:
        raise ValueError("accounting_dictionary_version_mismatch")
    for contract in contracts:
        policy = policies[contract.policy_id]
        if policy.status != "approved" or accounting.status != "approved":
            raise ValueError("bundle_component_not_approved")
        if policy.branch_id is not None and policy.branch_id != contract.branch_id:
            raise ValueError("execution_branch_mismatch")
        if {r.decision_id for r in contract.rules} != {d.id for d in policy.decisions}:
            raise ValueError("executable_rule_contract_incomplete")
        requirements = {r.key: r for r in contract.input_requirements}
        if (
            len(requirements) != len(contract.input_requirements)
            or not {"training_goal", "training_experience"} <= requirements.keys()
        ):
            raise ValueError("required_input_contract_missing_or_duplicate")
        if any(
            not r.collection_approved or not r.allowed_actor_roles for r in requirements.values()
        ):
            raise ValueError("required_input_authority_unapproved")
        declared_inputs = {i.key for d in policy.decisions for i in d.required_inputs}
        if declared_inputs - requirements.keys():
            raise ValueError("declared_input_not_executable")
        for definition in contract.instructions.values():
            if (
                definition.condition_fact is not None
                and definition.condition_fact not in requirements
            ):
                raise ValueError("instruction_condition_input_missing")
        for definition in contract.calculations.values():
            requirement = requirements.get(definition.baseline_fact)
            method = (
                "measured_1rm"
                if definition.operation == "percentage_load"
                else "observed_working_load"
            )
            if (
                requirement is None
                or not requirement.collection_approved
                or requirement.source != "request"
                or requirement.measurement_method != method
            ):
                raise ValueError("calculation_authority_required")
        for rule in contract.rules:
            if set(rule.permitted_instruction_keys) - contract.instructions.keys():
                raise ValueError("unknown_executable_instruction")
            decision = next(d for d in policy.decisions if d.id == rule.decision_id)
            if decision.dimension == "selection" and not rule.allowed_exercises:
                raise ValueError("exercise_choices_missing")
            for key, variations in rule.allowed_exercises.items():
                exercise = next((e for e in catalog.dictionary.exercises if e.key == key), None)
                if exercise is None or not variations or set(variations) - set(exercise.variations):
                    raise ValueError("unknown_executable_exercise_or_variation")
    return catalog, accounting, contracts


def required_dependencies(catalog):
    dependencies = set()
    for policy in catalog.policies:
        if policy.approval_basis != "owner_decision":
            continue
        for decision in policy.decisions:
            dependencies.update("rule:" + key for key in decision.research_rule_ids)
            dependencies.update("source:" + ref.source_id for ref in decision.evidence)
    return dependencies


def verify_owner_bundle(bundle, authorization_id, *, artifacts=None, now=None):
    from app.modules.training.evidence_review import current_artifacts, prescription_bundle_hash

    today = now or datetime.now(UTC).date()
    try:
        catalog, accounting, _ = validate_bundle(bundle)
        registry = AuthorizationRegistry.model_validate_json(
            AUTHORIZATION_PATH.read_text(encoding="utf-8")
        )
        record = next(a for a in registry.authorizations if a.id == authorization_id)
        owner = load_owner_approval()
        components = [*catalog.policies, catalog.dictionary, accounting]
        if any(
            c.approval_basis != "owner_decision" or c.owner_authorization_id != record.id
            for c in components
        ):
            raise ValueError("mixed_approval_basis")
        if record.status != "approved" or not record.decided_on <= today < record.review_due_at:
            raise ValueError("owner_bundle_authorization_not_current")
        if (
            owner is None
            or record.owner_decision_id != owner.decision_id
            or record.decided_on < owner.decided_on
        ):
            raise ValueError("owner_decision_reference_mismatch")
        if set(record.policy_ids) != {
            p.id for p in catalog.policies
        } or record.bundle_sha256 != prescription_bundle_hash(bundle):
            raise ValueError("owner_bundle_scope_or_content_changed")
        if (
            any(p.review_due_at > record.review_due_at for p in catalog.policies)
            or accounting.review_due_at > record.review_due_at
        ):
            raise ValueError("owner_authorization_deadline_exceeded")
        actual = artifacts if artifacts is not None else current_artifacts()
        required = required_dependencies(catalog)
        if set(record.dependency_hashes) != required:
            raise ValueError("owner_bundle_dependencies_incomplete")
        for key, digest in record.dependency_hashes.items():
            if (
                actual[key]["sha256"] != digest
                or artifact_owner_approval(actual[key], owner) is None
            ):
                raise ValueError("owner_dependency_changed_or_revoked")
        return record.model_dump(mode="json")
    except (OSError, UnicodeError, ValidationError, ValueError, KeyError, StopIteration, TypeError):
        raise PrescriptionRejection(
            "insufficient_support", "current_owner_bundle_authorization_required"
        ) from None


def readiness_matrix():
    from app.modules.training.evidence_review import current_artifacts, prescription_bundle_hash

    proposals = json.loads((ROOT / "review-rule-candidates.json").read_text(encoding="utf-8"))
    artifacts, owner = current_artifacts(), load_owner_approval()
    bundle = artifacts["prescription-bundle"]["data"]
    compiled = PolicyCatalog.model_validate(bundle["policies"])
    rules = []
    for rule in proposals["rules"]:
        artifact = artifacts["rule:" + rule["id"]]
        rules.append(
            {
                "rule_id": rule["id"],
                "sha256": artifact["sha256"],
                "owner_accepted": artifact_owner_approval(artifact, owner) is not None,
                "kind": rule["kind"],
                "sources": artifact["data"]["sources"],
                "parameters": rule["parameters"],
                "required_inputs": rule["inputs"],
                "decision_needed": rule["decision_needed"],
                "executable_policy_ids": [
                    p.id
                    for p in compiled.policies
                    if any(rule["id"] in d.research_rule_ids for d in p.decisions)
                ],
            }
        )
    from app.modules.training import owner_rag

    try:
        rag_authorization = owner_rag.authorization()
        rag_ready = True
    except PrescriptionRejection:
        rag_authorization, rag_ready = None, False
    return {
        "version": "prescription-remediation-1",
        "professional_review_performed": False,
        "owner_rag": {
            "enabled": owner_rag.enabled(),
            "authorized": rag_ready,
            "decision_id": rag_authorization["decision_id"] if rag_authorization else None,
            "independent_evaluation_required": False,
            "professional_review_performed": False,
            "compiled_prescription_qualification": False,
        },
        "bundle_sha256": prescription_bundle_hash(bundle),
        "missing_items": artifacts["prescription-bundle"]["missing_items"],
        "rules": rules,
        "source_readiness": [
            {
                "source_id": a["id"][7:],
                "owner_accepted": artifact_owner_approval(a, owner) is not None,
                "passage_count": len(a["data"].get("chunks", [])),
                "artifact_provenance_available": bool(
                    a["data"].get("provenance", {}).get("artifact_sha256")
                ),
                "technical_status": a["data"].get("review_status"),
            }
            for a in artifacts.values()
            if a["kind"] == "source"
        ],
        "profiles": [
            {
                **p,
                "compiled_policy_ids": [
                    c.id
                    for c in compiled.policies
                    if c.goal_family == p["goal_family"] and c.status == "approved"
                ],
            }
            for p in proposals["profiles"]
        ],
        "enabled_cohorts": [],
    }
