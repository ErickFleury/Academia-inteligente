from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.modules.clients import instructor_service as service
from app.modules.training.review_service import review_metadata
from app.modules.training.router import (
    DatabaseSession,
    Instructor,
    lifecycle_error,
    version_response,
)
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.service import TrainingLifecycleError

router = APIRouter(prefix="/instructor/clients", tags=["instructor-clients"])


@router.get("")
def search(
    session: DatabaseSession,
    instructor: Instructor,
    search: Annotated[str, Query(max_length=300)] = "",
    onboarding: Literal["all", "completed", "incomplete"] = "all",
    training: Literal["all", "none", "pending", "current"] = "all",
    responsibility: Literal["all", "none", "me", "specific"] = "all",
    responsible: UUID | None = None,
    cursor: Annotated[str | None, Query(max_length=2500)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
):
    try:
        return service.search_clients(
            session,
            subject=instructor.subject,
            search=search,
            onboarding=onboarding,
            training=training,
            responsibility=responsibility,
            responsible=responsible,
            cursor=cursor,
            limit=limit,
        )
    except ValueError:
        raise HTTPException(422, "Invalid client search filters") from None


@router.get("/{client_id}")
def workspace(client_id: UUID, session: DatabaseSession, instructor: Instructor):
    try:
        return service.workspace(session, client_id)
    except TrainingLifecycleError as error:
        raise lifecycle_error(error) from None


@router.post("/{client_id}/draft", status_code=201)
def create(
    client_id: UUID,
    payload: TrainingPlanVersionInput,
    session: DatabaseSession,
    instructor: Instructor,
):
    try:
        version = service.create_first_draft(session, client_id, instructor.subject, payload)
        return dict(version_response(session, version), **review_metadata(session, version))
    except TrainingLifecycleError as error:
        session.rollback()
        raise lifecycle_error(error) from None
