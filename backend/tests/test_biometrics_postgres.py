"""Real database lock/rollback evidence; provider calls remain synthetic."""

import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select
from test_biometrics_enrollment import FakeFaces, enrolled_person, stage
from test_clients import FakeProvisioner, client_data
from test_training_review_postgres import sessions as sessions

from app.modules.biometrics.config import BiometricConfig, BiometricError
from app.modules.biometrics.enrollment import EnrollmentService
from app.modules.biometrics.models import (
    BiometricCleanupJob,
    BiometricCommand,
    BiometricEnrollment,
    BiometricLock,
    EnrollmentSession,
)
from app.modules.biometrics.registration import RegistrationService
from app.modules.clients.models import Account, Client
from app.modules.clients.service import ClientService, validate_client_data

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


@pytest.fixture
def service(sessions):
    return EnrollmentService(BiometricConfig(mode="pilot", api_key="fixture"), FakeFaces())


def test_migration_round_trip_seeds_lock(sessions):
    specification = importlib.util.spec_from_file_location(
        "biometrics_migration", Path("alembic/versions/20260927_26_biometric_enrollment.py")
    )
    migration = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(migration)
    with sessions() as session:
        migration.op = Operations(MigrationContext.configure(session.connection()))
        migration.downgrade()
        migration.upgrade()
        session.commit()
        assert session.get(BiometricLock, 1) is not None


def test_same_command_concurrently_creates_one_staging_session(sessions, service):
    command_id = uuid4()
    barrier = Barrier(2)

    def create(_):
        with sessions() as session:
            barrier.wait(timeout=10)
            result = service.create(
                session,
                "admin",
                command_id,
                email="ada@example.test",
                cpf="52998224725",
                role="client",
            )
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, range(2)))
    assert results[0] == results[1]
    with sessions() as session:
        assert len(session.scalars(select(EnrollmentSession)).all()) == 1
        assert len(session.scalars(select(BiometricCommand)).all()) == 1


def test_two_revocations_with_stale_identity_maps_cannot_both_commit(sessions, service):
    with sessions() as session:
        person_id = enrolled_person(service, session)
    barrier = Barrier(2)

    def revoke(_):
        with sessions() as session:
            session.get(BiometricEnrollment, person_id)
            barrier.wait(timeout=10)
            try:
                service.revoke(session, "admin", person_id, uuid4(), 1)
                return "success"
            except BiometricError as error:
                session.rollback()
                return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(revoke, range(2))) == ["enrollment_stale", "success"]
    with sessions() as session:
        assert session.get(BiometricEnrollment, person_id).revision == 2


def test_local_attach_rollback_does_not_lose_precommitted_cleanup(sessions, service):
    with sessions() as session:
        person_id = enrolled_person(service, session)
        identifier = stage(
            service, session, role="replacement", person_id=person_id, expected_revision=1
        )
        staged = session.get(EnrollmentSession, identifier).subject
    with sessions() as session:
        service.attach(
            session,
            account_id=person_id,
            email="ada@example.test",
            cpf="52998224725",
            role="replacement",
            actor="admin",
            session_id=identifier,
        )
        session.flush()
        session.rollback()
    with sessions() as session:
        assert session.get(BiometricEnrollment, person_id).revision == 1
        assert session.get(EnrollmentSession, identifier).status == "ready"
        assert session.get(BiometricCleanupJob, staged) is not None


def test_capture_lease_prevents_two_tabs_enrolling_during_one_provider_write(sessions, service):
    with sessions() as session:
        result = service.create(
            session, "admin", uuid4(), email="ada@example.test", cpf="52998224725", role="client"
        )
        identifier = UUID(result["session_id"])
    inside = Barrier(2)
    finished = Barrier(2)
    original = service.provider.enroll

    def blocked_enroll(subject, image):
        inside.wait(timeout=10)
        finished.wait(timeout=10)
        original(subject, image)

    service.provider.enroll = blocked_enroll

    def capture():
        with sessions() as session:
            return service.capture(session, "admin", identifier, uuid4(), b"fixture")

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(capture)
        inside.wait(timeout=10)
        try:
            with sessions() as session:
                with pytest.raises(BiometricError, match="session_not_capturable"):
                    service.capture(session, "admin", identifier, uuid4(), b"fixture")
                session.rollback()
        finally:
            finished.wait(timeout=10)
        assert future.result(timeout=10)["status"] == "ready"
    assert len(service.provider.enrolled) == 1


def test_registration_retry_creates_one_role_and_erasure_removes_foreign_keys(sessions, service):
    with sessions() as session:
        stage_id = stage(service, session)
    barrier = Barrier(2)
    command_id = uuid4()
    clients = ClientService(FakeProvisioner())

    def register(_):
        with sessions() as session:
            barrier.wait(timeout=10)
            return (
                RegistrationService(service)
                .create(
                    session,
                    actor="admin",
                    command_id=command_id,
                    enrollment_session_id=stage_id,
                    role="client",
                    data=validate_client_data(**client_data()),
                    service=clients,
                )
                .id
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(register, range(2)))
    assert results[0] == results[1]
    with sessions() as session:
        assert len(session.scalars(select(Client)).all()) == 1
        assert clients.erase(session, results[0])
        assert session.scalars(select(Account)).all() == []
        assert session.scalars(select(EnrollmentSession)).all() == []
        service.cleanup(session)
        assert session.scalars(select(BiometricCleanupJob)).all() == []
