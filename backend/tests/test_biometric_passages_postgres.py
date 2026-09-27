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
from test_biometric_access import known_client, recognize
from test_biometric_access_postgres import services
from test_training_review_postgres import sessions as sessions

from app.modules.biometrics.config import BiometricError
from app.modules.biometrics.passages import PassageService
from app.modules.occupancy.models import AccessPassageEvent, OccupancyCorrection
from app.modules.occupancy.service import OccupancyService

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


def setup(sessions):
    enrollment, access = services()
    passages = PassageService(access.config, access.provider)
    with sessions() as session:
        _, client_id = known_client(session, enrollment, access)
        first = UUID(recognize(access, session, actor="first")["attempt_id"])
        second = UUID(recognize(access, session, actor="second")["attempt_id"])
    return passages, client_id, first, second


def test_migration_roundtrip(sessions):
    spec = importlib.util.spec_from_file_location(
        "passage_migration", Path("alembic/versions/20260927_28_pilot_passage_corrections.py")
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with sessions() as session:
        migration.op = Operations(MigrationContext.configure(session.connection()))
        migration.downgrade()
        migration.upgrade()
        session.commit()
        assert session.scalars(select(OccupancyCorrection)).all() == []


def test_history_pagination_on_postgres(sessions):
    from test_biometric_history import verify_pagination

    enrollment, access = services()
    with sessions() as session:
        verify_pagination(session, enrollment, access)


@pytest.mark.parametrize("second_action", ["confirm", "correct"])
def test_competing_commands_cannot_apply_two_transitions(sessions, second_action):
    passages, client_id, first, second = setup(sessions)
    barrier = Barrier(2)

    def change(index):
        with sessions() as session:
            barrier.wait(timeout=10)
            try:
                if index == 1 and second_action == "correct":
                    passages.correct(
                        session, "second", uuid4(), client_id, True, 0, "Entrada omitida"
                    )
                else:
                    passages.confirm(
                        session,
                        "first" if index == 0 else "second",
                        first if index == 0 else second,
                        uuid4(),
                    )
                return "success"
            except BiometricError:
                session.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(change, range(2))) == ["conflict", "success"]
    with sessions() as session:
        assert OccupancyService().snapshot(session).occupancy == 1
        assert passages.state(session, client_id)["revision"] == 1
        assert (
            len(session.scalars(select(AccessPassageEvent)).all())
            + len(session.scalars(select(OccupancyCorrection)).all())
            == 1
        )


def test_concurrent_replay_of_one_confirmation_is_idempotent(sessions):
    passages, client_id, first, _ = setup(sessions)
    barrier = Barrier(2)
    command_id = uuid4()

    def confirm(_):
        with sessions() as session:
            barrier.wait(timeout=10)
            return passages.confirm(session, "first", first, command_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(confirm, range(2)))
    assert results[0] == results[1]
    with sessions() as session:
        assert len(session.scalars(select(AccessPassageEvent)).all()) == 1
        assert passages.state(session, client_id)["inside"]
