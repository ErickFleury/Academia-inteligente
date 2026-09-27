from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_database_session
from app.modules.biometrics.config import BiometricConfig
from app.modules.biometrics.enrollment import EnrollmentService, enrollment_status, owned_session
from app.modules.biometrics.enrollment import session_status as staging_status
from app.modules.biometrics.images import read_capture
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity

router = APIRouter(prefix="/biometrics", tags=["biometrics"])
Administrator = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "admin"))
]
DatabaseSession = Annotated[Session, Depends(get_database_session)]


def get_enrollment_service():
    return EnrollmentService(BiometricConfig.from_environment())


Service = Annotated[EnrollmentService, Depends(get_enrollment_service)]


class SessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: UUID
    email: str = Field(max_length=320)
    cpf: str = Field(max_length=32)
    role: Literal["client", "employee", "replacement"]
    person_id: UUID | None = None
    expected_revision: int = Field(default=0, ge=0)


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: UUID
    expected_revision: int = Field(ge=0)


class ReplacementRequest(RevisionRequest):
    session_id: UUID


class EnrollmentSessionResponse(BaseModel):
    session_id: UUID
    status: Literal["awaiting_capture", "capturing", "ready", "rejected", "expired", "consumed"]
    result_code: str
    expires_at: str


class EnrollmentResponse(BaseModel):
    person_id: UUID
    status: Literal["enabled", "missing_or_revoked"]
    revision: int
    cleanup_pending: bool


@router.post("/enrollment-sessions", response_model=EnrollmentSessionResponse)
def create_session(
    payload: SessionRequest,
    administrator: Administrator,
    session: DatabaseSession,
    service: Service,
):
    return service.create(session, administrator.subject, **payload.model_dump())


@router.get("/enrollment-sessions/{session_id}", response_model=EnrollmentSessionResponse)
def get_session(session_id: UUID, administrator: Administrator, session: DatabaseSession):
    return staging_status(owned_session(session, session_id, administrator.subject))


@router.post("/enrollment-sessions/{session_id}/capture", response_model=EnrollmentSessionResponse)
async def capture(
    session_id: UUID,
    request: Request,
    administrator: Administrator,
    session: DatabaseSession,
    service: Service,
):
    # Authorization resolves before any body is accepted or decoded.
    command_id, image = await read_capture(request)
    return await run_in_threadpool(
        service.capture, session, administrator.subject, session_id, command_id, image
    )


@router.get("/people/{person_id}/enrollment", response_model=EnrollmentResponse)
def get_enrollment(person_id: UUID, administrator: Administrator, session: DatabaseSession):
    return enrollment_status(session, person_id)


@router.post("/people/{person_id}/enrollment/replacement", response_model=EnrollmentResponse)
def replace(
    person_id: UUID,
    payload: ReplacementRequest,
    administrator: Administrator,
    session: DatabaseSession,
    service: Service,
):
    return service.replace(session, administrator.subject, person_id, **payload.model_dump())


@router.post("/people/{person_id}/enrollment/revocation", response_model=EnrollmentResponse)
def revoke(
    person_id: UUID,
    payload: RevisionRequest,
    administrator: Administrator,
    session: DatabaseSession,
    service: Service,
):
    return service.revoke(session, administrator.subject, person_id, **payload.model_dump())
