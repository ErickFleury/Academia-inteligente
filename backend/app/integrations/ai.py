"""Provider-neutral contracts and HTTP adapters for onboarding interviews."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class TrainingGenerationProvider(Protocol):
    def generate(self, *, prompt: str) -> str: ...


class AiProviderError(Exception):
    def __init__(self, category: str, *, retryable: bool) -> None:
        super().__init__(category)
        self.category, self.retryable = category, retryable


class AiInterviewTurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assistant_message: str = Field(min_length=1, max_length=4000)
    interview_status: Literal["in_progress", "ready"]


class AiOnboardingExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    onboarding: dict[str, Any]


class OnboardingAiProvider(Protocol):
    def interview_turn(self, context: dict[str, object]) -> AiInterviewTurnResponse: ...
    def extract_onboarding(self, context: dict[str, object]) -> AiOnboardingExtractionResponse: ...


_FIELDS: dict[str, object] = {
    "training_goal": {"type": "string", "maxLength": 500},
    "training_experience": {
        "type": "string",
        "enum": ["none", "beginner", "intermediate", "advanced"],
    },
    "height_cm": {"type": "integer", "minimum": 1, "maximum": 300},
    "weight_kg": {"type": "number", "exclusiveMinimum": 0, "maximum": 500},
    "has_limitations_or_complaints": {"type": "boolean"},
    "limitations_or_complaints": {"type": ["string", "null"], "maxLength": 2000},
    "uses_medications": {"type": "boolean"},
    "medications": {"type": ["string", "null"], "maxLength": 2000},
    "has_health_conditions": {"type": "boolean"},
    "health_conditions": {"type": ["string", "null"], "maxLength": 2000},
}
_INTERVIEW = (
    "Você entrevista onboarding de academia em português. Pergunte de forma natural, use o "
    "contexto, não invente, diagnostique ou exponha termos técnicos. Retorne ready apenas "
    "quando tudo foi explicitamente informado."
)
_EXTRACTION = (
    "Extraia somente fatos explicitamente informados para o esquema. "
    "Não invente, diagnostique ou prescreva."
)


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        default=lambda item: float(item) if isinstance(item, Decimal) else str(item),
    )


def _turn_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "assistant_message": {"type": "string", "minLength": 1, "maxLength": 4000},
            "interview_status": {"type": "string", "enum": ["in_progress", "ready"]},
        },
        "required": ["assistant_message", "interview_status"],
    }


def _extraction_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "onboarding": {
                "type": "object",
                "additionalProperties": False,
                "properties": _FIELDS,
                "required": list(_FIELDS),
            }
        },
        "required": ["onboarding"],
    }


@dataclass(frozen=True)
class OpenAiConfig:
    api_key: str
    model: str
    timeout_seconds: int

    @classmethod
    def from_environment(cls) -> "OpenAiConfig":
        return cls(
            os.environ.get("OPENAI_API_KEY", ""),
            os.environ.get("OPENAI_MODEL", "gpt-5.6-luna"),
            int(os.environ.get("AI_TIMEOUT_SECONDS", "10")),
        )


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str
    model: str
    timeout_seconds: int

    @classmethod
    def from_environment(cls) -> "OllamaConfig":
        return cls(
            os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
            os.environ.get("OLLAMA_MODEL", "qwen3:8b"),
            int(os.environ.get("OLLAMA_TIMEOUT_SECONDS", "30")),
        )


class _Provider:
    def _call(
        self,
        context: dict[str, object],
        instructions: str,
        schema: dict[str, object],
        type_: type[BaseModel],
    ) -> BaseModel:
        try:
            with urlopen(
                self._request(context, instructions, schema), timeout=self._timeout
            ) as response:  # noqa: S310
                return type_.model_validate_json(self._text(json.load(response)))
        except HTTPError as error:
            raise AiProviderError(
                "provider_server" if error.code >= 500 or error.code == 429 else "configuration",
                retryable=error.code >= 500 or error.code == 429,
            ) from None
        except (TimeoutError, URLError):
            raise AiProviderError("timeout_or_network", retryable=True) from None
        except (json.JSONDecodeError, ValidationError, ValueError, TypeError):
            raise AiProviderError("malformed_structured_output", retryable=True) from None

    def interview_turn(self, context: dict[str, object]) -> AiInterviewTurnResponse:
        return self._call(context, _INTERVIEW, _turn_schema(), AiInterviewTurnResponse)  # type: ignore[return-value]

    def extract_onboarding(self, context: dict[str, object]) -> AiOnboardingExtractionResponse:
        return self._call(
            context, _EXTRACTION, _extraction_schema(), AiOnboardingExtractionResponse
        )  # type: ignore[return-value]


class OpenAiResponsesOnboardingProvider(_Provider):
    def __init__(self, config: OpenAiConfig | None = None) -> None:
        self._config = config or OpenAiConfig.from_environment()
        self._timeout = self._config.timeout_seconds

    def _request(
        self, context: dict[str, object], instructions: str, schema: dict[str, object]
    ) -> Request:
        if not self._config.api_key:
            raise AiProviderError("configuration", retryable=False)
        body = {
            "model": self._config.model,
            "instructions": instructions,
            "input": _json(context),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "onboarding",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        return Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {self._config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

    def _text(self, payload: object) -> str:
        for item in payload.get("output", []) if isinstance(payload, dict) else []:
            for content in item.get("content", []) if isinstance(item, dict) else []:
                if (
                    isinstance(content, dict)
                    and content.get("type") == "output_text"
                    and isinstance(content.get("text"), str)
                ):
                    return content["text"]
        raise ValueError


class OllamaOnboardingProvider(_Provider):
    def __init__(self, config: OllamaConfig | None = None) -> None:
        self._config = config or OllamaConfig.from_environment()
        self._timeout = self._config.timeout_seconds

    def _request(
        self, context: dict[str, object], instructions: str, schema: dict[str, object]
    ) -> Request:
        body = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": _json(context)},
            ],
            "stream": False,
            "format": schema,
        }
        return Request(
            f"{self._config.base_url.rstrip('/')}/api/chat",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    def _text(self, payload: object) -> str:
        message = payload.get("message") if isinstance(payload, dict) else None
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ValueError
        return message["content"]


def onboarding_ai_provider_from_environment() -> OnboardingAiProvider:
    provider = os.environ.get("AI_PROVIDER", "openai").strip().lower()
    if provider == "openai":
        return OpenAiResponsesOnboardingProvider()
    if provider == "ollama":
        return OllamaOnboardingProvider()
    raise AiProviderError("configuration", retryable=False)
