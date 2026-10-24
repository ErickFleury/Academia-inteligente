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
        "| Reps | Load | Reps | Load | Reps | Load | Reps | Load |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        + "| 10–12 | 40–50 | 10–12 | 40–50 | 10–12 | 40–50 | 10–12 | 40–50 |\n"
        * 3,
        "Table 1 summarizes the results.\n" + "Beginners can use two sets when appropriate.\n" * 10,
        "Starting Position\n" + "\n".join(f"{i}. Keep the body supported." for i in range(12)),
    ],
)
def test_readable_tables_and_procedures_are_not_excluded(content):
    from app.modules.knowledge.service import unusable_table

    assert not unusable_table(content)


def test_plan_expansion_follows_explicit_tables_within_active_version(setup):
    sessions, service, _ = setup
    version = upload(
        sessions,
        service,
        body=(
            "# General guidance\nBased on table 3.1 and table 3.2, choose the appropriate range.\n"
            "# Unrelated neighbor\nA different topic.\nTable 3.2 presents recommended rest.\n"
            "# Table 3.1\nBeginners: 2 sets of 10 repetitions, only after learning the movement.\n"
            "# Table 3.2\nRest: 90 seconds; increase rest if technique declines."
        ),
    )
    service.import_next(sessions)
    activate(sessions, service, version)
    with sessions() as session:
        seeds = service.search(session, "general guidance")
        seed = next(r for r in seeds if "Based on table" in r["content"])
        refs = service.expand_plan_context(session, [seed], limit=3)
        assert len(refs) == 3
        assert any("only after learning" in r["content"] for r in refs)
        assert any("increase rest" in r["content"] for r in refs)
        assert all(r["version_id"] == seed["version_id"] for r in refs)


def test_rest_interval_table_is_not_misread_as_exercise_duration():
    from app.modules.knowledge.prescription_evidence import source_parameters

    content = (
        "TABLE 7.2 Rest Interval Recommendations\nTraining goal | Rest interval length\n"
        "Strength | 2-5 min\nPower | 2-5 min\n"
        "Note: Increase rest if technique declines.\n"
        "A separate activity lasts 10 minutes.\n"
    )
    fields = source_parameters([{"passage_id": "R1", "content": content}])[0]
    assert (120.0, 300.0) in fields["rest_seconds"]
    assert (120.0, 300.0) not in fields["duration_seconds"]
    assert (600.0, 600.0) in fields["duration_seconds"]


@pytest.mark.parametrize("preloaded", [False, True])
def test_linked_table_preserves_nearby_prose_that_conditions_its_application(setup, preloaded):
    sessions, service, _ = setup
    version = upload(
        sessions,
        service,
        body=(
            "# Sample plan\nBased on table 3.1, select a dose.\n"
            "# Other material\nUnrelated background.\n"
            "# More background\nA different subject.\n"
            "# Introduction\nBefore using table 3.1, novices must learn proper technique.\n"
            "# Continuation\nModerate loads also build strength during this learning phase.\n"
            "# Table 3.1\nGoal-specific programming: two sets of ten repetitions.\n"
            "# Other text\nAn unrelated topic."
        ),
    )
    service.import_next(sessions)
    activate(sessions, service, version)
    with sessions() as session:
        seed = next(
            r for r in service.search(session, "sample plan") if "Based on table" in r["content"]
        )
        seeds = [seed]
        if preloaded:
            seeds.append(
                next(
                    r
                    for r in service.search(session, "goal specific programming")
                    if "Goal-specific programming" in r["content"]
                )
            )
        refs = service.expand_plan_context(session, seeds, limit=4)
        assert any("Goal-specific programming" in r["content"] for r in refs)
        assert any("novices must learn" in r["content"] for r in refs)
        assert any("Moderate loads also build strength" in r["content"] for r in refs)


def test_continued_table_recovers_its_example_scope(setup):
    sessions, service, _ = setup
    version = upload(
        sessions,
        service,
        body=(
            "# TABLE 4.2 Example program for endurance\nThis case is an endurance circuit.\n"
            "# Other material\nBackground text.\n"
            "# More background\nAnother subject.\n"
            "# TABLE 4.2 (continued)\nRest 30 seconds in this case."
        ),
    )
    service.import_next(sessions)
    activate(sessions, service, version)
    with sessions() as session:
        seed = next(
            r for r in service.search(session, "rest seconds") if "(continued)" in r["content"]
        )
        refs = service.expand_plan_context(session, [seed], limit=2)
        assert any("This case is an endurance circuit" in r["content"] for r in refs)


def test_compound_exercise_queries_do_not_promote_unrequested_shared_words(setup):
    sessions, service, _ = setup
    for title, count in (
        ("Seated Barbell Shoulder Press", 12),
        ("Incline Barbell Bench Press", 3),
        ("Flat Barbell Bench Press", 3),
        ("Seated Leg Press", 1),
        ("Seated Row", 1),
    ):
        version = upload(
            sessions,
            service,
            body="\n".join(
                f"# {title}\nStarting Position: set up for {title}. Move slowly. Step {i}."
                for i in range(count)
            ),
        )
        service.import_next(sessions)
        activate(sessions, service, version)
    with sessions() as session:
        hits = service.search(
            session, "barbell bench press leg press seated row technique", prefer_technique=True
        )
    headings = [r["content"].split("\n")[0] for r in hits]
    assert not any("Shoulder" in title for title in headings)
    assert all(
        any(subject in title for title in headings)
        for subject in ("Flat Barbell Bench Press", "Seated Leg Press", "Seated Row")
    )


def test_compound_coverage_retains_an_explicit_subject_outside_known_aliases(setup):
    sessions, service, _ = setup
    for title in ("Pallof Press", "Bench Press", "Seated Shoulder Press"):
        version = upload(
            sessions,
            service,
            body=f"# {title}\nStarting Position: stand still. Movement: control {title}.",
        )
        service.import_next(sessions)
        activate(sessions, service, version)
    with sessions() as session:
        hits = service.search(session, "bench press pallof press technique", prefer_technique=True)
    assert any("Pallof Press" in row["content"].split("\n")[0] for row in hits)


def test_dense_broken_table_continuation_without_caption_is_excluded():
    from app.modules.knowledge.service import unusable_table

    content = (
        "Reps VL TI Reps VL TI Reps VL TI Reps VL TI\n"
        + ("1 120 18150 151 180 24750 138 120 16800 140 180 22200 123\n" * 4)
        + "Reps = repetitions; VL = volume load.\nGeneral discussion continues below."
    )
    assert unusable_table(content)
