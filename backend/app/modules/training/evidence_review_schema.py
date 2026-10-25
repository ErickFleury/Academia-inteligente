"""Review input declarations and public/private transport boundaries."""

from datetime import UTC, date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.training.owner_approval import OwnerApproval

Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Text = Annotated[str, Field(min_length=3, max_length=4000)]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)


class DomainJudgment(Record):
    domain: Text
    judgment: Text
    source_locator: Text


class OutcomeCertainty(Record):
    outcome: Text
    certainty: Literal["not_assessed", "very_low", "low", "moderate", "high"]
    rationale: Text


class JudgmentInput(Record):
    request_id: UUID
    expected_artifact_sha256: Hash
    function: Literal["methodological", "professional", "adjudicator"]
    decision: Literal["approved", "changes_requested", "rejected"]
    scope: Text
    method_and_version: Text
    rationale: str = Field(min_length=20, max_length=8000)
    competence: Text
    conflicts: Text
    judgments: list[DomainJudgment] = Field(min_length=1, max_length=100)
    outcomes: list[OutcomeCertainty] = Field(min_length=1, max_length=100)
    personally_performed: bool = Field(strict=True)
    independent_assessment: bool = Field(default=False, strict=True)
    resolves_judgment_ids: list[UUID] = Field(default_factory=list, max_length=100)
    supersedes_judgment_id: UUID | None = None
    review_due_at: date | None = None

    @model_validator(mode="after")
    def intentional_review(self):
        if not self.personally_performed:
            raise ValueError("personal_review_attestation_required")
        if self.decision == "approved" and not self.independent_assessment:
            raise ValueError("approval_requires_independent_assessment")
        if self.decision == "approved" and any(
            o.certainty == "not_assessed" for o in self.outcomes
        ):
            raise ValueError("approval_requires_assessed_outcomes")
        if self.decision == "approved" and (
            self.review_due_at is None or self.review_due_at <= datetime.now(UTC).date()
        ):
            raise ValueError("approval_requires_future_review_deadline")
        if self.function == "adjudicator" and len(set(self.resolves_judgment_ids)) < 2:
            raise ValueError("adjudication_requires_referenced_reviews")
        if self.function != "adjudicator" and self.resolves_judgment_ids:
            raise ValueError("review_cannot_impersonate_adjudication")
        return self


class ArtifactSection(Record):
    label: str
    text: str


class JudgmentOut(Record):
    id: UUID
    artifact_id: str
    artifact_sha256: Hash
    reviewer_name: str
    function: str
    decision: str
    created_at: datetime
    assessment: dict
    is_current: bool
    can_supersede: bool
    human_review_record: dict


class ArtifactOut(Record):
    id: str
    kind: Literal["source", "rule_proposal", "prescription_bundle", "evaluation_protocol"]
    title: str
    sha256: Hash
    approval_ready: bool
    missing_items: list[str]
    sections: list[ArtifactSection]
    content: dict | None = None
    judgments: list[JudgmentOut]
    independence_complete: bool
    owner_approval: OwnerApproval | None = None


class EvaluationProtocol(Record):
    title: str = Field(min_length=5, max_length=200)
    scope: Text
    methods: Text
    decision_thresholds: str = Field(min_length=20, max_length=8000)
    repeat_count: int = Field(strict=True, gt=0)
    maximum_writer_calls: int = Field(strict=True, gt=0)
    maximum_runtime_seconds: int = Field(strict=True, gt=0)


class SealedCase(Record):
    case_id: str = Field(min_length=1, max_length=100)
    cohort: str = Field(min_length=1, max_length=200)
    scenario: Text
    reference_judgment: Text
    critical: bool = Field(strict=True)


class SealInput(Record):
    request_id: UUID
    artifact_hashes: dict[str, Hash] = Field(min_length=1, max_length=50)
    protocol: EvaluationProtocol
    cases: list[SealedCase] = Field(min_length=1, max_length=500)
    synthetic_only: bool = Field(strict=True)
    independent_and_unexposed: bool = Field(strict=True)
    understands_no_release: bool = Field(strict=True)

    @model_validator(mode="after")
    def custody_attestations(self):
        if not all(
            (self.synthetic_only, self.independent_and_unexposed, self.understands_no_release)
        ):
            raise ValueError("custody_attestations_required")
        identifiers = [case.case_id for case in self.cases]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("duplicate_case_identifier")
        if self.protocol.maximum_writer_calls < len(self.cases) * self.protocol.repeat_count:
            raise ValueError("budget_below_prespecified_case_repetitions")
        return self


class SealOut(Record):
    id: UUID
    custodian_name: str
    protocol: EvaluationProtocol
    artifact_hashes: dict[str, Hash]
    attestations: dict[str, bool]
    case_count: int
    payload_sha256: Hash
    created_at: datetime
    can_read_cases: bool
    status: Literal["custody_registered_evaluation_and_release_pending"] = (
        "custody_registered_evaluation_and_release_pending"
    )


class SealCasesOut(Record):
    id: UUID
    payload_sha256: Hash
    cases: list[SealedCase]
