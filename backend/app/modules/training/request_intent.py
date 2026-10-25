"""Current-request text and goal intent, independent of conversation history."""

import re
import unicodedata

from app.modules.training.prescription_contract import PrescriptionRejection

GOAL_LABELS = {
    "strength": "Força",
    "hypertrophy": "Hipertrofia",
    "weight_loss": "Emagrecimento",
    "cardiorespiratory_fitness": "Condicionamento aeróbico",
    "muscular_endurance": "Resistência muscular",
    "power": "Potência",
    "mobility_flexibility": "Flexibilidade",
    "balance": "Equilíbrio",
    "functional_autonomy": "Autonomia funcional",
    "general_health": "Saúde geral",
    "sport_performance": "Desempenho esportivo",
}
GOAL_TERMS = {
    "strength": r"forca|strength",
    "hypertrophy": (
        r"hipertrof\w*|(?:ganho de |ganhar )massa(?: muscular)?|massa muscular|hypertrophy"
    ),
    "weight_loss": r"emagrec\w*|perder peso|perda de peso|(?:perder|reduzir) gordura",
    "cardiorespiratory_fitness": (
        r"cardio\w*|aerob\w*|condicionamento(?: aerobico)?|resistencia aerobica|endurance aerob\w*"
    ),
    "muscular_endurance": r"resistencia muscular(?: localizada)?|muscular endurance",
    "power": r"potencia|explos\w*",
    "mobility_flexibility": r"mobilidade|flexibilidade|alongamento\w*|flexibility|stretching",
    "balance": r"equilibrio|balance",
    "functional_autonomy": r"autonomia(?: funcional)?|funcional",
    "general_health": r"saude geral|bem[ -]estar|general health",
    "sport_performance": r"esport\w*|sport(?:s)?|atlet\w*",
}


def request_text(message: str) -> str:
    """Remove only a copied client-role header, never arbitrary transcript turns."""
    return re.sub(
        r"\A\s*(?:você|voce|cliente|usuário|usuario)\s*:?\s*\r?\n+",
        "",
        message,
        count=1,
        flags=re.IGNORECASE,
    ).strip()


def normalized(message: str) -> str:
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", request_text(str(message)).casefold())
            if not unicodedata.combining(c)
        ).split()
    )


def goal_families(message):
    value = normalized(message)
    # A stated replacement is different from asking for both the old and new goal.
    if re.search(r"\bantes\b.+\bagora\b", value):
        value = re.split(r"\bagora\b", value, maxsplit=1)[1]
    found = []
    for family, terms in GOAL_TERMS.items():
        for match in re.finditer(r"(?<!\w)(?:" + terms + r")(?!\w)", value):
            # Preserve an explicit "não quero ... e ..." span through conjunctions.
            before = re.split(r"[,;.!?]|\b(?:mas|porem)\b", value[: match.start()])[-1]
            negative = re.search(r"\b(?:nao (?:quero|desejo|pretendo|inclua|gere)|sem)\b", before)
            if negative and not re.search(
                r"\b(?:quero|prefiro|desejo|foco)\b", before[negative.end() :]
            ):
                continue
            if re.match(r"\s+nao\b", value[match.end() :]):
                continue
            found.append(family)
            break
    return found


def goal_family(value):
    found = goal_families(value)
    if len(found) != 1:
        raise PrescriptionRejection(
            "missing_input",
            "goal_priority_confirmation_required"
            if found
            else "training_goal_confirmation_required",
        )
    return found[0]


def requested_goal(request, onboarding_goal):
    found = goal_families(request)
    if len(found) > 1:
        value = request_text(request).casefold()
        for pattern in (
            r"(?:objetivo|foco)\s+principal\s*(?::|é\b|eh\b)\s*([^,;.!]+)",
            r"([^,;.!]+?)\s+(?:como\s+)?(?:objetivo|foco)\s+principal\b",
            r"\bprioridade(?:\s+para)?\s*:?\s*([^,;.!]+)",
        ):
            primary = re.search(pattern, value)
            if primary and len(selected := goal_families(primary.group(1))) == 1:
                return GOAL_LABELS[selected[0]]
        raise PrescriptionRejection("missing_input", "goal_priority_confirmation_required")
    return GOAL_LABELS[found[0]] if found else onboarding_goal
