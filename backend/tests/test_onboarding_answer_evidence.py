from uuid import uuid4

import pytest

from app.integrations.ai import AiOnboardingExtractionResponse
from app.modules.onboarding.answer_evidence import grounded_answers
from app.modules.onboarding.models import Onboarding, OnboardingAiMessage


def result(field, value, answer, *, question="", quote=None, role="user"):
    messages = [
        OnboardingAiMessage(sequence=1, role="assistant", content=question),
        OnboardingAiMessage(sequence=2, role=role, content=answer),
    ]
    extraction = AiOnboardingExtractionResponse(
        onboarding={field: value},
        evidence={field: {"message_sequence": 2, "quote": quote or answer}},
    )
    draft = Onboarding(client_id=uuid4(), status="draft")
    return getattr(grounded_answers(extraction, draft, messages), field)


@pytest.mark.parametrize(
    "field,value,answer,question",
    [
        ("height_cm", 175, "1,75 m", ""),
        ("height_cm", 175, "1,75", "Qual é sua altura?"),
        ("weight_kg", 70.5, "70,5 kg", ""),
        ("weight_kg", 70.5, "70,5", "Qual é seu peso?"),
        ("training_experience", "beginner", "Sou iniciante", ""),
        ("training_experience", "none", "Nenhuma", "Qual é sua experiência de treino?"),
        ("uses_medications", False, "Não", "Você usa algum medicamento?"),
        ("uses_medications", True, "Sim", "Você usa algum medicamento?"),
        ("has_health_conditions", False, "Não tenho condições de saúde", ""),
        ("medications", "Relato de teste", "Relato de teste", "Quais medicamentos você usa?"),
    ],
)
def test_accepts_supported_answers_and_unit_normalization(field, value, answer, question):
    assert result(field, value, answer, question=question) == value


@pytest.mark.parametrize(
    "field,value,answer,question",
    [
        ("height_cm", 175, "Quero ganhar força", "Qual é seu objetivo?"),
        ("height_cm", 175, "170 cm", ""),
        ("height_cm", 175, "175 kg", ""),
        ("weight_kg", 70, "70", "Qual é sua altura?"),
        ("training_experience", "beginner", "Quero ganhar força", ""),
        ("uses_medications", False, "Quero ganhar força", ""),
        ("uses_medications", False, "Não sei", "Você usa algum medicamento?"),
        ("has_health_conditions", False, "Não", "Você usa algum medicamento?"),
        ("has_limitations_or_complaints", False, "Não", "Você usa algum medicamento?"),
        ("health_conditions", "Doença inventada", "Relato original", "Quais condições de saúde?"),
    ],
)
def test_rejects_invented_ambiguous_or_unrelated_answers(field, value, answer, question):
    assert result(field, value, answer, question=question) is None


def test_rejects_assistant_claims_and_nonexistent_user_quotes():
    assert result("height_cm", 175, "175 cm", role="assistant") is None
    assert result("height_cm", 175, "Quero ganhar força", quote="175 cm") is None


def test_absent_health_flags_stay_unknown_instead_of_becoming_negative():
    draft = Onboarding(client_id=uuid4(), status="draft")
    response = AiOnboardingExtractionResponse(onboarding={"uses_medications": None})
    assert grounded_answers(response, draft, []).uses_medications is None


def test_health_negation_does_not_apply_to_another_clause():
    answer = "Não uso medicamentos e tenho uma condição de saúde."
    assert result("uses_medications", False, answer) is False
    assert result("has_health_conditions", False, answer) is True
    assert result("has_health_conditions", True, answer) is True


def test_short_experience_answer_cannot_be_taken_from_a_health_question():
    assert (
        result("training_experience", "none", "Nenhuma", question="Quais condições de saúde?")
        is None
    )


def test_canonical_categories_follow_client_words_instead_of_model_guesses():
    assert result("training_experience", "intermediate", "Sou iniciante.") == "beginner"
    assert (
        result("has_limitations_or_complaints", None, "Não tenho limitações ou queixas.") is False
    )


def test_citation_cannot_drop_a_negation_or_turn_a_target_into_current_weight():
    assert (
        result("uses_medications", True, "Não uso medicamentos.", quote="uso medicamentos") is False
    )
    assert result("weight_kg", 70, "Quero chegar a 70 kg.", quote="70 kg") is None
    assert result("height_cm", 175, "Não tenho 175 cm.", quote="175 cm") is None
    assert (
        result("training_experience", "beginner", "Não sou iniciante.", quote="iniciante") is None
    )
