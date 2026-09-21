"""Authoritative reusable structured onboarding validation boundary."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

TrainingExperience = Literal["none", "beginner", "intermediate", "advanced"]


def normalize_required_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("must not be blank")
    return normalized


def normalize_optional_detail(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class OnboardingDraftUpdate(BaseModel):
    """Partial draft update; final completion validation belongs to Task 12."""

    training_goal: str | None = Field(default=None, max_length=500)
    training_experience: TrainingExperience | None = None
    height_cm: int | None = Field(default=None, gt=0, le=300)
    weight_kg: Decimal | None = Field(default=None, gt=0, le=500)
    has_limitations_or_complaints: bool | None = None
    limitations_or_complaints: str | None = Field(default=None, max_length=2000)
    uses_medications: bool | None = None
    medications: str | None = Field(default=None, max_length=2000)
    has_health_conditions: bool | None = None
    health_conditions: str | None = Field(default=None, max_length=2000)

    @field_validator("training_goal")
    @classmethod
    def validate_training_goal(cls, value: str | None) -> str | None:
        return normalize_required_text(value) if value is not None else None

    @field_validator(
        "limitations_or_complaints", "medications", "health_conditions", mode="after"
    )
    @classmethod
    def normalize_details(cls, value: str | None) -> str | None:
        return normalize_optional_detail(value)

    @field_validator("weight_kg")
    @classmethod
    def validate_weight_precision(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value.as_tuple().exponent < -2:
            raise ValueError("must have at most two decimal places")
        return value


class OnboardingCompletionData(BaseModel):
    """The stricter prerequisite contract consumed by later completion work."""

    training_goal: str = Field(max_length=500)
    training_experience: TrainingExperience
    height_cm: int = Field(gt=0, le=300)
    weight_kg: Decimal = Field(gt=0, le=500)
    has_limitations_or_complaints: bool
    limitations_or_complaints: str | None = Field(default=None, max_length=2000)
    uses_medications: bool
    medications: str | None = Field(default=None, max_length=2000)
    has_health_conditions: bool
    health_conditions: str | None = Field(default=None, max_length=2000)

    @field_validator("training_goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        return normalize_required_text(value)

    @field_validator(
        "limitations_or_complaints", "medications", "health_conditions", mode="after"
    )
    @classmethod
    def normalize_completion_details(cls, value: str | None) -> str | None:
        return normalize_optional_detail(value)

    @field_validator("weight_kg")
    @classmethod
    def validate_completion_weight_precision(cls, value: Decimal) -> Decimal:
        if value.as_tuple().exponent < -2:
            raise ValueError("must have at most two decimal places")
        return value

    @model_validator(mode="after")
    def validate_required_conditional_details(self) -> "OnboardingCompletionData":
        conditional_fields = (
            (self.has_limitations_or_complaints, self.limitations_or_complaints),
            (self.uses_medications, self.medications),
            (self.has_health_conditions, self.health_conditions),
        )
        if any(enabled and not detail for enabled, detail in conditional_fields):
            raise ValueError("a detail is required when its corresponding answer is yes")
        return self
