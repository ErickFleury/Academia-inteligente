"""Necessary source checks, not a medical applicability or safety decision.

The model still reviews meaning, conditions and applicability. These conservative
checks prevent an affirmative model verdict from inventing exercise names or
numerical prescriptions absent from its actual citations.
"""

import re
import unicodedata

from app.modules.knowledge.search_terms import ALIASES

NUMBER = r"(?P<low>\d+(?:\.\d+)?)(?:\s*(?:-|to|a|ate)\s*(?P<high>\d+(?:\.\d+)?))?"
TIME = r"minutes?|minutos?|min|seconds?|segundos?|sec|s|hours?|horas?"
WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
    "thirty": 30,
    "sixty": 60,
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "doze": 12,
    "quinze": 15,
    "vinte": 20,
    "trinta": 30,
    "sessenta": 60,
}
EXERCISES = {
    **{key: [value] for key, value in ALIASES.items()},
    "caminhada": ["caminhar", "walking", "walk"],
    "corrida": ["correr", "running", "run"],
    "ciclismo": ["pedalar", "cycling"],
    "natacao": ["nadar", "swimming"],
    "danca": ["dancar", "dancing"],
    "flexao de braco": ["flexao de bracos", "flexoes", "push-up", "pushup", "push up"],
    "flexoes": ["flexao de bracos", "push-up", "pushup", "push up"],
    "pular corda": ["jump rope", "rope skipping"],
    "alongamento": ["alongar", "stretching"],
}


def normalized(value):
    text = "".join(
        c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c)
    )
    text = text.replace("–", "-").replace("−", "-")
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    return " ".join(text.split())


def numbers(value):
    return re.sub(r"\b[a-z]+\b", lambda m: str(WORDS.get(m[0], m[0])), normalized(value))


def bounds(match, factor=1):
    low = float(match["low"]) * factor
    return low, float(match["high"] or match["low"]) * factor


def contains(wanted, ranges):
    return any(low <= wanted[0] <= wanted[1] <= high for low, high in ranges)


def counts(text, unit):
    return [
        bounds(m)
        for pattern in (NUMBER + rf"\s*(?:{unit})\b", rf"\b(?:{unit})\s*[:=]\s*" + NUMBER)
        for m in re.finditer(pattern, text)
    ]


def time_factor(unit):
    return 3600 if unit.startswith(("hour", "hora")) else 60 if unit.startswith("min") else 1


def times(text):
    rest_rows, offset, in_rest_table = [], 0, False
    for line in text.splitlines(keepends=True):
        if re.search(
            r"\b(?:table|tabela)\s+\d+(?:\.\d+)?[^\n]*"
            r"(?:rest interval|intervalos? de descanso)",
            line,
        ):
            in_rest_table = True
        elif in_rest_table:
            if (
                not line.strip()
                or len(line.strip()) > 180
                or re.match(r"\s*(?:note\b|nota\b|based on\b|table\b|tabela\b|#)", line)
            ):
                in_rest_table = False
            else:
                rest_rows.append((offset, offset + len(line)))
        offset += len(line)
    for match in re.finditer(NUMBER + rf"\s*(?P<unit>{TIME})\b", text):
        before, after = (
            text[max(0, match.start() - 45) : match.start()],
            text[match.end() : match.end() + 120],
        )
        rest = any(start <= match.start() < end for start, end in rest_rows) or bool(
            re.search(r"(?:rest|descanso)(?:\s+[a-z]+){0,4}\s*$", before)
            or re.match(r"\s*(?:de |of )?(?:rest|descanso|between sets|entre series)\b", after)
        )
        weekly = bool(re.search(r"\b(?:por semana|per week|semanais|weekly)\b", after))
        yield bounds(match, time_factor(match["unit"])), rest, weekly


def exercise_present(name, text):
    for alternative in re.split(r"\s+ou\s+|\s*/\s*", normalized(name)):
        candidates = [alternative, *EXERCISES.get(alternative, [])]
        if not any(
            # OCR can join words, but every word/variant qualifier must remain.
            re.search(r"(?<!\w)" + r"\s*".join(map(re.escape, candidate.split())) + r"(?!\w)", text)
            for candidate in candidates
        ):
            return False
    return True


def intensities(text):
    patterns = {
        "moderada": r"\b(?:moderad[oa]s?|moderate)\b",
        "vigorosa": r"\b(?:vigoros[oa]s?|vigorous)\b",
        "leve": r"\b(?:leves?|light)\b",
    }
    return {label for label, pattern in patterns.items() if re.search(pattern, normalized(text))}


def weekly_prescriptions(content):
    """Retain explicit intensity conditions in the same dose clause.

    Ambiguous clauses are not allocation candidates. This recognizes a limited
    textual pattern; semantic review still checks other conditions/populations.
    """
    text = numbers(content)
    result = []
    for match in re.finditer(NUMBER + rf"\s*(?P<unit>{TIME})\b", text):
        before = re.split(r"[.!?;]|\b(?:ou|or)\b", text[: match.start()])[-1]
        after = re.split(r"[.!?;]|\b(?:ou|or)\b", text[match.end() :])[0]
        if not re.search(r"\b(?:por semana|per week|semanais|weekly)\b", after[:120]):
            continue
        labels = intensities(before[-180:] + " " + after[:120])
        result.append(
            {
                "seconds": bounds(match, time_factor(match["unit"])),
                "intensity": next(iter(labels)) if len(labels) == 1 else None,
                "ambiguous_intensity": len(labels) > 1,
            }
        )
    return result


def parameters(content):
    # Preserve row boundaries: a rest-table column applies to its rows, not to
    # the unrelated prose following its note/caption.
    timing = list(times("\n".join(numbers(line) for line in content.splitlines())))
    return {
        "sets": counts(numbers(content), r"sets?|series?"),
        "repetitions": counts(numbers(content), r"(?:rm\s*)?(?:repetitions?|repeticoes|reps?)"),
        "rest_seconds": [value for value, rest, _ in timing if rest],
        "duration_seconds": [value for value, rest, weekly in timing if not rest and not weekly],
        "weekly_seconds": [value for value, rest, weekly in timing if not rest and weekly],
        "weekly_prescriptions": weekly_prescriptions(content),
    }


def source_parameters(references, days_per_week=None):
    activities = [
        "supino reto com barra",
        "supino inclinado com barra",
        "supino declinado com barra",
        "desenvolvimento de ombros sentado com barra",
        "supino reto",
        "supino inclinado",
        "supino declinado",
        "supino",
        "puxada alta",
        "levantamento terra",
        "agachamento",
        "leg press",
        "remada sentada",
        "remada",
        "desenvolvimento de ombros",
        "rosca direta",
        "caminhada",
        "corrida",
        "ciclismo",
        "natacao",
        "danca",
        "flexoes",
        "pular corda",
        "alongamento",
    ]
    result = [
        {
            "passage_id": ref["passage_id"],
            **parameters(ref["content"]),
            "named_activities": [
                name for name in activities if exercise_present(name, normalized(ref["content"]))
            ],
        }
        for ref in references
    ]
    if (
        type(days_per_week) is int
        and 1 <= days_per_week <= 7
        and any(
            re.search(r"dividir|distribu|spread|divide", normalized(ref["content"]))
            for ref in references
        )
    ):
        for row in result:
            if row["weekly_seconds"]:
                row["allocation_days_per_week"] = days_per_week
                row["weekly_minutes"] = [
                    [low / 60, high / 60] for low, high in row["weekly_seconds"]
                ]
                row["daily_minutes_if_divided"] = [
                    [low / 60 / days_per_week, high / 60 / days_per_week]
                    for low, high in row["weekly_seconds"]
                ]
    return result


def duration_block_items(items):
    """Identify schema representation, never certify an activity or its dosage.

    Semantic review must distinguish continuous activity from timed resistance
    work. A duration and these sentinel values alone do not establish safety.
    """
    return [
        index
        for index, item in enumerate(items, 1)
        if item.get("sets") == 1
        and item.get("rest_seconds") == 0
        and re.fullmatch(NUMBER + rf"\s*(?P<unit>{TIME})", numbers(item.get("repetitions", "")))
    ]


def prescription_gaps(items, citations, *, context, objective=""):
    text = normalized("\n".join(ref["content"] for ref in citations))
    extracted = [parameters(ref["content"]) for ref in citations]

    def ranges(key):
        return [value for row in extracted for value in row[key]]

    set_ranges, rep_ranges = ranges("sets"), ranges("repetitions")
    rest_ranges = ranges("rest_seconds")
    duration_ranges, weekly_ranges = ranges("duration_seconds"), ranges("weekly_seconds")
    durations = []
    for item in items:
        match = re.fullmatch(NUMBER + rf"\s*(?P<unit>{TIME})", numbers(item["repetitions"]))
        durations.append(bounds(match, time_factor(match["unit"])) if match else None)
    days = context.get("client_answers", {}).get("weekly_availability", {}).get("value")
    session_minutes = context.get("client_answers", {}).get("session_duration", {}).get("value")
    # Weekly allocation needs explicit permission in the source, exact arithmetic
    # and a visible explanation. A range guessed by the model is not a derivation.
    allocation = False
    if (
        type(days) is int
        and 1 <= days <= 7
        and all(durations)
        and all(value[0] == value[1] for value in durations)
        and all(item["sets"] == 1 and item["rest_seconds"] == 0 for item in items)
        and re.search(r"dividir|distribu|spread|divide", text)
    ):
        daily = sum(value[0] for value in durations)
        total = daily * days
        explanation = numbers(objective)
        explanation_numbers = {float(value) for value in re.findall(r"\d+(?:\.\d+)?", explanation)}
        allocation = (
            contains((total, total), weekly_ranges)
            and all(value in explanation_numbers for value in (days, daily / 60, total / 60))
            and (not isinstance(session_minutes, (int, float)) or daily <= session_minutes * 60)
        )
    gaps = []
    for index, (item, duration) in enumerate(zip(items, durations), 1):
        fields = []
        if not exercise_present(item["exercise_name"], text):
            fields.append("exercise_supported")
        continuous = duration is not None and item["sets"] == 1
        if not continuous and not contains((item["sets"], item["sets"]), set_ranges):
            fields.append("sets_supported")
        if duration:
            supported = allocation or contains(duration, duration_ranges)
        else:
            match = re.match(NUMBER, numbers(item["repetitions"]))
            supported = bool(match and contains(bounds(match), rep_ranges))
        if not supported:
            fields.append("repetitions_supported")
        if allocation:
            matched = [
                row
                for row in ranges("weekly_prescriptions")
                if contains((total, total), [row["seconds"]])
            ]
            conditioned = [row for row in matched if row["intensity"]]
            stated = intensities(item.get("load_guidance", ""))
            if (conditioned and not any(stated == {row["intensity"]} for row in conditioned)) or (
                matched and all(row["ambiguous_intensity"] for row in matched)
            ):
                fields.append("load_supported")
        rest = item["rest_seconds"]
        if not (continuous and rest == 0) and not contains((rest, rest), rest_ranges):
            fields.append("rest_supported")
        previous = next(
            (
                old
                for old in (context.get("editable_training_draft") or {}).get("items", [])
                if old.get("exercise_name") == item["exercise_name"]
                and old.get("equipment_model_id") == item.get("equipment_model_id")
            ),
            None,
        )
        if previous:
            record_fields = {
                "exercise_supported": "exercise_name",
                "sets_supported": "sets",
                "repetitions_supported": "repetitions",
                "rest_supported": "rest_seconds",
                "load_supported": "load_guidance",
            }
            fields = [
                field
                for field in fields
                if previous.get(record_fields[field]) != item.get(record_fields[field])
            ]
        if fields:
            gaps.append({"item_position": index, "fields": fields})
    return gaps


def allocation_options(references, context):
    """Source-based arithmetic alternatives; the model still reviews applicability."""
    days = context.get("client_answers", {}).get("weekly_availability", {}).get("value")
    available = context.get("client_answers", {}).get("session_duration", {}).get("value")
    rows = source_parameters(references, days)
    by_id = {ref["passage_id"]: ref for ref in references}
    parameters_by_id = {row["passage_id"]: row for row in rows}

    def source_key(ref):
        return ref.get("version_id") or ref.get("source")

    names = {"caminhada": "Caminhada", "ciclismo": "Ciclismo", "danca": "Dança"}
    options = []
    for dose in rows:
        if "allocation_days_per_week" not in dose:
            continue
        # Prefer the guideline's own activity examples and distribution rule
        # over a different book's illustrative case. Other sources remain
        # available as complementary evidence and for independent conflict review.
        source = source_key(by_id[dose["passage_id"]])
        related = sorted(references, key=lambda ref: not (source and source_key(ref) == source))
        division = next(
            (
                ref["passage_id"]
                for ref in related
                if re.search(r"dividir|distribu|spread|divide", normalized(ref["content"]))
            ),
            None,
        )
        for prescription in dose["weekly_prescriptions"]:
            if prescription["ambiguous_intensity"]:
                continue
            weekly, maximum = (value / 60 for value in prescription["seconds"])
            daily, upper = weekly / days, maximum / days
            if daily != upper or (isinstance(available, (int, float)) and daily > available):
                continue
            for name, label in names.items():
                activity = next(
                    (
                        parameters_by_id[ref["passage_id"]]
                        for ref in related
                        if name in parameters_by_id[ref["passage_id"]]["named_activities"]
                    ),
                    None,
                )
                if activity and division:
                    options.append(
                        {
                            "exercise_name": label,
                            "sets": 1,
                            "repetitions": f"{daily:g} minutos",
                            "rest_seconds": 0,
                            "objective": (
                                f"{weekly:g} minutos por semana em {days} dias "
                                f"de {daily:g} minutos"
                                + (
                                    f", em intensidade {prescription['intensity']}"
                                    if prescription["intensity"]
                                    else ""
                                )
                                + "."
                            ),
                            "intensity": prescription["intensity"],
                            "supporting_passages": list(
                                dict.fromkeys(
                                    [dose["passage_id"], activity["passage_id"], division]
                                )
                            ),
                        }
                    )
    # A rounded allocation that our own arithmetic check rejects must not
    # displace a representable option. This is only a necessary evidence check;
    # the specialist and reviewer still decide scope and applicability.
    return [
        option
        for option in options
        if not prescription_gaps(
            [{**option, "load_guidance": option["intensity"] or ""}],
            [by_id[id_] for id_ in option["supporting_passages"]],
            context=context,
            objective=option["objective"],
        )
    ][:6]
