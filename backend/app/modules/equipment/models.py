import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EquipmentModel(Base):
    """One UUID-identified logical equipment type/model/variant."""

    __tablename__ = "equipment_model"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(2048))
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EquipmentUnit(Base):
    """One physical machine belonging to exactly one equipment model."""

    __tablename__ = "equipment_unit"
    __table_args__ = (
        CheckConstraint(
            "operational_state IN ('operational', 'out_of_order')",
            name="ck_equipment_operational_state",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    equipment_model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("equipment_model.id"), nullable=False, index=True
    )
    label: Mapped[str | None] = mapped_column(String(200))
    operational_state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="operational", server_default="operational"
    )
    operational_revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
