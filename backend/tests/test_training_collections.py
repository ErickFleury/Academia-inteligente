from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, select
from test_training_lifecycle import data
from test_training_lifecycle import session as session
from test_training_review import api as api
from test_training_review import approve, draft

from app.modules.clients.models import Account, Client
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training.collections_service import clone_current
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.service import TrainingLifecycleService

BASE = "/training/collections"


def current(session, name, subject="instructor-1", timestamp=None):
    client = Client(name=name, account=Account(email=f"{uuid4()}@test.test"))
    session.add(client)
    session.commit()
    version = TrainingLifecycleService().create_proposal(
        session, client_id=client.id, data=data(), created_by=subject, origin="instructor"
    )
    approve(session, version, subject)
    if timestamp:
        version.approved_at = datetime.fromisoformat(timestamp)
        session.commit()
    return version


def test_collection_scope_combined_filters_local_dates_and_minimization(session, api):
    client, _ = api
    a = current(session, "Ana Silva", timestamp="2026-09-27T02:59:59+00:00")
    b = current(session, "Ana Souza", timestamp="2026-09-27T03:00:00+00:00")
    c = current(session, "Ana Lima", "instructor-2", "2026-09-28T02:59:59+00:00")
    d = current(session, "Ana Prado", timestamp="2026-09-28T03:00:00+00:00")
    assert len(client.get(BASE).json()["items"]) == 4
    mine = client.get(BASE, {"mine": "true"}).json()["items"]
    assert {item["id"] for item in mine} == {str(v.id) for v in (a, b, d)}
    filters = {"start": "2026-09-27", "end": "2026-09-27", "search": "  Ana  "}
    assert {item["id"] for item in client.get(BASE, filters).json()["items"]} == {
        str(b.id),
        str(c.id),
    }
    filters["responsible"] = str(b.id)
    assert [item["id"] for item in client.get(BASE, filters).json()["items"]] == [str(b.id)]
    serialized = str(client.get(BASE).json())
    for forbidden in ("email", "cpf", "client_id", "employee_id", "account_id", "created_by"):
        assert forbidden not in serialized
    assert client.get(BASE, {"start": "2026-09-28", "end": "2026-09-27"}).status_code == 422
    assert client.get(BASE, {"cursor": "bad"}).status_code == 422
    assert client.get(BASE, {"search": "%"}).json()["items"] == []


def test_keyset_pagination_and_set_based_queries(session, api):
    client, _ = api
    for name in ("Ana", "Bia", "Clara"):
        current(session, name, timestamp="2026-09-27T12:00:00+00:00")
    counts = []

    def count(*args):
        counts.append(1)

    event.listen(session.bind, "before_cursor_execute", count)
    try:
        small = client.get(BASE, {"limit": "1"}).json()
        first_count = len(counts)
        counts.clear()
        full = client.get(BASE, {"limit": "100"}).json()
        assert len(counts) == first_count
    finally:
        event.remove(session.bind, "before_cursor_execute", count)
    current(session, "Newer", timestamp="2026-09-28T12:00:00+00:00")
    second = client.get(BASE, {"limit": "100", "cursor": small["next_cursor"]}).json()
    assert [item["id"] for item in small["items"] + second["items"]] == [
        item["id"] for item in full["items"]
    ]
    options = client.get(f"{BASE}/responsible").json()["items"]
    assert len(options) == 1 and set(options[0]) == {"reference", "name"}


def test_clone_conflict_cancel_exact_replacement_and_immutable_history(session, api):
    client, _ = api
    original = approve(session, draft(session))
    original_content = TrainingLifecycleService.content(session, original)
    path = f"{BASE}/{original.id}/draft"
    payload = {"expected_revision": original.revision}
    created = client.post(path, payload)
    assert created.status_code == 201
    pending_id = created.json()["id"]
    conflict = client.post(path, payload)
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["draft"]["id"] == pending_id
    # Opening/cancelling the dialog has no server mutation.
    assert client.get(f"/training/pending/{pending_id}").status_code == 200
    exact = {**payload, "discard_id": pending_id, "discard_revision": 1}
    newer = client.post(path, exact)
    assert newer.status_code == 201 and newer.json()["id"] != pending_id
    assert client.post(path, exact).status_code == 409
    assert client.get(f"{BASE}/{pending_id}").status_code == 404
    assert TrainingLifecycleService.content(session, original) == original_content
    new_version = session.get(TrainingPlanVersion, UUID(newer.json()["id"]))
    approve(session, new_version, "instructor-2")
    assert client.post(path, payload).status_code == 409
    history = client.get(f"{BASE}/{new_version.id}/history", {"limit": "1"}).json()
    assert history["items"][0]["id"] == str(new_version.id)
    older = client.get(
        f"{BASE}/{new_version.id}/history", {"cursor": history["next_cursor"]}
    ).json()
    assert [item["id"] for item in older["items"]] == [str(original.id)]
    assert (
        client.get(f"{BASE}/{original.id}").json()["responsible_instructor_name"]
        == original.responsible_name
    )
    assert (
        client.patch(
            f"/training/plans/{original.plan_id}/versions/1",
            {**data().model_dump(mode="json"), "expected_revision": original.revision},
        ).status_code
        == 409
    )


def test_stale_draft_revision_and_atomic_rollback(session, api, monkeypatch):
    client, _ = api
    original = approve(session, draft(session))
    pending = clone_current(
        session,
        original.id,
        actor="instructor-1",
        expected_revision=2,
        discard_id=None,
        discard_revision=None,
    )
    TrainingLifecycleService().revise(
        session,
        plan_id=pending.plan_id,
        version_number=pending.version_number,
        data=data("New work"),
        actor="instructor-2",
        expected_revision=1,
    )
    path = f"{BASE}/{original.id}/draft"
    assert (
        client.post(
            path, {"expected_revision": 2, "discard_id": str(pending.id), "discard_revision": 1}
        ).status_code
        == 409
    )
    assert pending.name == "New work" and pending.status == "proposal"
    with monkeypatch.context() as patch:
        patch.setattr(session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("failure")))
        with pytest.raises(RuntimeError):
            clone_current(
                session,
                original.id,
                actor="instructor-1",
                expected_revision=2,
                discard_id=pending.id,
                discard_revision=2,
            )
    session.expire_all()
    assert pending.status == "proposal" and original.status == "current"
    assert (
        len(
            session.scalars(
                select(TrainingPlanVersion).where(TrainingPlanVersion.status == "proposal")
            ).all()
        )
        == 1
    )


@pytest.mark.parametrize("role", ["client", "admin", "attendant", "employee", "instructor"])
def test_collection_family_denies_non_instructors_and_unlinked_token(session, api, role):
    client, identity = api
    version = approve(session, draft(session))
    identity.identity = AuthenticatedIdentity("unlinked", "user", (role,))
    for suffix in ("", "/responsible", f"/{version.id}", f"/{version.id}/history"):
        assert client.get(BASE + suffix).status_code in (401, 403)
    assert client.post(f"{BASE}/{version.id}/draft", {"expected_revision": 2}).status_code in (
        401,
        403,
    )
