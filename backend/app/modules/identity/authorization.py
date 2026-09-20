"""Reusable authorization policies for protected API operations."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.modules.identity.service import AuthenticatedIdentity


def has_any_role(identity: AuthenticatedIdentity, allowed_roles: frozenset[str]) -> bool:
    """Return whether an identity has at least one role allowed by a policy."""
    return bool(set(identity.roles).intersection(allowed_roles))


def require_roles(
    authenticate: Callable[..., AuthenticatedIdentity], *allowed_roles: str
) -> Callable[..., AuthenticatedIdentity]:
    """Create a FastAPI dependency that permits only the supplied realm roles."""
    roles = frozenset(allowed_roles)
    if not roles:
        raise ValueError("An authorization policy must allow at least one role")

    def authorize(
        identity: Annotated[AuthenticatedIdentity, Depends(authenticate)],
    ) -> AuthenticatedIdentity:
        if not has_any_role(identity, roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return identity

    return authorize
