import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select
from test_training_lifecycle import data
from test_training_review_postgres import sessions as sessions
from training_fixtures import instructor

from app.modules.clients.instructor_service import create_first_draft, search_clients
from app.modules.clients.models import Account, Client
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.service import TrainingLifecycleError

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


def test_postgres_accent_search_and_concurrent_first_draft(sessions):
    with sessions() as session:
        instructor(session, "one")
        instructor(session, "two")
        client = Client(name="João   da Conceição", account=Account(email="client@test.test"))
        session.add(client)
        session.commit()
        identifier = client.id
        result = search_clients(
            session,
            subject="one",
            search="  JOAO  da conceicao ",
            onboarding="all",
            training="all",
            responsibility="all",
            responsible=None,
            cursor=None,
            limit=20,
        )
        assert [item["id"] for item in result["items"]] == [str(identifier)]
    ready = Barrier(2)

    def create(actor):
        with sessions() as session:
            ready.wait(timeout=10)
            try:
                create_first_draft(session, identifier, actor, data())
                return "created"
            except TrainingLifecycleError:
                session.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(create, ["one", "two"])) == ["conflict", "created"]
    with sessions() as session:
        versions = session.scalars(select(TrainingPlanVersion)).all()
        assert len(versions) == 1 and versions[0].status == "proposal"
