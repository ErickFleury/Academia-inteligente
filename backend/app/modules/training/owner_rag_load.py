"""Qualitative load representation; never infer an individual external weight."""

import re

from app.modules.training.prescription_contract import PrescriptionRejection, record_hash

LOAD_GUIDANCE = {
    "bodyweight": "Peso corporal",
    "external_unmeasured": "Halteres; carga a definir na revisão do instrutor.",
    "no_external_load": "Sem carga externa; amplitude confortável, sem forçar dor.",
}
LOAD_ERROR = "unmeasured_external_load_generated"


def requires_measurement(request):
    from app.modules.training.owner_rag_schema import fold

    value = fold(str(request or ""))
    return bool(
        re.search(
            r"\b(?:1\s*rm|quantos?\s+(?:kg|quilos)|"
            r"(?:calcule|calcular|calculo)\b.{0,60}(?:carga|peso)|"
            r"(?:carga|peso)\b.{0,30}(?:em\s+kg|em\s+quilos|exat[oa]))",
            value,
        )
    )


def validate_candidate(plan, context):
    if not context.get("owner_rag_basis"):
        return
    from app.modules.training.owner_rag_schema import exercise_for_name

    preserved = context["owner_rag_basis"].get("preserved_item_hashes", [])
    issues = []
    for position, item in enumerate(plan.items, 1):
        # Only exact, server-snapshotted items of the approved adaptation base
        # retain historical representation. A changed field loses this exception.
        if record_hash(item) in preserved:
            continue
        exercise = exercise_for_name(item.exercise_name, context)
        if exercise is None:
            raise PrescriptionRejection("insufficient_support", "unknown_exercise_or_variation")
        from app.modules.training.owner_rag_flexibility import validate_item

        validate_item(item, exercise, context, position)
        allowed = LOAD_GUIDANCE[exercise["load_capability"]]
        if item.load_guidance != allowed:
            issues.append(
                {
                    "position": position,
                    "field": "load_guidance",
                    "reason": LOAD_ERROR,
                    "allowed": [allowed],
                }
            )
    if issues:
        raise PrescriptionRejection("insufficient_support", LOAD_ERROR, issues=issues)


def validate_load_correction(previous, candidate, positions):
    before, after = previous.model_dump(mode="json"), candidate.model_dump(mode="json")
    if len(before["items"]) == len(after["items"]):
        for position in positions:
            before["items"][position - 1].pop("load_guidance")
            after["items"][position - 1].pop("load_guidance")
        if before == after:
            return
    raise PrescriptionRejection("insufficient_support", "load_repair_changed_other_fields")
