"""Bounded client questions, rendered independently of agent-facing prose."""

import re
import unicodedata
from datetime import UTC, date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

ClientField = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,47}$")]


class ClientQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    field: ClientField
    text: str = Field(min_length=5, max_length=200)

    @field_validator("text")
    @classmethod
    def personal_question(cls, value):
        text = _normalized(value)
        if (
            not value.endswith("?")
            or "\n" in value
            or re.search(
                r"peca ao cliente|confirme com o cliente|os trechos|"
                r"quant[oa]s? (?:series|repeticoes)|intensidade desejada|"
                r"(?:carga|descanso) (?:devo|devemos|recomendada|ideal)|%.*1rm",
                text,
            )
        ):
            raise ValueError("Ask the client a personal question, not for technical prescription")
        return value


QUESTIONS = {
    "age": "Qual é sua idade?",
    "training_goal": "Qual é seu principal objetivo com o treino?",
    "training_experience": "Você já treinou antes? Qual é sua experiência?",
    "height_cm": "Qual é sua altura?",
    "weight_kg": "Qual é seu peso atual?",
    "limitations_or_complaints": "Você tem alguma dor, lesão ou limitação que afete o treino?",
    "medications": "Você usa algum medicamento? Se sim, qual?",
    "health_conditions": "Você tem alguma condição de saúde relevante para o treino? Qual?",
    "weekly_availability": "Quantos dias por semana você pode treinar?",
    "session_duration": "Quanto tempo você tem para cada treino?",
    "current_limitation_impact": "Quais movimentos ou exercícios sua limitação dificulta hoje?",
    "equipment_restrictions": "Há algum equipamento que você não pode usar? Qual?",
    "target_exercise": "Sobre qual exercício ou movimento você está falando?",
}


def _normalized(value):
    return "".join(
        c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c)
    )


def _answer_value(field, raw):
    value = _normalized(raw).strip().rstrip(".! ")
    if not value or re.search(r"\?|\b(?:talvez|acho|nao sei|nao lembro)\b", value):
        return None
    if field == "age":
        match = re.fullmatch(r"(?:tenho )?(\d{1,3})(?: anos)?", value)
        return int(match[1]) if match and 1 <= int(match[1]) <= 120 else None
    if field == "weekly_availability":
        match = re.fullmatch(r"([1-7])(?: (?:dias|vezes)(?: por semana)?)?", value)
        return int(match[1]) if match else None
    if field == "session_duration":
        match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(h|hora|horas|min|minuto|minutos)", value)
        if not match:
            return None  # A bare number does not establish minutes versus hours.
        minutes = float(match[1].replace(",", ".")) * (60 if match[2].startswith("h") else 1)
        return int(minutes) if minutes.is_integer() and 1 <= minutes <= 1440 else None
    if field in {"current_limitation_impact", "equipment_restrictions", "target_exercise"}:
        # Arbitrary prose needs semantic interpretation. A continuation command
        # or topic change is not an answer merely because it is one line.
        return raw.strip() if value in {"nenhum", "nenhuma", "nao"} else None
    return None


def question_catalog(context):
    """Legacy wording is a fallback, not the list of topics the model can discuss."""
    catalog = {**QUESTIONS, **context.get("question_catalog", {})}
    for fact in context.get("client_memory", []):
        if fact.get("answer_data"):
            catalog[fact["answer_data"]["field"]] = fact["answer_data"]["question"]
    for item in context.get("recent_messages", []):
        for question in (item.get("clarification") or {}).get("questions", []):
            catalog[question["field"]] = question["text"]
    for key, answer in context.get("client_answers", {}).items():
        catalog.setdefault(key, answer.get("question", "Contexto informado"))
    return catalog


def client_answers(context):
    """Bind short replies only to the immediately preceding saved question list.

    These dated client reports complement, never rewrite, completed onboarding.
    Recompute from bounded retained history rather than retaining extra health data.
    """
    history = [
        *context.get("recent_messages", []),
        {
            "role": "user",
            "content": context.get("current_user_message", ""),
            "created_at": context.get("current_message_created_at", context.get("current_date")),
            "event_id": context.get("current_event_id"),
        },
    ]
    answers = {
        fact["answer_data"]["field"]: {
            **{key: value for key, value in fact["answer_data"].items() if key != "field"},
            "reported_at": fact["reported_at"],
            "attribution": "client_reported",
        }
        for fact in context.get("client_memory", [])
        if fact.get("answer_data")
    }
    catalog = question_catalog(context)
    for previous, reply in zip(history, history[1:]):
        if previous.get("role") != "assistant" or reply.get("role") != "user":
            continue
        detail = previous.get("clarification") or {}
        for field, report in detail.get("client_answers", {}).items():
            if not isinstance(report, dict):
                continue
            cutoff = context.get("answer_event_after")
            if cutoff:
                if not report.get("reported_at"):
                    continue
                reported = datetime.fromisoformat(report["reported_at"])
                reported = reported.replace(tzinfo=reported.tzinfo or UTC)
                if reported <= datetime.fromisoformat(cutoff):
                    continue
            existing = answers.get(field)
            if not existing or (report.get("reported_at") or "") >= existing["reported_at"]:
                answers[field] = report
        fields = detail.get("missing_fields", [])
        if (
            detail.get("reason") != "missing_client_information"
            or not fields
            or len(fields) != len(set(fields))
            or any(field not in catalog for field in fields)
            or previous.get("content") != render_questions(fields, catalog)
        ):
            continue
        lines = reply.get("content", "").strip().splitlines()
        numbered = [re.fullmatch(r"\s*(\d+)[.)]\s+(.+)", line) for line in lines]
        if lines and all(numbered):
            indexes = [int(match[1]) - 1 for match in numbered]
            if len(indexes) != len(set(indexes)) or any(i < 0 or i >= len(fields) for i in indexes):
                continue
            pairs = [(fields[i], match[2]) for i, match in zip(indexes, numbered)]
        elif len(lines) == len(fields) and not any(numbered):
            pairs = list(zip(fields, lines))
        else:
            continue  # Do not shift an incomplete or mixed-format answer list.
        for field, raw in pairs:
            raw = re.sub(r"^\s*[-*]\s+", "", raw).strip()
            value = _answer_value(field, raw)
            if value is None and not re.search(
                r"\b(?:talvez|acho|nao sei|nao lembro)\b", _normalized(raw)
            ):
                continue
            answers[field] = {
                "question": catalog[field],
                "value": value,
                "source_text": raw,
                "reported_at": reply.get("created_at"),
                "attribution": "client_reported",
                "source_event_id": reply.get("event_id"),
                **({"unit": "minutes"} if field == "session_duration" else {}),
            }
    return answers


def available_fields(context, plan_brief):
    """Exclude recorded answers; explicit false and experience='none' are answers."""
    records = {
        **context.get("relevant_onboarding", {}),
        **context.get("completed_onboarding", {}),
        **plan_brief,
        **context.get("authoritative_health_records", {}),
    }
    catalog = question_catalog(context)
    known = {key for key in catalog if records.get(key) not in (None, "")}
    for flag, detail in (
        ("has_limitations_or_complaints", "limitations_or_complaints"),
        ("uses_medications", "medications"),
        ("has_health_conditions", "health_conditions"),
    ):
        if records.get(flag) is False:
            known.add(detail)
    statements = [context.get("current_user_message", "")]
    statements += [
        item.get("content", "")
        for item in context.get("recent_messages", [])
        if item.get("role") == "user"
    ]
    today = date.fromisoformat(context.get("current_date", date.today().isoformat()))
    for fact in context.get("client_memory", []):
        # Old reports are not automatically proof of a current answer.
        try:
            reported = datetime.fromisoformat(fact["reported_at"]).date()
        except (KeyError, ValueError, TypeError):
            continue
        if 0 <= (today - reported).days <= 30:
            statements.append(fact.get("text", ""))
    for statement in statements:
        if not isinstance(statement, str):
            continue
        if re.search(r"\?|\b(?:talvez|acho|nao sei|nao lembro)\b", _normalized(statement)):
            continue
        # Split before accent folding: Portuguese 'é' is not the conjunction 'e'.
        for clause in re.split(r"[.;,\n]|\s+e\s+", statement, flags=re.IGNORECASE):
            clause = _normalized(clause.strip())
            if re.fullmatch(r"(?:eu\s+)?(?:tenho\s+)?(?:[1-9]\d?|1[01]\d|120)\s+anos", clause):
                known.add("age")
            if re.match(
                r"^(?:eu\s+)?(?:posso|consigo|vou) treinar "
                r"(?:[1-7]|um|dois|tres|quatro|cinco|seis|sete) (?:dias|vezes) por semana\b",
                clause,
            ):
                known.add("weekly_availability")
            if re.match(r"^(?:eu\s+)?tenho \d+ minutos (?:para|por|em cada) treino\b", clause):
                known.add("session_duration")
    if records.get("has_limitations_or_complaints") is not True:
        known.add("current_limitation_impact")
    for field, answer in context.get("client_answers", {}).items():
        # Durable reports remain useful context, but old reports may need a
        # relevant confirmation before a consequential new prescription.
        if answer.get("reported_at"):
            reported = datetime.fromisoformat(answer["reported_at"]).date()
            if (today - reported).days > 30:
                continue
        if answer["value"] is not None:
            known.add(field)
        elif field not in records:
            known.discard(field)
    return [field for field in catalog if field not in known]


def render_questions(fields, catalog=None):
    questions = [(catalog or QUESTIONS)[field] for field in dict.fromkeys(fields)]
    return questions[0] if len(questions) == 1 else "\n".join(f"- {q}" for q in questions)
