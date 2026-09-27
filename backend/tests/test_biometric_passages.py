from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select
from test_biometric_access import access as access
from test_biometric_access import known_client, recognize
from test_biometrics_enrollment import service as service
from test_clients import AsgiClient, FakeProvisioner
from test_clients import database_session as database_session

from app.database import get_database_session
from app.main import create_app
from app.modules.biometrics.access import rebuild_access_states
from app.modules.biometrics.config import BiometricError
from app.modules.biometrics.enrollment import utcnow
from app.modules.biometrics.models import ClientAccessState, RecognitionAttempt, ReleaseRequest
from app.modules.biometrics.passages import PassageService
from app.modules.biometrics.router import get_access_service
from app.modules.clients.models import Account, Client
from app.modules.clients.service import ClientService
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.occupancy.models import (
    AccessPassageEvent,
    AccessSourceHeartbeat,
    OccupancyCorrection,
)
from app.modules.occupancy.service import OccupancyService
from app.modules.presence.service import ProfilePresenceService


@pytest.fixture
def passages(access):
    return PassageService(access.config, access.provider)


def scan_and_confirm(session, access, passages, direction="entry", actor="admin"):
    result = recognize(access, session, direction, actor)
    return passages.confirm(session, actor, UUID(result["attempt_id"]), uuid4())


def test_scan_alone_does_not_count_and_confirmed_entry_exit_count_once(
    database_session, service, access, passages
):
    person_id, client_id = known_client(database_session, service, access)
    attempt = recognize(access, database_session)
    assert OccupancyService().snapshot(database_session).occupancy == 0
    command_id = uuid4()
    result = passages.confirm(database_session, "admin", UUID(attempt["attempt_id"]), command_id)
    assert result["occupancy"] == 1 and result["state"]["inside"]
    assert (
        passages.confirm(database_session, "admin", UUID(attempt["attempt_id"]), command_id)
        == result
    )
    assert (
        passages.confirm(database_session, "admin", UUID(attempt["attempt_id"]), uuid4())[
            "occupancy"
        ]
        == 1
    )
    assert len(database_session.scalars(select(AccessPassageEvent)).all()) == 1
    database_session.get(Client, client_id).active = False
    database_session.get(Account, person_id).account_active = False
    database_session.commit()
    result = scan_and_confirm(database_session, access, passages, "exit")
    assert result["occupancy"] == 0 and not result["state"]["inside"]
    assert all(
        row.source_kind == "simulated"
        for row in database_session.scalars(select(AccessPassageEvent))
    )


@pytest.mark.parametrize("change", ["expired", "deactivated", "revoked", "corrected"])
def test_confirmation_rechecks_changes_since_recognition(
    database_session, service, access, passages, change
):
    person_id, client_id = known_client(database_session, service, access)
    result = recognize(access, database_session)
    attempt_id = UUID(result["attempt_id"])
    if change == "expired":
        database_session.get(RecognitionAttempt, attempt_id).expires_at = utcnow() - timedelta(
            seconds=1
        )
    elif change == "deactivated":
        database_session.get(Client, client_id).active = False
    elif change == "revoked":
        service.revoke(database_session, "admin", person_id, uuid4(), 1)
    else:
        passages.correct(database_session, "admin", uuid4(), client_id, True, 0, "Passagem omitida")
    database_session.commit()
    with pytest.raises(BiometricError):
        passages.confirm(database_session, "admin", attempt_id, uuid4())
    database_session.rollback()
    assert database_session.scalars(select(AccessPassageEvent)).all() == []
    assert OccupancyService().snapshot(database_session).occupancy == (
        1 if change == "corrected" else 0
    )


def test_reasoned_correction_and_noop_are_idempotent_and_never_release(
    database_session, service, access, passages
):
    _, client_id = known_client(database_session, service, access)
    command_id = uuid4()
    first = passages.correct(
        database_session, "admin", command_id, client_id, True, 0, "  Entrada omitida  "
    )
    assert first["occupancy"] == 1 and first["state"]["revision"] == 1
    assert (
        passages.correct(
            database_session, "admin", command_id, client_id, True, 0, "Entrada omitida"
        )
        == first
    )
    noop = passages.correct(
        database_session, "admin", uuid4(), client_id, True, 1, "Já estava dentro"
    )
    assert (
        noop["status"] == "unchanged" and noop["occupancy"] == 1 and noop["state"]["revision"] == 1
    )
    assert database_session.scalars(select(ReleaseRequest)).all() == []
    assert not access.release.requests
    rows = database_session.scalars(
        select(OccupancyCorrection).order_by(OccupancyCorrection.occurred_at)
    ).all()
    assert [(row.previous_inside, row.target_inside, row.adjustment) for row in rows] == [
        (False, True, 1),
        (True, True, 0),
    ]
    with pytest.raises(BiometricError, match="correction_invalid"):
        passages.correct(database_session, "admin", uuid4(), client_id, False, 1, "   ")
    with pytest.raises(BiometricError, match="state_changed"):
        passages.correct(database_session, "admin", uuid4(), client_id, False, 0, "Stale")


def test_rebuild_from_ledger_preserves_corrected_state_and_count(
    database_session, service, access, passages
):
    _, client_id = known_client(database_session, service, access)
    scan_and_confirm(database_session, access, passages)
    passages.correct(database_session, "admin", uuid4(), client_id, False, 1, "Teste corrigido")
    passages.correct(database_session, "admin", uuid4(), client_id, True, 2, "Entrada manual")
    before = passages.state(database_session, client_id)
    database_session.execute(delete(ClientAccessState))
    database_session.commit()
    rebuild_access_states(database_session)
    assert passages.state(database_session, client_id) == before
    assert before["inside"] and before["revision"] == 3
    assert OccupancyService().snapshot(database_session).occupancy == 1


def test_presence_remains_opt_in_and_person_correction_overrides_old_passage(
    database_session, service, access, passages
):
    person_id, client_id = known_client(database_session, service, access)
    database_session.get(Account, person_id).keycloak_subject = "client-subject"
    database_session.commit()
    passages.heartbeat(database_session, "admin", uuid4())
    scan_and_confirm(database_session, access, passages)
    presence = ProfilePresenceService()
    assert not presence.get_own(database_session, "client-subject").currently_present
    assert presence.set_own(database_session, "client-subject", True).currently_present
    passages.correct(
        database_session, "admin", uuid4(), client_id, False, 1, "Saída não registrada"
    )
    current = presence.get_own(database_session, "client-subject")
    assert current.sharing_enabled and not current.currently_present


def test_provider_outage_does_not_fabricate_freshness_or_reset_count(
    database_session, service, access, passages
):
    _, client_id = known_client(database_session, service, access)
    passages.correct(database_session, "admin", uuid4(), client_id, True, 0, "Entrada")
    heartbeat_id = uuid4()
    first = passages.heartbeat(database_session, "admin", heartbeat_id)
    assert passages.heartbeat(database_session, "admin", heartbeat_id) == first
    access.provider.failure = True
    with pytest.raises(BiometricError):
        passages.heartbeat(database_session, "admin", uuid4())
    database_session.rollback()
    row = database_session.get(AccessSourceHeartbeat, "pilot-webcam")
    snapshot = OccupancyService().snapshot(
        database_session, row.occurred_at + timedelta(seconds=121)
    )
    assert snapshot.occupancy == 1 and snapshot.status == "stale"


def test_erasure_removes_both_passages_and_person_corrections(
    database_session, service, access, passages
):
    _, client_id = known_client(database_session, service, access)
    scan_and_confirm(database_session, access, passages)
    passages.correct(database_session, "admin", uuid4(), client_id, False, 1, "Saída")
    ClientService(FakeProvisioner()).erase(database_session, client_id)
    assert database_session.scalars(select(OccupancyCorrection)).all() == []
    assert database_session.scalars(select(AccessPassageEvent)).all() == []
    assert database_session.scalars(select(ClientAccessState)).all() == []
    assert OccupancyService().snapshot(database_session).occupancy == 0


def test_api_guards_and_public_count_contains_no_identity(
    database_session, service, access, passages
):
    _, client_id = known_client(database_session, service, access)
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: database_session
    app.dependency_overrides[get_access_service] = lambda: access
    app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        "admin", None, ("admin",)
    )
    http = AsgiClient(app)
    assert (
        http.post(
            "/biometrics/state-corrections",
            {
                "command_id": str(uuid4()),
                "client_id": str(client_id),
                "inside": True,
                "expected_revision": 0,
                "reason": "Entrada",
            },
        ).status_code
        == 200
    )
    assert set(http.get("/occupancy").json()) == {"occupancy", "status", "updated_at"}
    for role in ("client", "instructor", "attendant"):
        app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
            "other", None, (role,)
        )
        assert (
            http.post("/biometrics/pilot-heartbeat", {"command_id": str(uuid4())}).status_code
            == 403
        )
        assert http.get(f"/biometrics/clients/{client_id}/state").status_code == 403
        assert (
            http.post(
                "/biometrics/state-corrections",
                {
                    "command_id": str(uuid4()),
                    "client_id": str(client_id),
                    "inside": False,
                    "expected_revision": 1,
                    "reason": "Saída",
                },
            ).status_code
            == 403
        )
