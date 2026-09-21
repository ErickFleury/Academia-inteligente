"""Client-scoped draft onboarding persistence without sensitive-value logging."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Account, Client
from app.modules.onboarding.models import Onboarding, OnboardingAuditEvent
from app.modules.onboarding.schema import OnboardingCompletionData, OnboardingDraftUpdate


class OnboardingNotFoundError(Exception):
    """The authenticated identity is not linked to a local client."""


class OnboardingNotEditableError(Exception):
    """A completed onboarding cannot be silently changed."""


class OnboardingDraftValidationError(Exception):
    """A partial draft violates an approved field or conditional rule."""


@dataclass(frozen=True)
class ClientOnboardingScope:
    client_id: UUID
    account_id: UUID


class OnboardingDraftService:
    """Keeps structured onboarding authoritative for form and future AI flows."""

    _conditional_fields = (
        ("has_limitations_or_complaints", "limitations_or_complaints"),
        ("uses_medications", "medications"),
        ("has_health_conditions", "health_conditions"),
    )

    def resolve_client_scope(self, session: Session, subject: str) -> ClientOnboardingScope:
        row = session.execute(
            select(Client.id, Account.id)
            .join(Account, Client.account_id == Account.id)
            .where(Account.keycloak_subject == subject)
        ).one_or_none()
        if row is None:
            raise OnboardingNotFoundError
        return ClientOnboardingScope(client_id=row[0], account_id=row[1])

    def get_or_create_draft(self, session: Session, scope: ClientOnboardingScope) -> Onboarding:
        onboarding = session.scalar(
            select(Onboarding).where(Onboarding.client_id == scope.client_id)
        )
        if onboarding is None:
            onboarding = Onboarding(client_id=scope.client_id, status="draft")
            session.add(onboarding)
            session.flush()
            self._audit(session, onboarding, scope, "onboarding_draft_created", ())
            session.commit()
        return onboarding

    def save_draft(
        self, session: Session, scope: ClientOnboardingScope, update: OnboardingDraftUpdate
    ) -> Onboarding:
        onboarding = self.get_or_create_draft(session, scope)
        if onboarding.status != "draft":
            raise OnboardingNotEditableError

        changes = update.model_dump(exclude_unset=True)
        values = self._merged_values(onboarding, changes)
        self._validate_conditional_draft_values(values)

        for field, value in values.items():
            if field in changes or any(field == detail for _, detail in self._conditional_fields):
                setattr(onboarding, field, value)

        self._audit(session, onboarding, scope, "onboarding_draft_saved", tuple(sorted(changes)))
        session.commit()
        session.refresh(onboarding)
        return onboarding

    @staticmethod
    def completion_data(onboarding: Onboarding) -> OnboardingCompletionData:
        """Expose final completion prerequisites without completing the record."""
        try:
            return OnboardingCompletionData.model_validate(
                {
                    "training_goal": onboarding.training_goal,
                    "training_experience": onboarding.training_experience,
                    "height_cm": onboarding.height_cm,
                    "weight_kg": onboarding.weight_kg,
                    "has_limitations_or_complaints": onboarding.has_limitations_or_complaints,
                    "limitations_or_complaints": onboarding.limitations_or_complaints,
                    "uses_medications": onboarding.uses_medications,
                    "medications": onboarding.medications,
                    "has_health_conditions": onboarding.has_health_conditions,
                    "health_conditions": onboarding.health_conditions,
                }
            )
        except ValidationError as error:
            raise OnboardingDraftValidationError(
                "Onboarding is not ready for completion"
            ) from error

    def _merged_values(self, onboarding: Onboarding, changes: dict[str, Any]) -> dict[str, Any]:
        fields = (
            "training_goal",
            "training_experience",
            "height_cm",
            "weight_kg",
            "has_limitations_or_complaints",
            "limitations_or_complaints",
            "uses_medications",
            "medications",
            "has_health_conditions",
            "health_conditions",
        )
        values = {field: changes.get(field, getattr(onboarding, field)) for field in fields}
        for boolean_field, detail_field in self._conditional_fields:
            if values[boolean_field] is False:
                values[detail_field] = None
        return values

    def _validate_conditional_draft_values(self, values: dict[str, Any]) -> None:
        for boolean_field, detail_field in self._conditional_fields:
            if values[boolean_field] is True and not values[detail_field]:
                raise OnboardingDraftValidationError(
                    f"{detail_field} is required when {boolean_field} is true"
                )

    @staticmethod
    def _audit(
        session: Session,
        onboarding: Onboarding,
        scope: ClientOnboardingScope,
        action: str,
        changed_fields: tuple[str, ...],
    ) -> None:
        session.add(
            OnboardingAuditEvent(
                onboarding_id=onboarding.id,
                client_id=scope.client_id,
                actor_account_id=scope.account_id,
                action=action,
                changed_fields=",".join(changed_fields) or None,
                succeeded=True,
            )
        )
