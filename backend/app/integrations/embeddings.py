"""Replaceable, bounded document/query embeddings; never stores input or output."""

from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import dataclass
from typing import Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from app.integrations.ai import AiProviderError
from app.integrations.ai_budget import BudgetExceeded, bounded_wait

Purpose = Literal["document", "query"]
MAX_INPUT_BYTES = 6000
MAX_BATCH = 16
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = "ollama"
    model: str = "embeddinggemma"
    dimensions: int = 768
    base_url: str = "http://ollama:11434"
    api_key: str = ""
    timeout_seconds: float = 10
    revision: str = "1"
    gpu_layers: int = 0

    def __post_init__(self):
        if (
            self.provider not in {"ollama", "openai"}
            or not self.model.strip()
            or not 1 <= self.dimensions <= 4096
            or not 0 < self.timeout_seconds <= 120
            or not self.revision.strip()
            or not -1 <= self.gpu_layers <= 999
        ):
            raise AiProviderError("configuration", retryable=False)
        if self.provider == "ollama":
            parsed = urlsplit(self.base_url)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or parsed.query
                or parsed.fragment
                or ":cloud" in self.model.lower()
                or parsed.hostname == "ollama.com"
            ):
                raise AiProviderError("configuration", retryable=False)

    @property
    def fingerprint(self) -> str:
        # Index identity includes preprocessing and an operator-controlled artifact revision.
        value = [self.provider, self.model, self.dimensions, self.revision, "retrieval-prefix-v1"]
        return hashlib.sha256(json.dumps(value).encode()).hexdigest()

    @classmethod
    def from_environment(cls) -> EmbeddingConfig:
        provider = os.environ.get("AI_EMBEDDING_PROVIDER", "ollama").strip().lower()
        hosted = provider == "openai"
        try:
            return cls(
                provider=provider,
                model=os.environ.get(
                    "AI_EMBEDDING_MODEL", "text-embedding-3-small" if hosted else "embeddinggemma"
                ),
                dimensions=int(
                    os.environ.get("AI_EMBEDDING_DIMENSIONS", "1536" if hosted else "768")
                ),
                base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
                api_key=os.environ.get("OPENAI_API_KEY", "") if hosted else "",
                timeout_seconds=float(os.environ.get("AI_EMBEDDING_TIMEOUT_SECONDS", "10")),
                revision=os.environ.get("AI_EMBEDDING_REVISION", "1"),
                gpu_layers=int(os.environ.get("AI_EMBEDDING_GPU_LAYERS", "0")),
            )
        except ValueError:
            raise AiProviderError("configuration", retryable=False) from None


class EmbeddingProvider(Protocol):
    config: EmbeddingConfig

    def embed(
        self, texts: list[str], *, purpose: Purpose, timeout: float | None = None
    ) -> list[list[float]]: ...


class HttpEmbeddingProvider:
    def __init__(self, config: EmbeddingConfig | None = None):
        self.config = config or EmbeddingConfig.from_environment()

    def embed(
        self, texts: list[str], *, purpose: Purpose, timeout: float | None = None
    ) -> list[list[float]]:
        if purpose not in {"query", "document"} or not 1 <= len(texts) <= MAX_BATCH:
            raise AiProviderError("embedding_input", retryable=False)
        if any(not isinstance(t, str) or not t.strip() for t in texts):
            raise AiProviderError("embedding_input", retryable=False)
        inputs = list(texts)
        if self.config.provider == "ollama" and self.config.model.split(":")[0] == "embeddinggemma":
            prefix = (
                "task: search result | query: " if purpose == "query" else "title: none | text: "
            )
            inputs = [prefix + text for text in texts]
        if any(len(t.encode("utf-8")) > MAX_INPUT_BYTES for t in inputs):
            raise AiProviderError("embedding_input", retryable=False)
        deadline_timeout = min(
            self.config.timeout_seconds,
            self.config.timeout_seconds if timeout is None else timeout,
        )
        if deadline_timeout <= 0:
            raise AiProviderError("budget_exhausted", retryable=False)
        headers = {"Content-Type": "application/json"}
        body = {"model": self.config.model, "input": inputs, "dimensions": self.config.dimensions}
        if self.config.provider == "openai":
            if not self.config.api_key:
                raise AiProviderError("configuration", retryable=False)
            endpoint = "https://api.openai.com/v1/embeddings"
            headers["Authorization"] = f"Bearer {self.config.api_key}"
            body["encoding_format"] = "float"
        else:
            endpoint = f"{self.config.base_url.rstrip('/')}/api/embed"
            body["truncate"] = False
            # Keep the small embedding model in RAM by default, leaving scarce
            # VRAM for generation and avoiding repeated model evictions on 8GB GPUs.
            body["options"] = {"num_gpu": self.config.gpu_layers}
        request = Request(endpoint, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:

            def read():
                with urlopen(request, timeout=deadline_timeout) as response:  # noqa: S310
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise ValueError
                    return json.loads(raw)

            payload = bounded_wait(read, deadline_timeout)
            if not isinstance(payload, dict):
                raise ValueError
            if self.config.provider == "openai":
                entries = payload.get("data")
                if not isinstance(entries, list) or len(entries) != len(texts):
                    raise ValueError
                ordered = sorted(entries, key=lambda entry: entry["index"])
                if [e["index"] for e in ordered] != list(range(len(texts))):
                    raise ValueError
                vectors = [e["embedding"] for e in ordered]
            else:
                if payload.get("model") != self.config.model:
                    raise ValueError
                vectors = payload.get("embeddings")
            if not isinstance(vectors, list) or len(vectors) != len(texts):
                raise ValueError
            for vector in vectors:
                if not isinstance(vector, list) or len(vector) != self.config.dimensions:
                    raise ValueError
                if any(type(v) not in (int, float) or not math.isfinite(v) for v in vector):
                    raise ValueError
                if not any(v != 0 for v in vector):
                    raise ValueError
            return vectors
        except HTTPError as error:
            retryable = error.code >= 500 or error.code == 429
            raise AiProviderError(
                "provider_server" if retryable else "embedding_rejected", retryable=retryable
            ) from None
        except (TimeoutError, URLError, BudgetExceeded):
            raise AiProviderError("timeout_or_network", retryable=True) from None
        except (ValueError, TypeError, KeyError, AttributeError):
            raise AiProviderError("malformed_embedding_output", retryable=False) from None
