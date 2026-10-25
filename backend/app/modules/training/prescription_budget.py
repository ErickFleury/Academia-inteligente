"""One request budget across writer, focus, reviewer and nested correction helpers."""

import logging
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from app.modules.training.prescription_contract import PrescriptionRejection

CURRENT_BUDGET = ContextVar("prescription_budget", default=None)
CURRENT_STAGE = ContextVar("prescription_stage", default=None)
logger = logging.getLogger(__name__)


@dataclass
class AttemptBudget:
    timeout_seconds: float
    clock: object = time.monotonic
    counts: dict = field(default_factory=lambda: {"writer": 0, "review": 0, "focus": 0})
    http_counts: dict = field(default_factory=lambda: {"writer": 0, "review": 0, "focus": 0})
    stage_seconds: dict = field(
        default_factory=lambda: {"writer": 0.0, "review": 0.0, "focus": 0.0}
    )
    deadline: float = field(init=False)
    content_corrections: int = 0

    def consume_content_correction(self):
        if self.content_corrections >= 1:
            return False
        self.content_corrections += 1
        return True

    def __post_init__(self):
        if self.timeout_seconds <= 0:
            raise ValueError("positive_adapter_timeout_required")
        self.deadline = self.clock() + 10 * self.timeout_seconds

    def remaining(self, adapter_timeout):
        remaining = min(adapter_timeout, self.deadline - self.clock())
        if remaining <= 0:
            raise PrescriptionRejection(
                "technical_unavailability", "prescription_deadline_exhausted"
            )
        return remaining

    def call(self, stage, operation):
        limits = {"writer": 4, "review": 4, "focus": 2}
        self.remaining(self.timeout_seconds)
        if (
            stage not in limits
            or self.counts[stage] >= limits[stage]
            or sum(self.counts.values()) >= 10
        ):
            raise PrescriptionRejection(
                "technical_unavailability", "prescription_call_budget_exhausted"
            )
        self.counts[stage] += 1
        token = CURRENT_STAGE.set(stage)
        started = self.clock()
        try:
            result = operation()
            self.remaining(self.timeout_seconds)
            return result
        finally:
            self.stage_seconds[stage] += self.clock() - started
            CURRENT_STAGE.reset(token)

    def record_http(self):
        stage = CURRENT_STAGE.get()
        limits = {"writer": 4, "review": 4, "focus": 2}
        if (
            stage not in limits
            or self.http_counts[stage] >= limits[stage]
            or sum(self.http_counts.values()) >= 10
        ):
            raise PrescriptionRejection(
                "technical_unavailability", "prescription_call_budget_exhausted"
            )
        self.remaining(self.timeout_seconds)
        self.http_counts[stage] += 1


@contextmanager
def attempt_budget(timeout_seconds):
    existing = CURRENT_BUDGET.get()
    if existing is not None:
        yield existing
        return
    budget = AttemptBudget(timeout_seconds)
    token = CURRENT_BUDGET.set(budget)
    try:
        yield budget
    finally:
        logger.info(
            "prescription_attempt calls=%s http_calls=%s stage_seconds=%s deadline_exhausted=%s",
            budget.counts,
            budget.http_counts,
            budget.stage_seconds,
            budget.clock() >= budget.deadline,
        )
        CURRENT_BUDGET.reset(token)
