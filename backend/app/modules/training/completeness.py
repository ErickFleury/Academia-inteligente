"""Check requested sessions and bounded AI coverage review before persistence."""

import re
import unicodedata

from app.integrations.ai import AiTrainingPlanAssessment
from app.modules.training.schema import TrainingPlanItemInput, TrainingPlanVersionInput

_DAY = re.compile(r"\s*\(dia\s+([a-z]|[1-7])\)\s*$", re.IGNORECASE)
_RESOURCE_PREFIX = re.compile(
    r"^\s*(?P<resource>peso corporal|peso do corpo|body\s?weight|halteres?|barras?|"
    r"m[aá]quinas?|equipamentos?|el[aá]sticos?)\s*[:—–-]\s*",
    re.IGNORECASE,
)
_NUMBERS = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "três": 3,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
}
FULL_BODY_PATTERNS = ("upper_push", "upper_pull", "lower_knee", "lower_hip", "trunk")


def full_body_patterns(context):
    if context.get("owner_rag_basis", {}).get("goal_family") == "mobility_flexibility":
        return ("flexibility_upper", "flexibility_lower", "flexibility_trunk")
    return FULL_BODY_PATTERNS


class IncompleteTrainingPlanError(ValueError):
    def __init__(self, issues: list[dict]):
        super().__init__("incomplete_training_plan")
        self.issues = issues


def split_training_day(name: str) -> tuple[str, str]:
    match = _DAY.search(name)
    if not match:
        return "", name
    label = match.group(1).upper()
    if label.isdigit():
        label = "ABCDEFG"[int(label) - 1]
    return label, name[: match.start()].strip()


def exercise_identity(name: str) -> tuple[str, str]:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", name.casefold())
        if not unicodedata.combining(char)
    )
    day, exercise = split_training_day(" ".join(normalized.split()))
    return day, " ".join(re.sub(r"[^\w\s]", " ", exercise).split())


def training_review_context(plan: TrainingPlanVersionInput, context: dict) -> dict:
    """Review every actual session even when the request has no explicit schedule."""
    labels = context.get("training_schedule", {}).get("session_labels", [])
    if not labels:
        labels = list(
            dict.fromkeys(split_training_day(item.exercise_name)[0] for item in plan.items)
        )
    result = {
        **context,
        "training_schedule": {"session_labels": labels},
        "proposed_plan": plan.model_dump(mode="json"),
    }
    if context.get("owner_exercise_dictionary"):
        from app.modules.training.owner_rag_schema import exercise_for_name

        result["review_index"] = [
            {
                "position": position,
                "label": split_training_day(item.exercise_name)[0],
                "exercise_key": (exercise_for_name(item.exercise_name, context) or {}).get("key"),
                "exercise_name": item.exercise_name,
            }
            for position, item in enumerate(plan.items, 1)
        ]
    return result


def normalize_exercise_resource(item: TrainingPlanItemInput) -> TrainingPlanItemInput:
    """Separate an explicit resource prefix without inventing or substituting a movement."""
    day, name = split_training_day(item.exercise_name)
    prefix = _RESOURCE_PREFIX.match(name)
    if prefix is None or not name[prefix.end() :].strip():
        return item
    movement = name[prefix.end() :].strip()
    resource = " ".join(prefix.group("resource").split())
    guidance = item.load_guidance
    if resource.casefold() not in guidance.casefold():
        guidance = f"{resource}; {guidance}"
    return type(item).model_validate(
        {
            **item.model_dump(),
            "exercise_name": movement + (f" (Dia {day})" if day else ""),
            "load_guidance": guidance,
        }
    )


def normalize_training_resources(plan: TrainingPlanVersionInput) -> TrainingPlanVersionInput:
    return plan.model_copy(
        update={"items": [normalize_exercise_resource(item) for item in plan.items]}
    )


def validate_exercise_names(plan: TrainingPlanVersionInput) -> None:
    """Reject obvious resource-only labels; semantic validity still needs AI review."""
    resources = {
        "peso corporal",
        "peso do corpo",
        "bodyweight",
        "body weight",
        "halter",
        "halteres",
        "barra",
        "barras",
        "maquina",
        "maquinas",
        "equipamento",
        "equipamentos",
        "elastico",
        "elasticos",
    }
    issues = []
    for position, item in enumerate(plan.items, 1):
        day, name = exercise_identity(item.exercise_name)
        _, raw_name = split_training_day(item.exercise_name)
        resource_prefix = _RESOURCE_PREFIX.match(raw_name)
        ambiguous = re.match(
            r"^(?:flexao (?:de|da|das) pernas?|pressao (?:de|do|dos) joelhos?)\b", name
        )
        if not name or name in resources or resource_prefix or ambiguous:
            issues.append(
                {
                    "label": day,
                    "issues": ["ambiguous_exercise"],
                    "position": position,
                    "exercise_name": item.exercise_name,
                    "reason": "resource_prefix" if resource_prefix else "unidentified_movement",
                }
            )
    if issues:
        raise IncompleteTrainingPlanError(issues)


def validate_full_body_coverage(plan, context):
    if (
        not context.get("owner_rag_basis")
        or (context.get("training_focus") or {}).get("scope") != "full_body"
    ):
        return
    from app.modules.training.owner_rag_schema import exercise_for_name

    found = {}
    for item in plan.items:
        label = split_training_day(item.exercise_name)[0]
        exercise = exercise_for_name(item.exercise_name, context)
        found.setdefault(label, set()).update((exercise or {}).get("movement_patterns", []))
    issues = []
    for label, patterns in found.items():
        missing = [pattern for pattern in full_body_patterns(context) if pattern not in patterns]
        if missing:
            issues.append(
                {
                    "label": label,
                    "issues": ["missing_" + pattern for pattern in missing],
                    "allowed_exercises": {
                        pattern: [
                            e["key"]
                            for e in context["owner_exercise_dictionary"]["exercises"]
                            if pattern in e["movement_patterns"]
                        ]
                        for pattern in missing
                    },
                }
            )
    if issues:
        raise IncompleteTrainingPlanError(issues)


def validate_session_variation(
    plan: TrainingPlanVersionInput,
    context: dict,
    *,
    assessment: AiTrainingPlanAssessment | None = None,
    citations: list[str] | None = None,
) -> None:
    """Allow a copied sheet only with an assessed, cited recommendation to repeat it."""
    if not context.get("training_session"):
        days = list(dict.fromkeys(split_training_day(item.exercise_name)[0] for item in plan.items))
        if len(days) > 1:
            previous = []
            for label in days:
                day = plan.model_copy(
                    update={
                        "items": [
                            item
                            for item in plan.items
                            if split_training_day(item.exercise_name)[0] == label
                        ]
                    }
                )
                validate_session_variation(
                    day,
                    {
                        **context,
                        "training_session": {"label": label},
                        "previous_sessions": previous,
                    },
                    assessment=assessment,
                    citations=citations,
                )
                previous.append({"label": label, "plan": day.model_dump(mode="json")})
        return
    current = sorted({exercise_identity(item.exercise_name)[1] for item in plan.items})
    for previous in context.get("previous_sessions", []):
        previous_plan = TrainingPlanVersionInput.model_validate(previous["plan"])
        selection = sorted(
            {exercise_identity(item.exercise_name)[1] for item in previous_plan.items}
        )
        if current == selection:
            if _has_repetition_recommendation(context, assessment, citations):
                continue
            raise IncompleteTrainingPlanError(
                [
                    {
                        "label": context["training_session"]["label"],
                        "issues": ["repeated_session"],
                        "matches_label": previous["label"],
                    }
                ]
            )


def _has_repetition_recommendation(
    context: dict,
    assessment: AiTrainingPlanAssessment | None,
    citations: list[str] | None,
) -> bool:
    knowledge = context.get("knowledge", {})
    if assessment is None or knowledge.get("knowledge_status") != "supported":
        return False
    label = context["training_session"]["label"]
    review = next((item for item in assessment.sessions if item.label == label), None)
    if review is None or not review.complete or review.issues:
        return False
    recommendation = review.repetition_recommendation
    if recommendation is None or recommendation.chunk_id not in (citations or []):
        return False
    chunk = next(
        (
            item
            for item in knowledge.get("chunks", [])[:6]
            if item["chunk_id"] == recommendation.chunk_id
        ),
        None,
    )
    # Quote matching grounds the review in retrieved text; semantic applicability
    # is assessed by the existing reviewer, never inferred from citation presence.
    return chunk is not None and " ".join(recommendation.quote.split()) in " ".join(
        chunk["content"].split()
    )


def requested_training_schedule(request: str, focus: dict | None = None) -> dict:
    """Requested sessions are independent of anatomical focus and model guesses."""
    from app.modules.training.prescription_contract import PrescriptionRejection

    value = "".join(
        c for c in unicodedata.normalize("NFKD", request.casefold()) if not unicodedata.combining(c)
    )
    labels = []
    for match in re.finditer(
        r"\b(?:treinos?|fichas?|dias?)\s*[(:]?\s*([a-g](?:\s*(?:[,/;+&-]|\be\b)\s*[a-g]){1,6})\b",
        value,
    ):
        selected = re.split(r"\s*[,/;+&-]\s*", re.sub(r"\s+e\s+", ",", match.group(1)))
        if labels and labels != [item.upper() for item in selected]:
            raise PrescriptionRejection("missing_input", "training_schedule_confirmation_required")
        labels = [item.upper() for item in selected]
    if not labels and re.search(r"\babc\b|\ba\s*/\s*b\s*/\s*c\b", value):
        labels = list("ABC")
    if not labels:
        single = re.search(r"\b(?:treino|ficha)\s+([A-G])(?=\s*(?:[).,!;:]|$))", request)
        if single:
            labels = [single.group(1)]
    counts = set()
    for match in re.finditer(
        r"\b(\d+|um|uma|dois|duas|tres|quatro|cinco|seis|sete)\s+(dias?|vezes|fichas|treinos)\b",
        value,
    ):
        number, unit = match.groups()
        if number in {"um", "uma"} and unit in {"fichas", "treinos"}:
            continue
        if re.match(r"\s+(?:de descanso|sem treinar)\b", value[match.end() :]):
            continue
        counts.add(int(number) if number.isdigit() else _NUMBERS[number])
    if (
        len(counts) > 1
        or any(n < 1 or n > 7 for n in counts)
        or len(labels) != len(set(labels))
        or (labels and counts and len(labels) not in counts)
    ):
        raise PrescriptionRejection("missing_input", "training_schedule_confirmation_required")
    return {"session_labels": labels or list("ABCDEFG"[: next(iter(counts), 0)])}


def validate_requested_sessions(plan: TrainingPlanVersionInput, context: dict) -> None:
    expected = context.get("training_schedule", {}).get("session_labels", [])
    if not expected:
        return
    actual = {split_training_day(item.exercise_name)[0] for item in plan.items}
    if actual != set(expected):
        raise IncompleteTrainingPlanError(
            [
                {"label": label, "issues": ["missing_session"]}
                for label in expected
                if label not in actual
            ]
            or [{"label": "", "issues": ["missing_session"]}]
        )


def validate_assessment(assessment: AiTrainingPlanAssessment, context: dict) -> None:
    expected = context.get("training_schedule", {}).get("session_labels", []) or [""]
    labels = [item.label for item in assessment.sessions]
    if sorted(labels) != sorted(expected):
        raise IncompleteTrainingPlanError(
            [{"label": label, "issues": ["missing_session"]} for label in expected]
        )
    issues = []
    proposed = context.get("proposed_plan", {}).get("items", [])
    for item in assessment.sessions:
        if not item.complete or item.issues or item.item_issues:
            if not item.item_issues:
                issues.append(item.model_dump())
            for detail in item.item_issues:
                if (
                    detail.position > len(proposed)
                    or split_training_day(proposed[detail.position - 1]["exercise_name"])[0]
                    != item.label
                ):
                    raise IncompleteTrainingPlanError(
                        [
                            {
                                "label": item.label,
                                "issues": ["ambiguous_exercise"],
                                "reason": "invalid_review_item_position",
                            }
                        ]
                    )
                issues.append(
                    {
                        "label": item.label,
                        "issues": [detail.reason],
                        "position": detail.position,
                        "exercise_name": proposed[detail.position - 1]["exercise_name"],
                        "reason": detail.reason,
                    }
                )
    if issues:
        raise IncompleteTrainingPlanError(issues)
