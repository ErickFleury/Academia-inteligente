from uuid import UUID, uuid4

import pytest
import test_training_lifecycle as lifecycle_fixtures
from sqlalchemy import event
from test_training_lifecycle import data
from test_training_review import api as api
from test_training_review import approve
from training_fixtures import instructor

from app.modules.clients.models import Account, Client
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding.models import Onboarding
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.service import TrainingLifecycleService

BASE = "/instructor/clients"
lifecycle_session = lifecycle_fixtures.session


@pytest.fixture
def session(lifecycle_session):
    lifecycle_session.connection().connection.driver_connection.create_function(
        "translate", 3, lambda value, source, target: value.translate(str.maketrans(source, target))
    )
    return lifecycle_session


def client_record(session, name, active=True, completed=False):
    client = Client(
        name=name, active=active, account=Account(email=f"{uuid4()}@test.test", account_active=True)
    )
    session.add(client)
    session.flush()
    if completed:
        session.add(
            Onboarding(
                client_id=client.id, status="completed", health_conditions="Private condition"
            )
        )
    session.commit()
    return client


def plan(session, client, active=False, actor="instructor-1"):
    version = TrainingLifecycleService().create_proposal(
        session, client_id=client.id, data=data(), created_by=actor, origin="instructor"
    )
    return approve(session, version, actor) if active else version


def test_name_filters_states_minimization_and_keyset_pagination(session, api):
    http, _ = api
    joao = client_record(session, "João   Silva", completed=True)
    ana = client_record(session, "Ana Lima")
    bia = client_record(session, "Bia Souza", completed=True)
    client_record(session, "João Inativo", active=False)
    base = plan(session, joao, True)
    TrainingLifecycleService().create_revision(
        session, plan_id=base.plan_id, version_number=1, data=data(), actor="instructor-1"
    )
    plan(session, bia, True, "instructor-2")
    assert [item["name"] for item in http.get(BASE).json()["items"]] == [
        ana.name,
        bia.name,
        joao.name,
    ]
    assert [item["id"] for item in http.get(BASE, {"search": " JOAO  sil "}).json()["items"]] == [
        str(joao.id)
    ]
    for filters, expected in [
        ({"onboarding": "completed"}, 2),
        ({"onboarding": "incomplete"}, 1),
        ({"training": "none"}, 1),
        ({"training": "pending"}, 1),
        ({"training": "current"}, 2),
        ({"responsibility": "none"}, 1),
        ({"responsibility": "me"}, 1),
        ({"responsibility": "specific", "responsible": str(base.id)}, 1),
        (
            {
                "training": "pending",
                "onboarding": "completed",
                "responsibility": "me",
                "search": "joao",
            },
            1,
        ),
    ]:
        result = http.get(BASE, filters)
        assert result.status_code == 200 and len(result.json()["items"]) == expected
    first = http.get(BASE, {"limit": "1"}).json()
    second = http.get(BASE, {"cursor": first["next_cursor"]}).json()
    assert len(first["items"] + second["items"]) == 3
    workspace = http.get(f"{BASE}/{joao.id}").json()
    assert workspace["draft_id"] and workspace["current_id"]
    for forbidden in (
        "email",
        "cpf",
        "phone",
        "address",
        "health_conditions",
        "account_id",
        "employee_id",
    ):
        assert forbidden not in str(workspace)
    assert http.get(BASE, {"responsibility": "specific"}).status_code == 422
    assert http.get(BASE, {"training": "draft_only"}).status_code == 422
    assert http.get(BASE, {"search": "%"}).json()["items"] == []


def test_list_query_count_does_not_grow_with_page_size(session, api):
    http, _ = api
    for index in range(4):
        client_record(session, f"Client {index}")
    counts = []

    def count(*args):
        counts.append(1)

    event.listen(session.bind, "before_cursor_execute", count)
    try:
        assert http.get(BASE, {"limit": "1"}).status_code == 200
        expected = len(counts)
        counts.clear()
        assert http.get(BASE, {"limit": "100"}).status_code == 200
        assert len(counts) == expected
    finally:
        event.remove(session.bind, "before_cursor_execute", count)


def test_first_manual_draft_separate_approval_and_all_entrypoints_recheck_eligibility(session, api):
    http, _ = api
    client = client_record(session, "Novo cliente")
    payload = data().model_dump(mode="json")
    created = http.post(f"{BASE}/{client.id}/draft", payload)
    assert created.status_code == 201
    version = session.get(TrainingPlanVersion, UUID(created.json()["id"]))
    assert version.status == "proposal" and version.origin == "instructor"
    assert version.created_employee_id == instructor(session).id
    assert version.approved_at is None and version.responsible_employee_id is None
    assert http.get(f"/training/pending/{version.id}").status_code == 200
    assert http.post(f"{BASE}/{client.id}/draft", payload).status_code == 409
    assert http.post("/training/plans", {**payload, "client_id": str(client.id)}).status_code == 409
    approve(session, version)
    assert http.post(f"{BASE}/{client.id}/draft", payload).status_code == 409
    assert http.post("/training/plans", {**payload, "client_id": str(client.id)}).status_code == 409


@pytest.mark.parametrize("role", ["client", "admin", "attendant", "employee", "instructor"])
def test_non_instructor_or_unlinked_identity_is_denied(session, api, role):
    http, identity = api
    client = client_record(session, "Cliente")
    identity.identity = AuthenticatedIdentity("unlinked", "user", (role,))
    assert http.get(BASE).status_code in (401, 403)
    assert http.get(f"{BASE}/{client.id}").status_code in (401, 403)
    assert http.post(f"{BASE}/{client.id}/draft", data().model_dump(mode="json")).status_code in (
        401,
        403,
    )


def test_inactive_missing_targets_and_inactive_employee_fail_closed(session, api):
    http, _ = api
    target = client_record(session, "Inactive", active=False)
    for identifier in (target.id, uuid4()):
        assert http.get(f"{BASE}/{identifier}").status_code == 404
        assert (
            http.post(f"{BASE}/{identifier}/draft", data().model_dump(mode="json")).status_code
            == 404
        )
    instructor(session).active = False
    session.commit()
    assert http.get(BASE).status_code == 401
