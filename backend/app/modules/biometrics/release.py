"""TURNSTILE_RELEASE_REQUESTED: the sole future turnstile integration boundary.

Pilot persistence belongs to AccessService's authorization transaction. This
adapter acknowledges simulation only; it has no network/hardware dependency.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID


@dataclass(frozen=True)
class TurnstileReleaseRequest:
    release_request_id: UUID
    recognition_attempt_id: UUID
    occurred_at: datetime
    checkpoint_id: str
    direction: Literal["entry", "exit"]
    subject_reference: str
    mode: Literal["simulated"] = "simulated"


class TurnstileReleaseAdapter(Protocol):
    def request_release(self, request: TurnstileReleaseRequest) -> Literal["simulated"]: ...


class SimulatedTurnstileReleaseAdapter:
    def request_release(self, request: TurnstileReleaseRequest) -> Literal["simulated"]:
        if request.mode != "simulated":
            raise ValueError("Only simulated release is supported")
        return "simulated"
