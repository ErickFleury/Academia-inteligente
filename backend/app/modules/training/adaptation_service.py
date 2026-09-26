"""Client-confirmed, instructor-approved adaptation proposals."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.ai import (
    AiProviderError,
    TrainingAdaptationProvider,
    training_adaptation_provider_from_environment,
)
from app.modules.clients.models import Account, Client
from app.modules.equipment.models import EquipmentModel
from app.modules.equipment.service import EquipmentService
from app.modules.onboarding.models import Onboarding
from app.modules.training.models import (
    TrainingAdaptationOperation,
    TrainingAdaptationProposal,
    TrainingAiConversation,
    TrainingAiMessage,
    TrainingPlan,
    TrainingPlanItem,
    TrainingPlanVersion,
)
from app.modules.training.schema import (
    AdaptationInstructorUpdate,
    AdaptationOperationInput,
    TrainingPlanItemInput,
    TrainingPlanVersionInput,
)


class AdaptationError(Exception):
    pass


class AdaptationNotFoundError(AdaptationError):
    pass


class AdaptationUnavailableError(AdaptationError):
    pass


class AdaptationStateError(AdaptationError):
    pass


class CurrentTrainingPlanRequiredError(AdaptationStateError):
    pass


class InvalidEquipmentReferenceError(AdaptationStateError):
    pass


class TrainingAdaptationService:
    """Keeps proposed changes separate from plans until instructor approval."""

    def __init__(self, provider: TrainingAdaptationProvider | None = None) -> None:
        self._provider = provider or training_adaptation_provider_from_environment()
        self._equipment = EquipmentService()

    def generate(
        self,
        session: Session,
        subject: str,
        *,
        source_client_request_id: UUID,
        client_request_id: UUID,
        reason: str,
    ) -> TrainingAdaptationProposal:
        client_id = self._client_id(session, subject)
        base = self._current(session, client_id)
        existing = session.scalar(
            select(TrainingAdaptationProposal).where(
                TrainingAdaptationProposal.client_id == client_id,
                TrainingAdaptationProposal.base_version_id == base.id,
                TrainingAdaptationProposal.client_request_id == client_request_id,
            )
        )
        if existing is not None:
            return existing

        source = self._source_message(session, client_id, source_client_request_id)
        response = self._retry(
            lambda: self._provider.generate_adaptation(
                self._context(session, client_id, base, source, reason.strip())
            )
        )
        try:
            operations = [
                AdaptationOperationInput.model_validate(value) for value in response.operations
            ]
        except ValidationError as error:
            raise AdaptationStateError from error
        self._validate_operations(session, base, operations)

        proposal = TrainingAdaptationProposal(
            client_id=client_id,
            base_version_id=base.id,
            source_client_request_id=source_client_request_id,
            client_request_id=client_request_id,
            reason=reason.strip(),
            explanation=response.explanation.strip(),
            status="proposed",
        )
        session.add(proposal)
        session.flush()
        self._replace_operations(session, proposal, operations)
        session.commit()
        session.refresh(proposal)
        return proposal

    def client_decide(
        self, session: Session, subject: str, proposal_id: UUID, accept: bool
    ) -> TrainingAdaptationProposal:
        proposal = self._owned(session, subject, proposal_id)
        if proposal.status != "proposed":
            raise AdaptationStateError
        proposal.status = "pending_instructor_review" if accept else "client_rejected"
        proposal.client_reviewed_at = datetime.now(UTC)
        session.commit()
        session.refresh(proposal)
        return proposal

    def instructor_edit(
        self, session: Session, proposal_id: UUID, update: AdaptationInstructorUpdate
    ) -> TrainingAdaptationProposal:
        proposal = self._proposal(session, proposal_id)
        if proposal.status != "pending_instructor_review":
            raise AdaptationStateError
        base = session.get(TrainingPlanVersion, proposal.base_version_id)
        if base is None:
            raise AdaptationNotFoundError
        preserved_equipment_model_ids = set(
            session.scalars(
                select(TrainingAdaptationOperation.equipment_model_id).where(
                    TrainingAdaptationOperation.proposal_id == proposal.id,
                    TrainingAdaptationOperation.equipment_model_id.is_not(None),
                )
            )
        )
        self._validate_operations(
            session,
            base,
            update.operations,
            preserved_equipment_model_ids=preserved_equipment_model_ids,
        )
        proposal.explanation = update.explanation.strip()
        self._replace_operations(session, proposal, update.operations)
        session.commit()
        session.refresh(proposal)
        return proposal

    def instructor_decide(
        self, session: Session, proposal_id: UUID, instructor: str, approve: bool
    ) -> TrainingAdaptationProposal:
        proposal = self._proposal(session, proposal_id)
        if proposal.status != "pending_instructor_review":
            raise AdaptationStateError

        proposal.instructor_reviewed_at = datetime.now(UTC)
        proposal.instructor_id = instructor
        if not approve:
            proposal.status = "instructor_rejected"
            session.commit()
            session.refresh(proposal)
            return proposal

        base = session.scalar(
            select(TrainingPlanVersion)
            .where(TrainingPlanVersion.id == proposal.base_version_id)
            .with_for_update()
        )
        if base is None or not self._is_current(session, base):
            proposal.status = "superseded"
            session.commit()
            raise AdaptationStateError

        data = self._apply(session, base, proposal)
        current = self._create_current_version(session, base, data, instructor)
        proposal.status = "approved"
        proposal.resulting_version_id = current.id
        # One commit prevents partial plan/version activation on a failure.
        session.commit()
        session.refresh(proposal)
        return proposal

    def own_proposals(self, session: Session, subject: str) -> list[TrainingAdaptationProposal]:
        client_id = self._client_id(session, subject)
        return list(
            session.scalars(
                select(TrainingAdaptationProposal)
                .where(TrainingAdaptationProposal.client_id == client_id)
                .order_by(TrainingAdaptationProposal.created_at.desc())
            )
        )

    def pending_for_instructor(self, session: Session) -> list[TrainingAdaptationProposal]:
        return list(
            session.scalars(
                select(TrainingAdaptationProposal)
                .where(TrainingAdaptationProposal.status == "pending_instructor_review")
                .order_by(TrainingAdaptationProposal.created_at.asc())
            )
        )

    @staticmethod
    def _client_id(session: Session, subject: str) -> UUID:
        client_id = session.scalar(
            select(Client.id)
            .join(Account, Client.account_id == Account.id)
            .where(Account.keycloak_subject == subject, Account.account_active)
        )
        if client_id is None:
            raise AdaptationNotFoundError
        return client_id

    @staticmethod
    def _current(session: Session, client_id: UUID) -> TrainingPlanVersion:
        version = session.scalar(
            select(TrainingPlanVersion)
            .join(TrainingPlan, TrainingPlanVersion.plan_id == TrainingPlan.id)
            .where(
                TrainingPlan.client_id == client_id,
                TrainingPlan.is_current,
                TrainingPlanVersion.status == "current",
            )
        )
        if version is None:
            raise CurrentTrainingPlanRequiredError
        return version

    def _owned(
        self, session: Session, subject: str, proposal_id: UUID
    ) -> TrainingAdaptationProposal:
        proposal = self._proposal(session, proposal_id)
        if proposal.client_id != self._client_id(session, subject):
            raise AdaptationNotFoundError
        return proposal

    @staticmethod
    def _proposal(session: Session, proposal_id: UUID) -> TrainingAdaptationProposal:
        proposal = session.get(TrainingAdaptationProposal, proposal_id)
        if proposal is None:
            raise AdaptationNotFoundError
        return proposal

    @staticmethod
    def _source_message(session: Session, client_id: UUID, request_id: UUID) -> TrainingAiMessage:
        message = session.scalar(
            select(TrainingAiMessage)
            .join(
                TrainingAiConversation,
                TrainingAiMessage.conversation_id == TrainingAiConversation.id,
            )
            .where(
                TrainingAiConversation.client_id == client_id,
                TrainingAiMessage.role == "user",
                TrainingAiMessage.client_request_id == request_id,
            )
        )
        if message is None:
            raise AdaptationNotFoundError
        return message

    @staticmethod
    def _is_current(session: Session, version: TrainingPlanVersion) -> bool:
        return version.status == "current" and bool(
            session.scalar(
                select(TrainingPlan.is_current).where(TrainingPlan.id == version.plan_id)
            )
        )

    def _context(
        self,
        session: Session,
        client_id: UUID,
        base: TrainingPlanVersion,
        source: TrainingAiMessage,
        reason: str,
    ) -> dict[str, object]:
        chat = session.scalar(
            select(TrainingAiConversation).where(TrainingAiConversation.client_id == client_id)
        )
        recent: list[TrainingAiMessage] = []
        if chat is not None:
            recent = list(
                session.scalars(
                    select(TrainingAiMessage)
                    .where(TrainingAiMessage.conversation_id == chat.id)
                    .order_by(TrainingAiMessage.sequence.desc())
                    .limit(6)
                )
            )
        onboarding = session.scalar(
            select(Onboarding).where(
                Onboarding.client_id == client_id, Onboarding.status == "completed"
            )
        )
        health_terms = ("dor", "les", "limit", "saúde", "joelho")
        health: dict[str, object | None] = {}
        if onboarding is not None and any(term in reason.lower() for term in health_terms):
            health = {
                "limitations_or_complaints": onboarding.limitations_or_complaints,
                "health_conditions": onboarding.health_conditions,
            }
        items = session.scalars(
            select(TrainingPlanItem)
            .where(TrainingPlanItem.version_id == base.id)
            .order_by(TrainingPlanItem.position)
        )
        active_equipment_models = self._equipment.active_models_with_units(session)
        return {
            "reason": reason,
            "source_client_message": source.content,
            "base_plan": {
                "name": base.name,
                "objective": base.objective,
                "items": [
                    {
                        "position": item.position,
                        "exercise_name": item.exercise_name,
                        "sets": item.sets,
                        "repetitions": item.repetitions,
                        "load_guidance": item.load_guidance,
                        "rest_seconds": item.rest_seconds,
                    }
                    for item in items
                ],
            },
            "recent_messages": [
                {"role": item.role, "content": item.content} for item in reversed(recent)
            ],
            "conversation_summary": chat.summary if chat else None,
            "relevant_onboarding": {
                key: value for key, value in health.items() if value is not None
            },
            "active_equipment_models": [
                {"id": str(model.id), "name": model.name}
                for model in active_equipment_models
            ],
        }

    def _validate_operations(
        self,
        session: Session,
        base: TrainingPlanVersion,
        operations: list[AdaptationOperationInput],
        *,
        preserved_equipment_model_ids: set[UUID] | None = None,
    ) -> None:
        positions = set(
            session.scalars(
                select(TrainingPlanItem.position).where(TrainingPlanItem.version_id == base.id)
            )
        )
        for operation in operations:
            if operation.operation_type == "add":
                if operation.item is None:
                    raise AdaptationStateError
            elif operation.target_position not in positions:
                raise AdaptationStateError
            elif operation.operation_type in {"replace", "adjust"} and operation.item is None:
                raise AdaptationStateError
        self._validate_equipment_references(
            session, operations, preserved_equipment_model_ids or set()
        )

    def _validate_equipment_references(
        self,
        session: Session,
        operations: list[AdaptationOperationInput],
        preserved_equipment_model_ids: set[UUID],
    ) -> None:
        active_model_ids = {
            model.id for model in self._equipment.active_models_with_units(session)
        }
        allowed_model_ids = active_model_ids | preserved_equipment_model_ids
        for operation in operations:
            item = operation.item
            if item is None:
                continue
            requirement = (item.equipment_requirement or "").strip()
            if not requirement:
                if item.equipment_model_id is not None:
                    raise InvalidEquipmentReferenceError
                continue
            if item.equipment_model_id is None or item.equipment_model_id not in allowed_model_ids:
                raise InvalidEquipmentReferenceError
            if session.get(EquipmentModel, item.equipment_model_id) is None:
                raise InvalidEquipmentReferenceError

    @staticmethod
    def _replace_operations(
        session: Session,
        proposal: TrainingAdaptationProposal,
        operations: list[AdaptationOperationInput],
    ) -> None:
        current = session.scalars(
            select(TrainingAdaptationOperation).where(
                TrainingAdaptationOperation.proposal_id == proposal.id
            )
        )
        for operation in current:
            session.delete(operation)
        session.flush()
        for position, operation in enumerate(operations, 1):
            item = operation.item
            session.add(
                TrainingAdaptationOperation(
                    proposal_id=proposal.id,
                    position=position,
                    operation_type=operation.operation_type,
                    target_position=operation.target_position,
                    exercise_name=item.exercise_name if item else None,
                    sets=item.sets if item else None,
                    repetitions=item.repetitions if item else None,
                    load_guidance=item.load_guidance if item else None,
                    rest_seconds=item.rest_seconds if item else None,
                    equipment_requirement=item.equipment_requirement if item else None,
                    equipment_model_id=item.equipment_model_id if item else None,
                    is_existing_exercise=item.is_existing_exercise if item else None,
                )
            )

    @staticmethod
    def _apply(
        session: Session, base: TrainingPlanVersion, proposal: TrainingAdaptationProposal
    ) -> TrainingPlanVersionInput:
        items = {
            item.position: TrainingPlanItemInput(
                exercise_name=item.exercise_name,
                sets=item.sets,
                repetitions=item.repetitions,
                load_guidance=item.load_guidance,
                rest_seconds=item.rest_seconds,
            )
            for item in session.scalars(
                select(TrainingPlanItem).where(TrainingPlanItem.version_id == base.id)
            )
        }
        operations = session.scalars(
            select(TrainingAdaptationOperation)
            .where(TrainingAdaptationOperation.proposal_id == proposal.id)
            .order_by(TrainingAdaptationOperation.position)
        )
        for operation in operations:
            if operation.operation_type == "remove":
                items.pop(operation.target_position, None)
                continue
            item = TrainingPlanItemInput(
                exercise_name=operation.exercise_name or "",
                sets=operation.sets or 0,
                repetitions=operation.repetitions or "",
                load_guidance=operation.load_guidance or "",
                rest_seconds=(operation.rest_seconds if operation.rest_seconds is not None else -1),
            )
            if operation.operation_type == "add":
                items[max(items, default=0) + 1] = item
            else:
                items[operation.target_position or 0] = item
        return TrainingPlanVersionInput(
            name=base.name,
            objective=base.objective,
            items=[items[position] for position in sorted(items)],
        )

    @staticmethod
    def _create_current_version(
        session: Session,
        base: TrainingPlanVersion,
        data: TrainingPlanVersionInput,
        instructor: str,
    ) -> TrainingPlanVersion:
        plan = session.scalar(
            select(TrainingPlan).where(TrainingPlan.id == base.plan_id).with_for_update()
        )
        if plan is None:
            raise AdaptationStateError
        session.scalar(select(Client).where(Client.id == plan.client_id).with_for_update())
        current_plans = list(
            session.scalars(
                select(TrainingPlan)
                .where(TrainingPlan.client_id == plan.client_id, TrainingPlan.is_current)
                .with_for_update()
            )
        )
        for version in session.scalars(
            select(TrainingPlanVersion)
            .where(
                TrainingPlanVersion.plan_id.in_([item.id for item in current_plans]),
                TrainingPlanVersion.status == "current",
            )
            .with_for_update()
        ):
            version.status = "superseded"
        for current_plan in current_plans:
            current_plan.is_current = False
        session.flush()

        next_number = (
            session.scalar(
                select(func.max(TrainingPlanVersion.version_number)).where(
                    TrainingPlanVersion.plan_id == plan.id
                )
            )
            or 0
        ) + 1
        now = datetime.now(UTC)
        version = TrainingPlanVersion(
            plan_id=plan.id,
            client_id=plan.client_id,
            version_number=next_number,
            status="current",
            name=data.name.strip(),
            objective=data.objective.strip(),
            origin="instructor",
            created_by=instructor,
            approved_by=instructor,
            approved_at=now,
        )
        session.add(version)
        session.flush()
        for position, item in enumerate(data.items, 1):
            session.add(
                TrainingPlanItem(version_id=version.id, position=position, **item.model_dump())
            )
        plan.is_current = True
        session.flush()
        return version

    @staticmethod
    def _retry(operation):
        for attempt in range(2):
            try:
                return operation()
            except AiProviderError as error:
                if attempt or not error.retryable:
                    raise AdaptationUnavailableError from None
        raise AdaptationUnavailableError
