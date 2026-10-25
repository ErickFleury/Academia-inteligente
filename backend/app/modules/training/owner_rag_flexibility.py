"""Reuse typed holds/side projections for owner-assisted flexibility drafts."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.training.prescription_contract import PrescriptionRejection
from app.modules.training.prescription_modes import (
    FlexibilityDose,
    ProjectionDetails,
    RestPrescription,
)

INTENSITY = "comfortable_range_without_pain"


class FlexibilityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exercise_name: str
    holds: int = Field(strict=True, gt=0)
    hold_seconds: Decimal = Field(gt=0)
    side: Literal["each_side", "bilateral", "left", "right"]
    rest_seconds: int = Field(strict=True, ge=0, le=3600)
    intensity_instruction_key: Literal["comfortable_range_without_pain"]
    equipment_requirement: None = None
    equipment_model_id: None = None


def is_flexibility(context):
    return context.get("owner_rag_basis", {}).get("goal_family") == "mobility_flexibility"


def constrain_item(schema, context):
    from app.modules.training.owner_rag_schema import wire_names

    schema.clear()
    schema.update(
        type="object",
        additionalProperties=False,
        properties={
            "exercise_name": {"type": "string", "enum": wire_names(context)},
            "holds": {"type": "integer", "minimum": 1},
            "hold_seconds": {"type": "number", "exclusiveMinimum": 0},
            "side": {"type": "string", "enum": ["each_side", "bilateral", "left", "right"]},
            "rest_seconds": {"type": "integer", "minimum": 0, "maximum": 3600},
            "intensity_instruction_key": {"type": "string", "enum": [INTENSITY]},
            "equipment_requirement": {"type": "null"},
            "equipment_model_id": {"type": "null"},
        },
    )
    schema["required"] = list(schema["properties"])


def materialize_item(row, exercise):
    if "holds" not in row:
        return row
    from app.modules.training.owner_rag_load import LOAD_GUIDANCE

    item = FlexibilityItem.model_validate(row)
    dose = FlexibilityDose(
        kind="flexibility",
        holds=item.holds,
        hold_seconds=item.hold_seconds,
        side=item.side,
        target=exercise["groups"][0],
        intensity_instruction_key=item.intensity_instruction_key,
    )
    details = ProjectionDetails(
        mode="flexibility",
        dose=dose.model_dump(mode="json"),
        rest=RestPrescription(kind="between_holds", seconds=item.rest_seconds),
    )
    return {
        "exercise_name": item.exercise_name,
        "sets": None,
        # TrainingPlanItemInput renders the authoritative typed dose, not this wire text.
        "repetitions": "Duração por lado",
        "load_guidance": LOAD_GUIDANCE[exercise["load_capability"]],
        "rest_seconds": item.rest_seconds,
        "dose_details": details.model_dump(mode="json"),
        "equipment_requirement": None,
        "equipment_model_id": None,
    }


def validate_item(item, exercise, context, position):
    flexibility = is_flexibility(context)
    if (
        (exercise.get("mode", "resistance") == "flexibility") != flexibility
        or (flexibility and (item.dose_details is None or item.dose_details.mode != "flexibility"))
        or (
            not flexibility
            and item.dose_details is not None
            and item.dose_details.mode != "resistance"
        )
    ):
        raise PrescriptionRejection(
            "insufficient_support",
            "invalid_typed_candidate",
            issues=[
                {
                    "position": position,
                    "field": "dose_details",
                    "reason": "requested_modality_required",
                }
            ],
        )
    if flexibility:
        dose = FlexibilityDose.model_validate(item.dose_details.dose)
        if dose.target != exercise["groups"][0] or dose.intensity_instruction_key != INTENSITY:
            raise PrescriptionRejection("insufficient_support", "invalid_typed_candidate")
