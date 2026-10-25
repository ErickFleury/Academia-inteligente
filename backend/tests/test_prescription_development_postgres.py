"""Real PostgreSQL isolated persistence/concurrency; no live external providers."""

import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier, Lock
from uuid import uuid4

import pytest
from prescription_fixtures import valid_case
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker
from test_training_generation import create_client
from training_fixtures import instructor

from app.database import Base
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.prescription_development import (
    DevelopmentValidationRecord,
    IsolatedPrescriptionService,
)

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


@pytest.fixture
def prescription_sessions():
    schema = "test_prescription_" + uuid4().hex
    admin = create_engine(os.environ["DATABASE_URL"])
    with admin.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={
            "options": f"-csearch_path={schema} -clock_timeout=5000",
        },
    )
    try:
        Base.metadata.create_all(engine)
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def arrange(sessions):
    with sessions() as session:
        client = create_client(session, "prescription-dev-pg", "prescription-dev-pg@example.test")
        instructor(session)
        owner = client.id
    case = valid_case(owner)
    service = IsolatedPrescriptionService(
        client_ids={owner}, context_supplier=lambda: deepcopy(case)
    )
    identity = AuthenticatedIdentity("prescription-dev-pg", "client", ("client",))
    return owner, case, service, identity


def test_concurrent_same_request_creates_one_draft_and_one_immutable_trace(prescription_sessions):
    owner, case, service, identity = arrange(prescription_sessions)
    start, guard = Barrier(2), Lock()
    request_id, calls = uuid4(), []

    def writer(context):
        with guard:
            calls.append(True)
        candidate = case["candidate"].model_copy(deep=True)
        candidate.expected_revision = context["current_revision"]
        return candidate

    def run():
        with prescription_sessions() as session:
            start.wait(timeout=10)
            return service.generate(
                session,
                identity,
                client_id=owner,
                request_id=request_id,
                entry_point="initial",
                provider=writer,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: run(), range(2)))
    assert all(result["status"] == "accepted" for result in outcomes)
    assert outcomes[0]["version_id"] == outcomes[1]["version_id"]
    assert len(calls) == 1
    with prescription_sessions() as session:
        assert session.scalar(select(func.count()).select_from(TrainingPlanVersion)) == 1
        assert session.scalar(select(func.count()).select_from(DevelopmentValidationRecord)) == 1
        record = session.scalar(select(DevelopmentValidationRecord))
        assert (
            record.payload["input_snapshot_sha256"]
            == record.payload["typed_content"]["input_snapshot_sha256"]
        )


def test_database_error_rolls_back_draft_items_and_validation_record(
    prescription_sessions, monkeypatch
):
    owner, case, service, identity = arrange(prescription_sessions)
    with prescription_sessions() as session:
        with monkeypatch.context() as patch:
            patch.setattr(
                service,
                "_save_record",
                lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("trace-write failure")),
            )
            with pytest.raises(RuntimeError, match="trace-write"):
                service.generate(
                    session,
                    identity,
                    client_id=owner,
                    request_id=uuid4(),
                    entry_point="initial",
                    provider=lambda _: case["candidate"],
                )
    with prescription_sessions() as session:
        assert session.scalar(select(func.count()).select_from(TrainingPlanVersion)) == 0
        assert session.scalar(select(func.count()).select_from(DevelopmentValidationRecord)) == 0


def test_harness_refuses_ordinary_postgres_schema_before_client_access(prescription_sessions):
    owner, case, service, identity = arrange(prescription_sessions)
    # Explicitly change only this isolated test connection's schema; no production
    # table is queried because the development boundary must fail first.
    with prescription_sessions() as session:
        session.execute(text("SET LOCAL search_path=public"))
        with pytest.raises(PermissionError, match="development_scope"):
            service.generate(
                session,
                identity,
                client_id=owner,
                request_id=uuid4(),
                entry_point="initial",
                provider=lambda _: case["candidate"],
            )
