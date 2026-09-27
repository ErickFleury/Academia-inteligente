"""Read-only, client-scoped AI training chat orchestration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.integrations.ai import (
    AiProviderError,
    TrainingChatProvider,
    training_chat_provider_from_environment,
)
from app.modules.clients.models import Account, Client
from app.modules.onboarding.models import Onboarding
from app.modules.training.models import (
    TrainingAiConversation,
    TrainingAiMessage,
    TrainingPlan,
    TrainingPlanItem,
    TrainingPlanVersion,
)
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.service import (
    ConcurrentTrainingUpdateError,
    ImmutableTrainingVersionError,
    TrainingLifecycleService,
)


class TrainingChatNotFoundError(Exception):
    pass


class TrainingChatUnavailableError(Exception):
    pass


class TrainingChatDraftUpdateError(Exception):
    """The provider proposed an invalid or stale change to the AI draft."""


@dataclass(frozen=True)
class TrainingChatMessage:
    role: str
    content: str
    created_at: datetime
    client_request_id: UUID | None
    reply_to_client_request_id: UUID | None
    adaptation_suggested: bool
    adaptation_reason: str | None


@dataclass(frozen=True)
class TrainingChatState:
    messages: list[TrainingChatMessage]


class TrainingChatService:
    """Client-scoped chat; the sole active proposal may be revised by the AI."""

    def __init__(self, provider: TrainingChatProvider | None = None) -> None:
        self._provider = provider or training_chat_provider_from_environment()
        self._lifecycle = TrainingLifecycleService()
        self._recent_message_limit = int(os.environ.get("AI_RECENT_MESSAGE_LIMIT", "6"))
        self._summary_limit = int(os.environ.get("AI_TRAINING_CHAT_SUMMARY_LIMIT", "2000"))

    def state_for_subject(self, session: Session, subject: str) -> TrainingChatState:
        client_id = self._client_id(session, subject)
        self.purge_expired_content(session)
        conversation = self._conversation(session, client_id)
        return TrainingChatState(self._messages(session, conversation.id))

    def submit_for_subject(
        self, session: Session, subject: str, *, message: str, client_request_id: UUID
    ) -> TrainingChatState:
        client_id = self._client_id(session, subject)
        self.purge_expired_content(session)
        conversation = self._conversation(session, client_id)
        reply = session.scalar(
            select(TrainingAiMessage).where(
                TrainingAiMessage.conversation_id == conversation.id,
                TrainingAiMessage.reply_to_client_request_id == client_request_id,
            )
        )
        if reply is not None:
            return TrainingChatState(self._messages(session, conversation.id))

        user = session.scalar(
            select(TrainingAiMessage).where(
                TrainingAiMessage.conversation_id == conversation.id,
                TrainingAiMessage.client_request_id == client_request_id,
            )
        )
        if user is None:
            user = TrainingAiMessage(
                conversation_id=conversation.id,
                role="user",
                content=message,
                sequence=self._next(session, conversation.id),
                client_request_id=client_request_id,
            )
            session.add(user)
            conversation.raw_expires_at = self._expiry()
            session.commit()

        context = self._context(session, client_id, conversation, message, user.id)
        response = self._retry(lambda: self._provider.training_chat(context))
        editable_draft = self._editable_ai_draft(session, client_id)
        if response.draft_update is not None and editable_draft is not None:
            self._apply_draft_update(session, editable_draft, response.draft_update)
        can_suggest_adaptation = context["current_training_plan"] is not None
        assistant = TrainingAiMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=response.assistant_message,
            sequence=self._next(session, conversation.id),
            reply_to_client_request_id=client_request_id,
            adaptation_suggested=response.adaptation_suggested and can_suggest_adaptation,
            adaptation_reason=response.adaptation_reason
            if response.adaptation_suggested and can_suggest_adaptation
            else None,
        )
        session.add(assistant)
        conversation.raw_expires_at = self._expiry()
        conversation.summary = self._bounded_summary(session, conversation.id)
        session.commit()
        return TrainingChatState(self._messages(session, conversation.id))

    def purge_expired_content(self, session: Session, now: datetime | None = None) -> int:
        current_time = now or datetime.now(UTC)
        deleted = session.execute(
            delete(TrainingAiMessage).where(
                TrainingAiMessage.created_at <= current_time - timedelta(days=30)
            )
        ).rowcount
        expired_summaries = session.scalars(
            select(TrainingAiConversation).where(
                TrainingAiConversation.raw_expires_at.is_not(None),
                TrainingAiConversation.raw_expires_at <= current_time,
            )
        ).all()
        if expired_summaries:
            ids = [conversation.id for conversation in expired_summaries]
            session.execute(
                update(TrainingAiConversation)
                .where(TrainingAiConversation.id.in_(ids))
                .values(summary=None, raw_expires_at=None)
            )
        if deleted or expired_summaries:
            session.commit()
        return deleted or 0

    def _context(
        self,
        session: Session,
        client_id: UUID,
        conversation: TrainingAiConversation,
        message: str,
        message_id: UUID,
    ) -> dict[str, object]:
        history = self._messages(session, conversation.id, message_id)[
            -self._recent_message_limit :
        ]
        current_plan = self._current_plan(session, client_id)
        draft = self._editable_ai_draft(session, client_id)
        return {
            "current_user_message": message,
            "conversation_summary": conversation.summary,
            "recent_messages": [{"role": item.role, "content": item.content} for item in history],
            "current_training_plan": current_plan,
            "editable_training_draft": self._draft_context(session, draft) if draft else None,
            "relevant_onboarding": self._onboarding_context(session, client_id, message),
            "rules": {
                "language": "pt-BR",
                "must_not_diagnose": True,
                "must_not_mutate_current_or_approved_training_plan": True,
                "may_suggest_adaptation": current_plan is not None,
                "may_update_ai_draft": draft is not None,
            },
        }

    @staticmethod
    def _editable_ai_draft(session: Session, client_id: UUID) -> TrainingPlanVersion | None:
        drafts = session.scalars(
            select(TrainingPlanVersion)
            .where(
                TrainingPlanVersion.client_id == client_id,
                TrainingPlanVersion.status == "proposal",
            )
            .order_by(TrainingPlanVersion.created_at.desc())
        ).all()
        # Do not silently choose between legacy duplicate drafts.
        return drafts[0] if len(drafts) == 1 else None

    @staticmethod
    def _draft_context(session: Session, version: TrainingPlanVersion) -> dict[str, object]:
        return {
            "name": version.name,
            "objective": version.objective,
            "items": [
                {
                    "exercise_name": item.exercise_name,
                    "sets": item.sets,
                    "repetitions": item.repetitions,
                    "load_guidance": item.load_guidance,
                    "rest_seconds": item.rest_seconds,
                }
                for item in session.scalars(
                    select(TrainingPlanItem)
                    .where(TrainingPlanItem.version_id == version.id)
                    .order_by(TrainingPlanItem.position)
                )
            ],
        }

    def _apply_draft_update(
        self, session: Session, version: TrainingPlanVersion, update: dict[str, object]
    ) -> None:
        try:
            data = TrainingPlanVersionInput.model_validate(update)
            self._lifecycle.revise(
                session,
                plan_id=version.plan_id,
                version_number=version.version_number,
                data=data,
                actor="ai",
                expected_revision=version.revision,
            )
        except (ValidationError, ConcurrentTrainingUpdateError, ImmutableTrainingVersionError):
            raise TrainingChatDraftUpdateError from None

    def _current_plan(self, session: Session, client_id: UUID) -> dict[str, object] | None:
        version = session.scalar(
            select(TrainingPlanVersion)
            .join(TrainingPlan, TrainingPlanVersion.plan_id == TrainingPlan.id)
            .where(
                TrainingPlan.client_id == client_id,
                TrainingPlan.is_current,
                TrainingPlanVersion.status == "current",
            )
        )
        if version is None:
            return None
        return {
            "name": version.name,
            "objective": version.objective,
            "items": [
                {
                    "exercise_name": item.exercise_name,
                    "sets": item.sets,
                    "repetitions": item.repetitions,
                    "load_guidance": item.load_guidance,
                    "rest_seconds": item.rest_seconds,
                }
                for item in session.scalars(
                    select(TrainingPlanItem)
                    .where(TrainingPlanItem.version_id == version.id)
                    .order_by(TrainingPlanItem.position)
                )
            ],
        }

    @staticmethod
    def _onboarding_context(session: Session, client_id: UUID, message: str) -> dict[str, object]:
        onboarding = session.scalar(select(Onboarding).where(Onboarding.client_id == client_id))
        if onboarding is None or onboarding.status != "completed":
            return {}
        context: dict[str, object] = {
            "training_goal": onboarding.training_goal,
            "training_experience": onboarding.training_experience,
        }
        health_terms = ("dor", "lesão", "limit", "queixa", "medica", "remédio", "saúde", "condiç")
        if any(term in message.lower() for term in health_terms):
            context.update(
                {
                    "limitations_or_complaints": onboarding.limitations_or_complaints,
                    "medications": onboarding.medications,
                    "health_conditions": onboarding.health_conditions,
                }
            )
        return {key: value for key, value in context.items() if value is not None}

    def _bounded_summary(self, session: Session, conversation_id: UUID) -> str | None:
        messages = self._messages(session, conversation_id)
        older = messages[: -self._recent_message_limit]
        if not older:
            return None
        content = "\n".join(f"{item.role}: {item.content}" for item in older)
        return content[-self._summary_limit :]

    @staticmethod
    def _client_id(session: Session, subject: str) -> UUID:
        client_id = session.scalar(
            select(Client.id)
            .join(Account, Client.account_id == Account.id)
            .where(
                Account.keycloak_subject == subject, Account.account_active, Client.active.is_(True)
            )
        )
        if client_id is None:
            raise TrainingChatNotFoundError
        return client_id

    @staticmethod
    def _conversation(session: Session, client_id: UUID) -> TrainingAiConversation:
        conversation = session.scalar(
            select(TrainingAiConversation).where(TrainingAiConversation.client_id == client_id)
        )
        if conversation is None:
            conversation = TrainingAiConversation(client_id=client_id)
            session.add(conversation)
            session.commit()
        return conversation

    @staticmethod
    def _retry(operation):
        for attempt in range(2):
            try:
                return operation()
            except AiProviderError as error:
                if attempt or not error.retryable:
                    raise TrainingChatUnavailableError from None
        raise TrainingChatUnavailableError

    @staticmethod
    def _expiry() -> datetime:
        return datetime.now(UTC) + timedelta(days=30)

    @staticmethod
    def _next(session: Session, conversation_id: UUID) -> int:
        return (
            session.scalar(
                select(func.max(TrainingAiMessage.sequence)).where(
                    TrainingAiMessage.conversation_id == conversation_id
                )
            )
            or 0
        ) + 1

    @staticmethod
    def _messages(
        session: Session, conversation_id: UUID, exclude: UUID | None = None
    ) -> list[TrainingChatMessage]:
        statement = select(TrainingAiMessage).where(
            TrainingAiMessage.conversation_id == conversation_id
        )
        if exclude is not None:
            statement = statement.where(TrainingAiMessage.id != exclude)
        return [
            TrainingChatMessage(
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                client_request_id=message.client_request_id,
                reply_to_client_request_id=message.reply_to_client_request_id,
                adaptation_suggested=message.adaptation_suggested,
                adaptation_reason=message.adaptation_reason,
            )
            for message in session.scalars(statement.order_by(TrainingAiMessage.sequence)).all()
        ]
