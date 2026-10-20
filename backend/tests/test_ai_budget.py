import json
from io import BytesIO
from time import monotonic, sleep

import pytest
from pydantic import BaseModel

from app.integrations import ai
from app.integrations.ai import (
    AiProviderError,
    OllamaConfig,
    OllamaOnboardingProvider,
    OpenAiConfig,
    OpenAiResponsesOnboardingProvider,
)
from app.integrations.ai_budget import BudgetExceeded, ExecutionBudget, bounded_wait, current_budget


class Result(BaseModel):
    answer: str


def test_budget_counts_retries_and_shared_nested_scopes():
    budget = ExecutionBudget()
    with budget.scope():
        for _ in range(4):
            allocated = current_budget.get().reserve(50, 300)
            budget.reconcile_output(allocated, 10)
        with pytest.raises(BudgetExceeded, match="generation_call_limit"):
            budget.reserve(1, 300)
        with budget.scope():
            assert current_budget.get().calls == 4
    assert current_budget.get() is None


def test_token_and_retrieval_ceilings_fail_without_truncation():
    budget = ExecutionBudget()
    with pytest.raises(BudgetExceeded, match="input_token_limit"):
        budget.reserve(32000, 1000)
    assert budget.calls == 0
    budget.reserve(1, 4000)
    with pytest.raises(BudgetExceeded, match="output_token_limit"):
        budget.reserve(1, 1000)
    budget.retrieval()
    budget.retrieval()
    with pytest.raises(BudgetExceeded, match="retrieval_limit"):
        budget.retrieval()
    with pytest.raises(BudgetExceeded, match="deadline_exceeded"):
        ExecutionBudget(started=monotonic() - 31).remaining()


def test_provider_wait_cannot_extend_deadline():
    started = monotonic()
    with pytest.raises(BudgetExceeded, match="deadline_exceeded"):
        bounded_wait(lambda: sleep(0.1), 0.01)
    assert monotonic() - started < 0.08
    sleep(0.11)  # Let the bounded worker release its slot for other tests.


@pytest.mark.parametrize("hosted", [False, True])
def test_adapter_caps_output_and_uses_explicit_role_model(monkeypatch, hosted):
    captured = []

    def response(request, timeout):
        captured.append(json.loads(request.data))
        if hosted:
            payload = {
                "output": [{"content": [{"type": "output_text", "text": '{"answer":"ok"}'}]}],
                "usage": {"output_tokens": 5},
            }
        else:
            payload = {"message": {"content": '{"answer":"ok"}'}, "eval_count": 5}
        return BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(ai, "urlopen", response)
    monkeypatch.setenv("AI_MODEL_ORCHESTRATOR", "explicit-test-model")
    provider = (
        OpenAiResponsesOnboardingProvider(OpenAiConfig("test-key", "base", 10))
        if hosted
        else OllamaOnboardingProvider(OllamaConfig("http://local", "base", 10))
    )
    budget = ExecutionBudget()
    with budget.scope():
        assert (
            provider.structured(
                {}, "Return JSON", Result.model_json_schema(), Result, role="orchestrator"
            ).answer
            == "ok"
        )
    assert captured[0]["model"] == "explicit-test-model"
    assert budget.output_tokens == 5
    assert (
        captured[0]["max_output_tokens"] if hosted else captured[0]["options"]["num_predict"]
    ) == 1000
    if hosted:
        assert captured[0]["store"] is False
        assert captured[0]["truncation"] == "disabled"


def test_context_overflow_never_calls_provider(monkeypatch):
    monkeypatch.setenv("OLLAMA_CONTEXT_TOKENS", "100")
    monkeypatch.setattr(ai, "urlopen", lambda *args, **kwargs: pytest.fail("must not send"))
    with ExecutionBudget().scope(), pytest.raises(AiProviderError, match="context_capacity"):
        OllamaOnboardingProvider().structured({}, "instructions", {}, Result, role="orchestrator")
