"""Client-owned progressive interview with verified, expiring working memory."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
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
from app.modules.onboarding.direct_answers import direct_extraction, measurement_suggestion
from app.modules.onboarding.draft_service import (
    ClientOnboardingScope,
    OnboardingDraftService,
    OnboardingNotEditableError,
)
from app.modules.onboarding.interview_state import InterviewState, draft_values
from app.modules.onboarding.measurements import normalized
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
    known_answers: OnboardingDraftUpdate = field(default_factory=OnboardingDraftUpdate)
    clarification_fields: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    fallback_field: str | None = None


@dataclass(frozen=True)
class ConversationTurn:
    missing_required_fields: list[str]
    completion_ready: bool
    known_answers: OnboardingDraftUpdate = field(default_factory=OnboardingDraftUpdate)
    clarification_fields: list[str] = field(default_factory=list)
    needs_clarification: bool = False
    fallback_field: str | None = None


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
        memory = InterviewState.load(conversation.summary, onboarding)
        return self._state(session, conversation, memory)

    def _state(self, session, conversation, memory):
        missing = self._drafts.missing_required_fields(memory.answers)
        return ConversationState(
            self._messages(session, conversation.id),
            missing,
            not missing and not memory.pending and not memory.needs_target,
            memory.answers,
            memory.pending,
            memory.needs_target or bool(memory.pending),
            self._fallback_field(memory, missing),
        )

    def submit(
        self,
        session: Session,
        scope: ClientOnboardingScope,
        *,
        message: str,
        client_request_id: UUID,
    ) -> ConversationTurn:
        self.purge_expired_content(session)
        # Serialize this client's form/completion/conversation operations. The
        # verified memory and reply commit together after the provider succeeds.
        onboarding = self._drafts.get_or_create_draft(session, scope, commit=False)
        if onboarding.status != "draft":
            raise OnboardingNotEditableError
        conversation = self._conversation(session, scope, commit=False)
        memory = InterviewState.load(conversation.summary, onboarding)
        reply = session.scalar(
            select(OnboardingAiMessage).where(
                OnboardingAiMessage.conversation_id == conversation.id,
                OnboardingAiMessage.reply_to_client_request_id == client_request_id,
            )
        )
        if reply:
            state = self._state(session, conversation, memory)
            return ConversationTurn(
                state.missing_required_fields,
                state.completion_ready,
                state.known_answers,
                state.clarification_fields,
                state.needs_clarification,
                state.fallback_field,
            )
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
            session.flush()
        elif user.sequence <= memory.last_sequence:
            raise OnboardingNotEditableError
        message = user.content
        sources = self._source_messages(session, conversation.id)
        sources = [item for item in sources if item.sequence <= user.sequence]
        context = self._extraction_context(
            sources[-self._recent_message_limit - 1 :], memory.answers
        )
        context.update(
            current_message_sequence=user.sequence,
            pending_clarifications=memory.pending,
            needs_correction_target=memory.needs_target,
        )
        previous = next((item for item in sources if item.sequence == user.sequence - 1), None)
        question = previous.content if previous and previous.role == "assistant" else ""
        expected = next((name for name, prompt in _QUESTIONS.items() if prompt in question), None)
        if question and memory.confirmation:
            expected = next(iter(memory.confirmation))
        accepted: set[str] = set()
        answer = normalized(message).strip(" .!")
        confirmation = memory.confirmation.copy()
        direct = direct_extraction(message, user.sequence, question)
        try:
            if confirmation and answer in {"sim", "confirmo", "isso", "correto"}:
                candidate = OnboardingDraftUpdate(**(memory.answers.model_dump() | confirmation))
                accepted.update(confirmation)
            elif confirmation and answer in {"nao", "incorreto"}:
                candidate = memory.answers
            else:
                extracted = (
                    direct
                    if direct is not None
                    else self._retry(lambda: self._provider.extract_onboarding(context))
                )
                candidate = grounded_answers(
                    extracted,
                    memory.answers,
                    sources,
                    latest_sequence=user.sequence,
                    accepted_fields=accepted,
                )
        except (AiConversationUnavailableError, ValidationError):
            conversation.raw_expires_at = self._expiry()
            session.commit()
            raise AiConversationUnavailableError from None
        memory.confirmation = {}
        changed = memory.merge(candidate, message, user.sequence, accepted)
        for name in accepted:
            if name not in memory.pending:
                memory.failed_answers.pop(name, None)
        if expected and expected not in accepted and not changed:
            memory.failed_answers[expected] = min(2, memory.failed_answers.get(expected, 0) + 1)
            if expected in {"height_cm", "weight_kg"}:
                memory.needs_target = False
                memory.pending = list(dict.fromkeys([*memory.pending, expected]))
        # Offer a proposed measurement only in this client's expiring state. An
        # explicit confirmation or restated value is required before applying it.
        for name in memory.pending[:1] if not memory.needs_target else []:
            if name in {"height_cm", "weight_kg"}:
                proposed = measurement_suggestion(message, name)
                if proposed is not None:
                    memory.confirmation = {name: proposed}
                    break
        missing = self._drafts.missing_required_fields(memory.answers)
        ready = not missing and not memory.pending and not memory.needs_target
        if ready:
            complete = OnboardingCompletionData.model_validate(memory.answers.model_dump())
            self._drafts.save_draft(
                session,
                scope,
                OnboardingDraftUpdate(**complete.model_dump()),
                commit=False,
                sync_interview=False,
            )
            memory.baseline = draft_values(onboarding)
            text = _INTERVIEW_COMPLETE_MESSAGE
        elif memory.needs_target:
            text = "Qual informação você quer corrigir? As outras respostas foram mantidas."
        else:
            target = memory.pending[0] if memory.pending else missing[0]
            acknowledgment = (
                "Atualizei " + ", ".join(_LABELS[name] for name in changed) + ". "
                if changed
                else ""
            )
            text = acknowledgment + ("Vamos confirmar esse dado. " if memory.pending else "")
            if memory.confirmation and target in memory.confirmation:
                value = memory.confirmation[target].replace(".", ",")
                unit = "kg" if target == "weight_kg" else "cm"
                label = "esse peso" if target == "weight_kg" else "essa altura"
                text += f"Você quis dizer {value} {unit}? "
                text += f"Confirme {label} com “sim” ou informe o valor correto."
            else:
                if memory.failed_answers.get(target, 0):
                    text += self._clarification(target, message)
                text += _QUESTIONS[target]
            if memory.failed_answers.get(target, 0) >= 2:
                text += (
                    " Você também pode preencher esse dado diretamente abaixo ou usar o formulário."
                )

        session.add(
            OnboardingAiMessage(
                conversation_id=conversation.id,
                role="assistant",
                content=text,
                sequence=self._next(session, conversation.id),
                reply_to_client_request_id=client_request_id,
                missing_required_fields=json.dumps(missing),
                completion_ready=ready,
            )
        )
        conversation.summary = memory.dump()
        conversation.raw_expires_at = self._expiry()
        session.commit()
        return ConversationTurn(
            missing,
            ready,
            memory.answers,
            memory.pending,
            memory.needs_target or bool(memory.pending),
            self._fallback_field(memory, missing),
        )

    @staticmethod
    def _fallback_field(memory: InterviewState, missing: list[str]) -> str | None:
        return next(
            (
                name
                for name in [*memory.pending, *missing]
                if memory.failed_answers.get(name, 0) >= 2
            ),
            None,
        )

    @staticmethod
    def _clarification(target: str, message: str) -> str:
        if target in {"height_cm", "weight_kg"}:
            if len(re.findall(r"\d+(?:[.,]\d+)?", message)) > 1:
                return "Encontrei mais de um número e preciso saber qual é o valor atual. "
            unit = (
                "kg (por exemplo, 82 kg)"
                if target == "weight_kg"
                else "cm ou m (por exemplo, 180 cm)"
            )
            return f"Não consegui validar a medida. Informe um valor atual em {unit}. "
        return "Não consegui confirmar essa resposta. As outras informações foram mantidas. "

    def _retry(self, operation):
        for attempt in range(2):
            try:
                return operation()
            except AiProviderError as error:
                if attempt or not error.retryable:
                    raise AiConversationUnavailableError from None
        raise AiConversationUnavailableError

    def _conversation(
        self, session: Session, scope: ClientOnboardingScope, *, commit: bool = True
    ) -> OnboardingAiConversation:
        value = session.scalar(
            select(OnboardingAiConversation)
            .where(OnboardingAiConversation.client_id == scope.client_id)
            .execution_options(populate_existing=True)
        )
        if value is None:
            value = OnboardingAiConversation(client_id=scope.client_id)
            session.add(value)
            session.flush()
            if commit:
                session.commit()
        return value

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
