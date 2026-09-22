from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PlanOrigin = Literal["ai", "instructor"]
PlanStatus = Literal["proposal", "approved", "current", "superseded"]


class TrainingPlanItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    exercise_name: str = Field(min_length=1, max_length=200)
    sets: int = Field(gt=0, le=100)
    repetitions: str = Field(min_length=1, max_length=100)
    load_guidance: str = Field(min_length=1, max_length=500)
    rest_seconds: int = Field(ge=0, le=3600)


class TrainingPlanVersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=2000)
    items: list[TrainingPlanItemInput] = Field(min_length=1, max_length=100)


class ManualPlanCreate(TrainingPlanVersionInput):
    client_id: str


class ProposalUpdate(TrainingPlanVersionInput):
    expected_revision: int = Field(ge=1)


class VersionAction(BaseModel):
    expected_revision: int = Field(ge=1)
