"""Administrator-only nonfinancial dashboard API."""

from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.dashboard.service import DashboardService
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity

router = APIRouter(prefix="/admin/dashboard", tags=["administrative dashboard"])
service = DashboardService()

Administrator = Annotated[
    AuthenticatedIdentity,
    Depends(require_roles(get_authenticated_identity, "admin")),
]
DatabaseSession = Annotated[Session, Depends(get_database_session)]


class ActiveClientsResponse(BaseModel):
    active_clients: int


class AttendanceWeekResponse(BaseModel):
    week_start: date
    confirmed_entries: int


class AttendanceResponse(BaseModel):
    weeks: list[AttendanceWeekResponse]


class OccupancyResponse(BaseModel):
    occupancy: int
    status: Literal["current", "stale"]
    updated_at: datetime | None


@router.get("/active-clients", response_model=ActiveClientsResponse)
def get_active_clients(
    session: DatabaseSession, administrator: Administrator
) -> ActiveClientsResponse:
    """Return a non-identifying count for authorized administrators only."""
    del administrator
    return ActiveClientsResponse(active_clients=service.active_client_count(session))


@router.get("/attendance", response_model=AttendanceResponse)
def get_attendance(session: DatabaseSession, administrator: Administrator) -> AttendanceResponse:
    """Return aggregate confirmed-entry counts grouped into recent UTC weeks."""
    del administrator
    return AttendanceResponse(
        weeks=[
            AttendanceWeekResponse(
                week_start=week.week_start, confirmed_entries=week.confirmed_entries
            )
            for week in service.attendance_history(session)
        ]
    )


@router.get("/occupancy", response_model=OccupancyResponse)
def get_occupancy(session: DatabaseSession, administrator: Administrator) -> OccupancyResponse:
    """Return the existing anonymous occupancy projection to an administrator."""
    del administrator
    snapshot = service.occupancy(session)
    return OccupancyResponse(
        occupancy=snapshot.occupancy,
        status=snapshot.status,
        updated_at=snapshot.updated_at,
    )
