from typing import Annotated
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
