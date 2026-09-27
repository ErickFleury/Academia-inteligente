from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
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


class EquipmentModelMetadata(BaseModel):
    brand: str | None = Field(default=None, max_length=100)
    manufacturer_model: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=80)


class EquipmentModelInput(EquipmentModelMetadata):
    model_config = ConfigDict(extra="forbid")
    initial_quantity: int = Field(default=0, ge=0, le=100, strict=True)
    unit_prefix: str = Field(default="UN", max_length=40)
    name: str = Field(max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    image_url: str | None = Field(default=None, max_length=2048)
    active: bool = True


class EquipmentModelPatch(EquipmentModelMetadata):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    image_url: str | None = Field(default=None, max_length=2048)
    active: bool | None = None


class EquipmentUnitInput(BaseModel):
    label: str | None = Field(default=None, max_length=200)
    active: bool = True


class EquipmentUnitBatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quantity: int = Field(ge=1, le=100, strict=True)
    prefix: str = Field(default="UN", max_length=40)


class EquipmentUnitPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)
    label: str | None = Field(default=None, max_length=200)
    active: bool | None = None


class EquipmentCatalogResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    image_url: str | None
    active_quantity: int


class EquipmentAdminModelResponse(EquipmentCatalogResponse, EquipmentModelMetadata):
    image_source: Literal["upload", "link", "none"]
    image_link: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class EquipmentUnitResponse(BaseModel):
    location: str | None = None
    serial_number: str | None = None
    operational_state: Literal["operational", "out_of_order"]
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


def admin_model_response(
    session: Session, value: EquipmentModel, summary: ModelSummary | None = None
) -> EquipmentAdminModelResponse:
    summary = summary or next(item for item in service.models(session) if item.id == value.id)
    uploaded = summary.image_url == f"/equipment/{value.id}/image"
    projection = catalog_response(summary).model_dump()
    if uploaded:
        projection["image_url"] = f"/equipment/admin/models/{value.id}/image"
    return EquipmentAdminModelResponse(
        **projection,
        image_source="upload" if uploaded else "link" if value.image_url else "none",
        image_link=value.image_url,
        brand=value.brand,
        manufacturer_model=value.manufacturer_model,
        category=value.category,
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
    return [admin_model_response(session, model, summaries[model.id]) for model in models]


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
                session,
                payload.name,
                payload.description,
                payload.image_url,
                payload.active,
                initial_quantity=payload.initial_quantity,
                unit_prefix=payload.unit_prefix,
                metadata={
                    key: getattr(payload, key)
                    for key in ("brand", "manufacturer_model", "category")
                },
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
                metadata={
                    key: getattr(payload, key)
                    for key in ("brand", "manufacturer_model", "category")
                    if key in payload.model_fields_set
                },
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


@router.post(
    "/admin/models/{model_id}/units/batch",
    response_model=list[EquipmentUnitResponse],
    status_code=201,
)
def create_units(
    model_id: UUID,
    payload: EquipmentUnitBatchInput,
    session: DatabaseSession,
    administrator: Administrator,
):
    del administrator
    try:
        return [
            unit_response(unit)
            for unit in service.create_units(session, model_id, payload.quantity, payload.prefix)
        ]
    except (EquipmentNotFoundError, EquipmentValidationError) as exc:
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
            service.update_unit(
                session,
                unit_id,
                label=payload.label,
                active=payload.active,
                metadata={
                    key: getattr(payload, key)
                    for key in ("location", "serial_number")
                    if key in payload.model_fields_set
                },
            )
        )
    except EquipmentNotFoundError as exc:
        raise error(exc) from None


@router.put("/admin/models/{model_id}/image", response_model=EquipmentAdminModelResponse)
def upload_image(
    model_id: UUID,
    session: DatabaseSession,
    administrator: Administrator,
    raw: bytes = Body(media_type="application/octet-stream"),
):
    del administrator
    try:
        service.save_image(session, model_id, raw)
        return admin_model_response(session, service.model(session, model_id))
    except (EquipmentNotFoundError, EquipmentValidationError) as exc:
        raise error(exc) from None


@router.get("/admin/models/{model_id}/image")
def admin_image(model_id: UUID, session: DatabaseSession, administrator: Administrator):
    del administrator
    try:
        image = service.image(session, model_id, administrator=True)
        return Response(image.content, media_type=image.media_type)
    except EquipmentNotFoundError as exc:
        raise error(exc) from None


@router.get("/{model_id}/image")
def public_image(model_id: UUID, session: DatabaseSession):
    try:
        image = service.image(session, model_id)
        return Response(image.content, media_type=image.media_type)
    except EquipmentNotFoundError as exc:
        raise error(exc) from None
