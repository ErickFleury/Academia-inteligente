"""Bounded search aliases for common training vocabulary, never answer content."""

import re
import unicodedata

# Longer phrases take precedence, preserving exercise variations. These aliases
# add retrieval terms only; they make no prescription or applicability claim.
ALIASES = {
    "supino reto": "flat bench press",
    "supino inclinado": "incline bench press",
    "supino declinado": "decline bench press",
    "supino": "bench press",
    "puxada alta": "lat pulldown",
    "levantamento terra": "deadlift",
    "agachamento": "squat",
    "remada sentada": "seated row",
    "remada": "row",
    "desenvolvimento de ombros": "shoulder press",
    "rosca direta": "biceps curl",
    "com barra": "barbell",
    "halteres": "dumbbell",
    "ajudante": "spotter",
    "recolocar barra": "rerack bar",
    "pontos de contato": "contact points",
    "travar joelhos": "locking knees",
    "extensao dos joelhos": "knee extension",
    "musculacao": "resistance training",
    "treinamento resistido": "resistance training",
    "hipertrofia": "hypertrophy",
    "adultos saudaveis": "healthy adults",
    "grupos musculares": "muscle groups",
    "frequencia": "frequency",
    "semanal": "weekly",
    "series": "sets",
    "repeticoes": "repetitions",
    "por semana": "per week",
}


def expand_search_terms(query: str) -> str:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", query.casefold())
        if not unicodedata.combining(char)
    )
    matched = set()
    aliases = []
    for phrase, equivalent in ALIASES.items():
        for match in re.finditer(r"\b" + re.escape(phrase) + r"\b", normalized):
            positions = set(range(match.start(), match.end()))
            if positions & matched:
                continue
            matched.update(positions)
            if equivalent not in normalized and equivalent not in aliases:
                aliases.append(equivalent)
    expanded = query
    for alias in aliases:
        if len(expanded) + len(alias) + 1 <= 500:
            expanded += " " + alias
    return expanded
