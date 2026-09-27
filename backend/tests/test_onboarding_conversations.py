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
        result = self.extractions.pop(0)
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
    assert len(provider.turn_contexts) == 1
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
    result = OnboardingConversationService(provider=provider, draft_service=drafts).submit(
        database_session, scope, message="Terminei.", client_request_id=uuid4()
    )
    onboarding = drafts.get_or_create_draft(database_session, scope)
    assert result.completion_ready is False
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
    provider = FakeProvider([AiProviderError("timeout", retryable=True), turn()])
    drafts, scope = scope_for(database_session)
    OnboardingConversationService(provider=provider, draft_service=drafts).submit(
        database_session, scope, message="Olá", client_request_id=uuid4()
    )
    assert len(provider.turn_contexts) == 2


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
        [
            AiProviderError("timeout", retryable=True),
            AiProviderError("timeout", retryable=True),
            turn(),
        ]
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
    assert provider.turn_contexts[-1]["current_user_message"] == "Ganhar força"


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
    assert len(provider.turn_contexts) == 1


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
                    for field, item in zip(ANSWERS, users, strict=False)
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
