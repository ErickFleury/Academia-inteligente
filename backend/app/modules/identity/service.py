"""OIDC identity verification kept separate from transport concerns."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InvalidSessionError(Exception):
    """The supplied bearer token cannot establish an authenticated identity."""


class IdentityProviderUnavailableError(Exception):
    """The identity provider could not be contacted or returned an invalid response."""


@dataclass(frozen=True)
class AuthenticatedIdentity:
    subject: str
    username: str | None
    roles: tuple[str, ...]


class IdentityProvider(Protocol):
    def get_identity(self, access_token: str) -> AuthenticatedIdentity: ...


class OidcUserInfoProvider:
    """Validates an access token through the configured OIDC UserInfo endpoint."""

    def __init__(self, issuer_url: str | None = None) -> None:
        self._issuer_url = (issuer_url or os.environ.get("OIDC_ISSUER_URL", "")).rstrip("/")

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        if not self._issuer_url:
            raise IdentityProviderUnavailableError

        request = Request(
            f"{self._issuer_url}/protocol/openid-connect/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            with urlopen(request, timeout=2) as response:  # noqa: S310 - configured OIDC endpoint
                payload = json.load(response)
        except HTTPError as error:
            if error.code in {400, 401, 403}:
                raise InvalidSessionError from error
            raise IdentityProviderUnavailableError from error
        except (URLError, TimeoutError, json.JSONDecodeError):
            raise IdentityProviderUnavailableError from None

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise InvalidSessionError

        roles = payload.get("realm_access", {}).get("roles", [])
        return AuthenticatedIdentity(
            subject=subject,
            username=payload.get("preferred_username"),
            roles=tuple(role for role in roles if isinstance(role, str)),
        )
