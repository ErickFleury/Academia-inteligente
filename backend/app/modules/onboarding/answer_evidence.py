"""Conservative source checks: model readiness and plausible values are not evidence.

Only retained client messages or existing form values can support an extraction.
Ambiguous language stays unanswered; the interviewer can ask for clarification.
This is input provenance validation, not medical interpretation.
"""

import re
import unicodedata
from decimal import Decimal

from app.integrations.ai import AiOnboardingExtractionResponse
from app.modules.onboarding.measurements import measurement_values
from app.modules.onboarding.models import Onboarding, OnboardingAiMessage
from app.modules.onboarding.schema import OnboardingDraftUpdate

_TOPICS = {
    "training_goal": r"\b(objetivo|objetivos|meta|metas|alcan[cç]ar|busca)\b",
    "training_experience": (
        r"\b(experiencia|nivel|iniciante|intermediari\w*|avancad\w*|treinou|treinei)\b"
    ),
    "height_cm": r"\b(altura|alto|alta|centimetros?)\b",
    "weight_kg": r"\b(peso|pesa|quilos?|kilos?|kg|kgs|quilogramas?|kilogramas?)\b",
    "has_limitations_or_complaints": (
        r"\b(limitac\w*|queixa\w*|dor|dores|lesao|lesoes|desconforto\w*)\b"
    ),
    "uses_medications": r"\b(medicac\w*|medicament\w*|remedio\w*)\b",
    "has_health_conditions": r"\b(saude|doenca\w*|condic\w*|historico|diagnostico\w*)\b",
}
_DETAILS = {
    "limitations_or_complaints": "has_limitations_or_complaints",
    "medications": "uses_medications",
    "health_conditions": "has_health_conditions",
}
_EXPERIENCE = {
    "none": r"\b(nunca treinei|nunca treinou|sem experiencia|nenhuma experiencia|nenhuma|nenhum)\b",
    "beginner": r"\b(iniciante|principiante|beginner)\b",
    "intermediate": r"\b(intermediari[oa]|intermediate)\b",
    "advanced": r"\b(avancad[oa]|advanced)\b",
}
_UNCERTAIN = r"\b(nao sei|nao lembro|nao tenho certeza|talvez|acho que|pode ser)\b"
_NEGATIVE = r"\b(nao|nunca|nenhum\w*|sem)\b"
_POSITIVE = r"\b(sim|tenho|sinto|tomo|uso|possuo|apresento)\b"


def _normalize(text: str) -> str:
    return " ".join(
        "".join(
            char
            for char in unicodedata.normalize("NFKD", text.casefold())
            if not unicodedata.combining(char)
        ).split()
    )


def _topic_fields(text: str) -> set[str]:
    return {field for field, pattern in _TOPICS.items() if re.search(pattern, text)}


def _supports(field: str, value: object, quote: str, question: str, answer: str) -> bool:
    quote, question, answer = map(_normalize, (quote, question, answer))
    # Include the surrounding client sentence, so citing "uso remédios" from
    # "não uso remédios" cannot reverse the answer by dropping its negation.
    surrounding = [part for part in re.split(r"(?<=[.!?;])\s+", answer) if quote in part]
    if len(surrounding) == 1:
        quote = surrounding[0]
    # Acknowledgments may mention other fields; only the final question sets focus.
    question = re.split(r"[.!]\s+", question)[-1]
    if field in {"height_cm", "weight_kg"}:
        quote = re.sub(r"\b(peso|altura) e (?=\d)", r"\1 ", quote)
    topic = _DETAILS.get(field, field)
    clauses = re.split(r",(?!\d)|;|\s+(?:e|mas|porem)\s+", quote)
    relevant = [clause for clause in clauses if topic in _topic_fields(clause)]
    if field == "height_cm":
        relevant += [clause for clause in clauses if re.search(r"\d\s*(?:cm|m|metros?)\b", clause)]
    if relevant:
        quote = " ; ".join(dict.fromkeys(relevant))
    topics = _topic_fields(quote)
    focused = _topic_fields(question) == {topic} and (not topics or topic in topics)
    explicit = topic in topics
    # Never turn uncertainty or a question into a reported fact.
    if re.search(_UNCERTAIN, quote) or "?" in quote:
        return False
    if field in {"height_cm", "weight_kg"}:
        return measurement_values(field, quote, focused=focused) == {Decimal(str(value))}
    if field == "training_experience":
        if value != "none" and re.search(_NEGATIVE, quote):
            return False
        return (focused or explicit) and bool(
            re.search(_EXPERIENCE.get(str(value), r"(?!)"), quote)
        )
    if field in _DETAILS or field == "training_goal":
        # No paraphrased health claims: the saved text must exist in the citation.
        literal = _normalize(str(value)) in quote
        goal_statement = field == "training_goal" and bool(
            re.search(r"\b(quero|objetivo|ganhar|perder|hipertrofia|emagrecer)\b", quote)
        )
        return literal and (focused or explicit or goal_statement)
    if isinstance(value, bool):
        # A single "não" to a medication question cannot answer every health flag.
        if not (focused or explicit):
            return False
        clauses = re.split(r"[,;.!]|\s+(?:e|mas|porem)\s+", quote)
        relevant = [clause for clause in clauses if topic in _topic_fields(clause)]
        if not relevant and focused:
            relevant = [quote]
        reported = set()
        for clause in relevant:
            if re.search(_NEGATIVE, clause):
                reported.add(False)
            elif re.search(_POSITIVE, clause):
                reported.add(True)
        return reported == {value}
    return False


def grounded_answers(
    extraction: AiOnboardingExtractionResponse,
    onboarding: Onboarding | OnboardingDraftUpdate,
    messages: list[OnboardingAiMessage],
    *,
    latest_sequence: int | None = None,
    accepted_fields: set[str] | None = None,
) -> OnboardingDraftUpdate:
    """Filter unsupported values without writing the draft or persisting citations."""
    candidate = OnboardingDraftUpdate.model_validate(extraction.onboarding)
    values = {field: getattr(onboarding, field) for field in OnboardingDraftUpdate.model_fields}
    by_sequence = {message.sequence: message for message in messages}
    for field, value in candidate.model_dump().items():
        evidence = extraction.evidence.get(field)
        source = by_sequence.get(evidence.message_sequence) if evidence else None
        if not source or source.role != "user" or evidence.quote not in source.content:
            continue
        if latest_sequence is not None and source.sequence != latest_sequence:
            continue
        previous = by_sequence.get(source.sequence - 1)
        question = previous.content if previous and previous.role == "assistant" else ""
        # These finite categories are normalized from verified client words.
        # A provider saying "intermediate" while citing "iniciante" cannot
        # override the client's answer; an explicit "não" is not an unknown.
        options = (
            list(_EXPERIENCE)
            if field == "training_experience"
            else [False, True]
            if field in _DETAILS.values()
            else []
        )
        if options:
            supported = [
                option
                for option in options
                if _supports(field, option, evidence.quote, question, source.content)
            ]
            if len(supported) == 1:
                values[field] = supported[0]
                if accepted_fields is not None:
                    accepted_fields.add(field)
            continue
        if value is None:
            continue
        if _supports(field, value, evidence.quote, question, source.content):
            values[field] = value
            if accepted_fields is not None:
                accepted_fields.add(field)
    # Explicit measurements can be normalized directly from the current client
    # statement, even if the model omitted or reversed the number. This uses the
    # same negation/uncertainty checks and never borrows measurements from history.
    source = by_sequence.get(latest_sequence)
    if source and source.role == "user":
        previous = by_sequence.get(source.sequence - 1)
        question = previous.content if previous and previous.role == "assistant" else ""
        focus = _topic_fields(_normalize(re.split(r"[.!]\s+", question)[-1]))
        for field in ("height_cm", "weight_kg"):
            measurements = measurement_values(field, source.content, focused=focus == {field})
            if len(measurements) != 1:
                continue
            number = next(iter(measurements))
            if _supports(field, number, source.content, question, source.content):
                try:
                    normalized = OnboardingDraftUpdate(**{field: number})
                except ValueError:
                    continue
                values[field] = getattr(normalized, field)
                if accepted_fields is not None:
                    accepted_fields.add(field)
    for detail, flag in _DETAILS.items():
        if values[flag] is False:
            values[detail] = None
    return OnboardingDraftUpdate.model_validate(values)
