from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding.draft_service import (
    OnboardingDraftService,
    OnboardingDraftValidationError,
    OnboardingNotEditableError,
    OnboardingNotFoundError,
)
from app.modules.onboarding.models import Onboarding
from app.modules.onboarding.schema import OnboardingDraftUpdate, TrainingExperience
from app.modules.onboarding.service import (
    ClientInvitationUnavailableError,
    InvitationDeliveryError,
    InvitationSummary,
    OnboardingInvitationService,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
invitation_service = OnboardingInvitationService()
draft_service = OnboardingDraftService()

Administrator = Annotated[
    AuthenticatedIdentity,
    Depends(require_roles(get_authenticated_identity, "admin")),
]
ClientUser = Annotated[
    AuthenticatedIdentity,
    Depends(require_roles(get_authenticated_identity, "client")),
]
DatabaseSession = Annotated[Session, Depends(get_database_session)]


class InvitationResponse(BaseModel):
    id: UUID
    delivery_status: str
    expires_at: str
    sent_at: str | None


class InvitationAccessResponse(BaseModel):
    """Public token state without account, client, or onboarding data."""

    status: Literal["valid", "expired", "invalid", "redeemed"]


class OnboardingDraftResponse(BaseModel):
    """Own-client structured data; no client/account fields are exposed."""

    status: Literal["draft", "completed"]
    training_goal: str | None
    training_experience: TrainingExperience | None
    height_cm: int | None
    weight_kg: Decimal | None
    has_limitations_or_complaints: bool | None
    limitations_or_complaints: str | None
    uses_medications: bool | None
    medications: str | None
    has_health_conditions: bool | None
    health_conditions: str | None


def response_from_onboarding(onboarding: Onboarding) -> OnboardingDraftResponse:
    return OnboardingDraftResponse(
        status=onboarding.status,
        training_goal=onboarding.training_goal,
        training_experience=onboarding.training_experience,
        height_cm=onboarding.height_cm,
        weight_kg=onboarding.weight_kg,
        has_limitations_or_complaints=onboarding.has_limitations_or_complaints,
        limitations_or_complaints=onboarding.limitations_or_complaints,
        uses_medications=onboarding.uses_medications,
        medications=onboarding.medications,
        has_health_conditions=onboarding.has_health_conditions,
        health_conditions=onboarding.health_conditions,
    )


def response_from_summary(summary: InvitationSummary) -> InvitationResponse:
    return InvitationResponse(
        id=summary.id,
        delivery_status=summary.delivery_status,
        expires_at=summary.expires_at.isoformat(),
        sent_at=summary.sent_at.isoformat() if summary.sent_at else None,
    )


@router.post(
    "/clients/{client_id}/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_onboarding_invitation(
    client_id: UUID, session: DatabaseSession, administrator: Administrator
) -> InvitationResponse:
    """Issue and send the newest usable onboarding invitation for one client."""
    del administrator
    try:
        return response_from_summary(invitation_service.issue(session, client_id))
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        ) from None
    except ClientInvitationUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Client identity is not provisioned and active",
        ) from None
    except InvitationDeliveryError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Onboarding invitation delivery failed",
        ) from None


@router.get("/access", response_model=InvitationAccessResponse)
def validate_onboarding_access(token: str, session: DatabaseSession) -> InvitationAccessResponse:
    """Validate a mailed token passively; a GET request never consumes it."""
    access = invitation_service.validate_access(session, token)
    return InvitationAccessResponse(status=access.status)


@router.post("/access/redemptions", response_model=InvitationAccessResponse)
def redeem_onboarding_access(token: str, session: DatabaseSession) -> InvitationAccessResponse:
    """Consume a valid token only after the recipient intentionally starts onboarding."""
    if invitation_service.consume_access_after_redemption(session, token):
        return InvitationAccessResponse(status="redeemed")
    return InvitationAccessResponse(status="invalid")


@router.get("/me", response_model=OnboardingDraftResponse)
def get_own_onboarding_draft(
    session: DatabaseSession, client_user: ClientUser
) -> OnboardingDraftResponse:
    """Return only the authenticated client's draft, creating its empty draft when needed."""
    try:
        scope = draft_service.resolve_client_scope(session, client_user.subject)
        return response_from_onboarding(draft_service.get_or_create_draft(session, scope))
    except OnboardingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated"
        ) from None


@router.patch("/me", response_model=OnboardingDraftResponse)
def save_own_onboarding_draft(
    payload: OnboardingDraftUpdate,
    session: DatabaseSession,
    client_user: ClientUser,
) -> OnboardingDraftResponse:
    """Save a partial, validated draft without exposing a client-selected ID path."""
    try:
        scope = draft_service.resolve_client_scope(session, client_user.subject)
        return response_from_onboarding(draft_service.save_draft(session, scope, payload))
    except OnboardingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated"
        ) from None
    except OnboardingNotEditableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed onboarding cannot be changed",
        ) from None
    except OnboardingDraftValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from None
