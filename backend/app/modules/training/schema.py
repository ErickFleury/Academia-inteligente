from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

from app.integrations.ai import KnowledgeStatus
from app.modules.training.prescription_modes import ProjectionDetails

PlanOrigin = Literal["ai", "instructor"]
PlanStatus = Literal["proposal", "approved", "current", "superseded"]


class KnowledgeCitation(BaseModel):
    chunk_id: str
    source_id: str
    title: str
    url: str
    authors: list[str]
    license: str
    license_url: str
    section: str
    attribution: str | None = None
    content_note: str | None = None
    captured_at: str | None = None


class TrainingKnowledgeResponse(BaseModel):
    citations: list[KnowledgeCitation] = Field(default_factory=list)
    knowledge_status: KnowledgeStatus = "insufficient_evidence"
    knowledge_limitations: str = ""


class TrainingPlanItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    exercise_name: str = Field(min_length=1, max_length=200)
    sets: int | None = Field(gt=0, le=100)
    repetitions: str = Field(min_length=1, max_length=100)
    load_guidance: str = Field(min_length=1, max_length=500)
    rest_seconds: int | None = Field(ge=0, le=3600)
    dose_details: ProjectionDetails | None = None
    equipment_requirement: str | None = Field(default=None, max_length=200)
    equipment_model_id: UUID | None = None

    @model_validator(mode="after")
    def explicit_projection_mode(self):
        if self.dose_details is None:
            if self.sets is None or self.rest_seconds is None:
                raise ValueError("legacy_resistance_quantities_required")
        elif self.dose_details.mode != "resistance":
            if self.sets is not None or self.rest_seconds != self.dose_details.rest.seconds:
                raise ValueError("projection_quantity_mismatch")
        elif self.rest_seconds is not None or self.sets != self.dose_details.group.rounds:
            raise ValueError("group_projection_quantity_mismatch")
        if self.dose_details is not None:
            from types import SimpleNamespace

            from app.modules.training.prescription_mode_validation import modality_dose_text
            from app.modules.training.prescription_modes import (
                AerobicDose,
                FlexibilityDose,
                TaskDose,
            )

            mode = self.dose_details.mode
            if mode != "resistance":
                model = {
                    "aerobic": AerobicDose,
                    "flexibility": FlexibilityDose,
                    "balance": TaskDose,
                    "functional": TaskDose,
                }[mode]
                self.repetitions = modality_dose_text(
                    SimpleNamespace(mode=mode, dose=model.model_validate(self.dose_details.dose))
                )
            else:
                from app.modules.training.prescription_contract import Duration, Repetitions
                from app.modules.training.prescription_validation import _range_text

                value = self.dose_details.dose
                dose = (
                    Repetitions if value.get("kind") == "repetitions" else Duration
                ).model_validate(value)
                self.repetitions = _range_text(dose.minimum, dose.maximum) + (
                    " s" if dose.kind == "duration_seconds" else ""
                )
        return self

    @model_serializer(mode="wrap")
    def serialize_projection(self, handler):
        data = handler(self)
        if self.dose_details is None:
            data.pop("dose_details", None)
        return data


class TrainingPlanVersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=2000)
    items: list[TrainingPlanItemInput] = Field(min_length=1, max_length=100)


class ManualPlanCreate(TrainingPlanVersionInput):
    client_id: str


class ProposalUpdate(TrainingPlanVersionInput):
    expected_revision: int = Field(ge=1)


class VersionAction(BaseModel):
    expected_revision: int = Field(ge=1)


class AppendToCurrentAction(VersionAction):
    current_version_id: UUID
    expected_current_revision: int = Field(ge=1)
    selected_positions: list[Annotated[int, Field(strict=True, ge=1)]] = Field(
        min_length=1, max_length=100
    )


AdaptationOperationType = Literal["add", "remove", "replace", "adjust"]


class AdaptationExerciseCandidate(TrainingPlanItemInput):
    equipment_requirement: str | None = Field(default=None, max_length=200)
    equipment_model_id: UUID | None = None
    is_existing_exercise: bool


class AdaptationOperationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_type: AdaptationOperationType
    target_position: int | None = Field(default=None, ge=1)
    item: AdaptationExerciseCandidate | None = None


class AdaptationGenerationInput(BaseModel):
    source_client_request_id: UUID
    client_request_id: UUID
    reason: str = Field(min_length=1, max_length=2000)


class AdaptationClientDecision(BaseModel):
    accept: bool
