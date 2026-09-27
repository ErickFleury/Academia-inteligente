from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from test_onboarding_draft_api import request
from test_training_review import api as api
from training_fixtures import instructor

from app.modules.equipment.service import EquipmentService
from app.modules.identity.service import AuthenticatedIdentity

pytest_plugins = ["test_training_lifecycle"]
BASE = "/instructor/equipment"


def equipment(session):
    service = EquipmentService()
    model = service.create_model(session, "Leg Press", None, None, True)
    return model, service.create_unit(session, model.id, "Unidade A", True)


def test_state_changes_preserve_inventory_and_drive_usable_model_query(session, api):
    http, _ = api
    service = EquipmentService()
    model, unit = equipment(session)
    path = f"{BASE}/units/{unit.id}/operational-state"
    assert unit.operational_state == "operational" and unit.operational_revision == 1
    before = http.get("/equipment").json()
    assert http.get(BASE).json()["items"][0]["active_quantity"] == 1
    assert http.get(f"{BASE}/{model.id}/units").json()["items"][0]["label"] == "Unidade A"
    assert [item.id for item in service.usable_models_with_units(session)] == [model.id]
    updated = http.patch(path, {"operational_state": "out_of_order", "expected_revision": 1})
    assert updated.status_code == 200 and updated.json()["revision"] == 2
    assert http.get("/equipment").json() == before and unit.active
    assert service.usable_models_with_units(session) == []
    assert (
        http.patch(path, {"operational_state": "operational", "expected_revision": 1}).status_code
        == 409
    )
    assert (
        http.patch(path, {"operational_state": "operational", "expected_revision": 2}).status_code
        == 200
    )
    assert len(service.usable_models_with_units(session)) == 1
    service.update_unit(session, unit.id, label=None, active=False)
    assert service.usable_models_with_units(session) == []
    assert (
        http.patch(path, {"operational_state": "out_of_order", "expected_revision": 3}).status_code
        == 409
    )
    assert http.get(f"{BASE}/{model.id}/units").json()["items"][0]["active"] is False


def test_exact_state_input_and_no_inventory_mutations(session, api):
    http, identity = api
    model, unit = equipment(session)
    path = f"{BASE}/units/{unit.id}/operational-state"
    assert (
        http.patch(path, {"operational_state": "free", "expected_revision": 1}).status_code == 422
    )
    assert (
        http.patch(
            path, {"operational_state": "out_of_order", "expected_revision": 1, "active": False}
        ).status_code
        == 422
    )
    assert http.post("/equipment/admin/models", {"name": "Forbidden"}).status_code == 403
    assert (
        http.patch(
            f"/equipment/admin/models/{model.id}", {"name": "Forbidden", "active": False}
        ).status_code
        == 403
    )
    assert (
        http.post(f"/equipment/admin/models/{model.id}/units", {"label": "Forbidden"}).status_code
        == 403
    )
    assert (
        http.patch(
            f"/equipment/admin/units/{unit.id}", {"active": False, "label": "Forbidden"}
        ).status_code
        == 403
    )
    identity.identity = AuthenticatedIdentity("admin", "admin", ("admin",))
    assert (
        http.patch(f"/equipment/admin/units/{unit.id}", {"label": "Atualizada"}).status_code == 200
    )
    assert unit.operational_state == "operational"
    assert http.get(BASE).status_code == 403


@pytest.mark.parametrize("role", ["client", "admin", "attendant", "employee", "instructor"])
def test_operations_require_linked_active_instructor(session, api, role):
    http, identity = api
    model, unit = equipment(session)
    identity.identity = AuthenticatedIdentity("unlinked", "user", (role,))
    assert http.get(BASE).status_code in (401, 403)
    assert http.get(f"{BASE}/{model.id}/units").status_code in (401, 403)
    assert http.patch(
        f"{BASE}/units/{unit.id}/operational-state",
        {"operational_state": "out_of_order", "expected_revision": 1},
    ).status_code in (401, 403)
    assert request(http.app, "GET", BASE, authenticated=False)[0] == 401


def test_missing_inactive_models_and_database_constraint(session, api):
    http, _ = api
    model, unit = equipment(session)
    assert http.get(f"{BASE}/{uuid4()}/units").status_code == 404
    unit.operational_state = "unknown"
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    model.active = False
    session.commit()
    assert http.get(BASE).json()["items"] == []
    assert http.get(f"{BASE}/{model.id}/units").status_code == 404
    instructor(session).active = False
    session.commit()
    assert http.get(BASE).status_code == 401
