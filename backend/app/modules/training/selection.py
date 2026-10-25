"""Validate AI exercise selection before saving a draft; never pick a row arbitrarily."""

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from app.integrations.ai_diagnostics import record_retry
from app.modules.training.completeness import (
    IncompleteTrainingPlanError,
    exercise_identity,
    normalize_training_resources,
    training_review_context,
    validate_assessment,
    validate_exercise_names,
    validate_requested_sessions,
    validate_session_variation,
)
from app.modules.training.prescription_contract import PrescriptionRejection
from app.modules.training.schema import TrainingPlanVersionInput

Response = TypeVar("Response", bound=BaseModel)


class RedundantTrainingExerciseError(ValueError):
    """The writer did not resolve competing prescriptions for the same exercise."""

    def __init__(self, reason="redundant_exercise_prescription", *, issues=None):
        super().__init__(reason)
        self.issues = issues or []


def validate_exercise_selection(plan: TrainingPlanVersionInput) -> None:
    seen: dict[str, list[tuple[str, int, str | None]]] = {}
    for position, item in enumerate(plan.items, 1):
        day, name = exercise_identity(item.exercise_name)
        side = (
            item.dose_details.dose["side"]
            if item.dose_details is not None and item.dose_details.mode == "flexibility"
            else None
        )
        for previous_day, previous_position, previous_side in seen.get(name, []):
            if not day or not previous_day or day == previous_day:
                if {side, previous_side} == {"left", "right"}:
                    continue
                raise RedundantTrainingExerciseError(
                    issues=[
                        {
                            "position": position,
                            "duplicate_of": previous_position,
                            "field": "exercise_name",
                            "exercise_name": item.exercise_name,
                            "reason": "duplicate_exercise_within_session",
                        }
                    ]
                )
        seen.setdefault(name, []).append((day, position, side))


def request_selected_training(
    operation: Callable[[dict[str, object]], Response],
    context: dict[str, object],
    *,
    assess: Callable,
    plan_field: str = "plan",
    plan_builder: Callable | None = None,
    repair_domain_errors: bool = False,
    candidate_validator: Callable | None = None,
) -> Response:
    """Require exercise review and one bounded correction before any AI plan is saved."""

    def write(selected_context):
        result = operation(selected_context)
        if plan_builder is None:
            raw_plan = getattr(result, plan_field)
            if raw_plan is not None:
                normalized = normalize_training_resources(
                    TrainingPlanVersionInput.model_validate(raw_plan)
                )
                result = result.model_copy(update={plan_field: normalized.model_dump(mode="json")})
        return result

    selected_context = context
    load_repair = None
    for attempt in range(2):
        plan = None
        try:
            response = write(selected_context)
            raw_plan = plan_builder(response) if plan_builder else getattr(response, plan_field)
            if raw_plan is None:
                if attempt:
                    raise RedundantTrainingExerciseError("missing_corrected_plan")
                return response
            plan = TrainingPlanVersionInput.model_validate(raw_plan)
            validate_exercise_names(plan)
            validate_exercise_selection(plan)
            validate_requested_sessions(plan, context)
            if load_repair is not None:
                from app.modules.training.owner_rag_load import validate_load_correction

                validate_load_correction(load_repair[0], plan, load_repair[1])
            if candidate_validator is not None:
                candidate_validator(plan, context)
            review_context = training_review_context(plan, context)
            assessment = assess(review_context)
            validate_session_variation(
                plan,
                context,
                assessment=assessment,
                citations=getattr(response, "citations", []),
            )
            validate_assessment(assessment, review_context)
            return response
        except (
            RedundantTrainingExerciseError,
            IncompleteTrainingPlanError,
            PrescriptionRejection,
        ) as error:
            if isinstance(error, PrescriptionRejection) and (
                not repair_domain_errors
                or error.category != "insufficient_support"
                or error.reason
                not in {
                    "invalid_typed_candidate",
                    "unknown_exercise_or_variation",
                    "exercise_outside_policy",
                    "parameter_outside_policy",
                    "calculated_quantity_mismatch",
                    "unknown_load_calculation",
                    "calculation_intent_required",
                    "invalid_decision_rule",
                    "mandatory_dimension_missing",
                    "unknown_intensity_scale",
                    "progression_outside_policy",
                    "invalid_observation_reference",
                    "modality_choice_outside_policy",
                    "unmeasured_external_load_generated",
                }
            ):
                raise
            may_correct = not attempt
            if may_correct and context.get("owner_rag_basis"):
                from app.modules.training.prescription_budget import CURRENT_BUDGET

                budget = CURRENT_BUDGET.get()
                if budget is not None:
                    may_correct = budget.consume_content_correction()
            record_retry(
                "incomplete_training_plan"
                if isinstance(error, IncompleteTrainingPlanError)
                else "redundant_exercise_prescription",
                will_retry=may_correct,
            )
            if not may_correct:
                raise
            issues = (
                error.issues
                if isinstance(
                    error,
                    (
                        IncompleteTrainingPlanError,
                        PrescriptionRejection,
                        RedundantTrainingExerciseError,
                    ),
                )
                else []
            )
            if isinstance(error, PrescriptionRejection) and not issues:
                issues = [{"field": "candidate", "reason": error.reason}]
            if (
                isinstance(error, PrescriptionRejection)
                and error.reason == "unmeasured_external_load_generated"
            ):
                load_repair = (plan, [issue["position"] for issue in issues])
        selected_context = {
            **context,
            "selection_correction": exercise_selection_correction(plan, issues)
            if plan is not None
            else {
                "issues": issues,
                "instruction": (
                    "Corrija somente os campos indicados usando as opções permitidas; "
                    "preserve fatos, objetivo e regras recebidos."
                ),
            },
        }
        if load_repair is not None:
            selected_context["selection_correction"]["instruction"] = (
                "Corrija somente load_guidance nas posições indicadas usando exatamente "
                "as opções allowed. Preserve todos os demais campos, fatos, objetivo, "
                "exercícios, séries, repetições e descanso. Não invente medições. "
                "Retorne a ficha completa e suas citações."
            )
    raise RedundantTrainingExerciseError("redundant_exercise_prescription")


def exercise_selection_correction(plan: TrainingPlanVersionInput, issues: list[dict]) -> dict:
    """The same precise feedback repairs legacy content and a newly rejected candidate."""
    return {
        "rejected_plan": plan.model_dump(mode="json"),
        "completeness_issues": issues,
        "instruction": (
            "Corrija rejected_plan conforme completeness_issues e o pedido original. "
            "repeated_session: a ficha copia matches_label; substitua ao menos um "
            "exercício por uma alternativa real de função complementar aplicável. "
            "Compare com TODOS os previous_sessions. Não devolva a mesma seleção "
            "mudando só ordem, grafia, séries, repetições, carga ou descanso. "
            "Só repita a ficha inteira com recomendação explícita e aplicável nos "
            "trechos citados, confirmada na revisão; frequência semanal não basta. "
            "Consolide duplicatas no mesmo dia; não oculte repetições só trocando nomes "
            "nem invente dias. "
            "ambiguous_exercise: corrija cada position/exercise_name informado com um movimento "
            "reconhecido e preciso. Pressão de joelho e flexão de perna são ambíguos; "
            "substitua esses itens por exercícios identificáveis, não por sinônimos vagos. "
            "Acrescentar com peso corporal, com halteres ou leve não resolve o nome ambíguo. "
            "Exemplos de nomes identificáveis: flexão de braços, agachamento, ponte de quadril "
            "e remada. São exemplos de identificação, não substituições automáticas; escolha "
            "apenas movimentos compatíveis com as fontes e restrições do cliente. "
            "Peso corporal é carga, "
            "não exercício nem prefixo do nome; mantenha recursos apenas em load_guidance. "
            "Preserve restrições e a abrangência pedida: treino localizado não exige "
            "corpo inteiro. Preserve os dias de training_schedule. "
            "Retorne a ficha completa e suas citações."
        ),
    }
