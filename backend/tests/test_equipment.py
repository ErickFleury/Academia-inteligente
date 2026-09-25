import asyncio
import json
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_database_session
from app.main import create_app
from app.modules.equipment.service import EquipmentService
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity


class FakeIdentityProvider:
    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        del access_token
        return AuthenticatedIdentity("employee", "employee@example.test", ("employee",))


def request(app, method: str, path: str) -> tuple[int, object]:
    sent: list[dict[str, object]] = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [(b"authorization", b"Bearer test-token")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(message["status"] for message in sent if message["type"] == "http.response.start")
    body = next(message["body"] for message in sent if message["type"] == "http.response.body")
    return status, json.loads(body)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    value = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield value
    finally:
        value.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_catalog_groups_units_by_model_and_derives_active_quantity(session: Session) -> None:
    service = EquipmentService()
    angled = service.create_model(
        session, "Leg Press 45°", "Plataforma inclinada", None, active=True
    )
    horizontal = service.create_model(session, "Leg Press Horizontal", None, None, active=True)
    for label in ("A", "B", "C", "D"):
        service.create_unit(session, angled.id, label, active=True)
    service.create_unit(session, horizontal.id, "A", active=True)

    catalog = {item.name: item for item in service.catalog(session)}

    assert catalog["Leg Press 45°"].id == angled.id
    assert catalog["Leg Press 45°"].active_quantity == 4
    assert catalog["Leg Press Horizontal"].id == horizontal.id
    assert catalog["Leg Press Horizontal"].active_quantity == 1

    unit = service.units(session, angled.id)[0]
    service.update_unit(session, unit.id, label=None, active=False)

    catalog = {item.name: item for item in service.catalog(session)}
    assert catalog["Leg Press 45°"].active_quantity == 3
    assert service.units(session, angled.id)[0].active is False


def test_model_and_unit_deactivation_preserve_records_but_hide_active_catalog(
    session: Session,
) -> None:
    service = EquipmentService()
    model = service.create_model(session, "Remo sentado", None, "/images/remo.jpg", active=True)
    unit = service.create_unit(session, model.id, "Unidade 1", active=True)

    service.update_model(
        session,
        model.id,
        name="Remo sentado com apoio",
        description=None,
        image_url=None,
        active=False,
    )

    assert service.catalog(session) == []
    assert service.model(session, model.id).name == "Remo sentado com apoio"
    assert service.units(session, model.id)[0].id == unit.id
    assert service.units(session, model.id)[0].active is True
    assert service.models(session)[0].active_quantity == 1


def test_public_catalog_and_admin_authorization(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = EquipmentService()
    model = service.create_model(session, "Puxador frontal", None, None, active=True)
    service.create_unit(session, model.id, None, active=True)
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    monkeypatch.setattr(identity_router, "identity_provider", FakeIdentityProvider())
    public_status, catalog = request(app, "GET", "/equipment")
    admin_status, _ = request(app, "GET", "/equipment/admin/models")

    assert public_status == 200
    assert catalog == [
        {
            "id": str(model.id),
            "name": "Puxador frontal",
            "description": None,
            "image_url": None,
            "active_quantity": 1,
        }
    ]
    assert admin_status == 403
