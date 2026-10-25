"""Ground the AI-selected retrieval scope in the client's actual request."""

import re
import unicodedata
from collections.abc import Callable

from app.integrations.ai import AiTrainingRequestFocus
from app.integrations.ai_diagnostics import record_retry


class InvalidTrainingFocusError(ValueError):
    """The writer added a muscle/region that the client did not request."""


def _normalized(value: str) -> str:
    return " ".join(
        "".join(
            char
            for char in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(char)
        ).split()
    )


def explicit_full_body_request(request):
    text = _normalized(request)
    body_term = r"(?:corpo inteiro|todo o corpo|full[ -]?body)"
    return bool(
        re.search(r"\b" + body_term + r"\b", text)
        and not re.search(r"\bnao(?:\s+\w+){0,3}\s+" + body_term + r"\b", text)
    )


def analyze_training_focus(
    operation: Callable[[dict[str, object]], AiTrainingRequestFocus],
    request: str,
    *,
    allowed_muscle_groups: list[str] | None = None,
) -> dict[str, object]:
    text = _normalized(request)
    full_body_requested = explicit_full_body_request(request)
    explicit_groups = [
        g
        for g in (allowed_muscle_groups or [])
        if re.search(r"(?<!\w)" + re.escape(_normalized(g)) + r"(?!\w)", text)
    ]
    allowed_scopes = ["full_body"] if full_body_requested else ["targeted", "unspecified"]
    if allowed_muscle_groups is not None and not full_body_requested and not explicit_groups:
        allowed_scopes = ["unspecified"]
    context: dict[str, object] = {
        "training_request": request,
        "focus_constraints": {
            "allowed_scopes": allowed_scopes,
        },
    }
    if allowed_muscle_groups is not None:
        context["focus_constraints"]["allowed_muscle_groups"] = explicit_groups
    for attempt in range(2):
        focus = operation(context)
        scope_matches = focus.scope in allowed_scopes
        if (
            scope_matches
            and (focus.scope != "targeted" or focus.muscle_groups)
            and (
                allowed_muscle_groups is None
                or all(
                    _normalized(g) in {_normalized(v) for v in explicit_groups}
                    for g in focus.muscle_groups
                )
            )
            and all(
                re.search(r"(?<!\w)" + re.escape(_normalized(group)) + r"(?!\w)", text)
                for group in focus.muscle_groups
            )
        ):
            return focus.model_dump()
        record_retry("invalid_training_focus", will_retry=not attempt)
        if attempt:
            raise InvalidTrainingFocusError("ungrounded_training_focus")
        context = {
            **context,
            "training_request": request,
            "focus_correction": {
                "rejected_focus": focus.model_dump(),
                "instruction": (
                    "Respeite focus_constraints.allowed_scopes. Refazer toda a ficha do zero "
                    "não é um pedido explícito de corpo inteiro. Sem músculos ou regiões "
                    "explícitos, retorne scope=unspecified e muscle_groups=[]. "
                    "Se o pedido é de corpo inteiro ou todo o corpo, mantenha scope=full_body "
                    "e retorne muscle_groups=[]; não abrevie a expressão nem a trate como "
                    "um grupo muscular localizado. "
                    "O foco incluiu grupos ausentes do pedido ou omitiu os grupos do foco "
                    "localizado. Copie em muscle_groups somente os termos musculares ou "
                    "regiões literalmente presentes no pedido original, sem traduzir ou "
                    "trocar por sinônimos. Por exemplo, se o aluno pediu bíceps, não inclua "
                    "tríceps nem ombros. Preserve todos os grupos explicitamente pedidos."
                ),
            },
        }
    raise InvalidTrainingFocusError("ungrounded_training_focus")
