from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_database_session
from app.modules.biometrics.access import AccessService, attempt_result, owned_attempt
from app.modules.biometrics.config import BiometricConfig
from app.modules.biometrics.enrollment import (
    EnrollmentService,
    enrollment_status,
    identity_binding,
    owned_session,
)
from app.modules.biometrics.enrollment import session_status as staging_status
from app.modules.biometrics.history import event_history, provider_status
from app.modules.biometrics.images import read_capture
from app.modules.biometrics.passages import PassageService
from app.modules.clients.models import Account, PersonProfile
from app.modules.clients.service import normalize_cpf, normalize_email
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


def get_access_service():
    return AccessService(BiometricConfig.from_environment())


Access = Annotated[AccessService, Depends(get_access_service)]


def get_passage_service(service: Access):
    return PassageService(service.config, service.provider)


Passages = Annotated[PassageService, Depends(get_passage_service)]


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


class IdentityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=320)
    cpf: str = Field(max_length=32)


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command_id: UUID


class AttemptRequest(CommandRequest):
    direction: Literal["entry", "exit"]


class AttemptResponse(BaseModel):
    attempt_id: UUID
    direction: Literal["entry", "exit"]
    status: str
    result_code: str
    captures: int
    expires_at: str
    client_id: UUID | None
    client_name: str | None
    release_request_id: UUID | None
    release_mode: Literal["simulated"] | None
    can_retry: bool


class StateResponse(BaseModel):
    client_id: UUID
    client_name: str
    inside: bool
    revision: int
    client_active: bool


class EventResponse(BaseModel):
    id: str
    kind: Literal["audit", "correction"]
    occurred_at: str
    operation: str
    result: str
    client_id: UUID | None
    person_name: str | None
    direction: Literal["entry", "exit"] | None
    reason: str | None


class HistoryResponse(BaseModel):
    items: list[EventResponse]
    next_cursor: str | None


class ProviderStatusResponse(BaseModel):
    mode: Literal["disabled", "pilot"]
    available: bool
    cleanup_pending: int


@router.get("/events", response_model=HistoryResponse)
def recent_events(
    administrator: Administrator,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    client_id: UUID | None = None,
    result: Annotated[str | None, Query(max_length=60, pattern=r"^[a-z_]+$")] = None,
    direction: Literal["entry", "exit"] | None = None,
):
    return event_history(
        session, limit=limit, cursor=cursor, client_id=client_id, result=result, direction=direction
    )


@router.get("/provider-status", response_model=ProviderStatusResponse)
def get_provider_status(administrator: Administrator, session: DatabaseSession, service: Access):
    return provider_status(session, service)


class CorrectionRequest(CommandRequest):
    client_id: UUID
    inside: bool
    expected_revision: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=1000)


class PassageResponse(BaseModel):
    status: Literal["confirmed"]
    attempt_id: UUID
    passage_event_id: UUID
    state: StateResponse
    occupancy: int


class CorrectionResponse(BaseModel):
    status: Literal["corrected", "unchanged"]
    correction_id: UUID
    state: StateResponse
    occupancy: int


@router.get("/clients/{client_id}/state", response_model=StateResponse)
def get_client_state(
    client_id: UUID, administrator: Administrator, session: DatabaseSession, service: Passages
):
    return service.state(session, client_id)


@router.post("/access-attempts/{attempt_id}/passage", response_model=PassageResponse)
def confirm_passage(
    attempt_id: UUID,
    payload: CommandRequest,
    administrator: Administrator,
    session: DatabaseSession,
    service: Passages,
):
    return service.confirm(session, administrator.subject, attempt_id, payload.command_id)


@router.post("/state-corrections", response_model=CorrectionResponse)
def correct_state(
    payload: CorrectionRequest,
    administrator: Administrator,
    session: DatabaseSession,
    service: Passages,
):
    return service.correct(session, administrator.subject, **payload.model_dump())


@router.post("/pilot-heartbeat")
def pilot_heartbeat(
    payload: CommandRequest,
    administrator: Administrator,
    session: DatabaseSession,
    service: Passages,
):
    return service.heartbeat(session, administrator.subject, payload.command_id)


@router.post("/access-attempts", response_model=AttemptResponse)
def start_attempt(
    payload: AttemptRequest, administrator: Administrator, session: DatabaseSession, service: Access
):
    return service.create(session, administrator.subject, **payload.model_dump())


@router.get("/access-attempts/{attempt_id}", response_model=AttemptResponse)
def get_attempt(attempt_id: UUID, administrator: Administrator, session: DatabaseSession):
    return attempt_result(session, owned_attempt(session, attempt_id, administrator.subject))


@router.post("/access-attempts/{attempt_id}/capture", response_model=AttemptResponse)
async def recognize(
    attempt_id: UUID,
    request: Request,
    administrator: Administrator,
    session: DatabaseSession,
    service: Access,
):
    command_id, image = await read_capture(request)
    return await run_in_threadpool(
        service.capture, session, administrator.subject, attempt_id, command_id, image
    )


@router.post("/access-attempts/{attempt_id}/cancellation", response_model=AttemptResponse)
def cancel_attempt(
    attempt_id: UUID,
    payload: CommandRequest,
    administrator: Administrator,
    session: DatabaseSession,
    service: Access,
):
    return service.cancel(session, administrator.subject, attempt_id, payload.command_id)


@router.post("/enrollment-readiness")
def readiness(payload: IdentityRequest, administrator: Administrator, session: DatabaseSession):
    # POST keeps CPF/e-mail out of URL/access logs; this is a read, not a command.
    identity_binding(payload.email, payload.cpf)
    person = session.scalar(
        select(PersonProfile)
        .join(Account)
        .where(
            Account.email == normalize_email(payload.email),
            PersonProfile.cpf == normalize_cpf(payload.cpf),
        )
    )
    return (
        enrollment_status(session, person.account_id)
        if person
        else {
            "person_id": None,
            "status": "missing_or_revoked",
            "revision": 0,
            "cleanup_pending": False,
        }
    )


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
