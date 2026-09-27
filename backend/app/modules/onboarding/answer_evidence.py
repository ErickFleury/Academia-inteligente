"""Conservative source checks: model readiness and plausible values are not evidence.

Only retained client messages or existing form values can support an extraction.
Ambiguous language stays unanswered; the interviewer can ask for clarification.
This is input provenance validation, not medical interpretation.
"""

import re
import unicodedata
from decimal import Decimal

from app.integrations.ai import AiOnboardingExtractionResponse
from app.modules.onboarding.models import Onboarding, OnboardingAiMessage
from app.modules.onboarding.schema import OnboardingDraftUpdate

_TOPICS = {
    "training_goal": r"\b(objetivo|objetivos|meta|metas|alcan[cç]ar|busca)\b",
    "training_experience": (
        r"\b(experiencia|nivel|iniciante|intermediari\w*|avancad\w*|treinou|treinei)\b"
    ),
    "height_cm": r"\b(altura|alto|alta|centimetros?)\b",
    "weight_kg": r"\b(peso|pesa|quilos?|kg)\b",
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
    topic = _DETAILS.get(field, field)
    topics = _topic_fields(quote)
    focused = _topic_fields(question) == {topic} and (not topics or topic in topics)
    explicit = topic in topics
    # Never turn uncertainty or a question into a reported fact.
    if re.search(_UNCERTAIN, answer) or "?" in quote:
        return False
    if field in {"height_cm", "weight_kg"}:
        if re.search(r"\b(nao|meta|quero|queria|pretendo|objetivo|chegar|pesava|media)\b", quote):
            return False
        # Unit-bearing spans must contain the exact reported measurement. A bare
        # number is accepted only as a direct answer to that measurement's question.
        unit = (
            r"(?:cm|centimetros?|m|metros?)"
            if field == "height_cm"
            else r"(?:kg|quilos?|quilogramas?)"
        )
        matches = list(re.finditer(rf"(?<![\w.,])([0-9]+(?:[.,][0-9]+)?)\s*({unit})\b", quote))
        if not matches and focused:
            bare = re.fullmatch(r"\s*([0-9]+(?:[.,][0-9]+)?)\s*[.!]?", quote)
            matches = [bare] if bare else []
        for match in matches:
            number = Decimal(match[1].replace(",", "."))
            units = match[2] if match.lastindex == 2 else None
            if field == "height_cm" and (
                units in {"m", "metro", "metros"} or (units is None and number < 3)
            ):
                number *= 100
            if number == Decimal(str(value)):
                return True
        return False
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
    onboarding: Onboarding,
    messages: list[OnboardingAiMessage],
) -> OnboardingDraftUpdate:
    """Filter unsupported values without writing the draft or persisting citations."""
    candidate = OnboardingDraftUpdate.model_validate(extraction.onboarding)
    values = {field: getattr(onboarding, field) for field in OnboardingDraftUpdate.model_fields}
    by_sequence = {message.sequence: message for message in messages}
    for field, value in candidate.model_dump().items():
        if value is not None and value == values[field]:
            continue
        evidence = extraction.evidence.get(field)
        source = by_sequence.get(evidence.message_sequence) if evidence else None
        if not source or source.role != "user" or evidence.quote not in source.content:
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
            continue
        if value is None:
            continue
        if _supports(field, value, evidence.quote, question, source.content):
            values[field] = value
    for detail, flag in _DETAILS.items():
        if values[flag] is False:
            values[detail] = None
    return OnboardingDraftUpdate.model_validate(values)
