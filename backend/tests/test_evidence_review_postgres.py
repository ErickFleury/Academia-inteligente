"""Database-enforced independent identity and request idempotency, synthetic only."""

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from test_evidence_review import artifacts as artifacts
from test_evidence_review import judgment, seal
from test_training_review_postgres import sessions as sessions
from training_fixtures import instructor

from app.modules.identity.service import AuthenticatedIdentity
from app.modules.training import evidence_review as service
from app.modules.training.evidence_review_models import EvidenceJudgment, EvidenceSeal
from app.modules.training.evidence_review_schema import JudgmentInput, SealInput

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


def identity():
    return AuthenticatedIdentity("review-race", "", ("instructor",))


def test_same_person_cannot_race_both_independent_review_functions(sessions, artifacts):
    with sessions() as session:
        instructor(session, "review-race")
    ready = Barrier(2)

    def register(function):
        with sessions() as session:
            ready.wait(timeout=10)
            try:
                service.register_judgment(
                    session,
                    identity(),
                    "source:synthetic",
                    JudgmentInput.model_validate(judgment(artifacts, function=function)),
                )
                return "registered"
            except service.EvidenceReviewError as error:
                assert error.status == 409
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(register, ("methodological", "professional"))) == [
            "conflict",
            "registered",
        ]
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(EvidenceJudgment)) == 1


def test_same_seal_request_concurrently_creates_one_immutable_payload(sessions, artifacts):
    with sessions() as session:
        instructor(session, "review-race")
    data = SealInput.model_validate(seal(artifacts, request_id=str(uuid4())))
    ready = Barrier(2)

    def register(_):
        with sessions() as session:
            ready.wait(timeout=10)
            return service.register_seal(session, identity(), data)["id"]

    with ThreadPoolExecutor(max_workers=2) as workers:
        identifiers = list(workers.map(register, range(2)))
    assert identifiers[0] == identifiers[1]
    with sessions() as session:
        assert session.scalar(select(func.count()).select_from(EvidenceSeal)) == 1


def test_concurrent_replacements_keep_one_successor_and_preserve_original(sessions, artifacts):
    with sessions() as session:
        instructor(session, "review-race")
        original = service.register_judgment(
            session,
            identity(),
            "source:synthetic",
            JudgmentInput.model_validate(judgment(artifacts)),
        )
    ready = Barrier(2)

    def replace(_):
        with sessions() as session:
            data = JudgmentInput.model_validate(
                judgment(
                    artifacts,
                    decision="changes_requested",
                    supersedes_judgment_id=str(original["id"]),
                )
            )
            ready.wait(timeout=10)
            try:
                service.register_judgment(session, identity(), "source:synthetic", data)
                return "registered"
            except service.EvidenceReviewError as error:
                assert error.status == 409
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(replace, range(2))) == ["conflict", "registered"]
    with sessions() as session:
        rows = session.scalars(select(EvidenceJudgment)).all()
        assert len(rows) == 2 and sum(row.is_current for row in rows) == 1
        retained = session.get(EvidenceJudgment, original["id"])
        assert retained.payload == original["assessment"] and not retained.is_current
