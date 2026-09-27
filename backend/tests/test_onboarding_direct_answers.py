"""Conversational shortcuts preserve provenance, unknowns and explicit confirmation."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from test_onboarding_conversations import database_session as database_session
from test_onboarding_conversations import extraction, scope_for

from app.integrations.ai import AiOnboardingExtractionResponse
from app.modules.onboarding.conversation_service import _QUESTIONS, OnboardingConversationService
from app.modules.onboarding.direct_answers import direct_extraction
from app.modules.onboarding.draft_service import OnboardingDraftValidationError
from app.modules.onboarding.models import OnboardingAiConversation, OnboardingAiMessage
from app.modules.onboarding.schema import OnboardingDraftUpdate


class EmptyProvider:
    def __init__(self):
        self.calls = 0

    def extract_onboarding(self, context):
        self.calls += 1
        return AiOnboardingExtractionResponse(onboarding={})


def interview(session, field="weight_kg"):
    drafts, scope = scope_for(session)
    values = extraction().onboarding | {field: None}
    drafts.save_draft(session, scope, OnboardingDraftUpdate(**values))
    provider = EmptyProvider()
    service = OnboardingConversationService(provider, drafts)
    service.state(session, scope)
    conversation = session.scalar(select(OnboardingAiConversation))
    session.add(
        OnboardingAiMessage(
            conversation_id=conversation.id, sequence=1, role="assistant", content=_QUESTIONS[field]
        )
    )
    session.commit()
    return service, drafts, scope, provider


def send(session, service, scope, message, request_id=None):
    return service.submit(session, scope, message=message, client_request_id=request_id or uuid4())


@pytest.mark.parametrize(
    "message",
    [
        "82",
        "estou com 82",
        "Eu estou com 82",
        "tenho 82",
        "atualmente estou com 82",
        "meu peso é 82",
        "82 quilos",
        "82 kilos",
        "82 kgs",
        "Na verdade, estou com 82",
    ],
)
def test_natural_weight_answers_are_fast_and_do_not_complete_onboarding(database_session, message):
    service, drafts, scope, provider = interview(database_session)
    result = send(database_session, service, scope, message)
    assert result.known_answers.weight_kg == 82
    assert result.known_answers.height_cm == 170
    assert result.completion_ready and provider.calls == 0
    assert drafts.get_or_create_draft(database_session, scope).status == "draft"


@pytest.mark.parametrize(
    "field,message,value",
    [
        ("height_cm", "tenho 1,80", 180),
        ("height_cm", "minha altura é 180", 180),
        ("height_cm", "180 cm", 180),
        ("uses_medications", "Não", False),
        ("training_experience", "Sou iniciante", "beginner"),
    ],
)
def test_focused_simple_answers_skip_provider(database_session, field, message, value):
    service, _, scope, provider = interview(database_session, field)
    result = send(database_session, service, scope, message)
    assert getattr(result.known_answers, field) == value
    assert provider.calls == 0


@pytest.mark.parametrize(
    "message",
    [
        "quero chegar a 82 kg",
        "meu amigo pesa 82 kg",
        "tenho 82 anos",
        "uso 82 mg",
        "82 lbs",
        "80 ou 82 kg",
        "-82 kg",
        "tenho 900 kg",
        "Tenho 82 kg?",
    ],
)
def test_unrelated_ambiguous_and_invalid_numbers_are_not_saved(database_session, message):
    service, _, scope, _ = interview(database_session)
    result = send(database_session, service, scope, message)
    assert result.known_answers.weight_kg is None and not result.completion_ready


def test_uncertain_measurement_requires_confirmation_and_survives_reload(database_session):
    service, drafts, scope, provider = interview(database_session)
    result = send(database_session, service, scope, "Acho que estou com 82 kg")
    assert not result.completion_ready and result.known_answers.weight_kg is None
    assert "Você quis dizer 82 kg?" in service.state(database_session, scope).messages[-1].content
    with pytest.raises(OnboardingDraftValidationError):
        drafts.complete_draft(database_session, scope)
    calls = provider.calls
    result = send(database_session, service, scope, "Sim")
    assert result.known_answers.weight_kg == 82 and result.completion_ready
    assert provider.calls == calls


def test_rejection_does_not_save_suggestion_and_new_value_resolves_only_that_field(
    database_session,
):
    service, _, scope, provider = interview(database_session)
    send(database_session, service, scope, "Acho que estou com 82 kg")
    calls = provider.calls
    result = send(database_session, service, scope, "Não")
    assert result.known_answers.weight_kg is None and provider.calls == calls
    result = send(database_session, service, scope, "estou com 83")
    assert result.known_answers.weight_kg == 83 and result.known_answers.height_cm == 170
    assert result.fallback_field is None


def test_repeated_failure_offers_direct_entry_without_duplicate_retry_count(database_session):
    service, _, scope, _ = interview(database_session)
    request_id = uuid4()
    first = send(database_session, service, scope, "80 ou 82 kg", request_id)
    assert first.fallback_field is None
    assert "mais de um número" in service.state(database_session, scope).messages[-1].content
    replay = send(database_session, service, scope, "80 ou 82 kg", request_id)
    assert replay.fallback_field is None
    second = send(database_session, service, scope, "não lembro")
    assert second.fallback_field == "weight_kg"
    assert service.state(database_session, scope).fallback_field == "weight_kg"
    fixed = send(database_session, service, scope, "Na verdade, meu peso é 82 kg")
    assert fixed.known_answers.weight_kg == 82 and fixed.fallback_field is None


def test_manual_edit_invalidates_unconfirmed_suggestion(database_session):
    service, drafts, scope, _ = interview(database_session)
    send(database_session, service, scope, "Acho que estou com 82 kg")
    drafts.save_draft(database_session, scope, OnboardingDraftUpdate(weight_kg=83))
    result = send(database_session, service, scope, "Sim")
    assert result.known_answers.weight_kg == 83


def test_mixed_free_text_keeps_model_path_for_additional_information():
    assert (
        direct_extraction("Tenho 82 kg e sinto dor no joelho", 2, _QUESTIONS["weight_kg"]) is None
    )
    assert (
        direct_extraction("Sim, uso um remédio de teste", 2, _QUESTIONS["uses_medications"]) is None
    )
    assert direct_extraction("82", 2, _QUESTIONS["height_cm"]).onboarding == {"height_cm": 82}
    assert direct_extraction("82", 1, "") is None


def test_ambiguous_measurements_without_a_preceding_question_are_not_selected():
    from app.modules.onboarding.answer_evidence import grounded_answers

    response = AiOnboardingExtractionResponse(
        onboarding={"weight_kg": 82},
        evidence={"weight_kg": {"message_sequence": 1, "quote": "80 ou 82 kg"}},
    )
    source = OnboardingAiMessage(sequence=1, role="user", content="80 ou 82 kg")
    result = grounded_answers(response, OnboardingDraftUpdate(), [source], latest_sequence=1)
    assert result.weight_kg is None


def test_confirmation_and_failure_counter_expire_with_interview(database_session):
    from datetime import UTC, datetime, timedelta

    service, _, scope, _ = interview(database_session)
    send(database_session, service, scope, "Acho que estou com 82 kg")
    conversation = database_session.scalar(select(OnboardingAiConversation))
    conversation.raw_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    database_session.commit()
    result = send(database_session, service, scope, "Sim")
    assert result.known_answers.weight_kg is None
    assert result.fallback_field is None and not result.completion_ready


def test_yes_cannot_accept_a_suggestion_that_was_not_the_displayed_question(database_session):
    service, _, scope, _ = interview(database_session, "height_cm")
    send(database_session, service, scope, "não lembro")
    send(database_session, service, scope, "Acho que meu peso é 82 kg")
    assert "Qual é a sua altura" in service.state(database_session, scope).messages[-1].content
    result = send(database_session, service, scope, "Sim")
    assert result.known_answers.weight_kg != 82 and result.known_answers.height_cm is None
