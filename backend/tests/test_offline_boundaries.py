import pytest

from app.integrations.cep import PostalCodeUnavailableError, ViaCepLookup


def test_offline_postal_lookup_never_contacts_external_service(monkeypatch):
    monkeypatch.setenv("VIA_CEP_ENABLED", "false")
    monkeypatch.setattr(
        "app.integrations.cep.urlopen", lambda *a, **kw: pytest.fail("network call")
    )
    with pytest.raises(PostalCodeUnavailableError):
        ViaCepLookup().lookup("01001000")
