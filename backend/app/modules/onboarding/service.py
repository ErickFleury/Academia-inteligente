"""Secure onboarding invitation issuance and later redemption support."""

from __future__ import annotations

import hashlib
import os
import secrets
import smtplib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.integrations.email import EmailSender, SmtpEmailSender
from app.modules.clients.models import Client
from app.modules.onboarding.models import OnboardingInvitation

INVITATION_PURPOSE = "onboarding_invitation"
INVITATION_LIFETIME = timedelta(hours=24)


class ClientInvitationUnavailableError(Exception):
    """The local client does not have a usable Task 06 identity."""


class InvitationDeliveryError(Exception):
    """The provider did not confirm onboarding invitation delivery."""


@dataclass(frozen=True)
class InvitationAccess:
    """A token-derived onboarding scope that never exposes client identity."""

    invitation: OnboardingInvitation | None
    status: str


@dataclass(frozen=True)
class InvitationSummary:
    id: UUID
    expires_at: datetime
    delivery_status: str
    sent_at: datetime | None


def current_time() -> datetime:
    return datetime.now(UTC)


def hash_token(raw_token: str) -> str:
    """Return the fixed-size database representation of a high-entropy token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def is_expired(expires_at: datetime, now: datetime) -> bool:
    """Compare timestamps safely with SQLite's timezone-naive test values."""
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    return expires_at <= now


class OnboardingInvitationService:
    def __init__(
        self,
        sender: EmailSender | None = None,
        clock: Callable[[], datetime] = current_time,
        token_factory: Callable[[int], str] = secrets.token_urlsafe,
        invitation_url: str | None = None,
    ) -> None:
        self._sender = sender or SmtpEmailSender()
        self._clock = clock
        self._token_factory = token_factory
        self._invitation_url = invitation_url or os.environ.get(
            "ONBOARDING_INVITATION_URL", "http://localhost:5173/onboarding"
        )

    def issue(self, session: Session, client_id: UUID) -> InvitationSummary:
        client = session.scalar(
            select(Client).options(joinedload(Client.account)).where(Client.id == client_id)
        )
        if client is None:
            raise LookupError
        if not client.account.keycloak_subject or not client.account.account_active:
            raise ClientInvitationUnavailableError

        now = self._clock()
        raw_token = self._token_factory(32)
        invitation = OnboardingInvitation(
            client_id=client.id,
            purpose=INVITATION_PURPOSE,
            token_hash=hash_token(raw_token),
            issued_at=now,
            expires_at=now + INVITATION_LIFETIME,
            delivery_status="pending",
        )
        session.execute(
            update(OnboardingInvitation)
            .where(
                OnboardingInvitation.client_id == client.id,
                OnboardingInvitation.purpose == INVITATION_PURPOSE,
                OnboardingInvitation.invalidated_at.is_(None),
                OnboardingInvitation.redeemed_at.is_(None),
            )
            .values(invalidated_at=now)
            .execution_options(synchronize_session="fetch")
        )
        session.add(invitation)
        session.commit()

        try:
            self._sender.send(
                recipient=client.account.email,
                subject="Convite para onboarding da Academia Inteligente",
                body=self._message_body(raw_token),
            )
        except (OSError, TimeoutError, smtplib.SMTPException) as error:
            invitation.delivery_status = "failed"
            invitation.failure_recorded_at = self._clock()
            session.commit()
            raise InvitationDeliveryError from error

        invitation.delivery_status = "sent"
        invitation.sent_at = self._clock()
        session.commit()
        return self._summary(invitation)

    def validate_for_client(
        self, session: Session, raw_token: str, client_id: UUID
    ) -> OnboardingInvitation | None:
        """Validate passively; this intentionally never consumes a token."""
        now = self._clock()
        return session.scalar(
            select(OnboardingInvitation).where(
                OnboardingInvitation.token_hash == hash_token(raw_token),
                OnboardingInvitation.client_id == client_id,
                OnboardingInvitation.purpose == INVITATION_PURPOSE,
                OnboardingInvitation.delivery_status == "sent",
                OnboardingInvitation.expires_at > now,
                OnboardingInvitation.redeemed_at.is_(None),
                OnboardingInvitation.invalidated_at.is_(None),
            )
        )

    def validate_access(self, session: Session, raw_token: str) -> InvitationAccess:
        """Passively classify one token without exposing its bound client.

        This lookup deliberately does not consume the token, so URL prefetching
        and mail scanners cannot invalidate an invitation.
        """
        invitation = session.scalar(
            select(OnboardingInvitation).where(
                OnboardingInvitation.token_hash == hash_token(raw_token),
                OnboardingInvitation.purpose == INVITATION_PURPOSE,
            )
        )
        if invitation is None:
            return InvitationAccess(invitation=None, status="invalid")

        if is_expired(invitation.expires_at, self._clock()):
            return InvitationAccess(invitation=invitation, status="expired")
        if (
            invitation.delivery_status != "sent"
            or invitation.redeemed_at is not None
            or invitation.invalidated_at is not None
        ):
            return InvitationAccess(invitation=invitation, status="invalid")
        return InvitationAccess(invitation=invitation, status="valid")

    def consume_access_after_redemption(self, session: Session, raw_token: str) -> bool:
        """Consume an invitation without accepting a caller-selected client id."""
        access = self.validate_access(session, raw_token)
        if access.status != "valid":
            return False
        if access.invitation is None:
            return False
        return self.consume_after_valid_redemption(session, raw_token, access.invitation.client_id)

    def consume_after_valid_redemption(
        self, session: Session, raw_token: str, client_id: UUID
    ) -> bool:
        """Atomically consume a token only after Task 08 accepts an intentional redemption."""
        now = self._clock()
        result = session.execute(
            update(OnboardingInvitation)
            .where(
                OnboardingInvitation.token_hash == hash_token(raw_token),
                OnboardingInvitation.client_id == client_id,
                OnboardingInvitation.purpose == INVITATION_PURPOSE,
                OnboardingInvitation.delivery_status == "sent",
                OnboardingInvitation.expires_at > now,
                OnboardingInvitation.redeemed_at.is_(None),
                OnboardingInvitation.invalidated_at.is_(None),
            )
            .values(redeemed_at=now)
            .execution_options(synchronize_session="fetch")
        )
        session.commit()
        return result.rowcount == 1

    def _message_body(self, raw_token: str) -> str:
        link = self._link_for(raw_token)
        return (
            "Você recebeu um convite para iniciar seu onboarding na Academia Inteligente.\n\n"
            f"Acesse o convite em até 24 horas: {link}\n\n"
            "Se você não solicitou este convite, ignore esta mensagem."
        )

    def _link_for(self, raw_token: str) -> str:
        parsed = urlsplit(self._invitation_url)
        query = urlencode({"token": raw_token})
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))

    @staticmethod
    def _summary(invitation: OnboardingInvitation) -> InvitationSummary:
        return InvitationSummary(
            id=invitation.id,
            expires_at=invitation.expires_at,
            delivery_status=invitation.delivery_status,
            sent_at=invitation.sent_at,
        )
