"""Typed prescription contracts shared by isolated and gated operational adapters."""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.modules.training.prescription_accounting import DevelopmentSchedule, RepetitionCount
from app.modules.training.prescription_modes import (
    AerobicDose,
    ExerciseGroup,
    FlexibilityDose,
    RestPrescription,
    TaskDose,
)
from app.modules.training.prescription_policy import Dimension, Record

Key = Annotated[str, Field(min_length=1)]
Positive = Annotated[Decimal, Field(gt=0)]


def record_hash(value) -> str:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class NumericRange(Record):
    minimum: Decimal | None
    maximum: Decimal | None
    minimum_inclusive: bool | None = True
    maximum_inclusive: bool | None = True

    @model_validator(mode="after")
    def ordered(self):
        for endpoint in ("minimum", "maximum"):
            flag = endpoint + "_inclusive"
            if getattr(self, endpoint) is None:
                if flag in self.model_fields_set and getattr(self, flag) is not None:
                    raise ValueError("open_endpoint_has_no_inclusive_flag")
                setattr(self, flag, None)
            elif getattr(self, flag) is None:
                raise ValueError("finite_endpoint_requires_comparison_flag")
        if (
            self.minimum is not None
            and self.maximum is not None
            and (
                self.minimum > self.maximum
                or self.minimum == self.maximum
                and not (self.minimum_inclusive and self.maximum_inclusive)
            )
        ):
            raise ValueError("inverted_numeric_range")
        if self.minimum is None and self.maximum is None:
            raise ValueError("empty_numeric_range")
        return self

    def contains(self, value):
        if value is None or isinstance(value, bool):
            return False
        value = Decimal(str(value))
        return bool(
            value.is_finite()
            and (
                self.minimum is None
                or value > self.minimum
                or self.minimum_inclusive
                and value == self.minimum
            )
            and (
                self.maximum is None
                or value < self.maximum
                or self.maximum_inclusive
                and value == self.maximum
            )
        )


class Repetitions(RepetitionCount):
    kind: Literal["repetitions"] = "repetitions"


class Duration(NumericRange):
    kind: Literal["duration_seconds"] = "duration_seconds"

    @model_validator(mode="after")
    def positive(self):
        if self.minimum is None or self.maximum is None or self.minimum <= 0:
            raise ValueError("nonpositive_duration")
        return self


class NumericIntensity(NumericRange):
    mode: Literal["rir", "rpe", "percent_1rm", "external_load_kg"]
    scale_key: Key
    baseline_fact: str | None = None

    @model_validator(mode="after")
    def baseline_dependency(self):
        if self.minimum is None or self.maximum is None or self.minimum < 0:
            raise ValueError("negative_intensity")
        if self.mode in ("percent_1rm", "external_load_kg") and not self.baseline_fact:
            raise ValueError("missing_measured_baseline_reference")
        return self


class InstructionIntensity(Record):
    mode: Literal["approved_relative_instruction"] = "approved_relative_instruction"
    instruction_key: Key


class Progression(Record):
    instruction_key: Key
    condition_fact: Key
    action_key: Key
    amount: Positive
    unit: Literal["kg", "repetitions", "seconds", "sets"]
    stop_instruction_key: Key
    regression_instruction_key: Key


class TypedPrescriptionItem(Record):
    item_id: Key
    exercise_key: Key
    variation_key: Key
    equipment_model_id: UUID | None = None
    sets: int | None = Field(default=None, strict=True, gt=0)
    dose: Annotated[
        Repetitions | Duration | AerobicDose | FlexibilityDose | TaskDose,
        Field(discriminator="kind"),
    ]
    intensity: (
        Annotated[NumericIntensity | InstructionIntensity, Field(discriminator="mode")] | None
    ) = None
    rest_seconds: int | None = Field(default=None, strict=True, ge=0)
    rest: RestPrescription | None = None
    group: ExerciseGroup | None = None
    progression: Progression
    decision_rules: dict[Dimension, Key]
    note_instruction_keys: list[Key] = Field(default_factory=list)
    calculated_load: "CalculatedLoad | None" = None

    @property
    def mode(self):
        return (
            self.dose.kind
            if self.dose.kind in {"aerobic", "flexibility", "balance", "functional"}
            else "resistance"
        )

    @model_validator(mode="after")
    def explicit_mode(self):
        if self.mode == "resistance":
            if self.sets is None or self.intensity is None:
                raise ValueError("resistance_quantities_required")
            if self.group is None and self.rest_seconds is None:
                raise ValueError("resistance_rest_required")
            if self.group is not None and (
                self.rest_seconds is not None or self.sets != self.group.rounds
            ):
                raise ValueError("group_dose_or_rest_mismatch")
            if self.rest is not None:
                raise ValueError("unexpected_resistance_rest_object")
        else:
            if (
                self.sets is not None
                or self.intensity is not None
                or self.rest_seconds is not None
                or self.group is not None
                or self.calculated_load is not None
            ):
                raise ValueError("incompatible_modality_quantities")
            required = {
                "aerobic": "not_applicable",
                "flexibility": "between_holds",
                "balance": "between_attempts",
                "functional": "between_tasks",
            }
            if self.rest is None or self.rest.kind != required[self.mode]:
                raise ValueError("modality_rest_relation_required")
        return self


class TypedSession(Record):
    session_id: Key
    label: str = Field(pattern=r"^[A-G]$")
    items: list[TypedPrescriptionItem] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def consolidated_exercises(self):
        keys = [item.exercise_key for item in self.items]
        if len(set(keys)) != len(keys):
            raise ValueError("competing_prescriptions_in_one_session")
        groups = {}
        for item in self.items:
            if item.group is not None:
                groups.setdefault(item.group.group_id, []).append(item.group)
        for members in groups.values():
            if (
                members[0].kind == "pair"
                and len(members) != 2
                or members[0].kind == "circuit"
                and len(members) < 2
            ):
                raise ValueError("incomplete_exercise_group")
            if {m.order for m in members} != set(range(1, len(members) + 1)) or any(
                (m.kind, m.rounds, m.rest) != (members[0].kind, members[0].rounds, members[0].rest)
                for m in members
            ):
                raise ValueError("inconsistent_exercise_group")
        return self


class TypedPrescription(Record):
    schema_version: Literal[1, 2] = 1
    scope: Literal["session_sheet", "plan_revision"]
    input_snapshot_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_version: Key
    dictionary_version: Key
    accounting_method_version: Key
    expected_revision: int | None = Field(default=None, strict=True, ge=1)
    sessions: list[TypedSession] = Field(min_length=1, max_length=7)
    schedule: DevelopmentSchedule | None = None

    @model_validator(mode="after")
    def unique_ids(self):
        sessions = [s.session_id for s in self.sessions]
        labels = [s.label for s in self.sessions]
        items = [item.item_id for s in self.sessions for item in s.items]
        if len(set(sessions)) != len(sessions) or len(set(labels)) != len(labels):
            raise ValueError("duplicate_prescription_session")
        if len(set(items)) != len(items):
            raise ValueError("duplicate_prescription_item")
        if self.scope == "session_sheet" and len(self.sessions) != 1:
            raise ValueError("session_sheet_scope_mismatch")
        if self.schema_version == 1 and any(
            i.mode != "resistance" or i.group is not None for s in self.sessions for i in s.items
        ):
            raise ValueError("version_two_modality_required")
        return self


class ConfirmedFact(Record):
    value: str | bool | int | Decimal
    source: Literal["onboarding", "request"]
    source_id: Key
    source_revision: Key
    confirmed_by: Literal["client_owner", "instructor"]
    source_actor_role: Literal["client_owner", "instructor"] = "client_owner"
    observed_at: AwareDatetime
    confirmed_at: AwareDatetime | None = None
    valid_until: AwareDatetime | None = None
    conflict: bool = False
    measurement_method: str | None = None
    measurement_unit: Literal["kg"] | None = None
    exercise_key: str | None = None
    variation_key: str | None = None
    measurement_convention: Literal["total_external", "per_side"] | None = None
    source_actor_subject: str | None = None
    confirmed_by_subject: str | None = None


class InputSnapshot(Record):
    schema_version: Literal[1] = 1
    client_id: UUID
    facts: dict[Key, ConfirmedFact]
    schedule: DevelopmentSchedule | None = None

    @model_validator(mode="after")
    def minimized_fields(self):
        allowed = {
            "training_goal",
            "training_experience",
            "height_cm",
            "weight_kg",
            "has_limitations_or_complaints",
            "limitations_or_complaints",
            "uses_medications",
            "medications",
            "has_health_conditions",
            "health_conditions",
            "adult_eligibility",
            "schedule_confirmed",
            "baseline_capacity",
            "progression_observed",
            "observed_control",
            "support_available",
            "supervision_confirmed",
            "reported_talk_test",
            "completed_attempts",
            "sport",
            "sport_event",
            "goal_priorities",
        }
        if set(self.facts) - allowed:
            raise ValueError("unapproved_snapshot_field")
        boolean_keys = {
            "has_limitations_or_complaints",
            "uses_medications",
            "has_health_conditions",
            "adult_eligibility",
            "schedule_confirmed",
            "progression_observed",
            "observed_control",
            "support_available",
            "supervision_confirmed",
        }
        unavailable_onboarding = {
            "adult_eligibility",
            "schedule_confirmed",
            "baseline_capacity",
            "progression_observed",
            "observed_control",
            "support_available",
            "supervision_confirmed",
            "reported_talk_test",
            "completed_attempts",
            "sport",
            "sport_event",
            "goal_priorities",
        }
        for key, fact in self.facts.items():
            if key in {"sport", "sport_event", "goal_priorities"} and (
                not isinstance(fact.value, str) or not fact.value.strip() or len(fact.value) > 500
            ):
                raise ValueError("invalid_request_scope_fact")
            if key == "completed_attempts" and (
                not isinstance(fact.value, int) or isinstance(fact.value, bool) or fact.value < 0
            ):
                raise ValueError("completed_attempts_count_required")
            if key == "reported_talk_test" and fact.value not in ("talk_not_sing", "few_words"):
                raise ValueError("documented_talk_test_required")
            if key in unavailable_onboarding and fact.source == "onboarding":
                raise ValueError("fact_not_available_in_onboarding")
            if key in boolean_keys and not isinstance(fact.value, bool):
                raise ValueError("boolean_fact_required")
            if key == "training_goal" and (
                not isinstance(fact.value, str) or not fact.value.strip() or len(fact.value) > 500
            ):
                raise ValueError("invalid_goal_fact")
            if key == "training_experience" and fact.value not in {
                "none",
                "beginner",
                "intermediate",
                "advanced",
            }:
                raise ValueError("invalid_experience_fact")
            if key in {"medications", "health_conditions", "limitations_or_complaints"} and (
                not isinstance(fact.value, str) or not fact.value.strip() or len(fact.value) > 2000
            ):
                raise ValueError("invalid_onboarding_detail_fact")
            if key == "baseline_capacity" and (
                isinstance(fact.value, (bool, str))
                or fact.value <= 0
                or not fact.measurement_method
                or fact.measurement_unit != "kg"
            ):
                raise ValueError("measured_baseline_provenance_required")
            if key == "height_cm" and (
                not isinstance(fact.value, int)
                or isinstance(fact.value, bool)
                or not 0 < fact.value <= 300
            ):
                raise ValueError("invalid_height_fact")
            if key == "weight_kg" and (
                isinstance(fact.value, (bool, str))
                or not 0 < fact.value <= 500
                or isinstance(fact.value, Decimal)
                and fact.value.as_tuple().exponent < -2
            ):
                raise ValueError("invalid_weight_fact")
        return self


class InputRequirement(Record):
    key: Key
    source: Literal["onboarding", "request"]
    collection_approved: bool = False
    expected_value: str | bool | int | None = None
    max_age_seconds: int | None = Field(default=None, strict=True, gt=0)
    missing_action: Literal["clarify", "unsupported"] = "clarify"
    allowed_actor_roles: list[Literal["client_owner", "instructor"]] = Field(
        default_factory=lambda: ["client_owner", "instructor"]
    )
    measurement_method: str | None = None


class InstructionDefinition(Record):
    text_pt_br: Key
    kind: Literal["relative_load", "progression", "stop", "regression", "note"]
    condition_fact: str | None = None
    action_key: str | None = None
    unit: str | None = None
    amount_bounds: NumericRange | None = None


class ExecutableRule(Record):
    decision_id: Key
    allowed_exercises: dict[Key, list[Key]] = Field(default_factory=dict)
    bounds: dict[Key, NumericRange] = Field(default_factory=dict)
    permitted_instruction_keys: list[Key] = Field(default_factory=list)
    permitted_scale_keys: list[Key] = Field(default_factory=list)
    requires_weekly_context: bool = True
    permitted_values: dict[Key, list[Key]] = Field(default_factory=dict)


class RestrictionConflict(Record):
    fact_key: Key
    expected_value: str | bool | int
    decision_id: Key
    action: Literal["stop", "regress"] = "stop"


class CalculationDefinition(Record):
    operation: Literal["percentage_load", "percentage_increase"]
    baseline_fact: Key
    exercise_key: Key
    variation_key: Key
    percent: Decimal = Field(ge=0)
    load_convention: Literal["total_external", "per_side"]
    increment_kg: Decimal | None = Field(default=None, gt=0)
    rounding: Literal["exact", "floor", "ceiling", "nearest"] | None = None

    @model_validator(mode="after")
    def explicit_rounding(self):
        if self.rounding is None or (
            self.increment_kg is None
            and self.rounding != "exact"
            or self.increment_kg is not None
            and self.rounding == "exact"
        ):
            raise ValueError("rounding_policy_required")
        return self


class CalculatedLoad(Record):
    calculation_id: Key
    claimed_kg: Decimal = Field(ge=0)


class DevelopmentExecutionContract(Record):
    purpose: Literal["isolated_development", "operational"] = "isolated_development"
    policy_id: Key
    writer_configuration_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    input_requirements: list[InputRequirement]
    rules: list[ExecutableRule]
    instructions: dict[Key, InstructionDefinition]
    documented_conflicts: list[RestrictionConflict] = Field(default_factory=list)
    calculations: dict[Key, CalculationDefinition] = Field(default_factory=dict)
    branch_id: str | None = None
    schema_version: Literal[1, 2] = 1
    vigorous_equivalence: Decimal | None = Field(default=None, gt=0)


TypedPrescription.model_rebuild()


OutcomeCategory = Literal[
    "restriction_conflict", "missing_input", "insufficient_support", "technical_unavailability"
]


class PrescriptionRejection(Exception):
    def __init__(self, category: OutcomeCategory, reason: str, *, issues=None, action=None):
        super().__init__(reason)
        self.category, self.reason = category, reason
        self.issues = issues or []
        self.action = action or ("clarify" if category == "missing_input" else "abstain")


def fact_is_current(fact: ConfirmedFact | None, now: datetime) -> bool:
    return bool(
        fact
        and not fact.conflict
        and fact.confirmed_at is not None
        and fact.observed_at <= fact.confirmed_at <= now
        and (fact.valid_until is None or now < fact.valid_until)
    )
