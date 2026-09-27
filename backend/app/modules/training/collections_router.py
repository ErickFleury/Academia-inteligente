"""Instructor collection transport; no client-selected identity grants access."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.training import collections_service as collections
from app.modules.training.review_service import review_metadata
from app.modules.training.router import (
    DatabaseSession,
    Instructor,
    lifecycle_error,
    version_response,
)
from app.modules.training.service import TrainingLifecycleError

router = APIRouter(prefix="/training/collections", tags=["training"])
Limit = Annotated[int, Query(ge=1, le=100)]
Cursor = Annotated[str | None, Query(max_length=300)]


class CloneCurrent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    discard_id: UUID | None = None
    discard_revision: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_exact_discard(self):
        if (self.discard_id is None) != (self.discard_revision is None):
            raise ValueError("An exact draft revision is required")
        return self


@router.get("")
def collection(
    session: DatabaseSession,
    instructor: Instructor,
    mine: bool = False,
    search: Annotated[str, Query(max_length=300)] = "",
    responsible: UUID | None = None,
    start: date | None = None,
    end: date | None = None,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    try:
        return collections.current_collection(
            session,
            subject=instructor.subject,
            mine=mine,
            search=search,
            responsible=responsible,
            start=start,
            end=end,
            cursor=cursor,
            limit=limit,
        )
    except ValueError:
        raise HTTPException(422, "Invalid collection filters or cursor") from None


@router.get("/responsible")
def responsible(
    session: DatabaseSession, instructor: Instructor, cursor: UUID | None = None, limit: Limit = 100
):
    return collections.responsible_options(session, cursor, limit)


@router.get("/{version_id}")
def detail(version_id: UUID, session: DatabaseSession, instructor: Instructor):
    try:
        return collections.approved_detail(session, version_id)
    except TrainingLifecycleError as error:
        raise lifecycle_error(error) from None


@router.get("/{version_id}/history")
def history(
    version_id: UUID,
    session: DatabaseSession,
    instructor: Instructor,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    try:
        return collections.approved_history(session, version_id, cursor, limit)
    except ValueError:
        raise HTTPException(422, "Invalid history cursor") from None
    except TrainingLifecycleError as error:
        raise lifecycle_error(error) from None


@router.post("/{version_id}/draft", status_code=201)
def clone(
    version_id: UUID, payload: CloneCurrent, session: DatabaseSession, instructor: Instructor
):
    try:
        version = collections.clone_current(
            session, version_id, actor=instructor.subject, **payload.model_dump()
        )
        return dict(version_response(session, version), **review_metadata(session, version))
    except collections.ExistingDraftConflict as error:
        session.rollback()
        raise HTTPException(409, {"code": "existing_draft", "draft": error.draft}) from None
    except TrainingLifecycleError as error:
        session.rollback()
        raise lifecycle_error(error) from None
