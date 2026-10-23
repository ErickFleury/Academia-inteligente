"""Validate model-interpreted client answers against bounded, owned source messages."""

import re
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.assistant.client_questions import QUESTIONS, ClientField, _normalized


class AnswerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    field: ClientField
    status: Literal["answered", "uncertain"]
    value: str | None = Field(default=None, max_length=300)
    source_index: int = Field(ge=0, le=6)
    quote: str = Field(min_length=1, max_length=500)


class InvalidAnswerInterpretation(ValueError):
    """No unverified interpretation can proceed to generation or persistence."""


def answer_sources(context):
    history = [
        *context.get("recent_messages", [])[-6:],
        {
            "role": "user",
            "content": context.get("current_user_message", ""),
            "created_at": context.get("current_message_created_at", datetime.now(UTC).isoformat()),
        },
    ]
    return [
        {
            "index": index,
            "text": item["content"],
            "reported_at": item.get("created_at"),
            "preceding_question": history[index - 1].get("content")
            if index and history[index - 1].get("role") == "assistant"
            else None,
        }
        for index, item in enumerate(history)
        if item.get("role") == "user" and item.get("content")
    ]


def _stamp(value):
    stamp = datetime.fromisoformat(value) if value else datetime.min
    return stamp.astimezone(UTC) if stamp.tzinfo else stamp.replace(tzinfo=UTC)


def _evidence_context(text, quote):
    """Allow quoted clauses, while retaining qualifiers immediately before them."""
    if text.count(quote) != 1:
        raise InvalidAnswerInterpretation("invalid_answer_evidence")
    start = text.index(quote)
    end = start + len(quote)
    if (start and text[start - 1].isalnum()) or (end < len(text) and text[end].isalnum()):
        raise InvalidAnswerInterpretation("invalid_answer_evidence")
    prefix = re.split(r"[.!?;,\n]|\s+(?:mas|porém|e)\s+", text[:start], flags=re.I)[-1]
    suffix = "?" if text[end:].lstrip().startswith("?") else ""
    return _normalized(prefix + quote + suffix)


def apply_interpretations(previous, updates, sources):
    """The model handles meaning; enforce provenance, uncertainty, bounds and chronology."""
    answers = {**previous}
    sources = {source["index"]: source for source in sources}
    seen = set()
    for update in sorted(updates, key=lambda item: item.source_index):
        source = sources.get(update.source_index)
        if source is None or (update.source_index, update.field) in seen:
            raise InvalidAnswerInterpretation("invalid_answer_source")
        seen.add((update.source_index, update.field))
        evidence = _evidence_context(source["text"], update.quote)
        uncertain = update.status == "uncertain" or bool(
            re.search(
                r"\?|\b(?:talvez|acho|nao sei|nao lembro|nao tenho certeza|quem sabe)\b",
                evidence,
            )
        )
        if re.match(
            r"^(?:meu|minha) (?:pai|mae|irmao|irma|amigo|amiga|filho|filha)\b|^(?:ele|ela)\b",
            evidence,
        ) and not re.search(r"\b(?:eu|tenho|minha idade)\b", evidence):
            raise InvalidAnswerInterpretation("third_party_answer")
        if (
            update.field in {"age", "height_cm", "weight_kg"}
            and re.search(r"\bnao (?:tenho|estou com|peso|meco)\b", evidence)
            and not uncertain
        ):
            raise InvalidAnswerInterpretation("negated_measurement")
        value = None if uncertain else update.value
        if not uncertain:
            if value is None or not value.strip():
                raise InvalidAnswerInterpretation("empty_answer")
            bounds = {
                "age": (1, 120),
                "weekly_availability": (1, 7),
                "session_duration": (1, 1440),
                "height_cm": (1, 300),
                "weight_kg": (0.01, 500),
            }
            if update.field in bounds:
                if not re.fullmatch(r"\d+(?:\.\d{1,2})?", value):
                    raise InvalidAnswerInterpretation("invalid_answer_number")
                value = float(value)
                low, high = bounds[update.field]
                if not low <= value <= high or (
                    update.field != "weight_kg" and not value.is_integer()
                ):
                    raise InvalidAnswerInterpretation("answer_out_of_range")
                value = int(value) if value.is_integer() else value
                # The duration question has no default unit. An unexplained
                # number cannot be interpreted as minutes just to fill a field.
                if update.field == "session_duration" and re.fullmatch(r"\s*\d+\s*", update.quote):
                    value = None
            elif update.field == "training_experience" and value not in {
                "none",
                "beginner",
                "intermediate",
                "advanced",
            }:
                raise InvalidAnswerInterpretation("invalid_experience")
        existing = answers.get(update.field)
        if existing and _stamp(existing.get("reported_at")) > _stamp(source.get("reported_at")):
            continue
        answers[update.field] = {
            "question": QUESTIONS[update.field],
            "value": value,
            "source_text": update.quote,
            "reported_at": source.get("reported_at"),
            "attribution": "client_reported",
            **({"unit": "minutes"} if update.field == "session_duration" else {}),
        }
    return answers


INTERPRET_ANSWERS = """
Interprete a conversa livremente antes de decidir se faltam informações. Não exija
palavras-chave, frases prontas, números em algarismos ou uma ordem específica.
Não duplique client_answers para a mesma fonte sem nova informação ou correção.
answer_sources contém SOMENTE mensagens do próprio cliente, indexadas, e a pergunta
anterior para contextualizar respostas curtas. Em answer_updates, extraia relatos
claros e correções pertinentes; use [] se não houver nenhum. Cada item contém field,
status (answered ou uncertain), value (string ou null), source_index e quote.
Copie em quote uma frase ou oração literal da fonte, incluindo suas negações e incerteza.
Não cite o assistente, livros, resumos ou outra pessoa como relato do cliente.
Não invente informações. status=uncertain e value=null quando houver dúvida,
contradição não resolvida ou retirada de uma resposta. Uma correção explícita mais
recente substitui a anterior; não transforme a negação de um valor em outro valor.
Extraia todas as respostas pertinentes da mensagem, mesmo fora da ordem das perguntas.
Use value numérico em string para age (anos), weekly_availability (dias por semana),
session_duration (minutos), height_cm (cm), weight_kg (kg). Converta unidades explícitas,
mas não adivinhe unidades ausentes. Para training_experience use none, beginner,
intermediate ou advanced; nos outros campos preserve o relato em pt-BR sem diagnóstico.
Exemplos: 'Acabei de fazer trinta e um.' -> age='31'; 'Vou às terças e quintas.' ->
weekly_availability='2'; 'Tenho uma hora e meia.' -> session_duration='90';
'Não são três dias, agora só consigo dois.' -> weekly_availability='2';
'Talvez consiga dois ou três.' -> weekly_availability=null, status=uncertain.
Respostas parciais preservam o que já foi respondido. Pergunte somente informações
necessárias ainda desconhecidas ou ambíguas APÓS aplicar suas interpretações.
Não peça reconfirmação por causa da redação informal. Uma mudança de assunto deve
receber resposta ao novo assunto, sem repetir a entrevista ou gerar um plano.
Interpretações nunca editam onboarding nem removem restrições autorizadas.
"""
