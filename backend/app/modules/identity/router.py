from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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
) -> AuthenticatedIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated")

    try:
        return identity_provider.get_identity(credentials.credentials)
    except InvalidSessionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthenticated"
        ) from None
    except IdentityProviderUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable",
        ) from None


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
