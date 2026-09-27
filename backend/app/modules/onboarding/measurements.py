"""Explicit personal measurements, with question-scoped omission of units."""

import re
import unicodedata
from decimal import Decimal

NUMBER = r"([0-9]+(?:[.,][0-9]+)?)"
WEIGHT_UNIT = r"(?:kg|kgs|quilos?|kilos?|quilogramas?|kilogramas?)"
HEIGHT_UNIT = r"(?:cm|centimetros?|m|metros?)"
CORRECTION_PREFIX = r"^(?:na verdade|corrigindo|correcao|o correto e|quis dizer)[,:]?\s*"


def normalized(text: str) -> str:
    return " ".join(
        "".join(
            c
            for c in unicodedata.normalize("NFKD", text.casefold())
            if not unicodedata.combining(c)
        ).split()
    )


def measurement_clauses(text: str) -> list[str]:
    text = re.sub(CORRECTION_PREFIX, "", normalized(text))
    text = re.sub(r"\b(peso|altura) e (?=\d)", r"\1 ", text)
    return [
        part.strip(" .!")
        for part in re.split(r",(?!\d)|;|(?<=[.!])\s+|\s+(?:e|mas|ou)\s+", text)
        if part.strip(" .!")
    ]


def measurement_values(field: str, text: str, *, focused: bool = False) -> set[Decimal]:
    """Reject targets, third parties, questions, foreign units and arbitrary numbers.

    Only complete, recognizable personal clauses qualify. The preceding question
    may supply the unit for a simple personal answer, never for another topic.
    """
    unit = HEIGHT_UNIT if field == "height_cm" else WEIGHT_UNIT
    subject = (
        r"(?:(?:minha\s+)?altura\s+(?:e\s+)?)"
        if field == "height_cm"
        else (r"(?:(?:meu\s+)?peso\s+(?:e\s+)?|(?:eu\s+)?peso\s*)")
    )
    generic = r"(?:(?:eu\s+)?(?:tenho|estou com|to com|tenho atualmente)\s+)"
    if field == "weight_kg":
        generic = r"(?:(?:eu\s+)?(?:tenho|estou com|to com|estou pesando|tenho atualmente)\s+)"
    suffix = r"(?:\s+de\s+altura)?" if field == "height_cm" else r"(?:\s+de\s+peso)?"
    alternatives = " ou " in normalized(text) and bool(
        re.search(rf"\d\s*{unit}\b", normalized(text))
    )
    values = set()
    for clause in measurement_clauses(text):
        clause = re.sub(r"^atualmente[,]?\s+", "", clause)
        match = re.fullmatch(rf"(?:{subject}|{generic})?{NUMBER}\s*({unit})?{suffix}", clause)
        if not match:
            continue
        number, units = Decimal(match[1].replace(",", ".")), match[2]
        explicit_topic = bool(re.match(subject, clause))
        if units is None and not (focused or explicit_topic or alternatives):
            continue
        if field == "height_cm":
            if units in {"m", "metro", "metros"}:
                number *= 100
            elif units is None:
                if 1 <= number < 3:
                    number *= 100
                elif number < 50:
                    continue  # A small unitless height needs an explicit unit.
        values.add(number)
    return values
