"""Task 47 development accounting helpers; no prescription eligibility decision.

Inputs are explicit synthetic/review records, not parsed writer prose. This module
is disconnected from production training and supplies no real muscle weights.
"""

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.modules.training.prescription_policy import (
    ApprovalBasis,
    ExerciseDictionary,
    HumanReview,
    Record,
    require_approval_basis,
)

Key = Annotated[str, Field(min_length=1)]
Count = Annotated[int, Field(strict=True, gt=0)]


class RepetitionCount(Record):
    minimum: Count
    maximum: Count

    @model_validator(mode="after")
    def ordered(self):
        if self.minimum > self.maximum:
            raise ValueError("inverted_repetition_range")
        return self


class AccountingItem(Record):
    item_id: Key
    session_id: Key
    exercise_key: Key
    variation_key: Key
    sets: Count
    set_role: Literal["working", "warmup", "unknown"]
    repetitions: RepetitionCount | None = None
    repetition_convention: Literal["total", "per_side", "unknown"] = "unknown"
    external_load_kg: Decimal | None = Field(default=None, ge=0)
    load_convention: Literal["total_external", "per_side", "unknown"] = "unknown"


class MuscleAccountingMapping(Record):
    exercise_key: Key
    variation_key: Key
    direct_muscles: list[Key] = Field(default_factory=list)
    indirect_muscles: list[Key] = Field(default_factory=list)
    indirect_weights: dict[Key, Annotated[Decimal, Field(ge=0, le=1)]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def explicit_unique_classification(self):
        direct, indirect = set(self.direct_muscles), set(self.indirect_muscles)
        if (
            len(direct) != len(self.direct_muscles)
            or len(indirect) != len(self.indirect_muscles)
            or direct & indirect
            or not direct | indirect
            or set(self.indirect_weights) - indirect
        ):
            raise ValueError("invalid_muscle_accounting_classification")
        return self


class AccountingMethod(Record):
    version: Key
    dictionary_version: Key
    status: Literal["pending", "approved", "revoked"] = "pending"
    mappings: list[MuscleAccountingMapping] = Field(default_factory=list)
    review_records: list[HumanReview] = Field(default_factory=list)
    review_due_at: date | None = None
    approval_basis: ApprovalBasis = "independent_review"
    owner_authorization_id: str | None = None
    supported_modes: list[
        Literal["resistance", "aerobic", "flexibility", "balance", "functional"]
    ] = Field(default_factory=lambda: ["resistance"])

    @model_validator(mode="after")
    def unique_and_reviewed(self):
        keys = [(m.exercise_key, m.variation_key) for m in self.mappings]
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate_accounting_mapping")
        if self.status == "approved":
            require_approval_basis(
                self.review_records, self.approval_basis, self.owner_authorization_id
            )
            if (
                (not self.mappings and "resistance" in self.supported_modes)
                or not self.review_due_at
                or self.review_due_at <= datetime.now(UTC).date()
            ):
                raise ValueError("accounting_review_incomplete_or_expired")
        return self


class SessionOccurrence(Record):
    occurrence_id: Key
    session_id: Key
    day_index: int = Field(strict=True, ge=0, le=6)


class DevelopmentSchedule(Record):
    occurrences: list[SessionOccurrence] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_occurrences(self):
        identifiers = [o.occurrence_id for o in self.occurrences]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("duplicate_schedule_occurrence")
        return self


def _summarize(items: list[AccountingItem], mappings: dict) -> dict:
    working = [item for item in items if item.set_role == "working"]
    unknown_sets = any(item.set_role == "unknown" for item in items)
    working_sets = None if unknown_sets else sum(item.sets for item in working)
    direct, indirect = defaultdict(int), defaultdict(int)
    fractional = defaultdict(Decimal)
    missing_weights, missing_mapping = set(), False
    for item in working:
        mapping = mappings.get((item.exercise_key, item.variation_key))
        if mapping is None:
            missing_mapping = True
            continue
        for muscle in mapping.direct_muscles:
            direct[muscle] += item.sets
            fractional[muscle] += item.sets
        for muscle in mapping.indirect_muscles:
            indirect[muscle] += item.sets
            if muscle in mapping.indirect_weights:
                fractional[muscle] += item.sets * mapping.indirect_weights[muscle]
            else:
                missing_weights.add(muscle)
    muscle_unknown = unknown_sets or missing_mapping
    muscles = (
        None
        if muscle_unknown
        else {
            muscle: {
                "direct_sets": direct[muscle],
                "indirect_sets": indirect[muscle],
                "weighted_sets": None if muscle in missing_weights else fractional[muscle],
            }
            for muscle in sorted(set(direct) | set(indirect))
        }
    )
    # Load/repetition quantities stay per exercise AND variation. Neither
    # unilateral multipliers nor cross-equipment tonnage are inferred.
    grouped = defaultdict(list)
    for item in items:
        grouped[(item.exercise_key, item.variation_key)].append(item)
    exercises = []
    for (exercise, variation), entries in sorted(grouped.items()):
        classified = all(e.set_role != "unknown" for e in entries)
        active = [e for e in entries if e.set_role == "working"]
        rep_known = classified and all(
            e.repetitions is not None and e.repetition_convention == "total" for e in active
        )
        load_known = rep_known and all(
            e.external_load_kg is not None and e.load_convention == "total_external" for e in active
        )
        repetitions = (
            None
            if not rep_known
            else {
                bound: sum(e.sets * getattr(e.repetitions, bound) for e in active)
                for bound in ("minimum", "maximum")
            }
        )
        load = (
            None
            if not load_known
            else {
                bound: sum(
                    (e.sets * getattr(e.repetitions, bound) * e.external_load_kg for e in active),
                    Decimal(0),
                )
                for bound in ("minimum", "maximum")
            }
        )
        exercises.append(
            {
                "exercise_key": exercise,
                "variation_key": variation,
                "working_sets": sum(e.sets for e in active) if classified else None,
                "repetitions": repetitions,
                "external_load_volume_kg": load,
            }
        )
    return {
        "working_sets": working_sets,
        "warmup_sets": sum(item.sets for item in items if item.set_role == "warmup"),
        "muscles": muscles,
        "exercises": exercises,
        "issues": [
            reason
            for failed, reason in (
                (unknown_sets, "unclassified_sets"),
                (missing_mapping, "missing_muscle_mapping"),
                (bool(missing_weights), "indirect_weights_not_defined"),
            )
            if failed
        ],
    }


def summarize_development_workload(
    *,
    items: list[AccountingItem],
    dictionary: ExerciseDictionary,
    method: AccountingMethod,
    schedule: DevelopmentSchedule | None = None,
) -> dict:
    """Calculate explicit development quantities, never a supported/passing plan."""
    if method.dictionary_version != dictionary.version:
        raise ValueError("accounting_dictionary_version_mismatch")
    if dictionary.status == "revoked" or method.status == "revoked":
        raise ValueError("revoked_development_artifact")
    known = {exercise.key: set(exercise.variations) for exercise in dictionary.exercises}
    for item in items:
        if item.variation_key not in known.get(item.exercise_key, set()):
            raise ValueError("unknown_exercise_or_variation")
    for mapping in method.mappings:
        if mapping.variation_key not in known.get(mapping.exercise_key, set()):
            raise ValueError("unknown_accounting_exercise_or_variation")
    if not items or len({item.item_id for item in items}) != len(items):
        raise ValueError("empty_or_duplicate_accounting_items")
    mappings = {(m.exercise_key, m.variation_key): m for m in method.mappings}
    sessions = defaultdict(list)
    for item in items:
        sessions[item.session_id].append(item)
    weekly = None
    if schedule is not None:
        scheduled = {occurrence.session_id for occurrence in schedule.occurrences}
        if scheduled != set(sessions):
            raise ValueError("schedule_session_coverage_mismatch")
        weekly = _summarize(
            [
                item
                for occurrence in schedule.occurrences
                for item in sessions[occurrence.session_id]
            ],
            mappings,
        )
        weekly["session_occurrences"] = len(schedule.occurrences)
    return {
        "purpose": "development_only_accounting",
        "dictionary_version": dictionary.version,
        "dictionary_status": dictionary.status,
        "accounting_method_version": method.version,
        "accounting_status": method.status,
        "sessions": {key: _summarize(value, mappings) for key, value in sorted(sessions.items())},
        "seven_day_totals": weekly,
        "enabled_cohorts": [],
    }
