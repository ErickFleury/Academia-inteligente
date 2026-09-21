from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding.service import (
    ClientInvitationUnavailableError,
    InvitationDeliveryError,
    InvitationSummary,
    OnboardingInvitationService,
)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
invitation_service = OnboardingInvitationService()

Administrator = Annotated[
    AuthenticatedIdentity,
    Depends(require_roles(get_authenticated_identity, "admin")),
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
