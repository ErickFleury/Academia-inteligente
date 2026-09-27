import json
from io import BytesIO

import pytest

from app.modules.identity import service


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"sub": "s", "realm_access": None},
        {"sub": "s", "realm_access": {"roles": {"admin": True}}},
        {"sub": "s", "realm_access": {"roles": ["admin", 1]}},
        {"sub": "s", "preferred_username": []},
    ],
)
def test_malformed_identity_response_fails_closed(monkeypatch, payload):
    monkeypatch.setattr(
        service, "urlopen", lambda *args, **kwargs: BytesIO(json.dumps(payload).encode())
    )
    with pytest.raises(service.IdentityProviderUnavailableError):
        service.OidcUserInfoProvider("http://keycloak.test").get_identity("token")


def test_identity_response_read_is_bounded(monkeypatch):
    response = BytesIO(b" " * 100_000)

    # Keep the stream open to inspect how much the provider read.
    class Response:
        def __enter__(self):
            return response

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(service, "urlopen", lambda *args, **kwargs: Response())
    with pytest.raises(service.IdentityProviderUnavailableError):
        service.OidcUserInfoProvider("http://keycloak.test").get_identity("token")
    assert response.tell() == 65_537
