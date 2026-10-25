"""Task 47 draft policy records, disconnected from production generation.

These schemas validate record consistency, not a reviewer's competence or truth.
No clinical range, dictionary entry or real approval is supplied by this module.
"""

from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.onboarding.schema import TrainingExperience

Dimension = Literal[
    "selection", "volume", "intensity", "frequency", "progression", "rest", "restrictions"
]
DIMENSIONS = frozenset(
    ("selection", "volume", "intensity", "frequency", "progression", "rest", "restrictions")
)
Hash = str  # Field patterns below enforce byte-digest representation.


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


ApprovalBasis = Literal["independent_review", "owner_decision"]


def require_approval_basis(reviews, basis, authorization_id):
    if basis == "owner_decision":
        if not authorization_id or reviews:
            raise ValueError("explicit_owner_authorization_without_fabricated_reviews_required")
    else:
        if authorization_id is not None:
            raise ValueError("mixed_approval_basis")
        require_independent_reviews(reviews)


class HumanReview(Record):
    identity: str = Field(min_length=1)
    role: Literal["methodological", "professional", "adjudicator"]
    competence: str = Field(min_length=1)
    conflicts: str = Field(min_length=1)
    independent: bool
    reviewed_at: date
    artifact_sha256: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    record_locator: str = Field(min_length=1)


class EvidenceReference(Record):
    source_id: str = Field(min_length=1)
    passage_id: str = Field(min_length=1)
    artifact_sha256: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    passage_sha256: Hash = Field(pattern=r"^[a-f0-9]{64}$")
    locator: str = Field(min_length=1)
    appraisal_record: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    certainty: Literal["not_assessed", "very_low", "low", "moderate", "high"]
    certainty_rationale: str = Field(min_length=1)


class ParameterBound(Record):
    parameter: str = Field(min_length=1)
    unit: Literal[
        "sets",
        "repetitions",
        "seconds",
        "sessions_per_seven_days",
        "rir",
        "rpe",
        "percent_1rm",
        "kg",
    ]
    minimum: float = Field(strict=True)
    maximum: float = Field(strict=True)
    method: str = Field(min_length=1)
    required_input_keys: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def coherent_range(self):
        if self.minimum < 0 or self.minimum > self.maximum:
            raise ValueError("invalid_parameter_range")
        if self.unit in ("sets", "repetitions", "sessions_per_seven_days") and (
            not self.minimum.is_integer() or not self.maximum.is_integer()
        ):
            raise ValueError("integer_unit_requires_integer_bounds")
        if self.unit in ("percent_1rm", "kg") and not self.required_input_keys:
            raise ValueError("baseline_input_dependency_required")
        return self


class InputReadiness(Record):
    key: str = Field(min_length=1)
    representation: str = Field(min_length=1)
    authority: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    confirmer_role: str = Field(min_length=1)
    timestamps: str = Field(min_length=1)
    validity_rule: str = Field(min_length=1)
    permitted_audience: list[Literal["client_owner", "instructor"]] = Field(min_length=1)
    conflict_action: Literal["clarify", "professional_review"]
    missing_action: Literal["clarify", "unsupported"]
    collection_approved: bool = False


class EvidenceDecision(Record):
    id: str = Field(min_length=1)
    dimension: Dimension
    evidence: list[EvidenceReference] = Field(min_length=1)
    finding: str = Field(min_length=1)
    interpretation: str = Field(min_length=1)
    derivation: Literal["direct", "professionally_derived", "owner_derived"]
    research_rule_ids: list[str] = Field(default_factory=list)
    adoption: Literal["adopt", "adapt", "reassess"]
    compatibility_and_currency: str = Field(min_length=1)
    benefits_harms_burdens: str = Field(min_length=1)
    preferences_feasibility_alternatives: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    bounds: list[ParameterBound] = Field(default_factory=list)
    required_inputs: list[InputReadiness] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    conflict_resolution: str = Field(min_length=1)


class ExerciseDefinition(Record):
    key: str = Field(min_length=1)
    label_pt_br: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    variations: list[str] = Field(min_length=1)
    movement: str = Field(min_length=1)
    primary_muscles: list[str] = Field(min_length=1)
    equipment_constraints: list[str] = Field(default_factory=list)
    dose_modes: list[Literal["resistance", "aerobic", "flexibility", "balance", "functional"]] = (
        Field(default_factory=lambda: ["resistance"])
    )


class ExerciseDictionary(Record):
    version: str = Field(min_length=1)
    status: Literal["pending", "approved", "revoked"] = "pending"
    exercises: list[ExerciseDefinition] = Field(default_factory=list)
    review_records: list[HumanReview] = Field(default_factory=list)
    approval_basis: ApprovalBasis = "independent_review"
    owner_authorization_id: str | None = None

    @model_validator(mode="after")
    def unambiguous_names(self):
        keys, names = set(), {}
        for exercise in self.exercises:
            if exercise.key in keys:
                raise ValueError("duplicate_exercise_key")
            keys.add(exercise.key)
            for name in (exercise.label_pt_br, *exercise.aliases):
                normalized = " ".join(name.casefold().split())
                if not normalized or normalized in names and names[normalized] != exercise.key:
                    raise ValueError("ambiguous_exercise_alias")
                names[normalized] = exercise.key
        if self.status == "approved":
            if not self.exercises:
                raise ValueError("approved_dictionary_empty")
            require_approval_basis(
                self.review_records, self.approval_basis, self.owner_authorization_id
            )
        return self


def require_independent_reviews(reviews: list[HumanReview]) -> None:
    methods = [r for r in reviews if r.role == "methodological" and r.independent]
    professionals = [r for r in reviews if r.role == "professional" and r.independent]
    if not any(a.identity != b.identity for a in methods for b in professionals):
        raise ValueError("independent_methodological_and_professional_reviews_required")
    if any(r.reviewed_at > datetime.now(UTC).date() for r in reviews):
        raise ValueError("future_review")


class PrescriptionPolicy(Record):
    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    status: Literal["pending", "approved", "revoked"] = "pending"
    goal_family: str = Field(min_length=1)
    exact_goal_mappings: list[str] = Field(default_factory=list)
    experience_levels: list[TrainingExperience] = Field(min_length=1)
    population: str = Field(min_length=1)
    exclusions: list[str] = Field(default_factory=list)
    restriction_interactions: str = Field(min_length=1)
    dictionary_version: str | None = None
    accounting_method_version: str | None = None
    accounting_method: str | None = None
    decisions: list[EvidenceDecision] = Field(default_factory=list)
    review_records: list[HumanReview] = Field(default_factory=list)
    review_due_at: date | None = None
    unresolved_decisions: list[str] = Field(default_factory=list)
    approval_basis: ApprovalBasis = "independent_review"
    owner_authorization_id: str | None = None
    branch_id: str | None = None

    @model_validator(mode="after")
    def approval_record_complete(self):
        if self.status != "approved":
            return self
        require_approval_basis(
            self.review_records, self.approval_basis, self.owner_authorization_id
        )
        if not self.review_due_at or self.review_due_at <= datetime.now(UTC).date():
            raise ValueError("policy_review_expired")
        if self.unresolved_decisions or {d.dimension for d in self.decisions} != DIMENSIONS:
            raise ValueError("mandatory_policy_dimensions_unresolved")
        if len({d.id for d in self.decisions}) != len(self.decisions):
            raise ValueError("duplicate_decision_id")
        if not all(
            (
                self.dictionary_version,
                self.accounting_method_version,
                self.accounting_method,
                self.exact_goal_mappings,
            )
        ):
            raise ValueError("dictionary_accounting_and_goal_contract_required")
        for decision in self.decisions:
            if self.approval_basis == "independent_review" and any(
                e.certainty == "not_assessed" for e in decision.evidence
            ):
                raise ValueError("outcome_certainty_not_assessed")
            if self.approval_basis == "owner_decision" and (
                not self.branch_id or not decision.research_rule_ids
            ):
                raise ValueError("owner_branch_and_research_rule_links_required")
            if any(not i.collection_approved for i in decision.required_inputs):
                raise ValueError("required_input_authority_unapproved")
            inputs = {i.key for i in decision.required_inputs}
            if any(set(b.required_input_keys) - inputs for b in decision.bounds):
                raise ValueError("unresolved_bound_input_dependency")
        return self


class PolicyCatalog(Record):
    schema_version: Literal[1] = 1
    version: str = Field(min_length=1)
    policies: list[PrescriptionPolicy] = Field(default_factory=list)
    dictionary: ExerciseDictionary

    @model_validator(mode="after")
    def consistent_bundle(self):
        if len({p.id for p in self.policies}) != len(self.policies):
            raise ValueError("duplicate_policy_id")
        mappings = set()
        for policy in self.policies:
            if policy.status != "approved":
                continue
            if self.dictionary.status != "approved" or (
                policy.dictionary_version != self.dictionary.version
            ):
                raise ValueError("policy_dictionary_not_approved")
            for goal in policy.exact_goal_mappings:
                for experience in policy.experience_levels:
                    key = (goal.casefold(), experience, policy.population)
                    if key in mappings:
                        raise ValueError("conflicting_goal_policy_mapping")
                    mappings.add(key)
        return self
