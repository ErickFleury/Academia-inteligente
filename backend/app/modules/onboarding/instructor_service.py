"""Need-to-know instructor operations over the authoritative onboarding aggregate."""

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import Account, Client, Employee
from app.modules.onboarding.draft_service import (
    ClientOnboardingScope,
    OnboardingAlreadyCompletedError,
    OnboardingDraftService,
    OnboardingDraftValidationError,
    OnboardingNotFoundError,
)
from app.modules.onboarding.models import OnboardingAuditEvent
from app.modules.onboarding.schema import OnboardingCompletionData, OnboardingDraftUpdate


class InstructorOnboardingService:
    def __init__(self):
        self.drafts = OnboardingDraftService()

    def _scope(self, session: Session, subject: str, client_id: UUID):
        employee = session.scalar(
            select(Employee)
            .join(Account)
            .where(
                Account.keycloak_subject == subject,
                Account.account_active,
                Employee.active,
                Employee.specialization == "instructor",
            )
        )
        client = session.scalar(
            select(Client)
            .join(Account)
            .where(Client.id == client_id, Client.active, Account.account_active)
            .with_for_update(of=Client)
        )
        if employee is None or client is None:
            raise OnboardingNotFoundError
        return ClientOnboardingScope(client.id, employee.account_id, employee.id)

    def _record(self, session: Session, scope, onboarding, action, fields=(), succeeded=True):
        session.add(
            OnboardingAuditEvent(
                onboarding_id=onboarding.id,
                client_id=scope.client_id,
                actor_account_id=scope.account_id,
                actor_employee_id=scope.actor_employee_id,
                action=f"instructor_{action}",
                changed_fields=",".join(sorted(fields)) or None,
                succeeded=succeeded,
            )
        )

    def read(self, session: Session, subject: str, client_id: UUID):
        scope = self._scope(session, subject, client_id)
        onboarding = self.drafts.get_or_create_draft(session, scope, commit=False)
        self._record(session, scope, onboarding, "onboarding_read")
        session.commit()
        return onboarding

    def update(self, session: Session, subject: str, client_id: UUID, payload: dict):
        scope = self._scope(session, subject, client_id)
        onboarding = self.drafts.get_or_create_draft(session, scope, commit=False)
        # Refresh after the client lock even when this transaction held an old identity map.
        session.refresh(onboarding)
        action = (
            "onboarding_completed_updated"
            if onboarding.status == "completed"
            else "onboarding_draft_saved"
        )
        fields = set(payload).intersection(OnboardingDraftUpdate.model_fields)
        try:
            update = OnboardingDraftUpdate.model_validate(payload)
            changes = update.model_dump(exclude_unset=True)
            values = self.drafts._merged_values(onboarding, changes)
            self.drafts._validate_conditional_draft_values(values)
            if onboarding.status == "completed":
                OnboardingCompletionData.model_validate(values)
        except (ValidationError, OnboardingDraftValidationError):
            self._record(session, scope, onboarding, action, fields, succeeded=False)
            session.commit()
            raise OnboardingDraftValidationError("Invalid onboarding fields") from None
        changed = tuple(
            field for field, value in values.items() if getattr(onboarding, field) != value
        )
        for field, value in values.items():
            setattr(onboarding, field, value)
        self._record(session, scope, onboarding, action, changed)
        session.commit()
        session.refresh(onboarding)
        return onboarding

    def complete(self, session: Session, subject: str, client_id: UUID):
        scope = self._scope(session, subject, client_id)
        onboarding = self.drafts.get_or_create_draft(session, scope, commit=False)
        session.refresh(onboarding)
        try:
            result = self.drafts.complete_draft(session, scope, commit=False)
        except (OnboardingDraftValidationError, OnboardingAlreadyCompletedError):
            self._record(session, scope, onboarding, "onboarding_completed", succeeded=False)
            session.commit()
            raise
        session.commit()
        session.refresh(result)
        return result
