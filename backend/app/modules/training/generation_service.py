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
from app.modules.onboarding.draft_service import (
    ClientOnboardingScope,
    OnboardingDraftService,
)
from app.modules.onboarding.models import Onboarding
from app.modules.training.models import TrainingPlan, TrainingPlanVersion
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.service import TrainingLifecycleService


class CompletedOnboardingRequiredError(Exception):
    """Generation is allowed only after authoritative onboarding completion."""


class TrainingGenerationUnavailableError(Exception):
    """The external AI adapter could not produce a usable response."""


class InvalidTrainingGenerationError(Exception):
    """The provider response did not satisfy the approved plan schema."""


class InitialTrainingGenerationService:
    """Validates external output before creating an AI-owned proposal version."""

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

    def generate_for_subject(self, session: Session, subject: str):
        scope = self._drafts.resolve_client_scope(session, subject)
        return self.generate_for_scope(session, scope)

    def generate_for_scope(self, session: Session, scope: ClientOnboardingScope):
        onboarding = session.scalar(
            select(Onboarding).where(Onboarding.client_id == scope.client_id)
        )
        if onboarding is None or not self._drafts.has_valid_completed_onboarding(
            session, scope.client_id
        ):
            raise CompletedOnboardingRequiredError

        # A client can have one active initial AI draft. Reusing it prevents a
        # second provider call and leaves manual/instructor proposals untouched.
        existing = session.scalar(
            select(TrainingPlanVersion)
            .join(TrainingPlan, TrainingPlanVersion.plan_id == TrainingPlan.id)
            .where(
                TrainingPlan.client_id == scope.client_id,
                TrainingPlanVersion.status == "proposal",
                TrainingPlanVersion.origin == "ai",
            )
            .order_by(TrainingPlanVersion.created_at.desc())
        )
        if existing is not None:
            return existing

        # `completion_data` is the shared form/conversation-independent source
        # of truth. The provider never receives another client's data or identity.
        context = {
            "completed_onboarding": self._drafts.completion_data(onboarding).model_dump(),
            "proposal_rules": {
                "status": "proposal",
                "must_not_approve_or_activate": True,
                "instructor_review_required": True,
            },
        }
        response = self._retry(lambda: self._provider.generate_training(context))
        try:
            proposal = TrainingPlanVersionInput.model_validate(response.plan)
        except ValidationError as error:
            raise InvalidTrainingGenerationError from error

        # Validation happens before lifecycle persistence, so malformed output
        # cannot create a partial plan or version.
        return self._lifecycle.create_proposal(
            session,
            client_id=scope.client_id,
            data=proposal,
            created_by="ai",
            origin="ai",
        )

    @staticmethod
    def _retry(operation: Callable[[], object]):
        for attempt in range(2):
            try:
                return operation()
            except AiProviderError as error:
                if attempt or not error.retryable:
                    raise TrainingGenerationUnavailableError from None
        raise TrainingGenerationUnavailableError
