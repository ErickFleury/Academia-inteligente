from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_biometrics_enrollment import enrolled_person
from test_biometrics_enrollment import service as service
from test_clients import AsgiClient, FakeProvisioner, client_data
from test_clients import database_session as database_session

from app.database import get_database_session
from app.main import create_app
from app.modules.biometrics.access import (
    AccessService,
    access_state,
    attempt_result,
    recover_interrupted_attempts,
)
from app.modules.biometrics.config import BiometricError
from app.modules.biometrics.enrollment import utcnow
from app.modules.biometrics.models import BiometricEnrollment, RecognitionAttempt, ReleaseRequest
from app.modules.biometrics.provider import Candidate, Face
from app.modules.biometrics.router import get_access_service
from app.modules.clients.models import Account, Client
from app.modules.clients.service import ClientService, validate_client_data
from app.modules.employees.service import EmployeeService
from app.modules.identity.router import get_authenticated_identity
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.occupancy.models import AccessPassageEvent
from app.modules.occupancy.service import OccupancyService


class ReleaseSpy:
    def __init__(self):
        self.requests = []

    def request_release(self, request):
        self.requests.append(request)
        return "simulated"


@pytest.fixture
def access(service):
    return AccessService(service.config, service.provider, ReleaseSpy())


def known_client(session, service, access, *, inside=False, active=True, login_active=True):
    person_id = enrolled_person(service, session)
    enrollment = session.get(BiometricEnrollment, person_id)
    client = session.scalar(select(Client).where(Client.account_id == person_id))
    client.active = active
    session.get(Account, person_id).account_active = login_active
    access_state(session, client.id)
    if inside:
        session.add(
            AccessPassageEvent(
                event_id=str(uuid4()),
                client_id=client.id,
                client_reference_digest="f" * 64,
                occurred_at=utcnow(),
                checkpoint_id="fixture",
                direction="entry",
            )
        )
    session.commit()
    access.provider.faces = (Face(0.99, (Candidate(enrollment.subject, 0.95),)),)
    return person_id, client.id


def recognize(access, session, direction="entry", actor="admin"):
    result = access.create(session, actor, uuid4(), direction)
    identifier = UUID(result["attempt_id"])
    return access.capture(session, actor, identifier, uuid4(), b"synthetic")


def test_authorized_scan_records_one_simulated_release_but_no_passage(
    access, service, database_session
):
    known_client(database_session, service, access)
    created = access.create(database_session, "admin", uuid4(), "entry")
    attempt_id, command_id = UUID(created["attempt_id"]), uuid4()
    first = access.capture(database_session, "admin", attempt_id, command_id, b"synthetic")
    retry = access.capture(database_session, "admin", attempt_id, command_id, b"same command")
    assert (
        retry == first and first["status"] == "authorized" and first["release_mode"] == "simulated"
    )
    assert len(access.release.requests) == 1
    assert len(database_session.scalars(select(ReleaseRequest)).all()) == 1
    assert database_session.scalars(select(AccessPassageEvent)).all() == []
    assert OccupancyService().snapshot(database_session).occupancy == 0
    payload = access.release.requests[0].__dict__
    assert set(payload) == {
        "release_request_id",
        "recognition_attempt_id",
        "occurred_at",
        "checkpoint_id",
        "direction",
        "subject_reference",
        "mode",
    }
    assert not {"client_id", "name", "cpf", "email", "score", "image"}.intersection(payload)


@pytest.mark.parametrize(
    "inside,active,login_active,direction,result",
    [
        (False, True, True, "entry", "authorized"),
        (False, False, True, "entry", "client_inactive"),
        (True, True, True, "entry", "already_inside"),
        (False, True, True, "exit", "already_outside"),
        (True, False, False, "exit", "authorized"),
        (True, True, False, "exit", "authorized"),
    ],
)
def test_explicit_pilot_entry_exit_policy(
    access, service, database_session, inside, active, login_active, direction, result
):
    known_client(
        database_session, service, access, inside=inside, active=active, login_active=login_active
    )
    response = recognize(access, database_session, direction)
    assert response["result_code"] == result
    assert bool(access.release.requests) == (result == "authorized")
    assert len(database_session.scalars(select(AccessPassageEvent)).all()) == int(inside)


@pytest.mark.parametrize(
    "faces,code",
    [
        ((), "no_face"),
        ((Face(0.99, ()), Face(0.99, ())), "multiple_faces"),
        ((Face(0.7, ()),), "face_quality_low"),
        ((Face(0.99, ()),), "unknown_face"),
        ((Face(0.99, (Candidate("x", 0.5),)),), "match_below_threshold"),
        ((Face(0.99, (Candidate("x", 0.9), Candidate("y", 0.85))),), "ambiguous_face"),
        ((Face(0.99, (Candidate("staged-or-unknown", 0.95),)),), "unknown_face"),
    ],
)
def test_rejections_allow_exactly_one_additional_capture(access, database_session, faces, code):
    access.provider.faces = faces
    response = recognize(access, database_session)
    assert response["result_code"] == code and response["can_retry"]
    identifier = UUID(response["attempt_id"])
    second = access.capture(database_session, "admin", identifier, uuid4(), b"synthetic")
    assert second["captures"] == 2 and second["status"] == "failed" and not second["can_retry"]
    with pytest.raises(BiometricError, match="attempt_not_capturable"):
        access.capture(database_session, "admin", identifier, uuid4(), b"synthetic")
    assert not access.release.requests


def test_staff_only_face_never_receives_client_release(access, service, database_session):
    person_id, client_id = known_client(database_session, service, access)
    EmployeeService(FakeProvisioner()).create(
        database_session, validate_client_data(**client_data()), None, "instructor"
    )
    ClientService(FakeProvisioner()).erase(database_session, client_id)
    assert database_session.get(BiometricEnrollment, person_id).enabled
    result = recognize(access, database_session)
    assert result["result_code"] == "staff_only" and not access.release.requests


def test_revocation_cancels_pending_result_and_old_reference_is_unknown(
    access, service, database_session
):
    person_id, _ = known_client(database_session, service, access)
    response = recognize(access, database_session)
    service.revoke(database_session, "admin", person_id, uuid4(), 1)
    row = database_session.get(RecognitionAttempt, UUID(response["attempt_id"]))
    assert attempt_result(database_session, row)["status"] == "canceled"
    assert recognize(access, database_session)["result_code"] == "unknown_face"
    assert len(access.release.requests) == 1


def test_direction_change_cancels_previous_attempt_and_late_response(
    access, service, database_session
):
    known_client(database_session, service, access)
    original = access.provider.inspect

    def change_direction(image):
        access.create(database_session, "admin", uuid4(), "exit")
        return original(image)

    access.provider.inspect = change_direction
    result = recognize(access, database_session)
    assert result["status"] == "canceled" and not access.release.requests


def test_inflight_revocation_fails_closed(access, service, database_session):
    person_id, _ = known_client(database_session, service, access)
    original = access.provider.inspect

    def revoke(image):
        service.revoke(database_session, "admin", person_id, uuid4(), 1)
        return original(image)

    access.provider.inspect = revoke
    assert recognize(access, database_session)["result_code"] == "unknown_face"
    assert not access.release.requests


def test_interrupted_attempt_recovers_without_automatic_capture(access, database_session):
    response = access.create(database_session, "admin", uuid4(), "entry")
    row = database_session.get(RecognitionAttempt, UUID(response["attempt_id"]))
    row.status = "capturing"
    row.captures = 1
    row.capture_until = utcnow() - timedelta(seconds=1)
    database_session.commit()
    recover_interrupted_attempts(database_session)
    database_session.commit()
    assert row.status == "rejected" and row.result_code == "capture_interrupted"
    assert not access.release.requests


def test_provider_failure_is_a_controlled_rejection_without_release(access, database_session):
    def unavailable(image):
        raise BiometricError("provider_unavailable", 503)

    access.provider.inspect = unavailable
    result = recognize(access, database_session)
    assert result["result_code"] == "provider_unavailable" and result["can_retry"]
    assert not access.release.requests


def test_attempts_are_owned_and_api_is_admin_only(access, database_session):
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: database_session
    app.dependency_overrides[get_access_service] = lambda: access
    result = access.create(database_session, "admin", uuid4(), "entry")
    identifier = result["attempt_id"]
    app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
        "other", None, ("admin",)
    )
    http = AsgiClient(app)
    assert http.get(f"/biometrics/access-attempts/{identifier}").status_code == 404
    for role in ("client", "instructor", "attendant"):
        app.dependency_overrides[get_authenticated_identity] = lambda: AuthenticatedIdentity(
            "other", None, (role,)
        )
        for method, path, body in [
            ("GET", f"/{identifier}", None),
            ("POST", "", {"command_id": str(uuid4()), "direction": "entry"}),
            ("POST", f"/{identifier}/capture", None),
            ("POST", f"/{identifier}/cancellation", {"command_id": str(uuid4())}),
        ]:
            assert (
                http.request(method, "/biometrics/access-attempts" + path, body).status_code == 403
            )
