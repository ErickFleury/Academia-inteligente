import asyncio
from datetime import timedelta
from io import BytesIO
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from PIL import Image, PngImagePlugin
from sqlalchemy import select
from test_clients import (
    AsgiClient,
    FakeProvisioner,
    authenticate_as,
    client_data,
)
from test_clients import (
    database_session as database_session,
)

from app.database import get_database_session
from app.main import create_app
from app.modules.biometrics.config import BiometricConfig, BiometricError
from app.modules.biometrics.enrollment import EnrollmentService, enrollment_status, utcnow
from app.modules.biometrics.images import MAX_CAPTURE_BYTES, normalize_capture, read_capture
from app.modules.biometrics.models import (
    BiometricCleanupJob,
    BiometricCommand,
    BiometricEnrollment,
    BiometricLock,
    EnrollmentSession,
)
from app.modules.biometrics.provider import Candidate, Face
from app.modules.biometrics.router import get_enrollment_service
from app.modules.clients.models import Account, Client
from app.modules.clients.service import ClientService, validate_client_data
from app.modules.occupancy.models import ClientAccessReference


class FakeFaces:
    def __init__(self):
        self.faces = (Face(0.99, ()),)
        self.enrolled = []
        self.deleted = []
        self.failure = None

    def inspect(self, image):
        return self.faces

    def enroll(self, subject, image):
        self.enrolled.append(subject)
        if self.failure:
            raise BiometricError("provider_unavailable", 503)

    def delete(self, subject):
        if self.failure:
            raise BiometricError("provider_unavailable", 503)
        self.deleted.append(subject)

    def ready(self):
        if self.failure:
            raise BiometricError("provider_unavailable", 503)


@pytest.fixture
def service(database_session):
    database_session.add(BiometricLock(id=1))
    database_session.commit()
    return EnrollmentService(BiometricConfig(mode="pilot", api_key="fixture"), FakeFaces())


def stage(service, session, **kwargs):
    result = service.create(
        session,
        "admin",
        uuid4(),
        email="ada@example.test",
        cpf="52998224725",
        role=kwargs.pop("role", "client"),
        **kwargs,
    )
    identifier = UUID(result["session_id"])
    service.capture(session, "admin", identifier, uuid4(), b"synthetic-adapter-fixture")
    return identifier


def enrolled_person(service, session):
    # Legacy fixture insertion only. Task 40 wires the mandatory transaction guard.
    result = ClientService(FakeProvisioner()).create(session, validate_client_data(**client_data()))
    account_id = session.get(Client, result.id).account_id
    identifier = stage(service, session)
    service.attach(
        session,
        account_id=account_id,
        email="ada@example.test",
        cpf="52998224725",
        role="client",
        actor="admin",
        session_id=identifier,
    )
    session.commit()
    return account_id


def test_ready_staging_is_not_a_person_and_is_owned_and_single_use(service, database_session):
    identifier = stage(service, database_session)
    assert database_session.scalars(select(Account)).all() == []
    assert database_session.scalars(select(BiometricEnrollment)).all() == []
    with pytest.raises(BiometricError, match="session_not_found"):
        service.capture(database_session, "another-admin", identifier, uuid4(), b"fixture")
    database_session.rollback()
    with pytest.raises(BiometricError, match="session_not_capturable"):
        service.capture(database_session, "admin", identifier, uuid4(), b"fixture")
    assert len(service.provider.enrolled) == 1


@pytest.mark.parametrize(
    "faces,code",
    [
        ((), "no_face"),
        ((Face(0.99, ()), Face(0.99, ())), "multiple_faces"),
        ((Face(0.5, ()),), "face_quality_low"),
        ((Face(0.99, (Candidate("other-person", 0.99),)),), "face_identity_conflict"),
    ],
)
def test_bad_capture_creates_no_person_or_provider_enrollment(
    service, database_session, faces, code
):
    service.provider.faces = faces
    identifier = stage(service, database_session)
    assert database_session.get(EnrollmentSession, identifier).result_code == code
    assert service.provider.enrolled == []
    assert database_session.scalars(select(Client)).all() == []


def test_timeout_is_not_success_replay_does_not_repeat_and_cleanup_retries(
    service, database_session
):
    service.provider.failure = True
    identifier = stage(service, database_session)
    row = database_session.get(EnrollmentSession, identifier)
    assert row.status == "rejected"
    assert (
        service.capture(database_session, "admin", identifier, row.capture_command_id, b"again")[
            "result_code"
        ]
        == "provider_unavailable"
    )
    assert len(service.provider.enrolled) == 1
    database_session.rollback()
    job = database_session.scalar(select(BiometricCleanupJob))
    job.due_at = utcnow() - timedelta(seconds=1)
    database_session.commit()
    service.cleanup(database_session)
    assert job.attempts == 1 and job.last_code == "cleanup_pending"
    service.provider.failure = False
    job.due_at = utcnow() - timedelta(seconds=1)
    database_session.commit()
    service.cleanup(database_session)
    assert service.provider.deleted == service.provider.enrolled
    assert database_session.scalars(select(BiometricCleanupJob)).all() == []


def test_registration_rollback_preserves_cleanup_and_stage(service, database_session):
    identifier = stage(service, database_session)
    row = database_session.get(EnrollmentSession, identifier)
    row.expires_at = utcnow() - timedelta(seconds=1)
    job = database_session.scalar(select(BiometricCleanupJob))
    job.due_at = row.expires_at
    database_session.commit()
    service.cleanup(database_session)
    assert row.status == "expired"
    assert service.provider.deleted == service.provider.enrolled


def test_replacement_failure_preserves_old_then_atomic_swap_and_revoke(service, database_session):
    account_id = enrolled_person(service, database_session)
    old = database_session.get(BiometricEnrollment, account_id).subject
    service.provider.faces = (Face(0.99, (Candidate(old, 0.99),)),)
    service.provider.failure = True
    failed = stage(
        service, database_session, role="replacement", person_id=account_id, expected_revision=1
    )
    with pytest.raises(BiometricError, match="enrollment_not_ready"):
        service.replace(database_session, "admin", account_id, uuid4(), failed, 1)
    database_session.rollback()
    assert database_session.get(BiometricEnrollment, account_id).subject == old
    service.provider.failure = False
    ready = stage(
        service, database_session, role="replacement", person_id=account_id, expected_revision=1
    )
    command_id = uuid4()
    result = service.replace(database_session, "admin", account_id, command_id, ready, 1)
    assert result["revision"] == 2 and result["cleanup_pending"]
    assert service.replace(database_session, "admin", account_id, command_id, ready, 1) == result
    database_session.rollback()
    new = database_session.get(BiometricEnrollment, account_id).subject
    assert new != old
    service.cleanup(database_session)
    assert old in service.provider.deleted and new not in service.provider.deleted
    revoke_id = uuid4()
    result = service.revoke(database_session, "admin", account_id, revoke_id, 2)
    assert result["revision"] == 3 and result["status"] == "missing_or_revoked"
    assert not database_session.scalar(select(ClientAccessReference)).active
    assert service.revoke(database_session, "admin", account_id, revoke_id, 2) == result


def test_replacement_stale_after_revocation_never_reenables(service, database_session):
    account_id = enrolled_person(service, database_session)
    ready = stage(
        service, database_session, role="replacement", person_id=account_id, expected_revision=1
    )
    service.revoke(database_session, "admin", account_id, uuid4(), 1)
    with pytest.raises(BiometricError, match="enrollment_stale"):
        service.replace(database_session, "admin", account_id, uuid4(), ready, 1)
    database_session.rollback()
    assert enrollment_status(database_session, account_id)["status"] == "missing_or_revoked"


def test_command_cannot_be_repurposed_or_taken_by_another_operator(service, database_session):
    command_id = uuid4()
    arguments = dict(email="ada@example.test", cpf="52998224725", role="client")
    first = service.create(database_session, "admin", command_id, **arguments)
    assert service.create(database_session, "admin", command_id, **arguments) == first
    database_session.rollback()
    with pytest.raises(BiometricError, match="command_conflict"):
        service.create(database_session, "other-admin", command_id, **arguments)
    database_session.rollback()
    with pytest.raises(BiometricError, match="command_conflict"):
        service.create(database_session, "admin", command_id, **(arguments | {"role": "employee"}))


def test_interrupted_capture_recovers_after_restart(service, database_session):
    identifier = stage(service, database_session)
    row = database_session.get(EnrollmentSession, identifier)
    row.status = "capturing"
    row.capture_until = utcnow() - timedelta(seconds=1)
    database_session.commit()
    restarted = EnrollmentService(service.config, service.provider)
    restarted.cleanup(database_session)
    assert row.result_code == "capture_interrupted"
    assert service.provider.deleted == service.provider.enrolled


def test_shared_role_reuses_enrollment_without_second_provider_call(service, database_session):
    account_id = enrolled_person(service, database_session)
    service.attach(
        database_session,
        account_id=account_id,
        email="ada@example.test",
        cpf="52998224725",
        role="employee",
        actor="admin",
        session_id=None,
    )
    assert len(service.provider.enrolled) == 1
    assert database_session.get(BiometricEnrollment, account_id).revision == 1


def test_expired_session_cleanup_waits_for_inflight_capture(service, database_session):
    identifier = stage(service, database_session)
    row = database_session.get(EnrollmentSession, identifier)
    row.status = "capturing"
    row.expires_at = utcnow() - timedelta(seconds=1)
    row.capture_until = utcnow() + timedelta(seconds=30)
    job = database_session.get(BiometricCleanupJob, row.subject)
    job.due_at = row.capture_until
    database_session.commit()
    service.cleanup(database_session)
    assert not service.provider.deleted
    assert row.status == "capturing"


def test_late_response_cannot_overwrite_recovered_capture(service, database_session):
    result = service.create(
        database_session,
        "admin",
        uuid4(),
        email="ada@example.test",
        cpf="52998224725",
        role="client",
    )
    identifier = UUID(result["session_id"])
    newer_command = uuid4()

    def late_enroll(subject, image):
        row = database_session.get(EnrollmentSession, identifier)
        row.capture_command_id = newer_command
        row.status = "capturing"
        row.result_code = "processing"
        row.capture_until = utcnow() + timedelta(seconds=60)
        database_session.get(BiometricLock, 1).capture_until = row.capture_until
        database_session.commit()

    service.provider.enroll = late_enroll
    result = service.capture(database_session, "admin", identifier, uuid4(), b"fixture")
    assert result["result_code"] == "capture_superseded"
    row = database_session.get(EnrollmentSession, identifier)
    assert row.status == "capturing" and row.capture_command_id == newer_command
    assert database_session.get(BiometricLock, 1).capture_until is not None


@pytest.mark.parametrize("roles", [("client",), ("instructor",), ("attendant",), ()])
def test_all_biometric_routes_deny_non_admins(monkeypatch, database_session, service, roles):
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: database_session
    app.dependency_overrides[get_enrollment_service] = lambda: service
    authenticate_as(monkeypatch, *roles)
    client = AsgiClient(app)
    identifier = str(uuid4())
    for method, path, body in [
        (
            "POST",
            "/enrollment-sessions",
            {"command_id": identifier, "email": "a@b.test", "cpf": "52998224725", "role": "client"},
        ),
        ("GET", f"/enrollment-sessions/{identifier}", None),
        ("POST", f"/enrollment-sessions/{identifier}/capture", None),
        ("GET", f"/people/{identifier}/enrollment", None),
        (
            "POST",
            f"/people/{identifier}/enrollment/replacement",
            {"command_id": identifier, "expected_revision": 0, "session_id": identifier},
        ),
        (
            "POST",
            f"/people/{identifier}/enrollment/revocation",
            {"command_id": identifier, "expected_revision": 0},
        ),
    ]:
        assert client.request(method, "/biometrics" + path, body).status_code in {401, 403}
    assert database_session.scalars(select(BiometricCommand)).all() == []


def test_bad_identity_and_disabled_mode_are_controlled(monkeypatch, database_session, service):
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: database_session
    app.dependency_overrides[get_enrollment_service] = lambda: service
    authenticate_as(monkeypatch, "admin")
    client = AsgiClient(app)
    payload = dict(
        command_id=str(uuid4()), email="ada@example.test", cpf="11111111111", role="client"
    )
    assert client.post("/biometrics/enrollment-sessions", payload).status_code == 422
    app.dependency_overrides[get_enrollment_service] = lambda: EnrollmentService(BiometricConfig())
    assert client.post("/biometrics/enrollment-sessions", payload).status_code == 503


def png():
    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("private", "must disappear")
    Image.new("RGB", (40, 40)).save(output, "PNG", pnginfo=metadata)
    return output.getvalue()


def test_normalization_strips_metadata_and_rejects_malformed_large_or_animated_images():
    clean = normalize_capture(png())
    assert b"must disappear" not in clean
    assert Image.open(BytesIO(clean)).format == "JPEG"
    oversized = BytesIO()
    Image.new("RGB", (4097, 1)).save(oversized, "PNG")
    for capture in [b"not image", b"x" * (MAX_CAPTURE_BYTES + 1), oversized.getvalue()]:
        with pytest.raises(BiometricError):
            normalize_capture(capture)


def test_multipart_capture_is_bounded_and_does_not_accept_extra_fields():
    command_id = uuid4()
    body = (
        (
            f'--test\r\nContent-Disposition: form-data; name="command_id"\r\n\r\n{command_id}\r\n'
            '--test\r\nContent-Disposition: form-data; name="file"; filename="capture.png"\r\n'
            "Content-Type: image/png\r\n\r\n"
        ).encode()
        + png()
        + b"\r\n--test--\r\n"
    )

    def request(raw):
        async def receive():
            return {"type": "http.request", "body": raw, "more_body": False}

        return Request(
            {"type": "http", "headers": [(b"content-type", b"multipart/form-data; boundary=test")]},
            receive,
        )

    assert asyncio.run(read_capture(request(body)))[0] == command_id
    for invalid in [
        b"x" * (MAX_CAPTURE_BYTES + 8193),
        body.replace(b'name="file"', b'name="score"'),
    ]:
        with pytest.raises(BiometricError):
            asyncio.run(read_capture(request(invalid)))
