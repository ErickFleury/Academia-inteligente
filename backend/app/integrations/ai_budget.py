"""Request-local ceilings and bounded HTTP waiting shared by all agent roles."""

import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from threading import BoundedSemaphore
from time import monotonic


class BudgetExceeded(Exception):
    pass


def plan_deadline_seconds():
    """Keep the existing default; the optional extended mode cannot exceed 90s."""
    try:
        return min(90, max(60, int(os.getenv("AI_PLAN_DEADLINE_SECONDS", "60"))))
    except ValueError:
        return 60


current_budget: ContextVar["ExecutionBudget | None"] = ContextVar("ai_budget", default=None)
_http_workers = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ai-http")
_http_slots = BoundedSemaphore(2)


def bounded_wait(operation, timeout):
    """Late HTTP results cannot reach domain state; no unbounded work queue.

    Socket timeouts remain in force inside the operation. A server that dribbles
    bytes cannot extend the caller's deadline, and occupies at most one of two
    provider slots until its read ends. No database sessions enter these workers.
    """
    if timeout <= 0 or not _http_slots.acquire(blocking=False):
        raise BudgetExceeded("provider_capacity")

    def perform():
        try:
            return operation()
        finally:
            _http_slots.release()

    future = _http_workers.submit(perform)
    try:
        return future.result(timeout=timeout)
    except FutureTimeout:
        raise BudgetExceeded("deadline_exceeded") from None


@dataclass
class ExecutionBudget:
    plan: bool = False
    started: float = field(default_factory=monotonic)
    calls: int = 0
    retrievals: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    plan_seconds: int = field(default_factory=plan_deadline_seconds)

    def remaining(self):
        remaining = (self.plan_seconds if self.plan else 30) - (monotonic() - self.started)
        if remaining <= 0:
            raise BudgetExceeded("deadline_exceeded")
        return remaining

    def reserve(self, input_bytes, desired_output):
        self.remaining()
        # UTF-8 byte count plus protocol/schema overhead is a conservative
        # upper bound for the selected byte-tokenized models; never truncate.
        estimate = input_bytes + 512
        if self.calls >= (6 if self.plan else 4):
            raise BudgetExceeded("generation_call_limit")
        if self.input_tokens + estimate > (64000 if self.plan else 32000):
            raise BudgetExceeded("input_token_limit")
        available = (12000 if self.plan else 4000) - self.output_tokens
        if available < 256:
            raise BudgetExceeded("output_token_limit")
        reserved = min(desired_output, available)
        self.calls += 1
        self.input_tokens += estimate
        self.output_tokens += reserved
        return reserved

    def reconcile_output(self, reserved, actual):
        # Unknown usage (including timeouts) retains the full reservation.
        if actual is not None:
            if type(actual) is not int or actual < 0 or actual > reserved:
                raise BudgetExceeded("provider_usage_invalid")
            self.output_tokens -= reserved - actual
        self.remaining()

    def reconcile_input(self, reserved, actual):
        """Retain the conservative reservation if the adapter has no usage data."""
        if actual is not None:
            if type(actual) is not int or actual < 0:
                raise BudgetExceeded("provider_usage_invalid")
            self.input_tokens += actual - reserved
            if self.input_tokens > (64000 if self.plan else 32000):
                raise BudgetExceeded("input_token_limit")
        self.remaining()

    def retrieval(self):
        self.remaining()
        if self.retrievals >= 2:
            raise BudgetExceeded("retrieval_limit")
        self.retrievals += 1

    @contextmanager
    def scope(self):
        token = current_budget.set(self)
        try:
            yield self
        finally:
            current_budget.reset(token)
