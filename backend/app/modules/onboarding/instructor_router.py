from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.modules.onboarding.draft_service import (
    OnboardingAlreadyCompletedError,
    OnboardingDraftValidationError,
    OnboardingNotFoundError,
)
from app.modules.onboarding.instructor_service import InstructorOnboardingService
from app.modules.onboarding.router import OnboardingDraftResponse, response_from_onboarding
from app.modules.onboarding.schema import OnboardingDraftUpdate
from app.modules.training.router import DatabaseSession, Instructor

router = APIRouter(
    prefix="/instructor/clients/{client_id}/onboarding", tags=["instructor-onboarding"]
)
service = InstructorOnboardingService()


def error_response(error):
    if isinstance(error, OnboardingNotFoundError):
        return HTTPException(404, "Onboarding target not found")
    if isinstance(error, OnboardingAlreadyCompletedError):
        return HTTPException(409, "Onboarding already completed")
    return HTTPException(422, "Onboarding validation failed")


@router.get("", response_model=OnboardingDraftResponse)
def read(client_id: UUID, session: DatabaseSession, instructor: Instructor):
    try:
        return response_from_onboarding(service.read(session, instructor.subject, client_id))
    except OnboardingNotFoundError as error:
        raise error_response(error) from None


@router.patch(
    "",
    response_model=OnboardingDraftResponse,
    openapi_extra={
        "requestBody": {
            "content": {"application/json": {"schema": OnboardingDraftUpdate.model_json_schema()}}
        }
    },
)
def update(client_id: UUID, payload: dict, session: DatabaseSession, instructor: Instructor):
    try:
        return response_from_onboarding(
            service.update(session, instructor.subject, client_id, payload)
        )
    except (OnboardingNotFoundError, OnboardingDraftValidationError) as error:
        raise error_response(error) from None


@router.post("/completion", response_model=OnboardingDraftResponse)
def complete(client_id: UUID, session: DatabaseSession, instructor: Instructor):
    try:
        return response_from_onboarding(service.complete(session, instructor.subject, client_id))
    except (
        OnboardingNotFoundError,
        OnboardingDraftValidationError,
        OnboardingAlreadyCompletedError,
    ) as error:
        raise error_response(error) from None
