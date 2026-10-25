"""Typed modality quantities; no dose defaults or clinical assumptions."""

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from app.modules.training.prescription_policy import Record

Side = Literal["left", "right", "each_side", "bilateral"]


class RestPrescription(Record):
    kind: Literal[
        "not_applicable",
        "between_sets",
        "between_attempts",
        "between_holds",
        "between_tasks",
        "after_pair",
        "after_exercise",
        "after_round",
    ]
    seconds: int | None = Field(default=None, strict=True, ge=0, le=3600)

    @model_validator(mode="after")
    def explicit_applicability(self):
        if (self.kind == "not_applicable") != (self.seconds is None):
            raise ValueError("rest_applicability_mismatch")
        return self


class AerobicDose(Record):
    kind: Literal["aerobic"]
    minutes: Decimal = Field(gt=0)
    intensity: Literal["moderate", "vigorous"]
    observation_fact: str = Field(min_length=1)


class FlexibilityDose(Record):
    kind: Literal["flexibility"]
    holds: int = Field(strict=True, gt=0)
    hold_seconds: Decimal = Field(gt=0)
    side: Side
    target: str = Field(min_length=1, max_length=100)
    intensity_instruction_key: str = Field(min_length=1)


class TaskDose(Record):
    kind: Literal["balance", "functional"]
    attempts: int = Field(strict=True, gt=0)
    completed: int | None = Field(default=None, strict=True, ge=0)
    unit: Literal["seconds", "steps", "repetitions"]
    amount: Decimal = Field(gt=0)
    side: Side
    support_instruction_key: str = Field(min_length=1)
    supervision_instruction_key: str = Field(min_length=1)
    intensity_instruction_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def completed_attempts(self):
        if self.completed is not None and self.completed > self.attempts:
            raise ValueError("completed_attempts_exceed_attempts")
        if self.unit in ("steps", "repetitions") and self.amount != self.amount.to_integral_value():
            raise ValueError("integer_task_count_required")
        return self


class ExerciseGroup(Record):
    group_id: str = Field(min_length=1)
    kind: Literal["pair", "circuit"]
    rounds: int = Field(strict=True, gt=0)
    order: int = Field(strict=True, gt=0)
    rest: RestPrescription

    @model_validator(mode="after")
    def rest_relation(self):
        allowed = {"pair": {"after_pair"}, "circuit": {"after_exercise", "after_round"}}
        if self.rest.kind not in allowed[self.kind]:
            raise ValueError("group_rest_relation_mismatch")
        return self


class ProjectionDetails(Record):
    mode: Literal["resistance", "aerobic", "flexibility", "balance", "functional"]
    dose: dict
    rest: RestPrescription | None = None
    group: ExerciseGroup | None = None

    @model_validator(mode="after")
    def consistent_mode(self):
        models = {
            "aerobic": AerobicDose,
            "flexibility": FlexibilityDose,
            "balance": TaskDose,
            "functional": TaskDose,
        }
        if self.mode in models:
            value = models[self.mode].model_validate(self.dose)
            if value.kind != self.mode or self.group is not None:
                raise ValueError("projection_mode_mismatch")
            required = {
                "aerobic": "not_applicable",
                "flexibility": "between_holds",
                "balance": "between_attempts",
                "functional": "between_tasks",
            }
            if self.rest is None or self.rest.kind != required[self.mode]:
                raise ValueError("projection_rest_mismatch")
        elif self.group is None:
            raise ValueError("group_projection_required")
        return self
