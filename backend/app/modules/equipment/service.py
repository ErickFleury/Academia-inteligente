from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.media_images import ImageValidationError, normalize_image
from app.modules.equipment.models import EquipmentImage, EquipmentModel, EquipmentUnit


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
    @staticmethod
    def lock_models(session: Session, model_ids: set[UUID]) -> None:
        # All inventory/state writers use this same ordered parent-row boundary.
        list(
            session.scalars(
                select(EquipmentModel)
                .where(EquipmentModel.id.in_(model_ids))
                .order_by(EquipmentModel.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )

    def usable_models_with_units(
        self,
        session: Session,
        *,
        model_ids: set[UUID] | None = None,
        cursor: UUID | None = None,
        limit: int | None = None,
    ) -> list[EquipmentModel]:
        """Training usability only; operational never means currently free."""
        statement = (
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
            .order_by(EquipmentModel.id)
        )
        if model_ids is not None:
            statement = statement.where(EquipmentModel.id.in_(model_ids))
        if cursor is not None:
            statement = statement.where(EquipmentModel.id > cursor)
        if limit is not None:
            statement = statement.limit(limit)
        return list(session.scalars(statement.execution_options(populate_existing=True)))

    def training_context(self, session: Session) -> list[dict[str, str]]:
        return [
            {"id": str(model.id), "name": model.name}
            for model in self.usable_models_with_units(session, limit=100)
        ]

    def instructor_models(self, session: Session, cursor: UUID | None, limit: int, query: str = ""):
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
        if query.strip():
            escaped = query.strip().replace("!", "!!").replace("%", "!%").replace("_", "!_")
            statement = statement.where(EquipmentModel.name.ilike(f"%{escaped}%", escape="!"))
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
        *,
        initial_quantity: int = 0,
        unit_prefix: str = "UN",
        metadata: dict[str, str | None] | None = None,
    ) -> EquipmentModel:
        prefix = self._batch_options(initial_quantity, unit_prefix, allow_zero=True)
        model = EquipmentModel(
            name=self._required_name(name),
            description=self._optional_text(description),
            image_url=self._image_link(image_url),
            active=active,
        )
        self._metadata(model, metadata or {})
        session.add(model)
        session.flush()
        self._append_units(session, model.id, initial_quantity, prefix)
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
        metadata: dict[str, str | None] | None = None,
    ) -> EquipmentModel:
        self.lock_models(session, {model_id})
        model = self.model(session, model_id)
        if name is not None:
            model.name = self._required_name(name)
        if description is not None:
            model.description = self._optional_text(description)
        if image_url is not None:
            model.image_url = self._image_link(image_url)
            image = session.get(EquipmentImage, model_id)
            if image is not None:
                session.delete(image)
        if active is not None:
            model.active = active
        self._metadata(model, metadata or {})
        session.commit()
        session.refresh(model)
        return model

    def create_unit(
        self, session: Session, model_id: UUID, label: str | None, active: bool
    ) -> EquipmentUnit:
        self.lock_models(session, {model_id})
        self.model(session, model_id)
        unit = EquipmentUnit(
            equipment_model_id=model_id, label=self._optional_text(label), active=active
        )
        session.add(unit)
        session.commit()
        session.refresh(unit)
        return unit

    @staticmethod
    def _batch_options(quantity: int, prefix: str, *, allow_zero: bool = False) -> str:
        minimum = 0 if allow_zero else 1
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or not minimum <= quantity <= 100
        ):
            raise EquipmentValidationError("Unit quantity must be between 1 and 100")
        normalized = prefix.strip() or "UN"
        if len(normalized) > 40:
            raise EquipmentValidationError("Unit prefix is too long")
        return normalized

    @staticmethod
    def _append_units(
        session: Session, model_id: UUID, quantity: int, prefix: str
    ) -> list[EquipmentUnit]:
        existing = {
            label.casefold()
            for label in session.scalars(
                select(EquipmentUnit.label).where(EquipmentUnit.equipment_model_id == model_id)
            )
            if label
        }
        units = []
        number = 1
        while len(units) < quantity:
            label = f"{prefix}-{number:02}"
            number += 1
            if label.casefold() in existing:
                continue
            unit = EquipmentUnit(equipment_model_id=model_id, label=label, active=True)
            units.append(unit)
            existing.add(label.casefold())
        session.add_all(units)
        return units

    def create_units(
        self, session: Session, model_id: UUID, quantity: int, prefix: str
    ) -> list[EquipmentUnit]:
        prefix = self._batch_options(quantity, prefix)
        self.lock_models(session, {model_id})
        self.model(session, model_id)
        units = self._append_units(session, model_id, quantity, prefix)
        session.commit()
        for unit in units:
            session.refresh(unit)
        return units

    def update_unit(
        self,
        session: Session,
        unit_id: UUID,
        *,
        label: str | None,
        active: bool | None,
        metadata: dict[str, str | None] | None = None,
    ) -> EquipmentUnit:
        model_id = session.scalar(
            select(EquipmentUnit.equipment_model_id).where(EquipmentUnit.id == unit_id)
        )
        self.lock_models(session, {model_id} if model_id else set())
        unit = session.get(EquipmentUnit, unit_id, populate_existing=True)
        if unit is None:
            raise EquipmentNotFoundError
        if label is not None:
            unit.label = self._optional_text(label)
        if active is not None:
            unit.active = active
        self._metadata(unit, metadata or {})
        session.commit()
        session.refresh(unit)
        return unit

    @staticmethod
    def _metadata(record, values: dict[str, str | None]) -> None:
        allowed = (
            {"brand", "manufacturer_model", "category"}
            if isinstance(record, EquipmentModel)
            else {"location", "serial_number"}
        )
        for key, value in values.items():
            if key not in allowed:
                raise EquipmentValidationError("Invalid metadata field")
            setattr(record, key, EquipmentService._optional_text(value))

    @staticmethod
    def _image_link(value: str | None) -> str | None:
        value = EquipmentService._optional_text(value)
        if value is None:
            return None
        try:
            parts = urlsplit(value)
        except ValueError:
            raise EquipmentValidationError("Invalid image URL") from None
        if (
            "\\" in value
            or any(ord(char) < 33 for char in value)
            or parts.username
            or parts.password
            or not (
                (parts.scheme in {"https", "http"} and parts.netloc)
                or (value.startswith("/") and not value.startswith("//") and not parts.netloc)
            )
        ):
            raise EquipmentValidationError("Invalid image URL")
        return value

    def save_image(self, session: Session, model_id: UUID, raw: bytes) -> None:
        try:
            content, media_type, width, height = normalize_image(raw)
        except ImageValidationError as error:
            raise EquipmentValidationError(str(error)) from None
        self.lock_models(session, {model_id})
        model = self.model(session, model_id)
        image = session.get(EquipmentImage, model_id)
        if image is None:
            image = EquipmentImage(equipment_model_id=model_id)
            session.add(image)
        image.content, image.media_type, image.width, image.height = (
            content,
            media_type,
            width,
            height,
        )
        model.image_url = None
        model.updated_at = datetime.now(UTC)
        session.commit()

    def image(
        self, session: Session, model_id: UUID, *, administrator: bool = False
    ) -> EquipmentImage:
        model = self.model(session, model_id)
        image = session.get(EquipmentImage, model_id)
        if image is None or (not administrator and not model.active):
            raise EquipmentNotFoundError
        return image

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
            select(
                EquipmentModel,
                func.count(EquipmentUnit.id).label("active_quantity"),
                select(EquipmentImage.equipment_model_id)
                .where(EquipmentImage.equipment_model_id == EquipmentModel.id)
                .exists()
                .label("has_image"),
            )
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
                image_url=f"/equipment/{model.id}/image" if has_image else model.image_url,
                active=model.active,
                active_quantity=count,
            )
            for model, count, has_image in session.execute(statement)
        ]
