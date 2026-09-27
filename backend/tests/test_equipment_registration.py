from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import select
from test_equipment import session as session
from test_occupancy import request

from app.database import get_database_session
from app.main import create_app
from app.modules.equipment import router
from app.modules.equipment.models import EquipmentImage, EquipmentModel
from app.modules.equipment.service import (
    EquipmentNotFoundError,
    EquipmentService,
    EquipmentValidationError,
)
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity


def test_registration_creates_model_and_units_and_generates_unused_labels(session):
    service = EquipmentService()
    model = service.create_model(
        session,
        "Esteira",
        None,
        None,
        True,
        initial_quantity=3,
        unit_prefix="EST",
        metadata={"brand": "Private brand"},
    )
    assert sorted(u.label for u in service.units(session, model.id)) == [
        "EST-01",
        "EST-02",
        "EST-03",
    ]
    service.update_unit(session, service.units(session, model.id)[0].id, label=None, active=False)
    assert [u.label for u in service.create_units(session, model.id, 2, "EST")] == [
        "EST-04",
        "EST-05",
    ]
    assert service.catalog(session)[0].active_quantity == 4
    assert service.model(session, model.id).brand == "Private brand"


@pytest.mark.parametrize("quantity", [-1, 101, True, 1.5])
def test_invalid_registration_never_creates_partial_model(session, quantity):
    with pytest.raises(EquipmentValidationError):
        EquipmentService().create_model(
            session, "Invalid", None, None, True, initial_quantity=quantity
        )
    assert session.scalars(select(EquipmentModel)).all() == []


def test_metadata_stays_private_and_unit_labels_and_details_can_be_changed(session):
    service = EquipmentService()
    model = service.create_model(
        session,
        "Leg press",
        None,
        None,
        True,
        initial_quantity=1,
        metadata={"brand": "Private", "category": "Private", "manufacturer_model": "Private"},
    )
    unit = service.units(session, model.id)[0]
    service.update_unit(
        session,
        unit.id,
        label="LP-01",
        active=None,
        metadata={"location": "Private", "serial_number": "Private"},
    )
    public = router.catalog_response(service.catalog(session)[0]).model_dump()
    instructor = service.instructor_models(session, None, 20)
    instructor_units = service.instructor_units(session, model.id, None, 20)
    assert "Private" not in str(public) + str(instructor) + str(instructor_units) + str(
        service.training_context(session)
    )
    assert router.admin_model_response(session, model).brand == "Private"
    assert router.unit_response(unit).serial_number == "Private"
    assert router.unit_response(unit).operational_state == "operational"
    service.update_unit(session, unit.id, label=None, active=None, metadata={"location": None})
    assert unit.location is None and unit.serial_number == "Private"


def test_image_replacement_normalization_and_deactivation(session):
    service = EquipmentService()
    model = service.create_model(session, "Leg press", None, "/images/old.jpg", True)
    raw = BytesIO()
    Image.new("RGB", (1500, 1000)).save(raw, "PNG")
    service.save_image(session, model.id, raw.getvalue())
    image = service.image(session, model.id)
    assert image.width == 1024 and image.height <= 1024 and image.media_type == "image/webp"
    assert model.image_url is None
    assert service.catalog(session)[0].image_url == f"/equipment/{model.id}/image"
    assert router.admin_model_response(session, model).image_source == "upload"
    service.update_model(
        session, model.id, name=None, description=None, image_url=None, active=False
    )
    with pytest.raises(EquipmentNotFoundError):
        service.image(session, model.id)
    assert service.image(session, model.id, administrator=True).content
    service.update_model(
        session, model.id, name=None, description=None, image_url="/images/new.jpg", active=None
    )
    assert session.get(EquipmentImage, model.id) is None


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:image/png;base64,abc",
        "//other.test/pic",
        "/\\other.test/a",
        "https://user:pass@example.test/a",
    ],
)
def test_invalid_image_link_rejected(session, url):
    with pytest.raises(EquipmentValidationError):
        EquipmentService().create_model(session, "Image", None, url, True)


def test_instructor_search_filters_before_page_limit(session):
    service = EquipmentService()
    service.create_model(session, "Esteira", None, None, True)
    service.create_model(session, "Leg press", None, None, True)
    assert [m["name"] for m in service.instructor_models(session, None, 1, "leg")["items"]] == [
        "Leg press"
    ]
    assert service.instructor_models(session, None, 20, "%")["items"] == []


def test_bulk_api_and_private_routes_require_administrator(session, monkeypatch):
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: session

    class Provider:
        def get_identity(self, token):
            return AuthenticatedIdentity(
                "admin", "admin", ("admin",) if token == "admin" else ("attendant",)
            )

    monkeypatch.setattr(identity_router, "identity_provider", Provider())
    admin = [(b"content-type", b"application/json"), (b"authorization", b"Bearer admin")]
    denied = [(b"content-type", b"application/json"), (b"authorization", b"Bearer attendant")]
    code, body = request(
        app,
        "POST",
        "/equipment/admin/models",
        {"name": "Esteira", "initial_quantity": 3, "unit_prefix": "EST"},
        admin,
    )
    assert code == 201 and body["active_quantity"] == 3
    path = f"/equipment/admin/models/{body['id']}/units/batch"
    assert request(app, "POST", path, {"quantity": 2}, denied)[0] == 403
    assert request(app, "POST", path, {"quantity": 101}, admin)[0] == 422
    assert request(app, "POST", path, {"quantity": 2, "prefix": "EST"}, admin)[0] == 201
    assert (
        request(app, "GET", f"/equipment/admin/models/{body['id']}/image", headers=denied)[0] == 403
    )


def test_image_http_contract_and_inventory_visibility(session):
    import asyncio
    import json

    from app.modules.identity.router import get_authenticated_identity

    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: session
    app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        "admin", "admin", ("admin",)
    )
    model = EquipmentService().create_model(session, "Photo", None, None, True)
    raw = BytesIO()
    Image.new("RGB", (4, 4), "red").save(raw, "PNG")

    def call(method, path, body=b""):
        sent = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            sent.append(message)

        asyncio.run(
            app(
                {
                    "type": "http",
                    "http_version": "1.1",
                    "method": method,
                    "scheme": "http",
                    "path": path,
                    "query_string": b"",
                    "headers": [(b"content-type", b"application/octet-stream")],
                },
                receive,
                send,
            )
        )
        return sent[0]["status"], b"".join(item.get("body", b"") for item in sent)

    code, body = call("PUT", f"/equipment/admin/models/{model.id}/image", raw.getvalue())
    assert code == 200 and json.loads(body)["image_source"] == "upload"
    assert call("GET", f"/equipment/{model.id}/image")[0] == 200
    assert call("PUT", f"/equipment/admin/models/{model.id}/image", b"not an image")[0] == 422
    assert call("GET", f"/equipment/{model.id}/image")[0] == 200
    EquipmentService().update_model(
        session, model.id, name=None, description=None, image_url=None, active=False
    )
    assert call("GET", f"/equipment/{model.id}/image")[0] == 404
    assert call("GET", f"/equipment/admin/models/{model.id}/image")[0] == 200
    app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        "attendant", "attendant", ("attendant",)
    )
    assert call("PUT", f"/equipment/admin/models/{model.id}/image", raw.getvalue())[0] == 403
