import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from test_biometric_access import ReleaseSpy, known_client, recognize
from test_biometrics_enrollment import FakeFaces
from test_training_review_postgres import sessions as sessions

from app.modules.biometrics.access import AccessService
from app.modules.biometrics.config import BiometricConfig
from app.modules.biometrics.enrollment import EnrollmentService
from app.modules.biometrics.models import RecognitionAttempt, ReleaseRequest

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


def services():
    config = BiometricConfig(mode="pilot", api_key="fixture")
    provider = FakeFaces()
    return EnrollmentService(config, provider), AccessService(config, provider, ReleaseSpy())


def test_migration_roundtrip_and_simulated_only_constraint(sessions):
    spec = importlib.util.spec_from_file_location(
        "access_migration", Path("alembic/versions/20260927_27_facial_recognition_release.py")
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    enrollment, access = services()
    with sessions() as session:
        migration.op = Operations(MigrationContext.configure(session.connection()))
        migration.downgrade()
        migration.upgrade()
        session.commit()
        known_client(session, enrollment, access)
        recognize(access, session)
        with pytest.raises(IntegrityError):
            session.execute(text("UPDATE biometric_release_request SET mode = 'live'"))
        session.rollback()


def test_concurrent_capture_replay_emits_one_release_and_one_capture(sessions):
    enrollment, access = services()
    with sessions() as session:
        known_client(session, enrollment, access)
        identifier = UUID(access.create(session, "admin", uuid4(), "entry")["attempt_id"])
    barrier = Barrier(2)
    command_id = uuid4()

    def scan(_):
        with sessions() as session:
            barrier.wait(timeout=10)
            return access.capture(session, "admin", identifier, command_id, b"fixture")

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(scan, range(2)))
    assert all(result["captures"] == 1 for result in results)
    assert any(result["status"] == "authorized" for result in results)
    assert len(access.release.requests) == 1
    with sessions() as session:
        assert session.get(RecognitionAttempt, identifier).captures == 1
        assert len(session.scalars(select(ReleaseRequest)).all()) == 1
