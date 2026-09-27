"""Client-owned interview orchestration; extraction occurs only when interview is ready."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.integrations.ai import (
    AiProviderError,
    OnboardingAiProvider,
    onboarding_ai_provider_from_environment,
)
from app.modules.onboarding.answer_evidence import grounded_answers
from app.modules.onboarding.draft_service import ClientOnboardingScope, OnboardingDraftService
from app.modules.onboarding.models import OnboardingAiConversation, OnboardingAiMessage
from app.modules.onboarding.schema import OnboardingCompletionData, OnboardingDraftUpdate


class AiConversationUnavailableError(Exception):
    pass


@dataclass(frozen=True)
class ConversationMessage:
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class ConversationState:
    messages: list[ConversationMessage]
    missing_required_fields: list[str]
    completion_ready: bool


@dataclass(frozen=True)
class ConversationTurn:
    missing_required_fields: list[str]
    completion_ready: bool


_LABELS = {
    "training_goal": "objetivo de treino",
    "training_experience": "experiência de treino",
    "height_cm": "altura",
    "weight_kg": "peso",
    "has_limitations_or_complaints": "limitações ou queixas",
    "limitations_or_complaints": "detalhes de limitações ou queixas",
    "uses_medications": "uso de medicações",
    "medications": "detalhes de medicações",
    "has_health_conditions": "condições de saúde",
    "health_conditions": "detalhes de condições de saúde",
}

_INTERVIEW_COMPLETE_MESSAGE = (
    "As respostas foram reunidas no seu rascunho. O onboarding ainda não está concluído. "
    "Revise os dados no formulário e clique em “Concluir onboarding” quando estiver pronto."
)

_QUESTIONS = {
    "training_goal": "Qual é o seu principal objetivo de treino?",
    "training_experience": (
        "Como você descreve sua experiência: nenhuma, iniciante, intermediária ou avançada?"
    ),
    "height_cm": "Qual é a sua altura, em centímetros ou metros?",
    "weight_kg": "Qual é o seu peso, em quilos?",
    "has_limitations_or_complaints": (
        "Você tem alguma limitação, lesão, dor ou queixa que afete o treino?"
    ),
    "limitations_or_complaints": "Quais limitações, lesões, dores ou queixas você precisa relatar?",
    "uses_medications": "Você usa algum medicamento?",
    "medications": "Quais medicamentos você usa?",
    "has_health_conditions": (
        "Você tem alguma condição de saúde ou histórico de doença relevante para o treino?"
    ),
    "health_conditions": "Quais condições de saúde ou problemas anteriores você precisa relatar?",
}


class OnboardingConversationService:
    def __init__(
        self,
        provider: OnboardingAiProvider | None = None,
        draft_service: OnboardingDraftService | None = None,
    ) -> None:
        self._provider = provider or onboarding_ai_provider_from_environment()
        self._drafts = draft_service or OnboardingDraftService()
        self._recent_message_limit = int(os.environ.get("AI_RECENT_MESSAGE_LIMIT", "6"))
        self._final_message_limit = int(os.environ.get("AI_FINAL_EXTRACTION_MESSAGE_LIMIT", "60"))

    def state(self, session: Session, scope: ClientOnboardingScope) -> ConversationState:
        self.purge_expired_content(session)
        conversation = self._conversation(session, scope)
        onboarding = self._drafts.get_or_create_draft(session, scope)
        missing = self._drafts.missing_required_fields(onboarding)
        return ConversationState(self._messages(session, conversation.id), missing, not missing)

    def submit(
        self,
        session: Session,
        scope: ClientOnboardingScope,
        *,
        message: str,
        client_request_id: UUID,
    ) -> ConversationTurn:
        self.purge_expired_content(session)
        conversation = self._conversation(session, scope)
        reply = session.scalar(
            select(OnboardingAiMessage).where(
                OnboardingAiMessage.conversation_id == conversation.id,
                OnboardingAiMessage.reply_to_client_request_id == client_request_id,
            )
        )
        if reply:
            onboarding = self._drafts.get_or_create_draft(session, scope)
            missing = self._drafts.missing_required_fields(onboarding)
            return ConversationTurn(missing, bool(reply.completion_ready) and not missing)
        user = session.scalar(
            select(OnboardingAiMessage).where(
                OnboardingAiMessage.conversation_id == conversation.id,
                OnboardingAiMessage.client_request_id == client_request_id,
            )
        )
        if user is None:
            user = OnboardingAiMessage(
                conversation_id=conversation.id,
                role="user",
                content=message,
                sequence=self._next(session, conversation.id),
                client_request_id=client_request_id,
            )
            session.add(user)
            conversation.raw_expires_at = self._expiry()
            session.commit()
        onboarding = self._drafts.get_or_create_draft(session, scope)
        # Retries must use the original persisted message, not a new body sent
        # under the same idempotency key.
        message = user.content
        turn = self._retry(
            lambda: self._provider.interview_turn(
                self._context(session, conversation, onboarding, message, user.id)
            )
        )
        text, ready = turn.assistant_message, False
        missing = self._drafts.missing_required_fields(onboarding)
        if turn.interview_status == "ready":
            try:
                sources = self._source_messages(session, conversation.id)
                extracted = self._retry(
                    lambda: self._provider.extract_onboarding(
                        self._extraction_context(sources, onboarding)
                    )
                )
                grounded = grounded_answers(extracted, onboarding, sources)
                missing = self._drafts.missing_required_fields(grounded)
                if missing:
                    text = self._recovery_message(missing)
                else:
                    complete = OnboardingCompletionData.model_validate(grounded.model_dump())
                    self._drafts.save_draft(
                        session,
                        scope,
                        OnboardingDraftUpdate.model_validate(complete.model_dump()),
                        commit=False,
                    )
                    ready, text = True, _INTERVIEW_COMPLETE_MESSAGE
            except (AiConversationUnavailableError, ValidationError):
                missing = self._drafts.missing_required_fields(onboarding)
                text = self._recovery_message(missing)
        assistant = OnboardingAiMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=text,
            sequence=self._next(session, conversation.id),
            reply_to_client_request_id=client_request_id,
            missing_required_fields=json.dumps(missing),
            completion_ready=ready,
        )
        session.add(assistant)
        conversation.raw_expires_at = self._expiry()
        session.commit()
        return ConversationTurn(missing, ready)

    def _retry(self, operation):
        for attempt in range(2):
            try:
                return operation()
            except AiProviderError:
                if attempt:
                    raise AiConversationUnavailableError from None
        raise AiConversationUnavailableError

    def _recovery_message(self, missing: list[str]) -> str:
        return (
            _QUESTIONS[missing[0]]
            if missing
            else "Quero confirmar alguns detalhes antes de seguir. Pode explicar um pouco mais?"
        )

    def _conversation(
        self, session: Session, scope: ClientOnboardingScope
    ) -> OnboardingAiConversation:
        value = session.scalar(
            select(OnboardingAiConversation).where(
                OnboardingAiConversation.client_id == scope.client_id
            )
        )
        if value is None:
            value = OnboardingAiConversation(client_id=scope.client_id)
            session.add(value)
            session.commit()
        return value

    def _context(
        self,
        session: Session,
        conversation: OnboardingAiConversation,
        onboarding: object,
        message: str,
        message_id: UUID,
    ) -> dict[str, object]:
        history = self._messages(session, conversation.id, message_id)[
            -self._recent_message_limit :
        ]
        manual = {
            field: getattr(onboarding, field)
            for field in _LABELS
            if getattr(onboarding, field) is not None
        }
        return {
            "current_user_message": message,
            "recent_messages": [{"role": item.role, "content": item.content} for item in history],
            "existing_structured_onboarding": manual,
            "required_information": list(_LABELS),
        }

    def _extraction_context(
        self,
        messages: list[OnboardingAiMessage],
        onboarding: object,
    ) -> dict[str, object]:
        return {
            "conversation": [
                {"message_sequence": item.sequence, "role": item.role, "content": item.content}
                for item in messages
            ],
            "existing_structured_onboarding": {
                field: getattr(onboarding, field)
                for field in _LABELS
                if getattr(onboarding, field) is not None
            },
        }

    def _source_messages(
        self, session: Session, conversation_id: UUID
    ) -> list[OnboardingAiMessage]:
        return list(
            reversed(
                session.scalars(
                    select(OnboardingAiMessage)
                    .where(OnboardingAiMessage.conversation_id == conversation_id)
                    .order_by(OnboardingAiMessage.sequence.desc())
                    .limit(self._final_message_limit)
                ).all()
            )
        )

    def purge_expired_content(self, session: Session, now: datetime | None = None) -> int:
        expired = session.scalars(
            select(OnboardingAiConversation).where(
                OnboardingAiConversation.raw_expires_at.is_not(None),
                OnboardingAiConversation.raw_expires_at <= (now or datetime.now(UTC)),
            )
        ).all()
        if not expired:
            return 0
        ids = [item.id for item in expired]
        deleted = session.execute(
            delete(OnboardingAiMessage).where(OnboardingAiMessage.conversation_id.in_(ids))
        ).rowcount
        session.execute(
            update(OnboardingAiConversation)
            .where(OnboardingAiConversation.id.in_(ids))
            .values(summary=None, raw_expires_at=None)
        )
        session.commit()
        return deleted or 0

    @staticmethod
    def _expiry() -> datetime:
        return datetime.now(UTC) + timedelta(days=5)

    @staticmethod
    def _next(session: Session, id: UUID) -> int:
        return (
            session.scalar(
                select(func.max(OnboardingAiMessage.sequence)).where(
                    OnboardingAiMessage.conversation_id == id
                )
            )
            or 0
        ) + 1

    @staticmethod
    def _messages(
        session: Session, id: UUID, exclude: UUID | None = None
    ) -> list[ConversationMessage]:
        statement = select(OnboardingAiMessage).where(OnboardingAiMessage.conversation_id == id)
        if exclude:
            statement = statement.where(OnboardingAiMessage.id != exclude)
        return [
            ConversationMessage(item.role, item.content, item.created_at)
            for item in session.scalars(statement.order_by(OnboardingAiMessage.sequence)).all()
        ]
