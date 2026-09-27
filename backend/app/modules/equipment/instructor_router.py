from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.modules.equipment.service import (
    EquipmentNotFoundError,
    EquipmentService,
    EquipmentStateConflictError,
)
from app.modules.training.router import DatabaseSession, Instructor

router = APIRouter(prefix="/instructor/equipment", tags=["instructor-equipment"])
service = EquipmentService()
Limit = Annotated[int, Query(ge=1, le=100)]


class OperationalStateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operational_state: Literal["operational", "out_of_order"]
    expected_revision: int = Field(ge=1)


@router.get("")
def models(
    session: DatabaseSession,
    instructor: Instructor,
    cursor: UUID | None = None,
    limit: Limit = 20,
    query: Annotated[str, Query(max_length=200)] = "",
):
    return service.instructor_models(session, cursor, limit, query)


@router.get("/usable-models")
def usable_models(
    session: DatabaseSession, instructor: Instructor, cursor: UUID | None = None, limit: Limit = 20
):
    rows = service.usable_models_with_units(session, cursor=cursor, limit=limit + 1)
    return {
        "items": [{"id": str(model.id), "name": model.name} for model in rows[:limit]],
        "next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None,
    }


@router.get("/{model_id}/units")
def units(
    model_id: UUID,
    session: DatabaseSession,
    instructor: Instructor,
    cursor: UUID | None = None,
    limit: Limit = 20,
):
    try:
        return service.instructor_units(session, model_id, cursor, limit)
    except EquipmentNotFoundError:
        raise HTTPException(404, "Equipment not found") from None


@router.patch("/units/{unit_id}/operational-state")
def update(
    unit_id: UUID, payload: OperationalStateUpdate, session: DatabaseSession, instructor: Instructor
):
    try:
        return service.set_operational_state(
            session, unit_id, payload.operational_state, payload.expected_revision
        )
    except EquipmentNotFoundError:
        raise HTTPException(404, "Equipment not found") from None
    except EquipmentStateConflictError:
        raise HTTPException(409, "Equipment state changed or unit is inactive; reload") from None
