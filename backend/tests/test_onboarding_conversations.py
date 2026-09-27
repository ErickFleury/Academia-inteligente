from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.integrations.ai import (
    AiInterviewTurnResponse,
    AiOnboardingExtractionResponse,
    AiProviderError,
)
from app.modules.clients.models import Account, Client
from app.modules.equipment import models as equipment_models  # noqa: F401
from app.modules.onboarding.conversation_service import OnboardingConversationService
from app.modules.onboarding.draft_service import OnboardingDraftService
from app.modules.onboarding.models import OnboardingAiConversation, OnboardingAiMessage
from app.modules.onboarding.schema import OnboardingDraftUpdate


class FakeProvider:
    def __init__(
        self,
        turns: list[AiInterviewTurnResponse | Exception],
        extractions: list[AiOnboardingExtractionResponse | Exception] | None = None,
    ) -> None:
        self.turns, self.extractions = turns, extractions or []
        self.turn_contexts: list[dict[str, object]] = []
        self.extraction_contexts: list[dict[str, object]] = []

    def interview_turn(self, context: dict[str, object]) -> AiInterviewTurnResponse:
        self.turn_contexts.append(context)
        result = self.turns.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def extract_onboarding(self, context: dict[str, object]) -> AiOnboardingExtractionResponse:
        self.extraction_contexts.append(context)
        result = self.extractions.pop(0) if self.extractions else extraction()
        if isinstance(result, Exception):
            raise result
        return result


def turn(status: str = "in_progress") -> AiInterviewTurnResponse:
    return AiInterviewTurnResponse(
        assistant_message="Ótimo. Conte mais sobre sua experiência.", interview_status=status
    )


ANSWERS = {
    "training_goal": "Ganhar força",
    "training_experience": "Sou iniciante.",
    "height_cm": "Minha altura é 170 cm.",
    "weight_kg": "Peso 70,50 kg.",
    "has_limitations_or_complaints": "Não tenho limitações ou queixas.",
    "uses_medications": "Não uso medicamentos.",
    "has_health_conditions": "Não tenho condições de saúde.",
}


def extraction(*, with_evidence=False, **updates: object) -> AiOnboardingExtractionResponse:
    values: dict[str, object] = {
        "training_goal": "Ganhar força",
        "training_experience": "beginner",
        "height_cm": 170,
        "weight_kg": "70.50",
        "has_limitations_or_complaints": False,
        "limitations_or_complaints": None,
        "uses_medications": False,
        "medications": None,
        "has_health_conditions": False,
        "health_conditions": None,
    }
    values.update(updates)
    return AiOnboardingExtractionResponse(
        onboarding=values,
        evidence={
            field: {"message_sequence": 1, "quote": answer} for field, answer in ANSWERS.items()
        }
        if with_evidence
        else {},
    )


@pytest.fixture
def database_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def scope_for(session: Session):
    session.add(
        Client(
            name="Ada",
            account=Account(email="ada@example.test", keycloak_subject="ada", account_active=True),
        )
    )
    session.commit()
    drafts = OnboardingDraftService()
    return drafts, drafts.resolve_client_scope(session, "ada")


def test_normal_interview_turn_never_mutates_structured_draft_and_is_idempotent(
    database_session: Session,
) -> None:
    provider = FakeProvider([turn()])
    drafts, scope = scope_for(database_session)
    service = OnboardingConversationService(provider=provider, draft_service=drafts)
    request_id = uuid4()
    service.submit(
        database_session, scope, message="Quero ganhar força.", client_request_id=request_id
    )
    service.submit(
        database_session, scope, message="Quero ganhar força.", client_request_id=request_id
    )
    assert drafts.get_or_create_draft(database_session, scope).training_goal is None
    assert len(provider.extraction_contexts) == 1
    assert len(database_session.scalars(select(OnboardingAiMessage)).all()) == 2


def test_ready_turn_extracts_valid_data_without_completing(database_session: Session) -> None:
    provider = FakeProvider([turn("ready")], [extraction(with_evidence=True)])
    drafts, scope = scope_for(database_session)
    result = OnboardingConversationService(provider=provider, draft_service=drafts).submit(
        database_session, scope, message=". ".join(ANSWERS.values()), client_request_id=uuid4()
    )
    onboarding = drafts.get_or_create_draft(database_session, scope)
    assert result.completion_ready is True
    assert onboarding.training_goal == "Ganhar força"
    assert onboarding.status == "draft"
    assert len(provider.extraction_contexts) == 1
    assistant = database_session.scalar(
        select(OnboardingAiMessage).where(OnboardingAiMessage.role == "assistant")
    )
    assert assistant is not None
    assert "O onboarding ainda não está concluído" in assistant.content
    transcript = provider.extraction_contexts[0]["conversation"]
    assert len(transcript) == 1 and transcript[0]["role"] == "user"


def test_invalid_final_extraction_preserves_existing_draft(database_session: Session) -> None:
    provider = FakeProvider([turn("ready")], [extraction(height_cm=0)])
    drafts, scope = scope_for(database_session)
    drafts.save_draft(database_session, scope, OnboardingDraftUpdate(training_goal="Resistência"))
    from app.modules.onboarding.conversation_service import AiConversationUnavailableError

    with pytest.raises(AiConversationUnavailableError):
        OnboardingConversationService(provider=provider, draft_service=drafts).submit(
            database_session, scope, message="Terminei.", client_request_id=uuid4()
        )
    onboarding = drafts.get_or_create_draft(database_session, scope)
    assert onboarding.training_goal == "Resistência" and onboarding.height_cm is None


def test_context_expires_after_five_day_window(database_session: Session) -> None:
    provider = FakeProvider([turn()])
    drafts, scope = scope_for(database_session)
    service = OnboardingConversationService(provider=provider, draft_service=drafts)
    service.submit(
        database_session, scope, message="Quero condicionamento.", client_request_id=uuid4()
    )
    conversation = database_session.scalar(select(OnboardingAiConversation))
    assert conversation is not None
    conversation.raw_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    database_session.commit()
    assert service.state(database_session, scope).messages == []


def test_transient_interview_failure_retries_once(database_session: Session) -> None:
    provider = FakeProvider([], [AiProviderError("timeout", retryable=True), extraction()])
    drafts, scope = scope_for(database_session)
    OnboardingConversationService(provider=provider, draft_service=drafts).submit(
        database_session, scope, message="Olá", client_request_id=uuid4()
    )
    assert len(provider.extraction_contexts) == 2


@pytest.mark.parametrize("fabricated_evidence", [False, True])
def test_objective_only_cannot_fill_invented_measurements_or_health_answers(
    database_session: Session, fabricated_evidence: bool
) -> None:
    proposed = extraction()
    if fabricated_evidence:
        proposed = proposed.model_copy(update={"evidence": extraction(with_evidence=True).evidence})
    provider = FakeProvider([turn("ready")], [proposed])
    drafts, scope = scope_for(database_session)
    result = OnboardingConversationService(provider=provider, draft_service=drafts).submit(
        database_session, scope, message="Ganhar força", client_request_id=uuid4()
    )
    assert not result.completion_ready
    assert {"height_cm", "weight_kg", "uses_medications", "has_health_conditions"} <= set(
        result.missing_required_fields
    )
    draft = drafts.get_or_create_draft(database_session, scope)
    assert draft.status == "draft" and draft.completed_at is None
    assert all(getattr(draft, field) is None for field in OnboardingDraftUpdate.model_fields)
    assert not drafts.has_valid_completed_onboarding(database_session, scope.client_id)
    reply = database_session.scalar(
        select(OnboardingAiMessage).where(OnboardingAiMessage.role == "assistant")
    )
    assert "concluído" not in reply.content
    assert reply.content.count("?") == 1
    if fabricated_evidence:
        assert "experiência" in reply.content


def test_existing_form_answers_can_be_reused_without_model_citations(database_session: Session):
    drafts, scope = scope_for(database_session)
    drafts.save_draft(database_session, scope, OnboardingDraftUpdate(**extraction().onboarding))
    provider = FakeProvider([turn("ready")], [extraction()])
    result = OnboardingConversationService(provider=provider, draft_service=drafts).submit(
        database_session, scope, message="Revisar minhas respostas.", client_request_id=uuid4()
    )
    assert result.completion_ready
    assert drafts.get_or_create_draft(database_session, scope).status == "draft"


def test_retry_uses_original_client_message_as_its_source(database_session: Session):
    from app.modules.onboarding.conversation_service import AiConversationUnavailableError

    drafts, scope = scope_for(database_session)
    provider = FakeProvider(
        [],
        [
            AiProviderError("timeout", retryable=True),
            AiProviderError("timeout", retryable=True),
            extraction(),
        ],
    )
    service = OnboardingConversationService(provider=provider, draft_service=drafts)
    request_id = uuid4()
    with pytest.raises(AiConversationUnavailableError):
        service.submit(
            database_session, scope, message="Ganhar força", client_request_id=request_id
        )
    service.submit(
        database_session, scope, message="Um texto diferente", client_request_id=request_id
    )
    assert provider.extraction_contexts[-1]["conversation"][-1]["content"] == "Ganhar força"


def test_cached_ready_reply_cannot_override_a_later_incomplete_draft(database_session: Session):
    drafts, scope = scope_for(database_session)
    provider = FakeProvider([turn("ready")], [extraction(with_evidence=True)])
    service = OnboardingConversationService(provider=provider, draft_service=drafts)
    request_id = uuid4()
    original = ". ".join(ANSWERS.values())
    assert service.submit(
        database_session, scope, message=original, client_request_id=request_id
    ).completion_ready
    drafts.save_draft(database_session, scope, OnboardingDraftUpdate(height_cm=None))
    repeated = service.submit(
        database_session, scope, message=original, client_request_id=request_id
    )
    assert not repeated.completion_ready
    assert "height_cm" in repeated.missing_required_fields
    assert len(provider.extraction_contexts) == 1


def test_progressive_answers_are_required_before_ready_even_if_model_always_claims_ready(
    database_session: Session,
):
    class EagerProvider(FakeProvider):
        def extract_onboarding(self, context):
            self.extraction_contexts.append(context)
            users = [item for item in context["conversation"] if item["role"] == "user"]
            proposed = extraction()
            return AiOnboardingExtractionResponse(
                onboarding=proposed.onboarding,
                evidence={
                    field: {"message_sequence": item["message_sequence"], "quote": item["content"]}
                    for field, item in [
                        (list(ANSWERS)[len(self.extraction_contexts) - 1], users[-1])
                    ]
                },
            )

    provider = EagerProvider([turn("ready") for _ in ANSWERS])
    drafts, scope = scope_for(database_session)
    service = OnboardingConversationService(provider=provider, draft_service=drafts)
    answers = ["Ganhar força", "Iniciante", "1,70 m", "70,5 kg", "Não", "Não", "Não"]
    for index, answer in enumerate(answers):
        result = service.submit(database_session, scope, message=answer, client_request_id=uuid4())
        assert result.completion_ready == (index == len(answers) - 1)
        draft = drafts.get_or_create_draft(database_session, scope)
        assert draft.status == "draft" and draft.completed_at is None
        if not result.completion_ready:
            assert draft.height_cm is None  # No partial AI writes to the authoritative draft.
    assert draft.training_experience == "beginner" and draft.height_cm == 170
    assert draft.uses_medications is False and draft.has_health_conditions is False


class CurrentMessageProvider(FakeProvider):
    """A scripted extractor whose evidence always references the current client message."""

    def extract_onboarding(self, context):
        self.extraction_contexts.append(context)
        values = self.extractions.pop(0)
        if isinstance(values, Exception):
            raise values
        source = context["conversation"][-1]
        return AiOnboardingExtractionResponse(
            onboarding=values,
            evidence={
                name: {"message_sequence": source["message_sequence"], "quote": source["content"]}
                for name in values
            },
        )


def test_multi_fact_corrections_survive_reload_and_do_not_restart(database_session):
    drafts, scope = scope_for(database_session)
    provider = CurrentMessageProvider(
        [],
        [
            {"height_cm": 180, "weight_kg": 80},
            {"weight_kg": 82},
            {},
            {},
            {"weight_kg": 83},
        ],
    )
    service = OnboardingConversationService(provider, drafts)

    def send(message):
        return service.submit(database_session, scope, message=message, client_request_id=uuid4())

    first = send("Tenho 1,80 m e peso 80 kg.")
    assert first.known_answers.height_cm == 180
    assert first.known_answers.weight_kg == 80
    corrected = send("Na verdade, meu peso é 82 kg, não 80 kg.")
    assert corrected.known_answers.weight_kg == 82
    assert corrected.known_answers.height_cm == 180
    assert service.state(database_session, scope).known_answers == corrected.known_answers
    assert send("Errei uma informação.").needs_clarification
    assert send("O peso").clarification_fields == ["weight_kg"]
    final = send("83")
    assert final.known_answers.weight_kg == 83
    assert final.known_answers.height_cm == 180
    assert not final.needs_clarification
    assert drafts.get_or_create_draft(database_session, scope).height_cm is None


def test_conflict_blocks_completion_until_confirmation_and_preserves_other_answers(
    database_session,
):
    from app.modules.onboarding.draft_service import OnboardingDraftValidationError

    drafts, scope = scope_for(database_session)
    drafts.save_draft(database_session, scope, OnboardingDraftUpdate(**extraction().onboarding))
    provider = CurrentMessageProvider([], [{"weight_kg": 82}, {"weight_kg": 82}])
    service = OnboardingConversationService(provider, drafts)
    result = service.submit(
        database_session, scope, message="Peso 82 kg", client_request_id=uuid4()
    )
    assert result.clarification_fields == ["weight_kg"]
    assert result.known_answers.weight_kg != 82 and not result.completion_ready
    with pytest.raises(OnboardingDraftValidationError):
        drafts.complete_draft(database_session, scope)
    confirmed = service.submit(database_session, scope, message="82 kg", client_request_id=uuid4())
    assert confirmed.completion_ready and confirmed.known_answers.weight_kg == 82
    assert confirmed.known_answers.height_cm == 170
    assert drafts.get_or_create_draft(database_session, scope).weight_kg == 82


def test_manual_form_can_resolve_pending_conflict_with_original_value(database_session):
    drafts, scope = scope_for(database_session)
    drafts.save_draft(database_session, scope, OnboardingDraftUpdate(**extraction().onboarding))
    service = OnboardingConversationService(CurrentMessageProvider([], [{"weight_kg": 82}]), drafts)
    service.submit(database_session, scope, message="Peso 82 kg", client_request_id=uuid4())
    drafts.save_draft(database_session, scope, OnboardingDraftUpdate(weight_kg="70.50"))
    state = service.state(database_session, scope)
    assert state.completion_ready and not state.needs_clarification
    drafts.complete_draft(database_session, scope)
    from app.modules.onboarding.draft_service import OnboardingNotEditableError

    with pytest.raises(OnboardingNotEditableError):
        service.submit(database_session, scope, message="Peso 83 kg", client_request_id=uuid4())


def test_failed_provider_and_expiry_preserve_authoritative_form(database_session):
    from app.modules.onboarding.conversation_service import AiConversationUnavailableError

    drafts, scope = scope_for(database_session)
    drafts.save_draft(database_session, scope, OnboardingDraftUpdate(training_goal="Força"))
    provider = CurrentMessageProvider(
        [], [{"height_cm": 180}, AiProviderError("invalid", retryable=False)]
    )
    service = OnboardingConversationService(provider, drafts)
    service.submit(database_session, scope, message="Tenho 180 cm", client_request_id=uuid4())
    with pytest.raises(AiConversationUnavailableError):
        service.submit(database_session, scope, message="Peso 80 kg", client_request_id=uuid4())
    state = service.state(database_session, scope)
    assert state.known_answers.height_cm == 180 and state.known_answers.weight_kg is None
    conversation = database_session.scalar(select(OnboardingAiConversation))
    conversation.raw_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    database_session.commit()
    expired = service.state(database_session, scope)
    assert expired.known_answers.training_goal == "Força"
    assert expired.known_answers.height_cm is None and expired.messages == []


@pytest.mark.parametrize("uncertain", ["Acho que meu peso é 82 kg", "Meu peso pode ser 82 kg"])
def test_uncertain_existing_answer_blocks_ready_without_losing_other_fields(
    database_session, uncertain
):
    drafts, scope = scope_for(database_session)
    drafts.save_draft(database_session, scope, OnboardingDraftUpdate(**extraction().onboarding))
    provider = CurrentMessageProvider([], [{"weight_kg": 82}, {}])
    service = OnboardingConversationService(provider, drafts)
    state = service.submit(database_session, scope, message=uncertain, client_request_id=uuid4())
    assert not state.completion_ready and state.clarification_fields == ["weight_kg"]
    assert state.known_answers.weight_kg != 82 and state.known_answers.height_cm == 170
    state = service.submit(database_session, scope, message="Não lembro", client_request_id=uuid4())
    assert not state.completion_ready and state.clarification_fields == ["weight_kg"]
    conversation = service.state(database_session, scope)
    assert "Qual é o seu peso" in conversation.messages[-1].content
