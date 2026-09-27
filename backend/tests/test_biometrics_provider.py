import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from uuid import uuid4

import pytest

from app.modules.biometrics import provider as adapter
from app.modules.biometrics.config import BiometricConfig, BiometricError
from app.modules.biometrics.provider import CompreFaceProvider


class Response(BytesIO):
    status = 200


def transport(monkeypatch, response):
    calls = []

    class Opener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            if isinstance(response, Exception):
                raise response
            return Response(json.dumps(response).encode())

    monkeypatch.setattr(adapter, "build_opener", lambda *_: Opener())
    return calls


def provider():
    return CompreFaceProvider(BiometricConfig(mode="pilot", api_key="fixture-secret"))


def test_adapter_uses_all_faces_two_candidates_no_plugins_and_bounded_timeout(monkeypatch):
    calls = transport(
        monkeypatch,
        {
            "result": [
                {
                    "box": {"probability": 0.99},
                    "subjects": [
                        {"subject": "opaque", "similarity": 0.92},
                        {"subject": "other", "similarity": 0.82},
                    ],
                }
            ]
        },
    )
    faces = provider().inspect(b"synthetic")
    assert len(faces) == 1 and len(faces[0].candidates) == 2
    request, timeout = calls[0]
    assert timeout == 10
    assert "limit=0" in request.full_url and "prediction_count=2" in request.full_url
    assert "face_plugins=&" in request.full_url
    assert request.get_header("X-api-key") == "fixture-secret"
    assert b"synthetic" in request.data


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"result": [{"box": {"probability": 2}, "subjects": []}]},
        {"result": [{"box": {"probability": float("nan")}, "subjects": []}]},
        {"result": [{"box": {"probability": 0.99}, "subjects": [{"subject": "x"}]}]},
        URLError("sensitive response must not escape"),
    ],
)
def test_invalid_contracts_and_network_errors_are_safe(monkeypatch, response):
    transport(monkeypatch, response)
    with pytest.raises(BiometricError, match="^provider_unavailable$"):
        provider().inspect(b"fixture")


def test_no_face_provider_error_and_missing_subject_delete(monkeypatch):
    transport(
        monkeypatch,
        HTTPError("internal", 400, "private", {}, BytesIO(b'{"code":28,"message":"private"}')),
    )
    with pytest.raises(BiometricError, match="^no_face$"):
        provider().inspect(b"fixture")
    transport(monkeypatch, HTTPError("internal", 404, "private", {}, BytesIO(b"private")))
    provider().delete("opaque")


def test_enrollment_requires_matching_reference_and_valid_image_id(monkeypatch):
    transport(monkeypatch, {"subject": "other", "image_id": str(uuid4())})
    with pytest.raises(BiometricError):
        provider().enroll("expected", b"fixture")


def test_readiness_requires_both_api_and_recognition_worker(monkeypatch):
    calls = []

    class Opener:
        def open(self, request, timeout):
            calls.append(request)
            if len(calls) == 1:
                return Response(b'{"subjects":[]}')
            raise URLError("worker unavailable")

    monkeypatch.setattr(adapter, "build_opener", lambda *_: Opener())
    with pytest.raises(BiometricError, match="provider_unavailable"):
        provider().ready()
    assert calls[1].full_url == "http://compreface-core:3000/healthcheck"
    assert calls[1].get_header("X-api-key") is None


@pytest.mark.parametrize(
    "variable,value",
    [
        ("FACIAL_ACCESS_MODE", "live"),
        ("COMPREFACE_URL", "https://cloud.example"),
        ("BIOMETRIC_MATCH_THRESHOLD", "nan"),
        ("BIOMETRIC_TIMEOUT_SECONDS", "100"),
    ],
)
def test_invalid_configuration_fails_closed(monkeypatch, variable, value):
    monkeypatch.setenv(variable, value)
    with pytest.raises(BiometricError, match="biometric_configuration_invalid"):
        BiometricConfig.from_environment()
