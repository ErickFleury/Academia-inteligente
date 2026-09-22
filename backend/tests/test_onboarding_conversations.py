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


def extraction(**updates: object) -> AiOnboardingExtractionResponse:
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
    return AiOnboardingExtractionResponse(onboarding=values)


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
    provider = FakeProvider([turn("ready")], [extraction()])
    drafts, scope = scope_for(database_session)
    result = OnboardingConversationService(provider=provider, draft_service=drafts).submit(
        database_session, scope, message="Terminei.", client_request_id=uuid4()
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
    assert "Já reuni todas as informações necessárias" in assistant.content


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
