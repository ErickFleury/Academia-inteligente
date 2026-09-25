import os
import secrets
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.occupancy.service import (
    ConflictingEventError,
    InvalidCorrectionError,
    OccupancyService,
    UnknownClientReferenceError,
)

router = APIRouter(prefix="/occupancy", tags=["occupancy"])
service = OccupancyService()
DatabaseSession = Annotated[Session, Depends(get_database_session)]
Operator = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "admin", "attendant"))
]


class PassageInput(BaseModel):
    event_id: str = Field(min_length=1, max_length=255)
    occurred_at: datetime
    checkpoint_id: str = Field(min_length=1, max_length=200)
    direction: Literal["entry", "exit"]
    event_type: Literal["passage_confirmed"]
    client_reference: str = Field(min_length=1, max_length=1024)


class HeartbeatInput(BaseModel):
    checkpoint_id: str = Field(min_length=1, max_length=200)
    occurred_at: datetime


class CorrectionInput(BaseModel):
    adjustment: int = Field(ge=-10000, le=10000)
    reason: str = Field(min_length=1, max_length=1000)


class OccupancyResponse(BaseModel):
    occupancy: int
    status: Literal["current", "stale"]
    updated_at: datetime | None


def integration_authorized(
    integration_secret: Annotated[str | None, Header(alias="X-Access-Integration-Secret")] = None,
) -> None:
    configured_secret = os.environ.get("ACCESS_EVENT_INTEGRATION_SECRET", "")
    if not configured_secret:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Access-event integration is unavailable"
        )
    if integration_secret is None or not secrets.compare_digest(
        integration_secret, configured_secret
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthenticated")


@router.post(
    "/passage-events",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(integration_authorized)],
)
def ingest_passage(payload: PassageInput, session: DatabaseSession) -> dict[str, bool]:
    try:
        _, created = service.record_passage(
            session,
            event_id=payload.event_id.strip(),
            occurred_at=payload.occurred_at,
            checkpoint_id=payload.checkpoint_id.strip(),
            direction=payload.direction,
            event_type=payload.event_type,
            client_reference=payload.client_reference,
        )
    except UnknownClientReferenceError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown client reference"
        ) from None
    except ConflictingEventError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflicting access event") from None
    return {"accepted": True, "created": created}


@router.post(
    "/source-heartbeats",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(integration_authorized)],
)
def ingest_heartbeat(payload: HeartbeatInput, session: DatabaseSession) -> None:
    service.record_heartbeat(session, payload.checkpoint_id.strip(), payload.occurred_at)


@router.post("/admin/corrections", status_code=status.HTTP_201_CREATED)
def create_correction(
    payload: CorrectionInput, session: DatabaseSession, operator: Operator
) -> dict[str, object]:
    try:
        correction = service.correct(
            session,
            actor_subject=operator.subject,
            adjustment=payload.adjustment,
            reason=payload.reason,
            occurred_at=datetime.now(UTC),
        )
    except InvalidCorrectionError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "A non-zero adjustment and reason are required"
        ) from None
    return {
        "id": str(correction.id),
        "adjustment": correction.adjustment,
        "reason": correction.reason,
        "occurred_at": correction.occurred_at,
    }


@router.get("", response_model=OccupancyResponse)
def get_occupancy(session: DatabaseSession) -> OccupancyResponse:
    snapshot = service.snapshot(session)
    return OccupancyResponse(
        occupancy=snapshot.occupancy, status=snapshot.status, updated_at=snapshot.updated_at
    )
