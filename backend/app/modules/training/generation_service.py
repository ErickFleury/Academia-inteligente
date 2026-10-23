"""Initial AI proposal generation over completed, client-owned onboarding."""

from typing import Callable

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.ai import (
    AiProviderError,
    TrainingGenerationProvider,
    training_generation_provider_from_environment,
)
from app.integrations.ai_diagnostics import record_retry
from app.modules.assistant.runtime import AssistantRun, enabled
from app.modules.equipment.service import EquipmentService
from app.modules.onboarding.draft_service import (
    ClientOnboardingScope,
    OnboardingDraftService,
)
from app.modules.onboarding.models import Onboarding
from app.modules.training.models import TrainingAiConversation, TrainingAiMessage
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.service import (
    ActiveTrainingProposalExistsError,
    InvalidTrainingContentError,
    TrainingLifecycleService,
)


class CompletedOnboardingRequiredError(Exception):
    """Generation is allowed only after authoritative onboarding completion."""


class TrainingGenerationUnavailableError(Exception):
    """The external AI adapter could not produce a usable response."""


class InvalidTrainingGenerationError(Exception):
    """The provider response did not satisfy the approved plan schema."""


class InitialTrainingGenerationService:
    """Validates external output before creating the client's sole proposal version."""

    def __init__(
        self,
        *,
        provider: TrainingGenerationProvider | None = None,
        draft_service: OnboardingDraftService | None = None,
        lifecycle_service: TrainingLifecycleService | None = None,
    ) -> None:
        self._provider = provider or training_generation_provider_from_environment()
        self._drafts = draft_service or OnboardingDraftService()
        self._lifecycle = lifecycle_service or TrainingLifecycleService()

    def generate_for_subject(
        self,
        session: Session,
        subject: str,
        *,
        commit: bool = True,
        chat_context: dict | None = None,
    ):
        scope = self._drafts.resolve_client_scope(session, subject)
        return self.generate_for_scope(session, scope, commit=commit, chat_context=chat_context)

    def generate_for_scope(
        self,
        session: Session,
        scope: ClientOnboardingScope,
        *,
        commit: bool = True,
        chat_context: dict | None = None,
    ):
        source = None
        if chat_context and chat_context.get("current_event_id"):
            from uuid import UUID

            source = session.scalar(
                select(TrainingAiMessage)
                .join(TrainingAiConversation)
                .where(
                    TrainingAiConversation.client_id == scope.client_id,
                    TrainingAiMessage.id == UUID(chat_context["current_event_id"]),
                    TrainingAiMessage.role == "user",
                )
            )
            if source is None:
                raise InvalidTrainingGenerationError
        run = (
            AssistantRun(
                session, scope.client_id, "initial_plan", source=source, provider=self._provider
            )
            if enabled(scope.client_id)
            else None
        )
        onboarding = session.scalar(
            select(Onboarding).where(Onboarding.client_id == scope.client_id)
        )
        if onboarding is None or not self._drafts.has_valid_completed_onboarding(
            session, scope.client_id
        ):
            raise CompletedOnboardingRequiredError

        # Every client has at most one proposal, regardless of its creator.
        # Reusing it prevents a provider call and preserves the single-draft rule.
        existing = self._lifecycle.find_proposal(session, client_id=scope.client_id)
        if existing is not None:
            return existing

        # `completion_data` is the shared form/conversation-independent source
        # of truth. The provider never receives another client's data or identity.
        context = {
            "active_equipment_models": EquipmentService().training_context(session),
            "completed_onboarding": self._drafts.completion_data(onboarding).model_dump(),
            "proposal_rules": {
                "status": "proposal",
                "must_not_approve_or_activate": True,
                "instructor_review_required": True,
            },
        }
        if chat_context is not None:
            # Only the authenticated chat service supplies this already bounded,
            # own-client history. It cannot replace authoritative onboarding.
            context.update(
                {
                    key: chat_context[key]
                    for key in (
                        "current_user_message",
                        "recent_messages",
                        "recalled_messages",
                        "conversation_summary",
                        "resume_initial_plan",
                    )
                    if key in chat_context
                }
            )
        if run:
            if chat_context is not None:
                chat_context["_initial_plan_run"] = run
            # A caller using commit=False owns its transaction/savepoint.
            # Closing it here breaks chat generation and its atomic reply.
            if commit:
                session.commit()
            run.prepare(context)
            response = run.specialist()
        else:
            response = self._retry(lambda: self._provider.generate_training(context))
        try:
            proposal = TrainingPlanVersionInput.model_validate(response.plan)
        except ValidationError as error:
            raise InvalidTrainingGenerationError from error

        # Validation happens before lifecycle persistence, so malformed output
        # cannot create a partial plan or version.
        try:
            if run:
                run.finalize()
            result = self._lifecycle.create_proposal(
                session,
                client_id=scope.client_id,
                data=proposal,
                created_by="ai",
                origin="ai",
                commit=commit if not run else False,
            )
            if run:
                result.reference_citations = run.public_citations()
                if commit:
                    session.commit()
            return result
        except ActiveTrainingProposalExistsError:
            # Another request created the sole draft while the provider was running.
            existing = self._lifecycle.find_proposal(session, client_id=scope.client_id)
            if existing is not None:
                return existing
            raise
        except InvalidTrainingContentError:
            if run and commit:
                session.rollback()
            raise InvalidTrainingGenerationError from None

    @staticmethod
    def _retry(operation: Callable[[], object]):
        for attempt in range(2):
            try:
                return operation()
            except AiProviderError as error:
                record_retry(error.category, will_retry=not attempt and error.retryable)
                if attempt or not error.retryable:
                    raise TrainingGenerationUnavailableError from None
        raise TrainingGenerationUnavailableError
