"""CompreFace REST adapter. No raw provider response reaches callers or logs."""

import json
from dataclasses import dataclass
from math import isfinite
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID, uuid4

from app.modules.biometrics.config import BiometricConfig, BiometricError


@dataclass(frozen=True)
class Candidate:
    subject: str
    similarity: float


@dataclass(frozen=True)
class Face:
    probability: float
    candidates: tuple[Candidate, ...]


class FaceProvider(Protocol):
    def inspect(self, image: bytes) -> tuple[Face, ...]: ...
    def enroll(self, subject: str, image: bytes) -> None: ...
    def delete(self, subject: str) -> None: ...
    def ready(self) -> None: ...


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CompreFaceProvider:
    def __init__(self, config: BiometricConfig):
        self.config = config

    def _request(self, method, path, image=None):
        self.config.require_pilot()
        headers = {"x-api-key": self.config.api_key, "Accept": "application/json"}
        body = None
        if image is not None:
            boundary = uuid4().hex
            body = (
                (
                    f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                    'filename="capture.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
                ).encode()
                + image
                + f"\r\n--{boundary}--\r\n".encode()
            )
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        request = Request(
            self.config.url + "/api/v1/recognition" + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with build_opener(NoRedirect).open(request, timeout=self.config.timeout) as response:
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise ValueError
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError
                return result
        except HTTPError as error:
            # Only stable provider error codes are inspected, never their free text.
            if error.code == 404 and method == "DELETE":
                return {}
            if error.code == 400:
                try:
                    payload = json.loads(error.read(4096))
                    if payload.get("code") == 28:
                        raise BiometricError("no_face", 422) from None
                except (ValueError, AttributeError):
                    pass
            raise BiometricError("provider_unavailable", 503) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise BiometricError("provider_unavailable", 503) from None

    def inspect(self, image: bytes) -> tuple[Face, ...]:
        # Detect all faces, including weaker detections; quality is checked locally.
        query = urlencode(
            {
                "limit": 0,
                "prediction_count": 2,
                "det_prob_threshold": 0.5,
                "face_plugins": "",
                "detect_faces": "true",
            }
        )
        payload = self._request("POST", "/recognize?" + query, image)
        try:
            faces = []
            for item in payload["result"]:
                probability = self._score(item["box"]["probability"])
                candidates = tuple(
                    sorted(
                        (
                            Candidate(
                                self._subject(candidate["subject"]),
                                self._score(candidate["similarity"]),
                            )
                            for candidate in item["subjects"]
                        ),
                        key=lambda candidate: candidate.similarity,
                        reverse=True,
                    )
                )
                faces.append(Face(probability, candidates))
            return tuple(faces)
        except (KeyError, TypeError, ValueError):
            raise BiometricError("provider_unavailable", 503) from None

    @staticmethod
    def _score(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError
        if not isfinite(value) or not 0 <= value <= 1:
            raise ValueError
        return value

    @staticmethod
    def _subject(value):
        if not isinstance(value, str) or not 1 <= len(value) <= 255:
            raise ValueError
        return value

    def enroll(self, subject: str, image: bytes) -> None:
        query = urlencode(
            {"subject": subject, "det_prob_threshold": self.config.detection_threshold}
        )
        payload = self._request("POST", "/faces?" + query, image)
        try:
            UUID(payload["image_id"])
            if payload["subject"] != subject:
                raise ValueError
        except (KeyError, TypeError, ValueError, AttributeError):
            raise BiometricError("provider_unavailable", 503) from None

    def delete(self, subject: str) -> None:
        self._request("DELETE", "/subjects/" + quote(subject, safe=""))

    def ready(self) -> None:
        payload = self._request("GET", "/subjects")
        if not isinstance(payload.get("subjects"), list):
            raise BiometricError("provider_unavailable", 503)
        # API/DB readiness alone cannot certify a healthy recognition worker.
        # This fixed internal endpoint is the pinned Compose core healthcheck.
        try:
            request = Request("http://compreface-core:3000/healthcheck")
            with build_opener(NoRedirect).open(request, timeout=self.config.timeout) as response:
                if response.status != 200:
                    raise ValueError
        except (URLError, TimeoutError, OSError, ValueError):
            raise BiometricError("provider_unavailable", 503) from None


def single_face(faces: tuple[Face, ...], config: BiometricConfig) -> Face:
    if not faces:
        raise BiometricError("no_face", 422)
    if len(faces) != 1:
        raise BiometricError("multiple_faces", 422)
    if faces[0].probability < config.detection_threshold:
        raise BiometricError("face_quality_low", 422)
    return faces[0]
