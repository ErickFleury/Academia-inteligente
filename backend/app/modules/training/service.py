"""Lifecycle service shared by future AI and manual training callers."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client
from app.modules.training.models import TrainingPlan, TrainingPlanItem, TrainingPlanVersion
from app.modules.training.schema import PlanOrigin, TrainingPlanVersionInput


class TrainingLifecycleError(Exception):
    pass


class TrainingVersionNotFoundError(TrainingLifecycleError):
    pass


class ImmutableTrainingVersionError(TrainingLifecycleError):
    pass


class ConcurrentTrainingUpdateError(TrainingLifecycleError):
    pass


class InvalidTrainingTransitionError(TrainingLifecycleError):
    pass


class TrainingLifecycleService:
    def create_proposal(
        self,
        session: Session,
        *,
        client_id: UUID,
        data: TrainingPlanVersionInput,
        created_by: str,
        origin: PlanOrigin,
    ) -> TrainingPlanVersion:
        plan = TrainingPlan(client_id=client_id)
        session.add(plan)
        session.flush()
        return self._new_version(session, plan.id, 1, data, created_by, origin)

    def revise(
        self,
        session: Session,
        *,
        plan_id: UUID,
        version_number: int,
        data: TrainingPlanVersionInput,
        actor: str,
        expected_revision: int,
    ) -> TrainingPlanVersion:
        version = self._version(session, plan_id, version_number, lock=True)
        if version.status != "proposal":
            raise ImmutableTrainingVersionError
        if version.revision != expected_revision:
            raise ConcurrentTrainingUpdateError
        self._replace_content(session, version, data)
        version.revision += 1
        session.commit()
        session.refresh(version)
        return version

    def create_revision(
        self,
        session: Session,
        *,
        plan_id: UUID,
        version_number: int,
        data: TrainingPlanVersionInput,
        actor: str,
    ) -> TrainingPlanVersion:
        source = self._version(session, plan_id, version_number, lock=True)
        if source.status == "proposal":
            raise InvalidTrainingTransitionError
        next_number = (
            session.scalar(
                select(func.max(TrainingPlanVersion.version_number)).where(
                    TrainingPlanVersion.plan_id == plan_id
                )
            )
            or 0
        ) + 1
        return self._new_version(session, plan_id, next_number, data, actor, "instructor")

    def approve(
        self,
        session: Session,
        *,
        plan_id: UUID,
        version_number: int,
        actor: str,
        expected_revision: int,
    ) -> TrainingPlanVersion:
        version = self._version(session, plan_id, version_number, lock=True)
        if version.status != "proposal":
            raise InvalidTrainingTransitionError
        if version.revision != expected_revision:
            raise ConcurrentTrainingUpdateError
        version.status, version.approved_by, version.approved_at = (
            "approved",
            actor,
            datetime.now(UTC),
        )
        session.commit()
        session.refresh(version)
        return version

    def activate(
        self, session: Session, *, plan_id: UUID, version_number: int, expected_revision: int
    ) -> TrainingPlanVersion:
        version = self._version(session, plan_id, version_number, lock=True)
        if version.status != "approved":
            raise InvalidTrainingTransitionError
        if version.revision != expected_revision:
            raise ConcurrentTrainingUpdateError
        plan = session.scalar(
            select(TrainingPlan).where(TrainingPlan.id == plan_id).with_for_update()
        )
        if plan is None:
            raise TrainingVersionNotFoundError
        # Lock the client row so concurrent activations for distinct plans cannot
        # both pass the client-wide current-plan constraint.
        session.scalar(select(Client).where(Client.id == plan.client_id).with_for_update())
        current_plans = session.scalars(
            select(TrainingPlan)
            .where(TrainingPlan.client_id == plan.client_id, TrainingPlan.is_current)
            .with_for_update()
        ).all()
        for current in session.scalars(
            select(TrainingPlanVersion)
            .where(
                TrainingPlanVersion.plan_id.in_([item.id for item in current_plans]),
                TrainingPlanVersion.status == "current",
            )
            .with_for_update()
        ):
            current.status = "superseded"
        for current_plan in current_plans:
            current_plan.is_current = False
        # Flush the old states first so the partial unique indexes never observe
        # two current versions/plans, while retaining one transaction.
        session.flush()
        version.status = "current"
        plan.is_current = True
        session.commit()
        session.refresh(version)
        return version

    def _new_version(
        self,
        session: Session,
        plan_id: UUID,
        number: int,
        data: TrainingPlanVersionInput,
        actor: str,
        origin: PlanOrigin,
    ) -> TrainingPlanVersion:
        version = TrainingPlanVersion(
            plan_id=plan_id,
            version_number=number,
            status="proposal",
            name=data.name.strip(),
            objective=data.objective.strip(),
            origin=origin,
            created_by=actor,
        )
        session.add(version)
        session.flush()
        self._replace_content(session, version, data)
        session.commit()
        session.refresh(version)
        return version

    def _replace_content(
        self, session: Session, version: TrainingPlanVersion, data: TrainingPlanVersionInput
    ) -> None:
        version.name, version.objective = data.name.strip(), data.objective.strip()
        for item in session.scalars(
            select(TrainingPlanItem).where(TrainingPlanItem.version_id == version.id)
        ).all():
            session.delete(item)
        for position, item in enumerate(data.items, start=1):
            session.add(
                TrainingPlanItem(version_id=version.id, position=position, **item.model_dump())
            )
        session.flush()

    @staticmethod
    def _version(
        session: Session, plan_id: UUID, number: int, *, lock: bool
    ) -> TrainingPlanVersion:
        statement = select(TrainingPlanVersion).where(
            TrainingPlanVersion.plan_id == plan_id, TrainingPlanVersion.version_number == number
        )
        if lock:
            statement = statement.with_for_update()
        version = session.scalar(statement)
        if version is None:
            raise TrainingVersionNotFoundError
        return version
