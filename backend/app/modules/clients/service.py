"""Client registration and lookup business rules."""

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.clients.models import Account, Client

email_pattern = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class DuplicateEmailError(Exception):
    """The normalized e-mail already belongs to an application account."""


class ClientValidationError(Exception):
    """Submitted client registration data is invalid."""


@dataclass(frozen=True)
class ClientSummary:
    id: UUID
    name: str
    email: str
    created_at: datetime


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_client_data(name: str, email: str) -> tuple[str, str]:
    normalized_name = " ".join(name.split())
    normalized_email = normalize_email(email)
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
        id=client.id,
        name=client.name,
        email=client.account.email,
        created_at=client.created_at,
    )


class ClientService:
    def create(self, session: Session, name: str, email: str) -> ClientSummary:
        normalized_name, normalized_email = validate_client_data(name, email)
        account = Account(email=normalized_email, account_active=True)
        client = Client(name=normalized_name, account=account)
        try:
            session.add(client)
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise DuplicateEmailError from error
        session.refresh(client, attribute_names=["account"])
        return summary_from_client(client)

    def list(self, session: Session, query: str | None = None) -> list[ClientSummary]:
        statement: Select[tuple[Client]] = select(Client).options(joinedload(Client.account))
        if query and (normalized_query := query.strip()):
            pattern = f"%{normalized_query}%"
            statement = statement.join(Client.account).where(
                or_(Client.name.ilike(pattern), Account.email.ilike(pattern))
            )
        clients = session.scalars(statement.order_by(Client.name, Client.id)).all()
        return [summary_from_client(client) for client in clients]

    def get(self, session: Session, client_id: UUID) -> ClientSummary | None:
        statement = select(Client).options(joinedload(Client.account)).where(Client.id == client_id)
        client = session.scalar(statement)
        return summary_from_client(client) if client else None
