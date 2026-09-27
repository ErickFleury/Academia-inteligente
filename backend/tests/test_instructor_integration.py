"""Direct API authorization across every instructor endpoint family."""

from uuid import uuid4

import pytest
from test_equipment_operational import equipment
from test_instructor_clients import lifecycle_session as lifecycle_session
from test_instructor_clients import session as session
from test_onboarding_draft_api import request
from test_training_lifecycle import data
from test_training_review import api as api
from test_training_review import approve, draft
from training_fixtures import instructor

from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training.service import TrainingLifecycleService


@pytest.mark.parametrize(
    "identity", ["anonymous", "client", "admin", "attendant", "employee", "inactive", "unlinked"]
)
def test_every_instructor_endpoint_rejects_unauthorized_identity(session, api, identity):
    http, provider = api
    current = approve(session, draft(session))
    pending = TrainingLifecycleService().create_revision(
        session, plan_id=current.plan_id, version_number=1, data=data(), actor="instructor-1"
    )
    model, unit = equipment(session)
    if identity == "inactive":
        instructor(session).active = False
        session.commit()
    subject = (
        "instructor-1"
        if identity in {"inactive", "employee"}
        else "client"
        if identity == "client"
        else "unlinked"
    )
    role = "instructor" if identity in {"inactive", "unlinked"} else identity
    provider.identity = AuthenticatedIdentity(subject, "test", (role,))
    target = str(current.client_id)
    unknown = str(uuid4())
    paths = [
        ("GET", "/instructor/social/feed", None),
        ("GET", f"/instructor/social/posts/{unknown}", None),
        ("GET", f"/instructor/social/posts/{unknown}/images/{unknown}", None),
        ("GET", f"/instructor/social/posts/{unknown}/comments/{unknown}/image", None),
        ("GET", "/training/pending", None),
        ("GET", f"/training/pending/{pending.id}", None),
        (
            "PATCH",
            f"/training/plans/{pending.plan_id}/versions/2",
            {**data().model_dump(mode="json"), "expected_revision": 1},
        ),
        ("POST", f"/training/plans/{pending.plan_id}/versions/2/approve", {"expected_revision": 1}),
        ("GET", "/training/collections", None),
        ("GET", "/training/collections/responsible", None),
        ("GET", f"/training/collections/{current.id}", None),
        ("GET", f"/training/collections/{current.id}/history", None),
        (
            "POST",
            f"/training/collections/{current.id}/draft",
            {"expected_revision": current.revision},
        ),
        ("GET", "/instructor/clients", None),
        ("GET", f"/instructor/clients/{target}", None),
        ("POST", f"/instructor/clients/{target}/draft", data().model_dump(mode="json")),
        ("GET", f"/instructor/clients/{target}/onboarding", None),
        ("PATCH", f"/instructor/clients/{target}/onboarding", {"training_goal": "Treinar"}),
        ("POST", f"/instructor/clients/{target}/onboarding/completion", {}),
        ("GET", "/instructor/equipment", None),
        ("GET", "/instructor/equipment/usable-models", None),
        ("GET", f"/instructor/equipment/{model.id}/units", None),
        (
            "PATCH",
            f"/instructor/equipment/units/{unit.id}/operational-state",
            {"operational_state": "out_of_order", "expected_revision": 1},
        ),
    ]
    for method, path, body in paths:
        status, response = request(
            http.app, method, path, body, authenticated=identity != "anonymous"
        )
        assert status in (401, 403), (identity, method, path, status)
        assert set(response) == {"detail"}
    assert pending.status == "proposal" and pending.revision == 1
    assert unit.operational_state == "operational"


def test_active_instructor_missing_targets_are_controlled_and_admin_data_stays_denied(session, api):
    http, _ = api
    unknown = uuid4()
    for path in [
        f"/instructor/clients/{unknown}",
        f"/instructor/clients/{unknown}/onboarding",
        f"/training/pending/{unknown}",
        f"/training/collections/{unknown}",
        f"/training/collections/{unknown}/history",
        f"/instructor/equipment/{unknown}/units",
        f"/instructor/social/posts/{unknown}",
    ]:
        assert http.get(path).status_code == 404, path
    for path in ["/clients", "/employees", "/onboarding/me", "/training/chat"]:
        assert http.get(path).status_code == 403, path
