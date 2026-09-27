"""Actual PostgreSQL row-lock tests in a disposable, isolated test schema."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from test_training_lifecycle import client_id, data
from training_fixtures import instructor

from app.database import Base
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.service import TrainingLifecycleError, TrainingLifecycleService

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Explicit isolated PostgreSQL test opt-in required"
)


@pytest.fixture
def sessions():
    schema = "test_training_" + uuid4().hex
    admin = create_engine(os.environ["DATABASE_URL"])
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"options": f"-csearch_path={schema} -clock_timeout=5000"},
    )
    try:
        Base.metadata.create_all(engine)
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


@pytest.mark.parametrize("actions", [("save", "save"), ("save", "approve"), ("approve", "approve")])
def test_first_successful_write_wins_with_two_real_transactions(sessions, actions):
    lifecycle = TrainingLifecycleService()
    with sessions() as session:
        instructor(session, "one")
        instructor(session, "two")
        version = lifecycle.create_proposal(
            session, client_id=client_id(session), data=data(), created_by="ai", origin="ai"
        )
        version_id, plan_id = version.id, version.plan_id
    ready = Barrier(2)

    def write(index):
        with sessions() as session:
            # Both identity maps deliberately hold the original revision.
            stale = session.get(TrainingPlanVersion, version_id)
            expected = stale.revision
            ready.wait(timeout=10)
            try:
                options = dict(
                    plan_id=plan_id,
                    version_number=1,
                    actor=("one", "two")[index],
                    expected_revision=expected,
                )
                if actions[index] == "save":
                    lifecycle.revise(session, data=data(f"Saved {index}"), **options)
                else:
                    lifecycle.approve(session, **options)
                return "success"
            except TrainingLifecycleError:
                session.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(write, range(2)))
    assert sorted(results) == ["conflict", "success"]
    with sessions() as session:
        version = session.get(TrainingPlanVersion, version_id)
        assert version.revision == 2
        assert len(session.scalars(select(TrainingPlanVersion)).all()) == 1
