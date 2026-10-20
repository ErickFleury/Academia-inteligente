import json
from io import BytesIO
from urllib.error import URLError

import pytest

from app.integrations import embeddings
from app.integrations.ai import AiProviderError, OllamaOnboardingProvider
from app.integrations.embeddings import EmbeddingConfig, HttpEmbeddingProvider


def test_local_defaults_are_independent_of_generation_and_paid_credentials(monkeypatch):
    monkeypatch.delenv("AI_EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("AI_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("AI_EMBEDDING_DIMENSIONS", raising=False)
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "not-used")
    config = EmbeddingConfig.from_environment()
    assert (config.provider, config.model, config.dimensions) == ("ollama", "embeddinggemma", 768)
    assert config.api_key == ""
    monkeypatch.delenv("AI_PROVIDER")
    from app.integrations.ai import onboarding_ai_provider_from_environment

    assert isinstance(onboarding_ai_provider_from_environment(), OllamaOnboardingProvider)


def test_local_query_uses_prefix_no_truncation_and_remaining_timeout(monkeypatch):
    captured = []

    def respond(request, timeout):
        captured.append((request, timeout))
        return BytesIO(json.dumps({"model": "embeddinggemma", "embeddings": [[1, 2]]}).encode())

    monkeypatch.setattr(embeddings, "urlopen", respond)
    provider = HttpEmbeddingProvider(EmbeddingConfig(dimensions=2))
    assert provider.embed(["treino"], purpose="query", timeout=2) == [[1, 2]]
    request, timeout = captured[0]
    body = json.loads(request.data)
    assert body["input"] == ["task: search result | query: treino"]
    assert body["truncate"] is False
    assert body["options"] == {"num_gpu": 0}
    assert request.full_url == "http://ollama:11434/api/embed"
    assert request.get_header("Authorization") is None
    assert timeout == 2


def test_hosted_vectors_are_ordered_and_configuration_is_explicit(monkeypatch):
    captured = []

    def respond(request, timeout):
        captured.append(request)
        return BytesIO(
            json.dumps(
                {"data": [{"index": 1, "embedding": [3, 4]}, {"index": 0, "embedding": [1, 2]}]}
            ).encode()
        )

    monkeypatch.setattr(embeddings, "urlopen", respond)
    config = EmbeddingConfig(
        provider="openai", model="text-embedding-3-small", dimensions=2, api_key="test-only"
    )
    assert HttpEmbeddingProvider(config).embed(["a", "b"], purpose="document") == [[1, 2], [3, 4]]
    assert captured[0].full_url == "https://api.openai.com/v1/embeddings"
    assert json.loads(captured[0].data)["input"] == ["a", "b"]


@pytest.mark.parametrize("vectors", [[[0, 0]], [[1]], [[True, 2]], [[float("nan"), 1]], []])
def test_invalid_vectors_are_rejected(monkeypatch, vectors):
    monkeypatch.setattr(
        embeddings,
        "urlopen",
        lambda *a, **k: BytesIO(
            json.dumps({"model": "embeddinggemma", "embeddings": vectors}).encode()
        ),
    )
    with pytest.raises(AiProviderError, match="malformed_embedding_output"):
        HttpEmbeddingProvider(EmbeddingConfig(dimensions=2)).embed(["a"], purpose="query")


def test_network_failure_never_falls_back_to_hosted(monkeypatch):
    calls = []

    def fail(request, **kwargs):
        calls.append(request.full_url)
        raise URLError("private error")

    monkeypatch.setattr(embeddings, "urlopen", fail)
    with pytest.raises(AiProviderError, match="timeout_or_network"):
        HttpEmbeddingProvider().embed(["topic"], purpose="query")
    assert calls == ["http://ollama:11434/api/embed"]


def test_index_identity_tracks_model_dimensions_and_revision():
    assert EmbeddingConfig().fingerprint != EmbeddingConfig(revision="2").fingerprint
    assert EmbeddingConfig().fingerprint != EmbeddingConfig(dimensions=512).fingerprint


def test_oversized_input_is_rejected_before_network(monkeypatch):
    monkeypatch.setattr(embeddings, "urlopen", lambda *a, **k: pytest.fail("network called"))
    with pytest.raises(AiProviderError, match="embedding_input"):
        HttpEmbeddingProvider().embed(["a" * 6001], purpose="document")


def test_exhausted_deadline_never_starts_network_call(monkeypatch):
    monkeypatch.setattr(embeddings, "urlopen", lambda *a, **k: pytest.fail("network called"))
    with pytest.raises(AiProviderError, match="budget_exhausted"):
        HttpEmbeddingProvider().embed(["topic"], purpose="query", timeout=0)


def test_slow_response_read_has_a_total_deadline(monkeypatch):
    from threading import Event

    release = Event()

    def slow_read(*args, **kwargs):
        assert release.wait(2)
        return BytesIO(json.dumps({"model": "embeddinggemma", "embeddings": [[1, 2]]}).encode())

    monkeypatch.setattr(embeddings, "urlopen", slow_read)
    try:
        with pytest.raises(AiProviderError, match="timeout_or_network"):
            HttpEmbeddingProvider(EmbeddingConfig(dimensions=2)).embed(
                ["topic"], purpose="query", timeout=0.05
            )
    finally:
        release.set()


def test_hosted_selection_without_credentials_is_controlled(monkeypatch):
    monkeypatch.setattr(embeddings, "urlopen", lambda *a, **k: pytest.fail("network called"))
    with pytest.raises(AiProviderError, match="configuration"):
        HttpEmbeddingProvider(EmbeddingConfig(provider="openai")).embed(["topic"], purpose="query")
