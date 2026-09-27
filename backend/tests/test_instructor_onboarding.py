from uuid import uuid4

import pytest
from sqlalchemy import select
from test_onboarding_draft_api import request
from test_onboarding_drafts import create_client
from test_training_review import api as api
from training_fixtures import instructor

from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding.draft_service import OnboardingDraftService
from app.modules.onboarding.models import Onboarding, OnboardingAuditEvent
from app.modules.training.models import TrainingPlanVersion

pytest_plugins = ["test_training_lifecycle"]

PAYLOAD = {
    "training_goal": "Ganhar força",
    "training_experience": "beginner",
    "height_cm": 170,
    "weight_kg": "70.50",
    "has_limitations_or_complaints": True,
    "limitations_or_complaints": "Limitação privada",
    "uses_medications": True,
    "medications": "Medicação privada",
    "has_health_conditions": True,
    "health_conditions": "Condição privada",
}


def test_continue_complete_edit_all_fields_in_place_and_client_remains_read_only(
    session, api, caplog
):
    http, identity = api
    target = create_client(session, "client", "client@test.test")
    other = create_client(session, "other", "other@test.test")
    path = f"/instructor/clients/{target.id}/onboarding"
    assert http.get(path).json()["status"] == "draft"
    original_id = session.scalar(select(Onboarding.id).where(Onboarding.client_id == target.id))
    assert http.patch(path, {"training_goal": "  Ganhar força  "}).status_code == 200
    assert http.post(path + "/completion", {}).status_code == 422
    assert http.patch(path, PAYLOAD).status_code == 200
    completed = http.post(path + "/completion", {})
    assert completed.status_code == 200
    timestamp = completed.json()["completed_at"]
    updated = {
        **PAYLOAD,
        "training_goal": "Mobilidade",
        "training_experience": "advanced",
        "height_cm": 172,
        "weight_kg": "72.10",
        "has_limitations_or_complaints": False,
        "uses_medications": False,
        "has_health_conditions": False,
    }
    result = http.patch(path, updated)
    assert result.status_code == 200 and result.json()["status"] == "completed"
    assert result.json()["completed_at"] == timestamp
    assert result.json()["medications"] is None and result.json()["health_conditions"] is None
    assert result.json()["height_cm"] == 172 and result.json()["training_experience"] == "advanced"
    assert (
        session.scalar(select(Onboarding.id).where(Onboarding.client_id == target.id))
        == original_id
    )
    assert OnboardingDraftService().has_valid_completed_onboarding(session, target.id)
    assert http.get(f"/instructor/clients/{other.id}/onboarding").json()["training_goal"] is None
    assert session.scalars(select(TrainingPlanVersion)).all() == []
    for invalid in (
        {"height_cm": 0},
        {"training_goal": None},
        {"uses_medications": True},
        {"token": "secret"},
    ):
        assert http.patch(path, invalid).status_code == 422
    assert http.get(path).json()["height_cm"] == 172
    audits = session.scalars(select(OnboardingAuditEvent)).all()
    assert any(not event.succeeded for event in audits)
    assert all(event.actor_employee_id == instructor(session).id for event in audits)
    assert all(event.occurred_at and event.client_id for event in audits)
    for secret in (
        "Condição privada",
        "Medicação privada",
        "Limitação privada",
        "Ganhar força",
        "secret",
    ):
        assert secret not in caplog.text
        assert all(secret not in str(event.__dict__) for event in audits)
    identity.identity = AuthenticatedIdentity("client", "client", ("client",))
    assert http.get("/onboarding/me").json()["training_goal"] == "Mobilidade"
    assert http.patch("/onboarding/me", {"training_goal": "Forbidden"}).status_code == 409


@pytest.mark.parametrize("role", ["admin", "attendant", "employee", "client", "instructor"])
def test_other_roles_unlinked_and_anonymous_cannot_access_sensitive_endpoints(session, api, role):
    http, identity = api
    target = create_client(session, "client", "client@test.test")
    identity.identity = AuthenticatedIdentity("unlinked", "user", (role,))
    path = f"/instructor/clients/{target.id}/onboarding"
    assert http.get(path).status_code in (401, 403)
    assert http.patch(path, PAYLOAD).status_code in (401, 403)
    assert http.post(path + "/completion", {}).status_code in (401, 403)
    assert request(http.app, "GET", path, authenticated=False)[0] == 401
    assert session.scalars(select(Onboarding)).all() == []


def test_inactive_employee_and_inactive_or_missing_targets_fail_closed(session, api):
    http, _ = api
    target = create_client(session, "client", "client@test.test")
    target.active = False
    session.commit()
    for identifier in (target.id, uuid4()):
        assert http.get(f"/instructor/clients/{identifier}/onboarding").status_code == 404
    target.active = True
    instructor(session).active = False
    session.commit()
    assert http.get(f"/instructor/clients/{target.id}/onboarding").status_code == 401
