"""Replaceable postal-code lookup boundary backed by ViaCEP."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PostalCodeLookupError(Exception):
    """Base error for controlled postal-code lookup failures."""


class PostalCodeNotFoundError(PostalCodeLookupError):
    pass


class PostalCodeUnavailableError(PostalCodeLookupError):
    pass


@dataclass(frozen=True)
class CepAddress:
    street: str | None
    neighborhood: str | None
    city: str | None
    state: str | None


class PostalCodeLookup(Protocol):
    def lookup(self, postal_code: str) -> CepAddress: ...


class ViaCepLookup:
    """Small server-side ViaCEP adapter; callers retain manual entry on failure."""

    def lookup(self, postal_code: str) -> CepAddress:
        request = Request(
            f"https://viacep.com.br/ws/{postal_code}/json/",
            headers={"Accept": "application/json"},
        )
        try:
            with urlopen(request, timeout=3) as response:  # noqa: S310 - fixed public CEP API
                payload = json.load(response)
        except HTTPError as error:
            if error.code == 404:
                raise PostalCodeNotFoundError from None
            raise PostalCodeUnavailableError from None
        except (URLError, TimeoutError, json.JSONDecodeError):
            raise PostalCodeUnavailableError from None
        if not isinstance(payload, dict):
            raise PostalCodeUnavailableError
        if payload.get("erro") is True:
            raise PostalCodeNotFoundError
        return CepAddress(
            street=_text(payload.get("logradouro")),
            neighborhood=_text(payload.get("bairro")),
            city=_text(payload.get("localidade")),
            state=_text(payload.get("uf")),
        )


def _text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value or None
