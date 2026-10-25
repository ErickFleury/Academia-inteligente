"""Authenticated own-student confirmation and instructor prescription review."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding.draft_service import OnboardingDraftService, OnboardingNotFoundError
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.prescription_contract import PrescriptionRejection, record_hash
from app.modules.training.prescription_inputs import (
    RequestInputSubmission,
    input_requirements,
    submit_request_inputs,
)
from app.modules.training.prescription_runtime import (
    OperationalPrescriptionService,
    _existing_record,
)
from app.modules.training.review_service import pending_version
from app.modules.training.service import TrainingVersionNotFoundError

router = APIRouter(prefix="/training", tags=["training"])
FACT_LABELS = {
    "training_goal": "Objetivo do treino",
    "training_experience": "Experiência de treino",
    "height_cm": "Altura em centímetros",
    "weight_kg": "Peso em quilogramas",
    "has_limitations_or_complaints": "Limitações ou queixas informadas",
    "limitations_or_complaints": "Detalhes das limitações ou queixas",
    "uses_medications": "Uso de medicamentos",
    "medications": "Medicamentos informados",
    "has_health_conditions": "Condições de saúde informadas",
    "health_conditions": "Detalhes das condições de saúde",
    "adult_eligibility": "Confirmação de maioridade",
    "schedule_confirmed": "Programação confirmada",
    "baseline_capacity": "Capacidade medida",
    "progression_observed": "Desempenho observado para progressão",
    "observed_control": "Controle observado na tarefa",
    "support_available": "Apoio estável disponível",
    "supervision_confirmed": "Supervisão confirmada",
    "reported_talk_test": "Resultado informado do teste da fala",
    "completed_attempts": "Tentativas concluídas com controle",
    "sport": "Modalidade esportiva",
    "sport_event": "Prova ou tarefa esportiva",
    "goal_priorities": "Prioridades entre os objetivos",
}
Database = Annotated[Session, Depends(get_database_session)]
Owner = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "client"))
]
Instructor = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "instructor"))
]


class ConfirmationInput(BaseModel):
    expected_snapshot_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class ManualAssumptionInput(BaseModel):
    expected_revision: int = Field(strict=True, ge=1)
    reason: str = Field(min_length=1, max_length=500)


class InputRequirementRequest(BaseModel):
    goal: str | None = Field(default=None, min_length=1, max_length=500)


def _input_context(session, identity, *, client_id=None, requested_goal=None):
    if client_id is None:
        try:
            scope = OnboardingDraftService().resolve_client_scope(session, identity.subject)
        except OnboardingNotFoundError:
            raise HTTPException(404, "Training inputs not found") from None
        client_id = scope.client_id
    else:
        try:
            OperationalPrescriptionService._instructor(session, identity)
        except PermissionError:
            raise HTTPException(403, "Active instructor required") from None
    runtime = OperationalPrescriptionService(
        session=session, client_id=client_id, subject=identity.subject
    )
    try:
        return runtime._build_operational_context(collect_only=True, requested_goal=requested_goal)
    except PermissionError:
        raise HTTPException(404, "Training inputs not found") from None


@router.get("/prescription/inputs")
def own_input_requirements(session: Database, owner: Owner):
    return input_requirements(_input_context(session, owner), "client_owner", FACT_LABELS)


@router.post("/prescription/inputs/requirements")
def requested_input_requirements(payload: InputRequirementRequest, session: Database, owner: Owner):
    return input_requirements(
        _input_context(session, owner, requested_goal=payload.goal), "client_owner", FACT_LABELS
    )


@router.post("/prescription/inputs")
def provide_own_inputs(payload: RequestInputSubmission, session: Database, owner: Owner):
    goal = payload.values.get("training_goal")
    context = _input_context(
        session, owner, requested_goal=goal.value if goal and isinstance(goal.value, str) else None
    )
    return submit_request_inputs(
        session, context, payload, actor_role="client_owner", actor_subject=owner.subject
    )


@router.get("/clients/{client_id}/prescription/inputs")
def instructor_input_requirements(client_id: UUID, session: Database, instructor: Instructor):
    return input_requirements(
        _input_context(session, instructor, client_id=client_id), "instructor", FACT_LABELS
    )


@router.post("/clients/{client_id}/prescription/inputs")
def provide_instructor_inputs(
    client_id: UUID, payload: RequestInputSubmission, session: Database, instructor: Instructor
):
    goal = payload.values.get("training_goal")
    context = _input_context(
        session,
        instructor,
        client_id=client_id,
        requested_goal=goal.value if goal and isinstance(goal.value, str) else None,
    )
    return submit_request_inputs(
        session, context, payload, actor_role="instructor", actor_subject=instructor.subject
    )


def _owned_version(session, identity, version_id):
    try:
        scope = OnboardingDraftService().resolve_client_scope(session, identity.subject)
    except OnboardingNotFoundError:
        raise HTTPException(404, "Training draft not found") from None
    version = session.scalar(
        select(TrainingPlanVersion).where(
            TrainingPlanVersion.id == version_id,
            TrainingPlanVersion.client_id == scope.client_id,
            TrainingPlanVersion.status == "proposal",
        )
    )
    if version is None:
        raise HTTPException(404, "Training draft not found")
    return version


def _runtime(session, identity, version):
    return OperationalPrescriptionService(
        session=session, client_id=version.client_id, subject=identity.subject
    )


def _pending(session, version_id, identity):
    # Check the active local role before looking up a potentially private identifier.
    try:
        OperationalPrescriptionService._instructor(session, identity)
    except PermissionError:
        raise HTTPException(403, "Active instructor required") from None
    try:
        return pending_version(session, version_id)
    except TrainingVersionNotFoundError:
        raise HTTPException(404, "Training draft not found") from None


def _state(session, identity, version, *, instructor=False):
    runtime = _runtime(session, identity, version)
    if instructor:
        try:
            runtime._instructor(session, identity)
        except PermissionError:
            raise HTTPException(403, "Active instructor required") from None
    record = _existing_record(session, version)
    qualification = "manual" if record and record.kind == "manual" else "legacy"
    state = {
        "submitted_for_review": version.submitted_for_review_at is not None,
        "saved_draft": {
            "id": str(version.id),
            "revision": version.revision,
            "qualification": qualification,
            "projection": runtime.lifecycle.content(session, version).model_dump(mode="json"),
        },
    }
    if qualification == "manual":
        if record.payload.get("rendered_content_sha256") != record_hash(
            runtime.lifecycle.content(session, version)
        ):
            state["saved_draft"]["qualification"] = "stale"
        return state
    try:
        result = runtime._validate_saved(session, version)
        state["outcome"] = runtime._success(version, result, include_review=instructor)
        state.pop("saved_draft", None)
    except PrescriptionRejection as error:
        state["outcome"] = runtime._failure(error)
        if record:
            state["saved_draft"]["qualification"] = "stale"
        if error.category == "missing_input" and not instructor:
            context = runtime.context_supplier()
            state["confirmation"] = {
                "snapshotHash": record_hash(context["snapshot"]),
                "facts": [
                    {
                        "id": key,
                        "label": FACT_LABELS[key],
                        "value": ("Sim" if fact.value else "Não")
                        if isinstance(fact.value, bool)
                        else (
                            {
                                "none": "Sem experiência",
                                "beginner": "Iniciante",
                                "intermediate": "Intermediário",
                                "advanced": "Avançado",
                            }.get(str(fact.value), str(fact.value))
                            if key == "training_experience"
                            else str(fact.value)
                        ),
                    }
                    for key, fact in context["snapshot"].facts.items()
                ],
            }
    return state


@router.get("/drafts/{version_id}/prescription")
def own_prescription(version_id: UUID, session: Database, owner: Owner):
    return _state(session, owner, _owned_version(session, owner, version_id))


@router.get("/pending/{version_id}/prescription")
def instructor_prescription(version_id: UUID, session: Database, instructor: Instructor):
    return _state(session, instructor, _pending(session, version_id, instructor), instructor=True)


@router.post("/drafts/{version_id}/prescription/confirm")
def confirm_prescription(
    version_id: UUID, payload: ConfirmationInput, session: Database, owner: Owner
):
    version = _owned_version(session, owner, version_id)
    return _runtime(session, owner, version).confirm_inputs(
        session,
        owner,
        client_id=version.client_id,
        expected_snapshot_hash=payload.expected_snapshot_hash,
    )


@router.post("/pending/{version_id}/prescription/assume-manual")
def assume_prescription_manually(
    version_id: UUID, payload: ManualAssumptionInput, session: Database, instructor: Instructor
):
    version = _pending(session, version_id, instructor)
    runtime = _runtime(session, instructor, version)
    if version.revision != payload.expected_revision:
        raise PrescriptionRejection("insufficient_support", "stale_revision")
    if not payload.reason.strip():
        raise HTTPException(422, "A manual review reason is required")
    # Authorization and exact-revision checks happen again in the shared service.
    outcome = runtime.assume_manual(
        session,
        instructor,
        client_id=version.client_id,
        version_id=version.id,
        expected_revision=payload.expected_revision,
        reason=payload.reason,
    )
    outcome["purpose"] = "operational"
    return outcome
