"""Fast handling only when every clause has an explicit, supported meaning."""

import re

from app.integrations.ai import AiOnboardingExtractionResponse
from app.modules.onboarding.answer_evidence import _DETAILS, _EXPERIENCE, _supports
from app.modules.onboarding.measurements import measurement_clauses, measurement_values
from app.modules.onboarding.schema import OnboardingDraftUpdate


def direct_extraction(
    message: str, sequence: int, question: str
) -> AiOnboardingExtractionResponse | None:
    values: dict[str, object] = {}
    for clause in measurement_clauses(message):
        found: dict[str, object] = {}
        for name in ("height_cm", "weight_kg"):
            # Source support determines focus; a bare number cannot answer both fields.
            options = measurement_values(name, clause, focused=True)
            for value in options:
                if _supports(name, value, clause, question, message):
                    found[name] = value
        for name in _DETAILS.values():
            # Do not bypass the model for extra symptoms/details in the same clause.
            simple = re.fullmatch(
                r"(?:sim|nao|(?:nao )?(?:tenho|uso|tomo) "
                r"(?:nenhuma? |qualquer )?(?:medicamentos?|medicacoes?|remedios?|"
                r"limitacoes?|queixas?|condicoes? de saude|doencas?))",
                clause,
            )
            if simple:
                for value in (False, True):
                    if _supports(name, value, clause, question, message):
                        found[name] = value
        for value, pattern in _EXPERIENCE.items():
            if re.fullmatch(r"(?:(?:eu )?sou )?" + pattern, clause) and _supports(
                "training_experience", value, clause, question, message
            ):
                found["training_experience"] = value
        if not found:
            # A negated old measurement in an explicit correction contributes no answer.
            if clause.startswith("nao ") and any(
                measurement_values(name, clause[4:], focused=True)
                for name in ("height_cm", "weight_kg")
            ):
                continue
            return None
        if any(name in values and values[name] != value for name, value in found.items()):
            return None
        values.update(found)
    if not values:
        return None
    try:
        OnboardingDraftUpdate.model_validate(values)
    except ValueError:
        return None
    return AiOnboardingExtractionResponse(
        onboarding=values,
        evidence={name: {"message_sequence": sequence, "quote": message} for name in values},
    )


def measurement_suggestion(message: str, field: str) -> str | None:
    """A single uncertain but explicit measurement can be offered, never saved silently."""
    cleaned = re.sub(
        r"\b(?:acho que|talvez|pode ser|aproximadamente|cerca de|uns|umas)\b",
        "",
        message,
        flags=re.I,
    )
    options = measurement_values(field, cleaned, focused=True)
    if len(options) != 1:
        return None
    value = next(iter(options))
    try:
        OnboardingDraftUpdate(**{field: value})
    except ValueError:
        return None
    return str(value)
