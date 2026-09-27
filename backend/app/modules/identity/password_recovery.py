"""Authorized recovery requests; credentials and action tokens stay in Keycloak."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.clients.models import (
    Account,
    Client,
    ClientIdentityReconciliation,
    EmployeeIdentityReconciliation,
)
from app.modules.identity.keycloak_admin import (
    KeycloakAdminClient,
    KeycloakIdentityConflictError,
    KeycloakIdentityMissingError,
    KeycloakProvisioningError,
)


class PasswordRecoveryError(Exception):
    def __init__(self, code: str, status: int):
        self.code, self.status = code, status


class PasswordRecoveryService:
    def __init__(self, provider: KeycloakAdminClient | None = None):
        self._provider = provider or KeycloakAdminClient()

    def request_for_client(self, session: Session, client_id: UUID) -> None:
        account_id = session.scalar(select(Client.account_id).where(Client.id == client_id))
        if account_id is None:
            raise PasswordRecoveryError("Client not found", 404)
        self._send(session, account_id)

    def request_for_subject(self, session: Session, subject: str) -> None:
        account_id = session.scalar(
            select(Account.id)
            .join(Client)
            .where(Account.keycloak_subject == subject, Client.active.is_(True))
        )
        if account_id is None:
            raise PasswordRecoveryError("Unauthenticated", 401)
        self._send(session, account_id)

    def _send(self, session: Session, account_id: UUID) -> None:
        account = session.scalar(
            select(Account)
            .where(Account.id == account_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if account is None or not account.account_active or not account.keycloak_subject:
            raise PasswordRecoveryError("Password recovery requires an active linked account", 409)
        for model in (ClientIdentityReconciliation, EmployeeIdentityReconciliation):
            if session.scalar(select(model.id).where(model.account_id == account_id)) is not None:
                raise PasswordRecoveryError("Identity synchronization is pending", 409)
        now = datetime.now(UTC)
        previous = account.password_recovery_requested_at
        if previous and previous.tzinfo is None:
            previous = previous.replace(tzinfo=UTC)
        if previous and previous > now - timedelta(seconds=60):
            raise PasswordRecoveryError("Password recovery cooldown", 429)
        account.password_recovery_requested_at = now
        subject, email = account.keycloak_subject, account.email
        # Reserve before external I/O, shared by admin/self-service requests and
        # all workers. Retain the cooldown on uncertain delivery; never auto-resend.
        session.commit()
        try:
            self._provider.send_password_recovery_email(subject, email)
        except (KeycloakIdentityConflictError, KeycloakIdentityMissingError):
            raise PasswordRecoveryError("Identity synchronization is pending", 409) from None
        except KeycloakProvisioningError:
            raise PasswordRecoveryError(
                "Password recovery is temporarily unavailable", 503
            ) from None
