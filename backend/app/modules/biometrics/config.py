import os
from dataclasses import dataclass, field
from math import isfinite


class BiometricError(Exception):
    """Only a safe domain code may cross the API boundary."""

    def __init__(self, code: str, status: int = 409):
        self.code = code
        self.status = status
        super().__init__(code)


@dataclass(frozen=True)
class BiometricConfig:
    mode: str = "disabled"
    url: str = "http://compreface-api:8080"
    api_key: str = field(default="", repr=False)
    detection_threshold: float = 0.90
    match_threshold: float = 0.80
    ambiguity_margin: float = 0.10
    timeout: float = 10
    model: str = "facenet-20180402-114759"

    @classmethod
    def from_environment(cls):
        try:
            config = cls(
                mode=os.getenv("FACIAL_ACCESS_MODE", "disabled"),
                url=os.getenv("COMPREFACE_URL", "http://compreface-api:8080").rstrip("/"),
                api_key=os.getenv("COMPREFACE_API_KEY", ""),
                detection_threshold=float(os.getenv("BIOMETRIC_DETECTION_THRESHOLD", ".90")),
                match_threshold=float(os.getenv("BIOMETRIC_MATCH_THRESHOLD", ".80")),
                ambiguity_margin=float(os.getenv("BIOMETRIC_AMBIGUITY_MARGIN", ".10")),
                timeout=float(os.getenv("BIOMETRIC_TIMEOUT_SECONDS", "10")),
                model=os.getenv("BIOMETRIC_MODEL", "facenet-20180402-114759"),
            )
            numbers = (config.detection_threshold, config.match_threshold, config.ambiguity_margin)
            if any(not isfinite(value) or not 0 < value < 1 for value in numbers):
                raise ValueError
            if not isfinite(config.timeout) or not 0 < config.timeout <= 10:
                raise ValueError
            # This pilot has exactly one approved local provider, no cloud/live mode.
            if config.url != "http://compreface-api:8080" or config.mode not in {
                "disabled",
                "pilot",
            }:
                raise ValueError
            return config
        except ValueError:
            raise BiometricError("biometric_configuration_invalid", 503) from None

    def require_pilot(self):
        if self.mode != "pilot" or not self.api_key:
            raise BiometricError("biometrics_unavailable", 503)
