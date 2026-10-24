import pytest

from app.modules.knowledge.service import population_weight


@pytest.mark.parametrize(
    "content,query",
    [
        ("For older adults, resistance training uses several sets.", "adult beginner training"),
        ("Guidelines for youth resistance training include supervision.", "adult training"),
        ("Novice older adults may progress to additional sets.", "adult beginner training"),
        ("Para gestantes, ajuste o treinamento.", "adultos saudaveis treinamento"),
        ("For experienced athletes, the competition program changes weekly.", "beginner program"),
        ("The client's classification is intermediate.", "beginner program"),
    ],
)
def test_plain_text_scope_mismatch_is_downranked(content, query):
    assert population_weight(content, query) < 1


@pytest.mark.parametrize(
    "content,query",
    [
        ("For older adults, resistance training uses several sets.", "older adult training"),
        ("Guidelines for youth resistance training include supervision.", "youth training"),
        ("Para gestantes, ajuste o treinamento.", "treino para gestantes"),
        ("For novice adults, select exercises for each muscle group.", "adult beginner training"),
        (
            "Adult beginners and experienced athletes can use these general principles.",
            "beginner program",
        ),
        ("Resistance training can improve strength.", "adult beginner training"),
    ],
)
def test_matching_and_general_scope_are_preserved(content, query):
    assert population_weight(content, query) == 1
