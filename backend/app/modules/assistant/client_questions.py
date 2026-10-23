"""Bounded client questions, rendered independently of agent-facing prose."""

import re
import unicodedata
from datetime import date, datetime
from typing import Literal

ClientField = Literal[
    "age",
    "training_goal",
    "training_experience",
    "height_cm",
    "weight_kg",
    "limitations_or_complaints",
    "medications",
    "health_conditions",
    "weekly_availability",
    "session_duration",
    "current_limitation_impact",
    "equipment_restrictions",
    "target_exercise",
]

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
        return raw.strip() if len(raw) <= 300 else None
    return None


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
            "created_at": context.get("current_date"),
        },
    ]
    answers = {}
    for previous, reply in zip(history, history[1:]):
        if previous.get("role") != "assistant" or reply.get("role") != "user":
            continue
        detail = previous.get("clarification") or {}
        fields = detail.get("missing_fields", [])
        if (
            detail.get("reason") != "missing_client_information"
            or not fields
            or len(fields) != len(set(fields))
            or any(field not in QUESTIONS for field in fields)
            or previous.get("content") != render_questions(fields)
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
            answers[field] = {
                "question": QUESTIONS[field],
                "value": _answer_value(field, raw),
                "source_text": raw,
                "reported_at": reply.get("created_at"),
                "attribution": "client_reported",
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
    known = {key for key in QUESTIONS if records.get(key) not in (None, "")}
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
        if answer["value"] is not None:
            known.add(field)
        elif field not in records:
            known.discard(field)
    return [field for field in QUESTIONS if field not in known]


def render_questions(fields):
    questions = [QUESTIONS[field] for field in dict.fromkeys(fields)]
    return questions[0] if len(questions) == 1 else "\n".join(f"- {q}" for q in questions)
