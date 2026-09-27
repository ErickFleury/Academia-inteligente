import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from test_training_lifecycle import client_id, data
from test_training_review_postgres import sessions as sessions
from training_fixtures import instructor

from app.modules.training.collections_service import clone_current
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.service import TrainingLifecycleError, TrainingLifecycleService

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


@pytest.mark.parametrize("action", ["save", "approve", "replace"])
def test_confirmation_races_preserve_the_first_committed_change(sessions, action):
    lifecycle = TrainingLifecycleService()
    with sessions() as session:
        instructor(session, "one")
        instructor(session, "two")
        current = lifecycle.create_proposal(
            session,
            client_id=client_id(session),
            data=data(),
            created_by="one",
            origin="instructor",
        )
        lifecycle.approve(
            session, plan_id=current.plan_id, version_number=1, actor="one", expected_revision=1
        )
        pending = clone_current(
            session,
            current.id,
            actor="one",
            expected_revision=2,
            discard_id=None,
            discard_revision=None,
        )
        current_id, pending_id, plan_id, number = (
            current.id,
            pending.id,
            current.plan_id,
            pending.version_number,
        )
    ready = Barrier(2)

    def write(index):
        with sessions() as session:
            session.get(TrainingPlanVersion, pending_id)
            ready.wait(timeout=10)
            try:
                if index == 0 or action == "replace":
                    clone_current(
                        session,
                        current_id,
                        actor="one",
                        expected_revision=2,
                        discard_id=pending_id,
                        discard_revision=1,
                    )
                elif action == "save":
                    lifecycle.revise(
                        session,
                        plan_id=plan_id,
                        version_number=number,
                        actor="two",
                        expected_revision=1,
                        data=data("Updated"),
                    )
                else:
                    lifecycle.approve(
                        session,
                        plan_id=plan_id,
                        version_number=number,
                        actor="two",
                        expected_revision=1,
                    )
                return "success"
            except TrainingLifecycleError:
                session.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(write, range(2))) == ["conflict", "success"]
