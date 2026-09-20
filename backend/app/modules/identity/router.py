from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.clients.models import Account
from app.modules.identity.authorization import require_roles
from app.modules.identity.service import (
    AuthenticatedIdentity,
    IdentityProvider,
    IdentityProviderUnavailableError,
    InvalidSessionError,
    OidcUserInfoProvider,
)

router = APIRouter(prefix="/identity", tags=["identity"])
bearer_scheme = HTTPBearer(auto_error=False)
identity_provider: IdentityProvider = OidcUserInfoProvider()


def get_authenticated_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_database_session)],
) -> AuthenticatedIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated")

    try:
        identity = identity_provider.get_identity(credentials.credentials)
    except InvalidSessionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated"
        ) from None
    except IdentityProviderUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable",
        ) from None

    account = session.scalar(select(Account).where(Account.keycloak_subject == identity.subject))
    if "client" in identity.roles and account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated")
    if account is not None and not account.account_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated")
    return identity


@router.get("/me")
def get_current_identity(
    identity: Annotated[AuthenticatedIdentity, Depends(get_authenticated_identity)],
) -> dict[str, object]:
    """A protected endpoint used to establish and verify the browser session."""
    return {"subject": identity.subject, "username": identity.username, "roles": identity.roles}


@router.get("/admin")
def get_admin_capability(
    identity: Annotated[
        AuthenticatedIdentity,
        Depends(require_roles(get_authenticated_identity, "admin")),
    ],
) -> dict[str, bool]:
    """Expose the administrative capability only after the centralized role check."""
    del identity
    return {"authorized": True}
