from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training.current_service import CurrentTrainingPlanService
from app.modules.training.generation_service import (
    CompletedOnboardingRequiredError,
    InitialTrainingGenerationService,
    InvalidTrainingGenerationError,
    TrainingGenerationUnavailableError,
)
from app.modules.training.models import TrainingPlanItem, TrainingPlanVersion
from app.modules.training.schema import (
    ManualPlanCreate,
    ProposalUpdate,
    TrainingPlanVersionInput,
    VersionAction,
)
from app.modules.training.service import (
    ConcurrentTrainingUpdateError,
    ImmutableTrainingVersionError,
    InvalidTrainingTransitionError,
    TrainingLifecycleService,
    TrainingVersionNotFoundError,
)

router = APIRouter(prefix="/training", tags=["training"])
service = TrainingLifecycleService()
generation_service = InitialTrainingGenerationService()
current_service = CurrentTrainingPlanService()
Instructor = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "instructor"))
]
DatabaseSession = Annotated[Session, Depends(get_database_session)]


def version_response(session: Session, version: TrainingPlanVersion) -> dict[str, object]:
    return {
        "plan_id": str(version.plan_id),
        "version_number": version.version_number,
        "status": version.status,
        "name": version.name,
        "objective": version.objective,
        "origin": version.origin,
        "created_by": version.created_by,
        "created_at": version.created_at.isoformat(),
        "approved_by": version.approved_by,
        "approved_at": version.approved_at.isoformat() if version.approved_at else None,
        "revision": version.revision,
        "items": [
            {
                "exercise_name": item.exercise_name,
                "sets": item.sets,
                "repetitions": item.repetitions,
                "load_guidance": item.load_guidance,
                "rest_seconds": item.rest_seconds,
                "position": item.position,
            }
            for item in session.scalars(
                select(TrainingPlanItem)
                .where(TrainingPlanItem.version_id == version.id)
                .order_by(TrainingPlanItem.position)
            )
        ],
    }


def lifecycle_error(error: Exception) -> HTTPException:
    if isinstance(error, TrainingVersionNotFoundError):
        return HTTPException(404, "Training version not found")
    if isinstance(error, ConcurrentTrainingUpdateError):
        return HTTPException(409, "Training version changed; reload before saving")
    if isinstance(error, ImmutableTrainingVersionError):
        return HTTPException(409, "Approved, current, and historical versions are immutable")
    return HTTPException(409, "Invalid training version transition")


@router.get("/current")
def get_current_plan(
    session: DatabaseSession,
    client_user: Annotated[
        AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "client"))
    ],
) -> dict[str, object | None]:
    """Return the current version for only the caller's resolved client."""
    version = current_service.find_for_subject(session, client_user.subject)
    return {"plan": version_response(session, version) if version else None}


@router.post("/initial-proposal", status_code=status.HTTP_201_CREATED)
def generate_initial_proposal(
    session: DatabaseSession,
    client_user: Annotated[
        AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "client"))
    ],
) -> dict[str, object]:
    """Create only an AI proposal for the authenticated client's completed onboarding."""
    try:
        proposal = generation_service.generate_for_subject(session, client_user.subject)
        return version_response(session, proposal)
    except CompletedOnboardingRequiredError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Completed onboarding is required before generating a training proposal",
        ) from None
    except InvalidTrainingGenerationError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI training proposal could not be validated",
        ) from None
    except TrainingGenerationUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI training generation is temporarily unavailable",
        ) from None


@router.post("/plans", status_code=status.HTTP_201_CREATED)
def create_manual_proposal(
    payload: ManualPlanCreate, session: DatabaseSession, instructor: Instructor
) -> dict[str, object]:
    try:
        version = service.create_proposal(
            session,
            client_id=UUID(payload.client_id),
            data=payload,
            created_by=instructor.subject,
            origin="instructor",
        )
        return version_response(session, version)
    except ValueError:
        raise HTTPException(422, "Invalid client identifier") from None


@router.patch("/plans/{plan_id}/versions/{version_number}")
def revise_proposal(
    plan_id: UUID,
    version_number: int,
    payload: ProposalUpdate,
    session: DatabaseSession,
    instructor: Instructor,
) -> dict[str, object]:
    try:
        return version_response(
            session,
            service.revise(
                session,
                plan_id=plan_id,
                version_number=version_number,
                data=payload,
                actor=instructor.subject,
                expected_revision=payload.expected_revision,
            ),
        )
    except (
        TrainingVersionNotFoundError,
        ImmutableTrainingVersionError,
        ConcurrentTrainingUpdateError,
        InvalidTrainingTransitionError,
    ) as error:
        raise lifecycle_error(error) from None


@router.post("/plans/{plan_id}/versions/{version_number}/approve")
def approve_proposal(
    plan_id: UUID,
    version_number: int,
    payload: VersionAction,
    session: DatabaseSession,
    instructor: Instructor,
) -> dict[str, object]:
    try:
        return version_response(
            session,
            service.approve(
                session,
                plan_id=plan_id,
                version_number=version_number,
                actor=instructor.subject,
                expected_revision=payload.expected_revision,
            ),
        )
    except (
        TrainingVersionNotFoundError,
        ImmutableTrainingVersionError,
        ConcurrentTrainingUpdateError,
        InvalidTrainingTransitionError,
    ) as error:
        raise lifecycle_error(error) from None


@router.post("/plans/{plan_id}/versions/{version_number}/activate")
def activate_approved(
    plan_id: UUID,
    version_number: int,
    payload: VersionAction,
    session: DatabaseSession,
    instructor: Instructor,
) -> dict[str, object]:
    try:
        return version_response(
            session,
            service.activate(
                session,
                plan_id=plan_id,
                version_number=version_number,
                expected_revision=payload.expected_revision,
            ),
        )
    except (
        TrainingVersionNotFoundError,
        ImmutableTrainingVersionError,
        ConcurrentTrainingUpdateError,
        InvalidTrainingTransitionError,
    ) as error:
        raise lifecycle_error(error) from None


@router.post(
    "/plans/{plan_id}/versions/{version_number}/revisions", status_code=status.HTTP_201_CREATED
)
def create_revision(
    plan_id: UUID,
    version_number: int,
    payload: TrainingPlanVersionInput,
    session: DatabaseSession,
    instructor: Instructor,
) -> dict[str, object]:
    try:
        return version_response(
            session,
            service.create_revision(
                session,
                plan_id=plan_id,
                version_number=version_number,
                data=payload,
                actor=instructor.subject,
            ),
        )
    except (
        TrainingVersionNotFoundError,
        ImmutableTrainingVersionError,
        ConcurrentTrainingUpdateError,
        InvalidTrainingTransitionError,
    ) as error:
        raise lifecycle_error(error) from None
