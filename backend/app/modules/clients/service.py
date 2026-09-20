"""Client registration, identity provisioning, and lookup business rules."""

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.clients.models import Account, Client, ClientIdentityReconciliation
from app.modules.identity.keycloak_admin import (
    ClientIdentityProvisioner,
    KeycloakAdminClient,
    KeycloakIdentityConflictError,
    KeycloakProvisioningError,
)

email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CREATE, LINK, EMAIL = "create", "link_existing", "email_update"


class DuplicateEmailError(Exception):
    pass


class ClientValidationError(Exception):
    pass


class ClientIdentityProvisioningError(Exception):
    pass


class ClientIdentityConflictError(Exception):
    pass


@dataclass(frozen=True)
class ClientSummary:
    id: UUID
    name: str
    email: str
    account_active: bool
    identity_provisioned: bool
    created_at: datetime


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_client_data(name: str, email: str) -> tuple[str, str]:
    normalized_name, normalized_email = " ".join(name.split()), normalize_email(email)
    if not normalized_name:
        raise ClientValidationError("Name is required")
    if len(normalized_name) > 200:
        raise ClientValidationError("Name must contain at most 200 characters")
    if not email_pattern.fullmatch(normalized_email):
        raise ClientValidationError("A valid e-mail address is required")
    if len(normalized_email) > 320:
        raise ClientValidationError("E-mail must contain at most 320 characters")
    return normalized_name, normalized_email


def summary_from_client(client: Client) -> ClientSummary:
    return ClientSummary(
        client.id,
        client.name,
        client.account.email,
        client.account.account_active,
        client.account.keycloak_subject is not None,
        client.created_at,
    )


class ClientService:
    def __init__(self, provisioner: ClientIdentityProvisioner | None = None) -> None:
        self.provisioner = provisioner or KeycloakAdminClient()

    def create(self, session: Session, name: str, email: str) -> ClientSummary:
        name, email = validate_client_data(name, email)
        pending = session.scalar(
            select(ClientIdentityReconciliation).where(ClientIdentityReconciliation.email == email)
        )
        if pending is None:
            if session.scalar(select(Account).where(Account.email == email)):
                raise DuplicateEmailError
            pending = ClientIdentityReconciliation(operation=CREATE, email=email, name=name)
            self._commit_pending(session, pending)
        elif pending.operation != CREATE:
            raise ClientIdentityProvisioningError
        subject = self._ensure_identity(session, pending)
        if session.scalar(select(Account).where(Account.email == email)):
            raise DuplicateEmailError
        client = Client(
            name=name, account=Account(email=email, keycloak_subject=subject, account_active=True)
        )
        session.add(client)
        session.delete(pending)
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise ClientIdentityProvisioningError from error
        session.refresh(client, attribute_names=["account"])
        return summary_from_client(client)

    def list(self, session: Session, query: str | None = None) -> list[ClientSummary]:
        statement: Select[tuple[Client]] = select(Client).options(joinedload(Client.account))
        if query and (needle := query.strip()):
            pattern = f"%{needle}%"
            statement = statement.join(Client.account).where(
                or_(Client.name.ilike(pattern), Account.email.ilike(pattern))
            )
        return [
            summary_from_client(client)
            for client in session.scalars(statement.order_by(Client.name, Client.id)).all()
        ]

    def get(self, session: Session, client_id: UUID) -> ClientSummary | None:
        client = self._client(session, client_id)
        return summary_from_client(client) if client else None

    def provision_existing(self, session: Session, client_id: UUID) -> ClientSummary | None:
        client = self._client(session, client_id)
        if client is None or client.account.keycloak_subject:
            return summary_from_client(client) if client else None
        pending = session.scalar(
            select(ClientIdentityReconciliation).where(
                ClientIdentityReconciliation.account_id == client.account.id
            )
        )
        if pending is None:
            pending = ClientIdentityReconciliation(
                operation=LINK, email=client.account.email, account_id=client.account.id
            )
            self._commit_pending(session, pending)
        client.account.keycloak_subject = self._ensure_identity(session, pending)
        session.delete(pending)
        self._commit_client(session)
        return summary_from_client(client)

    def update(
        self,
        session: Session,
        client_id: UUID,
        *,
        name: str | None,
        email: str | None,
        account_active: bool | None,
    ) -> ClientSummary | None:
        client = self._client(session, client_id)
        if client is None:
            return None
        if name is None and email is None and account_active is None:
            raise ClientValidationError("At least one client field must be provided")
        name = (
            validate_client_data(name, client.account.email)[0] if name is not None else client.name
        )
        email = validate_client_data(name, email)[1] if email is not None else client.account.email
        if email != client.account.email and client.account.keycloak_subject:
            pending = session.scalar(
                select(ClientIdentityReconciliation).where(
                    ClientIdentityReconciliation.account_id == client.account.id
                )
            )
            if pending is None:
                if session.scalar(select(Account).where(Account.email == email)):
                    raise DuplicateEmailError
                pending = ClientIdentityReconciliation(
                    operation=EMAIL,
                    email=email,
                    account_id=client.account.id,
                    keycloak_subject=client.account.keycloak_subject,
                )
                self._commit_pending(session, pending)
            if pending.operation != EMAIL or pending.email != email:
                raise ClientIdentityProvisioningError
            try:
                self.provisioner.update_email(client.account.keycloak_subject, email)
            except KeycloakIdentityConflictError as error:
                raise ClientIdentityConflictError from error
            except KeycloakProvisioningError as error:
                raise ClientIdentityProvisioningError from error
            session.delete(pending)
        elif email != client.account.email and session.scalar(
            select(Account).where(Account.email == email)
        ):
            raise DuplicateEmailError
        client.name, client.account.email = name, email
        if account_active is not None:
            client.account.account_active = account_active
        self._commit_client(session)
        return summary_from_client(client)

    def _ensure_identity(self, session: Session, pending: ClientIdentityReconciliation) -> str:
        try:
            subject = self.provisioner.ensure_client_identity(
                pending.email, pending.id, pending.keycloak_subject
            )
        except KeycloakIdentityConflictError as error:
            self._store_subject(session, pending, error.subject)
            raise ClientIdentityConflictError from error
        except KeycloakProvisioningError as error:
            self._store_subject(session, pending, error.subject)
            raise ClientIdentityProvisioningError from error
        self._store_subject(session, pending, subject)
        return subject

    def _store_subject(
        self, session: Session, pending: ClientIdentityReconciliation, subject: str | None
    ) -> None:
        if subject and pending.keycloak_subject != subject:
            pending.keycloak_subject = subject
            self._commit_pending(session, pending)

    @staticmethod
    def _client(session: Session, client_id: UUID) -> Client | None:
        return session.scalar(
            select(Client).options(joinedload(Client.account)).where(Client.id == client_id)
        )

    @staticmethod
    def _commit_pending(session: Session, pending: ClientIdentityReconciliation) -> None:
        try:
            session.add(pending)
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise ClientIdentityProvisioningError from error

    @staticmethod
    def _commit_client(session: Session) -> None:
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise DuplicateEmailError from error
