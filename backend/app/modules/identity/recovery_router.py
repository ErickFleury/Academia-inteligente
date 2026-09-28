"""Self-service and administrator entry points for the same recovery action."""

from typing import Annotated, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.password_recovery import PasswordRecoveryError, PasswordRecoveryService
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity

router = APIRouter(tags=["identity"])
recovery_service = PasswordRecoveryService()
DatabaseSession = Annotated[Session, Depends(get_database_session)]
Administrator = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "admin"))
]
ClientIdentity = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "client"))
]


def recovery_response(operation: Callable[[], None]) -> dict[str, object]:
    try:
        operation()
    except PasswordRecoveryError as error:
        raise HTTPException(
            error.status,
            error.code,
            headers={"Retry-After": "60"} if error.status == 429 else None,
        ) from None
    return {"status": "sent", "expires_in_seconds": 900}


@router.post("/identity/me/password-reset")
def recover_own_password(session: DatabaseSession, identity: ClientIdentity):
    return recovery_response(
        lambda: recovery_service.request_for_subject(session, identity.subject)
    )


@router.post("/clients/{client_id}/password-reset")
def recover_client_password(
    client_id: UUID, session: DatabaseSession, administrator: Administrator
):
    return recovery_response(lambda: recovery_service.request_for_client(session, client_id))
