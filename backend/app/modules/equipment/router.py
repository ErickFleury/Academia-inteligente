from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_database_session
from app.modules.equipment.models import EquipmentModel, EquipmentUnit
from app.modules.equipment.service import (
    EquipmentNotFoundError,
    EquipmentService,
    EquipmentValidationError,
    ModelSummary,
)
from app.modules.identity.authorization import require_roles
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity

router = APIRouter(prefix="/equipment", tags=["equipment"])
service = EquipmentService()
DatabaseSession = Annotated[Session, Depends(get_database_session)]
Administrator = Annotated[
    AuthenticatedIdentity, Depends(require_roles(get_authenticated_identity, "admin"))
]


class EquipmentModelInput(BaseModel):
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    image_url: str | None = Field(default=None, max_length=2048)
    active: bool = True


class EquipmentModelPatch(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    image_url: str | None = Field(default=None, max_length=2048)
    active: bool | None = None


class EquipmentUnitInput(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    active: bool = True


class EquipmentUnitPatch(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    active: bool | None = None


class EquipmentCatalogResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    image_url: str | None
    active_quantity: int


class EquipmentAdminModelResponse(EquipmentCatalogResponse):
    active: bool
    created_at: datetime
    updated_at: datetime


class EquipmentUnitResponse(BaseModel):
    id: UUID
    equipment_model_id: UUID
    label: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


def catalog_response(value: ModelSummary) -> EquipmentCatalogResponse:
    return EquipmentCatalogResponse(
        id=value.id,
        name=value.name,
        description=value.description,
        image_url=value.image_url,
        active_quantity=value.active_quantity,
    )


def admin_model_response(session: Session, value: EquipmentModel) -> EquipmentAdminModelResponse:
    summary = next(item for item in service.models(session) if item.id == value.id)
    return EquipmentAdminModelResponse(
        **catalog_response(summary).model_dump(),
        active=value.active,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )


def unit_response(value: EquipmentUnit) -> EquipmentUnitResponse:
    return EquipmentUnitResponse.model_validate(value, from_attributes=True)


def error(exc: Exception) -> HTTPException:
    if isinstance(exc, EquipmentValidationError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc))
    return HTTPException(status.HTTP_404_NOT_FOUND, "Equipment not found")


@router.get("", response_model=list[EquipmentCatalogResponse])
def list_active_catalog(session: DatabaseSession) -> list[EquipmentCatalogResponse]:
    """Public catalog: active inventory only, never real-time availability."""
    return [catalog_response(item) for item in service.catalog(session)]


@router.get("/admin/models", response_model=list[EquipmentAdminModelResponse])
def list_models(
    session: DatabaseSession, administrator: Administrator
) -> list[EquipmentAdminModelResponse]:
    del administrator
    summaries = {item.id: item for item in service.models(session)}
    models = list(session.scalars(select(EquipmentModel).order_by(EquipmentModel.name)))
    return [
        EquipmentAdminModelResponse(
            **catalog_response(summaries[model.id]).model_dump(),
            active=model.active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        for model in models
    ]


@router.post(
    "/admin/models",
    response_model=EquipmentAdminModelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_model(
    payload: EquipmentModelInput, session: DatabaseSession, administrator: Administrator
) -> EquipmentAdminModelResponse:
    del administrator
    try:
        return admin_model_response(
            session,
            service.create_model(
                session, payload.name, payload.description, payload.image_url, payload.active
            ),
        )
    except EquipmentValidationError as exc:
        raise error(exc) from None


@router.patch("/admin/models/{model_id}", response_model=EquipmentAdminModelResponse)
def update_model(
    model_id: UUID,
    payload: EquipmentModelPatch,
    session: DatabaseSession,
    administrator: Administrator,
) -> EquipmentAdminModelResponse:
    del administrator
    try:
        return admin_model_response(
            session,
            service.update_model(
                session,
                model_id,
                name=payload.name,
                description=payload.description,
                image_url=payload.image_url,
                active=payload.active,
            ),
        )
    except (EquipmentNotFoundError, EquipmentValidationError) as exc:
        raise error(exc) from None


@router.get("/admin/models/{model_id}/units", response_model=list[EquipmentUnitResponse])
def list_units(
    model_id: UUID, session: DatabaseSession, administrator: Administrator
) -> list[EquipmentUnitResponse]:
    del administrator
    try:
        return [unit_response(unit) for unit in service.units(session, model_id)]
    except EquipmentNotFoundError as exc:
        raise error(exc) from None


@router.post(
    "/admin/models/{model_id}/units",
    response_model=EquipmentUnitResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_unit(
    model_id: UUID,
    payload: EquipmentUnitInput,
    session: DatabaseSession,
    administrator: Administrator,
) -> EquipmentUnitResponse:
    del administrator
    try:
        return unit_response(service.create_unit(session, model_id, payload.label, payload.active))
    except EquipmentNotFoundError as exc:
        raise error(exc) from None


@router.patch("/admin/units/{unit_id}", response_model=EquipmentUnitResponse)
def update_unit(
    unit_id: UUID,
    payload: EquipmentUnitPatch,
    session: DatabaseSession,
    administrator: Administrator,
) -> EquipmentUnitResponse:
    del administrator
    try:
        return unit_response(
            service.update_unit(session, unit_id, label=payload.label, active=payload.active)
        )
    except EquipmentNotFoundError as exc:
        raise error(exc) from None
