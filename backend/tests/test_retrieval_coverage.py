"""Multi-exercise coverage and unreadable-table exclusion at the real retrieval seam."""

import os

import pytest
from sqlalchemy import select
from test_knowledge import FakeEmbedding, activate, upload
from test_knowledge import setup as setup
from test_knowledge_postgres import postgres_sessions as postgres_sessions

from app.modules.knowledge.models import ReferencePassage
from app.modules.knowledge.service import KnowledgeService

QUERY = "bench press leg press seated row shoulder press beginner technique execution"
CORRUPT = (
    "TABLE 8 Sample loading structures\nType Repetition Loading\n"
    + "80/1 8022 8012 | |\n1 13 x 10/2 15\n851 8012 T5/1\n" * 5
    + "Note: progression depends on the client."
)


def coverage_fixture(setup):
    sessions, service, provider = setup
    # Higher-ranked repeated shoulder instructions must not crowd out all the
    # other explicitly requested exercises, even beyond the old candidate cap.
    for title, count in (
        ("Seated Barbell Shoulder Press", 24),
        ("Flat Bench Press", 1),
        ("Leg Press", 1),
        ("Seated Row", 1),
    ):
        body = "\n".join(
            f"# {title}\nStarting Position: set up for {title}. "
            f"Movement step {i}: move slowly under control."
            for i in range(count)
        )
        version = upload(sessions, service, body=body)
        service.import_next(sessions)
        activate(sessions, service, version)
    with sessions() as session:
        # Give the repeated subject a slightly better semantic distance.
        for row in session.scalars(select(ReferencePassage)):
            row.embedding = [0.0, 1.0] if "Shoulder" in row.content else [0.2, 1.0]
        session.commit()
        calls = len(provider.calls)
        hits = service.search(session, QUERY, prefer_technique=True)
        headings = {row["content"].split("\n", 1)[0] for row in hits}
        assert all(
            any(title in heading for heading in headings)
            for title in ("Shoulder Press", "Flat Bench Press", "Leg Press", "Seated Row")
        )
        assert len(hits) == 5
        assert len(provider.calls) == calls + 1
        provider.fail = True
        hits = service.search(session, QUERY, prefer_technique=True)
        headings = {row["content"].split("\n", 1)[0] for row in hits}
        assert all(
            any(title in heading for heading in headings)
            for title in ("Shoulder Press", "Flat Bench Press", "Leg Press", "Seated Row")
        )


def test_multiple_exercises_survive_repeated_sections(setup):
    coverage_fixture(setup)


@pytest.mark.skipif(os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in")
def test_multiple_exercises_survive_postgres_candidate_limits(postgres_sessions):
    provider = FakeEmbedding()
    coverage_fixture((postgres_sessions, KnowledgeService(provider), provider))


def test_corrupt_table_is_excluded_from_search_and_neighbors(setup):
    sessions, service, _ = setup
    version = upload(
        sessions,
        service,
        body=(
            "# Beginner programming\nBeginners use two sets of ten repetitions.\n"
            "# Loading table\n" + CORRUPT + "\n"
            "# Programming notes\nOnly progress when technique remains controlled."
        ),
    )
    service.import_next(sessions)
    activate(sessions, service, version)
    with sessions() as session:
        hits = service.search(session, "loading table repetition structures")
        assert all("80/1 8022" not in row["content"] for row in hits)
        seed = service.search(session, "beginner programming")[0]
        expanded = service.expand_plan_context(session, [seed])
        assert all("80/1 8022" not in row["content"] for row in expanded)
        assert (
            session.scalar(
                select(ReferencePassage).where(ReferencePassage.content.contains("80/1 8022"))
            )
            is not None
        )


@pytest.mark.parametrize(
    "content",
    [
        "Table 1\nExercise Sets Repetitions Rest\n" + "Squat 2 10 60\n" * 10,
        "Table 1\n| Sets | Reps | Rest |\n| --- | --- | --- |\n" + "| 2 | 10 | 60 |\n" * 10,
        "Table 1 summarizes the results.\n" + "Beginners can use two sets when appropriate.\n" * 10,
        "Starting Position\n" + "\n".join(f"{i}. Keep the body supported." for i in range(12)),
    ],
)
def test_readable_tables_and_procedures_are_not_excluded(content):
    from app.modules.knowledge.service import unusable_table

    assert not unusable_table(content)
