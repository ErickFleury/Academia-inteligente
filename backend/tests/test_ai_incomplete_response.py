"""Incomplete hosted output stays bounded and never becomes a partial domain result."""

import json
import logging
from io import BytesIO

import pytest
from test_ai_budget import Result

from app.integrations import ai
from app.integrations.ai import AiProviderError, OpenAiConfig, OpenAiResponsesOnboardingProvider
from app.integrations.ai_budget import ExecutionBudget


def provider():
    return OpenAiResponsesOnboardingProvider(OpenAiConfig("synthetic-key", "test-model", 25))


def test_hosted_router_can_complete_output_larger_than_old_limit(monkeypatch):
    allocations = []

    def respond(request, timeout):
        limit = json.loads(request.data)["max_output_tokens"]
        allocations.append(limit)
        required = 1500 if len(allocations) == 1 else 400
        return BytesIO(
            json.dumps(
                {
                    "status": "completed" if limit >= required else "incomplete",
                    "incomplete_details": None
                    if limit >= required
                    else {"reason": "max_output_tokens"},
                    "output": [{"content": [{"type": "output_text", "text": '{"answer":"ok"}'}]}],
                    "usage": {"input_tokens": 100, "output_tokens": min(limit, required)},
                }
            ).encode()
        )

    monkeypatch.setattr(ai, "urlopen", respond)
    budget = ExecutionBudget()
    with budget.scope():
        for role in ("orchestrator", "training_chat", "orchestrator"):
            result = provider().structured(
                {}, "Return JSON", Result.model_json_schema(), Result, role=role
            )
            assert result.answer == "ok"
    assert budget.calls == 3
    assert budget.output_tokens == 2300
    assert 1000 < allocations[0] <= 2000
    assert allocations[1] <= 2500
    assert allocations[2] <= 2100


@pytest.mark.parametrize(
    "reason, category",
    [
        ("max_output_tokens", "incomplete_output_limit"),
        ("content_filter", "incomplete_content_filter"),
        ("PRIVATE_UNKNOWN_REASON", "incomplete_response"),
        (None, "incomplete_response"),
    ],
)
def test_incomplete_reason_is_classified_without_exposing_payload(
    monkeypatch, caplog, reason, category
):
    caplog.set_level(logging.INFO, logger="uvicorn.error.ai")
    monkeypatch.setattr(
        ai,
        "urlopen",
        lambda request, timeout: BytesIO(
            json.dumps(
                {
                    "status": "incomplete",
                    "incomplete_details": {"reason": reason},
                    "output": [
                        {
                            "content": [
                                {"type": "output_text", "text": '{"answer":"PRIVATE_PARTIAL"}'}
                            ]
                        }
                    ],
                    "usage": {"input_tokens": 100, "output_tokens": 700},
                }
            ).encode()
        ),
    )
    budget = ExecutionBudget()
    with budget.scope(), pytest.raises(AiProviderError) as error:
        provider().structured(
            {}, "PRIVATE_PROMPT", Result.model_json_schema(), Result, role="orchestrator"
        )
    assert error.value.category == category
    assert error.value.retryable is False
    assert budget.calls == 1
    assert budget.output_tokens == 700
    event = json.loads(caplog.records[-1].message)
    assert event["reason"] == category
    assert event["role"] == "orchestrator"
    assert "PRIVATE" not in caplog.text


@pytest.mark.parametrize("details", [None, [], "PRIVATE_DETAILS", {"reason": []}])
def test_incomplete_legacy_call_never_accepts_parseable_partial_output(monkeypatch, details):
    monkeypatch.setattr(
        ai,
        "urlopen",
        lambda request, timeout: BytesIO(
            json.dumps(
                {
                    "status": "incomplete",
                    "incomplete_details": details,
                    "output": [
                        {"content": [{"type": "output_text", "text": '{"answer":"partial"}'}]}
                    ],
                }
            ).encode()
        ),
    )
    with pytest.raises(AiProviderError, match="incomplete_response") as error:
        provider().structured(
            {}, "Return JSON", Result.model_json_schema(), Result, role="orchestrator"
        )
    assert error.value.retryable is False


def test_unknown_role_never_leaks_into_provider_diagnostics(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="uvicorn.error.ai")
    monkeypatch.setattr(
        ai,
        "urlopen",
        lambda request, timeout: BytesIO(
            json.dumps(
                {
                    "output": [{"content": [{"type": "output_text", "text": '{"answer":"ok"}'}]}],
                    "usage": {"input_tokens": 100, "output_tokens": 10},
                }
            ).encode()
        ),
    )
    with ExecutionBudget().scope():
        provider().structured(
            {}, "Return JSON", Result.model_json_schema(), Result, role="PRIVATE_ROLE"
        )
    assert json.loads(caplog.records[-1].message)["role"] == "unknown"
    assert "PRIVATE_ROLE" not in caplog.text
