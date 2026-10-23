"""Client-scoped conversational support and explicitly requested proposal edits."""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.integrations.ai import (
    AiProviderError,
    AiTrainingChatResponse,
    TrainingChatProvider,
    training_chat_provider_from_environment,
)
from app.integrations.ai_budget import ExecutionBudget
from app.integrations.ai_diagnostics import observe_turn, record_retry, record_turn
from app.modules.assistant.runtime import (
    AssistantError,
    AssistantRun,
    InitialPlanFollowup,
    enabled,
)
from app.modules.clients.models import Account, Client
from app.modules.equipment.service import EquipmentService
from app.modules.memory.service import utc
from app.modules.onboarding.draft_service import OnboardingDraftService
from app.modules.onboarding.models import Onboarding
from app.modules.training.generation_service import (
    CompletedOnboardingRequiredError,
    InitialTrainingGenerationService,
    InvalidTrainingGenerationError,
    TrainingGenerationUnavailableError,
)
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
    InvalidTrainingContentError,
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
    reference_citations: list[dict] = field(default_factory=list)
    clarification: dict | None = None
    event_id: UUID | None = None


@dataclass(frozen=True)
class TrainingChatRequestState:
    client_request_id: UUID
    status: Literal["processing", "failed"]
    failure_code: str | None = None


@dataclass(frozen=True)
class TrainingChatState:
    messages: list[TrainingChatMessage]
    pending_request: TrainingChatRequestState | None = None


class TrainingChatService:
    """Client-scoped chat; the sole active proposal may be revised by the AI."""

    def __init__(
        self,
        provider: TrainingChatProvider | None = None,
        *,
        generation_service: InitialTrainingGenerationService | None = None,
    ) -> None:
        self._provider = provider or training_chat_provider_from_environment()
        self._generation = generation_service or InitialTrainingGenerationService()
        self._lifecycle = TrainingLifecycleService()
        self._recent_message_limit = int(os.environ.get("AI_RECENT_MESSAGE_LIMIT", "6"))
        self._summary_limit = int(os.environ.get("AI_TRAINING_CHAT_SUMMARY_LIMIT", "2000"))

    def state_for_subject(self, session: Session, subject: str) -> TrainingChatState:
        client_id = self._client_id(session, subject)
        self.purge_expired_content(session)
        conversation = self._conversation(session, client_id)
        return self._state(session, conversation.id)

    @observe_turn("training_chat")
    def submit_for_subject(
        self, session: Session, subject: str, *, message: str, client_request_id: UUID
    ) -> TrainingChatState:
        client_id = self._client_id(session, subject)
        self.purge_expired_content(session)
        session.scalar(select(Client.id).where(Client.id == client_id).with_for_update())
        conversation = self._conversation(session, client_id, commit=False)
        reply = session.scalar(
            select(TrainingAiMessage).where(
                TrainingAiMessage.conversation_id == conversation.id,
                TrainingAiMessage.reply_to_client_request_id == client_request_id,
            )
        )
        if reply is not None:
            record_turn(outcome="cached", path="cached")
            return self._state(session, conversation.id)

        active = session.scalar(
            select(TrainingAiMessage).where(
                TrainingAiMessage.conversation_id == conversation.id,
                TrainingAiMessage.processing_token.is_not(None),
                TrainingAiMessage.processing_expires_at > datetime.now(UTC),
            )
        )
        if active is not None:
            if active.client_request_id != client_request_id:
                raise ConcurrentTrainingUpdateError
            return self._state(session, conversation.id)

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
            session.flush()

        newer = session.scalar(
            select(TrainingAiMessage.id)
            .where(
                TrainingAiMessage.conversation_id == conversation.id,
                TrainingAiMessage.role == "user",
                TrainingAiMessage.sequence > user.sequence,
            )
            .limit(1)
        )
        if newer:
            raise ConcurrentTrainingUpdateError
        token = uuid4()
        user.processing_token = token
        # Covers the maximum 60s plan budget plus bounded finalization. A server
        # restart cannot leave the UI permanently busy; late attempts are fenced.
        user.processing_expires_at = datetime.now(UTC) + timedelta(seconds=65)
        user.failure_code = None
        session.commit()
        user_id = user.id
        try:
            context = self._context(session, client_id, conversation, user.content, user.id)
            plan = context["current_training_plan"] is None and (
                context["resume_initial_plan"]
                or self._requests_initial_plan(user.content, context["recent_messages"])
            )
            with ExecutionBudget(plan=plan).scope():
                return self._respond(
                    session, subject, client_id, conversation, user, token, context
                )
        except Exception as error:
            session.rollback()
            code = getattr(error, "code", None)
            if code not in {
                "deadline_exceeded",
                "assistant_clarification_required",
                "memory_capacity",
            }:
                code = (
                    "conflict"
                    if isinstance(error, ConcurrentTrainingUpdateError)
                    or getattr(error, "status", None) == 409
                    else "processing_failed"
                )
            session.execute(
                update(TrainingAiMessage)
                .where(TrainingAiMessage.id == user_id, TrainingAiMessage.processing_token == token)
                .values(processing_token=None, processing_expires_at=None, failure_code=code)
            )
            session.commit()
            raise

    def _respond(self, session, subject, client_id, conversation, user, token, context):
        client_request_id = user.client_request_id
        if not enabled(client_id):
            # Preserve the legacy provider's serialization during inference.
            session.scalar(select(Client.id).where(Client.id == client_id).with_for_update())
        editable_draft = self._editable_ai_draft(session, client_id)
        draft_revision = editable_draft.revision if editable_draft else None
        run = None
        initial_reply = None
        clarification = None
        try:
            initial_reply = self._initial_plan_reply(session, subject, client_id, context)
            if initial_reply is not None:
                response = AiTrainingChatResponse(assistant_message=initial_reply)
            else:
                record_turn(path="model")
                if enabled(client_id):
                    run = AssistantRun(
                        session, client_id, "training_chat", source=user, provider=self._provider
                    )
                    # Retain retry input, release the client lock during inference.
                    session.commit()
                    run.prepare(context)
                    if (
                        run.route.plan_action == "generate_initial_plan"
                        and context["current_training_plan"] is None
                    ):
                        context["model_requested_initial_plan"] = True
                        initial_reply = self._initial_plan_reply(
                            session, subject, client_id, context
                        )
                        response = AiTrainingChatResponse(assistant_message=initial_reply)
                        run = None
                    else:
                        context["rules"]["may_update_ai_draft"] = run.context["rules"][
                            "may_update_ai_draft"
                        ]
                        response = run.specialist()
                        run.finalize()
                        clarification = run.clarification
                else:
                    response = self._retry(lambda: self._provider.training_chat(context))
        except AssistantError as error:
            session.rollback()
            if error.code != "assistant_clarification_required" or error.clarification is None:
                raise
            clarification = error.clarification
            run = context.get("_initial_plan_run") or run
            if run:
                # A valid clarification is a successful conversational result.
                # Save verified personal answers, never its rejected plan.
                run.finalize()
            response = AiTrainingChatResponse(
                assistant_message=" ".join(
                    part
                    for part in (clarification["explanation"], clarification["next_step"])
                    if part
                )
            )
            record_turn(outcome="clarification", reason=clarification["reason"])
        except (TrainingChatUnavailableError, TrainingChatDraftUpdateError):
            session.rollback()
            raise
        session.scalar(select(Client.id).where(Client.id == client_id).with_for_update())
        claimed = session.get(TrainingAiMessage, user.id, populate_existing=True)
        if claimed is None or claimed.processing_token != token or not self._processing(claimed):
            raise ConcurrentTrainingUpdateError
        content = response.assistant_message
        if response.draft_update is not None:
            if editable_draft is not None and context["rules"]["may_update_ai_draft"]:
                self._apply_draft_update(
                    session, editable_draft, response.draft_update, draft_revision
                )
                if run:
                    editable_draft.reference_citations = run.public_citations()
                record_turn(outcome="draft_saved")
                content = (
                    "Atualizei o rascunho conforme solicitado. "
                    "Confira as alterações em Meu treino; "
                    "elas ainda dependem da aprovação do instrutor. "
                    "Seu plano atual não foi alterado."
                )
            else:
                record_turn(
                    outcome="draft_blocked",
                    reason="request_not_authorized" if editable_draft else "no_editable_draft",
                )
                content = (
                    "Não alterei nenhum plano. Diga qual mudança deseja fazer no rascunho."
                    if editable_draft
                    else "Não alterei nenhum plano: "
                    "não há um único rascunho disponível para edição. "
                    "Seu plano atual só pode mudar após revisão profissional."
                )
        elif clarification is None and initial_reply is None and self._claims_saved_change(content):
            record_turn(outcome="draft_blocked", reason="unsupported_save_claim")
            content = (
                "Nenhuma alteração foi salva no treino nesta mensagem. "
                "Diga qual mudança deseja fazer no rascunho para eu ajudar."
            )
        elif (
            clarification is None
            and initial_reply is None
            and context["current_training_plan"] is None
            and self._offers_initial_plan(content)
        ):
            # Ground an offer in real capabilities; the next confirmation is
            # handled by the backend, never sent back to the model to ask again.
            content = self._initial_plan_guidance(context)
        can_suggest_adaptation = context["current_training_plan"] is not None
        if (
            clarification
            and clarification.get("reason") == "missing_client_information"
            and editable_draft is not None
            and context["rules"]["may_update_ai_draft"]
        ):
            pending = run.context.get("pending_draft_edit") if run else None
            clarification["pending_draft_edit"] = {
                "draft_id": str(editable_draft.id),
                "draft_revision": draft_revision,
                "request_event_id": pending["request_event_id"] if pending else str(user.id),
            }
        assistant = TrainingAiMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=content,
            sequence=self._next(session, conversation.id),
            reply_to_client_request_id=client_request_id,
            reference_citations=run.public_citations() if run else None,
            clarification=clarification,
            adaptation_suggested=response.adaptation_suggested and can_suggest_adaptation,
            adaptation_reason=response.adaptation_reason
            if response.adaptation_suggested and can_suggest_adaptation
            else None,
        )
        session.add(assistant)
        conversation.raw_expires_at = self._expiry()
        session.flush()
        conversation.summary = self._bounded_summary(session, conversation.id)
        claimed.processing_token = None
        claimed.processing_expires_at = None
        claimed.failure_code = None
        session.commit()
        return self._state(session, conversation.id)

    @staticmethod
    def _processing(message):
        expires = message.processing_expires_at
        if expires is not None and expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return bool(message.processing_token and expires and expires > datetime.now(UTC))

    def _state(self, session, conversation_id):
        latest = session.scalar(
            select(TrainingAiMessage)
            .where(
                TrainingAiMessage.conversation_id == conversation_id,
                TrainingAiMessage.role == "user",
            )
            .order_by(TrainingAiMessage.sequence.desc())
            .limit(1)
            .execution_options(populate_existing=True)
        )
        messages = self._messages(session, conversation_id)
        pending = None
        if (
            latest
            and latest.client_request_id
            and not any(m.reply_to_client_request_id == latest.client_request_id for m in messages)
        ):
            processing = self._processing(latest)
            pending = TrainingChatRequestState(
                latest.client_request_id,
                "processing" if processing else "failed",
                None
                if processing
                else latest.failure_code
                or ("deadline_exceeded" if latest.processing_token else "processing_failed"),
            )
        return TrainingChatState(messages, pending)

    def purge_expired_content(self, session: Session, now: datetime | None = None) -> int:
        current_time = now or datetime.now(UTC)
        affected = session.scalars(
            select(TrainingAiMessage.conversation_id)
            .where(TrainingAiMessage.created_at <= current_time - timedelta(days=30))
            .distinct()
        ).all()
        if affected:
            session.execute(
                update(TrainingAiConversation)
                .where(TrainingAiConversation.id.in_(affected))
                .values(summary=None)
            )
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
        retained = self._messages(session, conversation.id, message_id)
        history = retained[-self._recent_message_limit :]
        # Recall a bounded set of older own-client statements, with their actual
        # question and provenance. A generated summary is never extraction evidence.
        older = retained[: -self._recent_message_limit]
        terms = {word for word in re.findall(r"\w+", self._normalized(message)) if len(word) > 3}
        candidates = [
            (index, item)
            for index, item in enumerate(older)
            if item.role == "user" and len(item.content) <= 500
        ]
        candidates.sort(
            key=lambda pair: (
                len(terms & set(re.findall(r"\w+", self._normalized(pair[1].content)))),
                pair[0],
            ),
            reverse=True,
        )
        recalled = [
            {
                "role": "user",
                "content": item.content,
                "created_at": item.created_at.isoformat(),
                "event_id": str(item.event_id),
                "preceding_question": (
                    older[index - 1].content[:800]
                    if index and older[index - 1].role == "assistant"
                    else None
                ),
            }
            for index, item in sorted(candidates[:4])
        ]
        current_plan = self._current_plan(session, client_id)
        draft = self._editable_ai_draft(session, client_id)
        draft_content = self._draft_context(session, draft) if draft else None
        pending_edit = self._pending_draft_edit(
            retained,
            draft,
            event_after=session.scalar(
                select(Client.memory_event_after).where(Client.id == client_id)
            ),
        )
        may_update = draft_content is not None and self._requests_draft_change(
            message, history, [item["exercise_name"] for item in draft_content["items"]]
        )
        health_context = " ".join(
            [*(item.content for item in history if item.role == "user"), message]
        )
        previous_clarification = history[-1].clarification if history else None
        resume_initial_plan = (
            bool(
                enabled(client_id)
                and current_plan is None
                and draft is None
                and history[-1].role == "assistant"
                and previous_clarification
                and previous_clarification.get("initial_plan_requested") is True
                and previous_clarification.get("reason") == "missing_client_information"
                and not self._requests_initial_plan(
                    message, [{"role": item.role, "content": item.content} for item in history]
                )
            )
            if history
            else False
        )
        return {
            "pending_draft_edit": pending_edit,
            "resume_initial_plan": resume_initial_plan,
            "current_user_message": message,
            "current_event_id": str(message_id),
            "recalled_messages": recalled,
            "conversation_summary": self._bounded_summary(session, conversation.id, message_id),
            "recent_messages": [
                {
                    "role": item.role,
                    "content": item.content,
                    "created_at": item.created_at.isoformat(),
                    "event_id": str(item.event_id),
                    "clarification": item.clarification if item.role == "assistant" else None,
                }
                for item in history
            ],
            "current_training_plan": current_plan,
            "active_equipment_models": EquipmentService().training_context(session)
            if draft
            else [],
            "editable_training_draft": draft_content,
            "relevant_onboarding": self._onboarding_context(session, client_id, health_context),
            "onboarding_completed": OnboardingDraftService().has_valid_completed_onboarding(
                session, client_id
            ),
            "rules": {
                "language": "pt-BR",
                "must_not_diagnose": True,
                "must_not_mutate_current_or_approved_training_plan": True,
                "may_suggest_adaptation": current_plan is not None,
                "may_update_ai_draft": may_update,
                "client_reports_are_not_completed_onboarding_edits": True,
                "summary_contains_only_client_statements": True,
                "initial_generation_requires_explicit_request": True,
            },
        }

    @staticmethod
    def _pending_draft_edit(history, draft, *, event_after=None):
        if not draft or not history or history[-1].role != "assistant":
            return None
        if event_after and utc(history[-1].created_at) <= utc(event_after):
            return None  # A later memory correction/forgetting invalidates old context.
        detail = history[-1].clarification or {}
        pending = detail.get("pending_draft_edit") or {}
        if (
            detail.get("reason") != "missing_client_information"
            or pending.get("draft_id") != str(draft.id)
            or pending.get("draft_revision") != draft.revision
        ):
            return None
        # Resolve the request from this conversation's retained user events.
        # Never trust a model-supplied request, another chat, or a stale draft.
        source = next(
            (
                item
                for item in history
                if item.role == "user" and str(item.event_id) == pending.get("request_event_id")
            ),
            None,
        )
        if source is None:
            return None
        return {
            **pending,
            "request": source.content,
            "missing_fields": detail.get("missing_fields", []),
            "questions": detail.get("questions", []),
        }

    def _initial_plan_reply(
        self, session: Session, subject: str, client_id: UUID, context: dict
    ) -> str | None:
        if context["current_training_plan"] is not None:
            return None  # Existing-plan changes keep the adaptation/review flow.
        resuming = context.get("resume_initial_plan", False)
        if (
            not resuming
            and not context.get("model_requested_initial_plan")
            and not self._requests_initial_plan(
                context["current_user_message"], context["recent_messages"]
            )
        ):
            return None
        if resuming and re.fullmatch(
            r"(?:por favor[, ]+)?(?:cancele|cancela|cancelar|pare|nao (?:gere|crie|monte)|"
            r"nao quero(?: mais)?|nao precisa|agora nao|deixa pra la|deix[ae] para depois)"
            r"(?: (?:o |meu |esse |este )?(?:plano|treino|rascunho)(?: de treino)?)?"
            r"(?:[, ]+por favor)?[.!]*",
            self._normalized(context["current_user_message"]).strip(),
        ):
            return "Tudo bem, cancelei a criação do rascunho."
        record_turn(path="direct")
        if self._lifecycle.find_proposal(session, client_id=client_id) is not None:
            return (
                "Seu rascunho já está disponível em Meu treino e aguarda revisão do instrutor. "
                "Não criei outro plano. Você pode pedir uma alteração nesse rascunho."
            )
        if not context["onboarding_completed"]:
            return self._initial_plan_guidance(context)
        try:
            # The input/claim was committed before inference. The outer request
            # now owns rollback of both the proposal and its eventual reply.
            self._generation.generate_for_subject(
                session, subject, commit=False, chat_context=context
            )
        except InitialPlanFollowup as decision:
            context.pop("_initial_plan_run", None)
            if decision.action == "cancel":
                return "Tudo bem, cancelei a criação do rascunho."
            return None
        except AssistantError as error:
            if error.clarification is not None:
                # Only this backend-owned workflow can authorize continuation.
                error.clarification = {**error.clarification, "initial_plan_requested": True}
            raise
        except CompletedOnboardingRequiredError:
            return "Revise e conclua seu onboarding antes de gerar o rascunho de treino."
        except TrainingGenerationUnavailableError:
            raise TrainingChatUnavailableError from None
        except InvalidTrainingGenerationError:
            raise TrainingChatDraftUpdateError from None
        record_turn(outcome="draft_saved")
        return "Criei seu rascunho. Confira em Meu treino; ele aguarda aprovação do instrutor."

    @staticmethod
    def _initial_plan_guidance(context: dict) -> str:
        if context["editable_training_draft"] is not None:
            return (
                "Seu rascunho já está disponível em Meu treino e aguarda revisão do instrutor. "
                "Você pode pedir uma alteração nesse rascunho."
            )
        if not context["onboarding_completed"]:
            return "Revise e conclua seu onboarding antes de gerar o rascunho de treino."
        return (
            "Posso gerar seu rascunho inicial com base no onboarding concluído, "
            "para revisão do instrutor. Quer que eu prepare seu rascunho de treino?"
        )

    @classmethod
    def _offers_initial_plan(cls, message: str) -> bool:
        text = cls._normalized(message)
        return bool(
            re.search(r"\b(?:prepar\w*|gerar|gere|montar|monte|criar|crie|elabor\w*)\b", text)
            and re.search(r"\b(?:plano|treino|rascunho|ficha|proposta)\b", text)
            and re.search(r"\b(?:quer|quero|deseja|gostaria|posso|vou|vamos)\b", text)
        )

    @classmethod
    def _requests_initial_plan(cls, message: str, history: list[dict]) -> bool:
        text = cls._normalized(message).strip()
        # Full matches intentionally exclude conditions, negation, health
        # corrections and ambiguous compound answers from consent.
        if re.fullmatch(
            r"(?:sim(?:[,!]\s*|\s+))?(?:sim|quero|pode|pode sim|confirmo|"
            r"pode fazer|pode preparar|pode gerar|pode criar|pode montar)"
            r"(?:[, ]+por favor)?[.!]*",
            text,
        ):
            questions = re.findall(r"[^.!?]*\?", history[-1]["content"]) if history else []
            return bool(
                history
                and history[-1]["role"] == "assistant"
                and len(questions) == 1
                and cls._offers_initial_plan(questions[0])
                and not re.search(r"\bnao\b", cls._normalized(questions[0]))
            )
        return bool(
            re.fullmatch(
                r"(?:por favor[, ]+)?(?:quero que (?:voce )?|"
                r"(?:pode|poderia|quero|gostaria de) )?"
                r"(?:prepare|preparar|gere|gerar|monte|montar|crie|criar|elabore|elaborar) "
                r"(?:(?:um|o|meu|novo|primeiro|seu) )*"
                r"(?:plano(?: de treino)?|treino|rascunho(?: de treino)?|ficha)"
                r"(?: inicial)?(?: para mim)?(?:[, ]+por favor)?[.!?]*",
                text,
            )
        )

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
                    "equipment_requirement": item.equipment_requirement,
                    "equipment_model_id": str(item.equipment_model_id)
                    if item.equipment_model_id
                    else None,
                }
                for item in session.scalars(
                    select(TrainingPlanItem)
                    .where(TrainingPlanItem.version_id == version.id)
                    .order_by(TrainingPlanItem.position)
                )
            ],
        }

    def _apply_draft_update(
        self,
        session: Session,
        version: TrainingPlanVersion,
        update: dict[str, object],
        expected_revision: int,
    ) -> None:
        try:
            data = TrainingPlanVersionInput.model_validate(update)
            self._lifecycle.revise(
                session,
                plan_id=version.plan_id,
                version_number=version.version_number,
                data=data,
                actor="ai",
                expected_revision=expected_revision,
                commit=False,
            )
        except ImmutableTrainingVersionError:
            raise ConcurrentTrainingUpdateError from None
        except (ValidationError, InvalidTrainingContentError):
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
        health_terms = (
            "dor",
            "lesao",
            "limit",
            "queixa",
            "medica",
            "remedio",
            "saude",
            "condic",
            "desconfort",
            "incomoda",
        )
        if any(term in TrainingChatService._normalized(message) for term in health_terms):
            context.update(
                {
                    "limitations_or_complaints": onboarding.limitations_or_complaints,
                    "medications": onboarding.medications,
                    "health_conditions": onboarding.health_conditions,
                }
            )
        return {key: value for key, value in context.items() if value is not None}

    def _bounded_summary(
        self, session: Session, conversation_id: UUID, exclude: UUID | None = None
    ) -> str | None:
        # Rebuild from retained sources, never from the previous generated summary.
        older = self._messages(session, conversation_id, exclude)[: -self._recent_message_limit]
        statements = []
        for item in reversed(older):
            if item.role != "user":
                continue
            entry = {"reported_at": item.created_at.isoformat(), "client_statement": item.content}
            candidate = [entry, *statements]
            if len(json.dumps(candidate, ensure_ascii=False)) > self._summary_limit:
                break  # Never cut a correction/negation midway or restore older stale facts.
            statements = candidate
        return json.dumps(statements, ensure_ascii=False) if statements else None

    @staticmethod
    def _normalized(text: str) -> str:
        return "".join(
            char
            for char in unicodedata.normalize("NFKD", text.lower())
            if not unicodedata.combining(char)
        )

    @classmethod
    def _requests_draft_change(
        cls, message: str, history: list[TrainingChatMessage], exercise_names: list[str]
    ) -> bool:
        text = cls._normalized(message).strip()
        if re.search(r"\bnao (?:quero|precisa|altere|mude|troque|atualize|modifique)\b", text):
            return False
        if re.match(
            r"(?:como|por que|qual|o que|sera que|vale a pena|explique|devo|posso|seria)\b", text
        ):
            return False
        action = (
            r"\b(?:alter(?:e|ar)|mud(?:e|ar)|tro(?:que|car)|substitu(?:a|ir)|"
            r"atualiz(?:e|ar)|ajust(?:e|ar)|reduz(?:a|ir)|aument(?:e|ar)|"
            r"remov(?:a|er)|inclu(?:a|ir)|adicion(?:e|ar))\b"
        )
        target = r"\b(?:rascunho|treino|plano|ficha|exercicio|series?|repeticoes|carga|descanso)\b"
        names_targeted = any(cls._normalized(name) in text for name in exercise_names)
        request = re.search(r"\b(?:quero|gostaria de|preciso que|pode|poderia)\b", text)
        imperative = re.search(
            r"(?:^|[,;.!]\s*)(?:por favor[,]?\s+)?"
            r"(?:altere|mude|troque|substitua|atualize|ajuste|reduza|aumente|remova|inclua|adicione)\b",
            text,
        )
        informational = re.search(r"\b(?:saber|entender|explicar|opiniao)\b", text)
        if (
            re.search(action, text)
            and (re.search(target, text) or names_targeted)
            and (request or imperative)
            and not informational
        ):
            return True
        if re.fullmatch(r"(?:sim|pode|pode sim|confirmo|pode fazer)[.!]?", text) and history:
            previous = history[-1]
            proposal = cls._normalized(previous.content)
            return (
                previous.role == "assistant"
                and "?" in proposal
                and "rascunho" in proposal
                and bool(re.search(action, proposal))
            )
        return False

    @classmethod
    def _claims_saved_change(cls, message: str) -> bool:
        text = cls._normalized(message)
        return bool(
            re.search(
                r"\b(?:atualizei|alterei|salvei|modifiquei|troquei|substitui|aprovei|ativei|"
                r"criei|gerei|preparei|montei)\b",
                text,
            )
        ) or bool(
            re.search(
                r"\b(?:plano|treino|rascunho|ficha)\b.{0,60}\b(?:foi|esta) "
                r"(?:atualizad|alterad|aprovad|ativad|salv)",
                text,
            )
        )

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
    def _conversation(
        session: Session, client_id: UUID, *, commit: bool = True
    ) -> TrainingAiConversation:
        # Existing reads must remain available while a request holds the client
        # lock. Only first creation needs serialization against competing reads.
        conversation = session.scalar(
            select(TrainingAiConversation).where(TrainingAiConversation.client_id == client_id)
        )
        if conversation is not None:
            return conversation
        # First reads can create a conversation too. Use the same client lock
        # as message submission before checking the unique conversation row.
        session.scalar(select(Client.id).where(Client.id == client_id).with_for_update())
        conversation = session.scalar(
            select(TrainingAiConversation).where(TrainingAiConversation.client_id == client_id)
        )
        if conversation is None:
            conversation = TrainingAiConversation(client_id=client_id)
            session.add(conversation)
            session.flush()
            if commit:
                session.commit()
        return conversation

    @staticmethod
    def _retry(operation):
        for attempt in range(2):
            try:
                return operation()
            except AiProviderError as error:
                record_retry(error.category, not attempt and error.retryable)
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
                reference_citations=message.reference_citations or [],
                clarification=message.clarification,
                event_id=message.id,
            )
            for message in session.scalars(statement.order_by(TrainingAiMessage.sequence)).all()
        ]
