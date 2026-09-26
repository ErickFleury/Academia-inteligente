from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.presence.service import PresenceClientNotFoundError, ProfilePresenceService

router = APIRouter(prefix="/profile-presence", tags=["profile-presence"])
service = ProfilePresenceService()
DatabaseSession = Annotated[Session, Depends(get_database_session)]
ClientUser = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "client"))
]


class PresencePreferenceInput(BaseModel):
    enabled: bool


class PresenceResponse(BaseModel):
    sharing_enabled: bool
    currently_present: bool


def response_for(session: Session, subject: str) -> PresenceResponse:
    try:
        presence = service.get_own(session, subject)
    except PresenceClientNotFoundError:
        raise HTTPException(status_code=401, detail="Authenticated client not found") from None
    return PresenceResponse(**presence.__dict__)


@router.get("/me", response_model=PresenceResponse)
def get_own_presence(session: DatabaseSession, client: ClientUser) -> PresenceResponse:
    return response_for(session, client.subject)


@router.patch("/me", response_model=PresenceResponse)
def update_own_presence(
    payload: PresencePreferenceInput, session: DatabaseSession, client: ClientUser
) -> PresenceResponse:
    try:
        presence = service.set_own(session, client.subject, payload.enabled)
    except PresenceClientNotFoundError:
        raise HTTPException(status_code=401, detail="Authenticated client not found") from None
    return PresenceResponse(**presence.__dict__)
