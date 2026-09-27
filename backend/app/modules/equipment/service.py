from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.modules.equipment.models import EquipmentModel, EquipmentUnit


class EquipmentNotFoundError(Exception):
    pass


class EquipmentValidationError(Exception):
    pass


class EquipmentStateConflictError(Exception):
    pass


@dataclass(frozen=True)
class ModelSummary:
    id: UUID
    name: str
    description: str | None
    image_url: str | None
    active: bool
    active_quantity: int


class EquipmentService:
    def usable_models_with_units(self, session: Session) -> list[EquipmentModel]:
        """Training usability only; operational never means currently free."""
        return list(
            session.scalars(
                select(EquipmentModel)
                .where(
                    EquipmentModel.active,
                    select(EquipmentUnit.id)
                    .where(
                        EquipmentUnit.equipment_model_id == EquipmentModel.id,
                        EquipmentUnit.active,
                        EquipmentUnit.operational_state == "operational",
                    )
                    .exists(),
                )
                .order_by(EquipmentModel.name, EquipmentModel.id)
            )
        )

    def instructor_models(self, session: Session, cursor: UUID | None, limit: int):
        statement = (
            select(
                EquipmentModel.id,
                EquipmentModel.name,
                func.count(EquipmentUnit.id).label("active_quantity"),
            )
            .outerjoin(
                EquipmentUnit,
                and_(EquipmentUnit.equipment_model_id == EquipmentModel.id, EquipmentUnit.active),
            )
            .where(EquipmentModel.active)
            .group_by(EquipmentModel.id, EquipmentModel.name)
        )
        if cursor:
            statement = statement.where(EquipmentModel.id > cursor)
        rows = session.execute(statement.order_by(EquipmentModel.id).limit(limit + 1)).all()
        return {
            "items": [
                {"id": str(row.id), "name": row.name, "active_quantity": row.active_quantity}
                for row in rows[:limit]
            ],
            "next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None,
        }

    def instructor_units(self, session: Session, model_id: UUID, cursor: UUID | None, limit: int):
        model = session.get(EquipmentModel, model_id)
        if model is None or not model.active:
            raise EquipmentNotFoundError
        statement = select(EquipmentUnit).where(EquipmentUnit.equipment_model_id == model_id)
        if cursor:
            statement = statement.where(EquipmentUnit.id > cursor)
        rows = list(session.scalars(statement.order_by(EquipmentUnit.id).limit(limit + 1)))
        return {
            "items": [self.operational_projection(row) for row in rows[:limit]],
            "next_cursor": str(rows[limit - 1].id) if len(rows) > limit else None,
        }

    @staticmethod
    def operational_projection(unit):
        return {
            "id": str(unit.id),
            "label": unit.label,
            "active": unit.active,
            "operational_state": unit.operational_state,
            "revision": unit.operational_revision,
        }

    def set_operational_state(
        self, session: Session, unit_id: UUID, state: str, expected_revision: int
    ):
        if state not in {"operational", "out_of_order"}:
            raise EquipmentValidationError
        model_id = session.scalar(
            select(EquipmentUnit.equipment_model_id).where(EquipmentUnit.id == unit_id)
        )
        model = session.scalar(
            select(EquipmentModel)
            .where(EquipmentModel.id == model_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        unit = session.scalar(
            select(EquipmentUnit)
            .where(EquipmentUnit.id == unit_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if model is None or unit is None or not model.active:
            raise EquipmentNotFoundError
        if not unit.active or unit.operational_revision != expected_revision:
            raise EquipmentStateConflictError
        if unit.operational_state != state:
            unit.operational_state = state
            unit.operational_revision += 1
        session.commit()
        session.refresh(unit)
        return self.operational_projection(unit)

    def catalog(self, session: Session) -> list[ModelSummary]:
        return self._models_with_counts(session, active_only=True)

    def active_models_with_units(self, session: Session) -> list[ModelSummary]:
        """Return catalog models that exist in active managed inventory.

        This intentionally describes inventory existence only. It does not
        imply that a physical unit is currently free or in use.
        """
        return [model for model in self.catalog(session) if model.active_quantity > 0]

    def models(self, session: Session) -> list[ModelSummary]:
        return self._models_with_counts(session, active_only=False)

    def model(self, session: Session, model_id: UUID) -> EquipmentModel:
        model = session.get(EquipmentModel, model_id)
        if model is None:
            raise EquipmentNotFoundError
        return model

    def units(self, session: Session, model_id: UUID) -> list[EquipmentUnit]:
        self.model(session, model_id)
        return list(
            session.scalars(
                select(EquipmentUnit)
                .where(EquipmentUnit.equipment_model_id == model_id)
                .order_by(EquipmentUnit.created_at, EquipmentUnit.id)
            )
        )

    def create_model(
        self,
        session: Session,
        name: str,
        description: str | None,
        image_url: str | None,
        active: bool,
    ) -> EquipmentModel:
        model = EquipmentModel(
            name=self._required_name(name),
            description=self._optional_text(description),
            image_url=self._optional_text(image_url),
            active=active,
        )
        session.add(model)
        session.commit()
        session.refresh(model)
        return model

    def update_model(
        self,
        session: Session,
        model_id: UUID,
        *,
        name: str | None,
        description: str | None,
        image_url: str | None,
        active: bool | None,
    ) -> EquipmentModel:
        model = self.model(session, model_id)
        if name is not None:
            model.name = self._required_name(name)
        if description is not None:
            model.description = self._optional_text(description)
        if image_url is not None:
            model.image_url = self._optional_text(image_url)
        if active is not None:
            model.active = active
        session.commit()
        session.refresh(model)
        return model

    def create_unit(
        self, session: Session, model_id: UUID, label: str | None, active: bool
    ) -> EquipmentUnit:
        self.model(session, model_id)
        unit = EquipmentUnit(
            equipment_model_id=model_id, label=self._optional_text(label), active=active
        )
        session.add(unit)
        session.commit()
        session.refresh(unit)
        return unit

    def update_unit(
        self, session: Session, unit_id: UUID, *, label: str | None, active: bool | None
    ) -> EquipmentUnit:
        unit = session.get(EquipmentUnit, unit_id)
        if unit is None:
            raise EquipmentNotFoundError
        if label is not None:
            unit.label = self._optional_text(label)
        if active is not None:
            unit.active = active
        session.commit()
        session.refresh(unit)
        return unit

    @staticmethod
    def _required_name(value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise EquipmentValidationError("Equipment name is required")
        return normalized

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @staticmethod
    def _models_with_counts(session: Session, *, active_only: bool) -> list[ModelSummary]:
        statement = (
            select(EquipmentModel, func.count(EquipmentUnit.id).label("active_quantity"))
            .outerjoin(
                EquipmentUnit,
                and_(
                    EquipmentUnit.equipment_model_id == EquipmentModel.id,
                    EquipmentUnit.active.is_(True),
                ),
            )
            .group_by(EquipmentModel.id)
            .order_by(EquipmentModel.name, EquipmentModel.id)
        )
        if active_only:
            statement = statement.where(EquipmentModel.active.is_(True))
        return [
            ModelSummary(
                id=model.id,
                name=model.name,
                description=model.description,
                image_url=model.image_url,
                active=model.active,
                active_quantity=count,
            )
            for model, count in session.execute(statement)
        ]
