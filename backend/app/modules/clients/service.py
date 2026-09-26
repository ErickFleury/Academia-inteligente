"""Client registration, identity provisioning, and lookup business rules."""

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.clients.models import Account, Client, ClientIdentityReconciliation
from app.modules.identity.keycloak_admin import (
    ClientIdentityProvisioner,
    KeycloakAdminClient,
    KeycloakIdentityConflictError,
    KeycloakProvisioningError,
)
from app.modules.occupancy.models import AccessPassageEvent, ClientAccessReference
from app.modules.onboarding.models import (
    Onboarding,
    OnboardingAiConversation,
    OnboardingAiMessage,
    OnboardingAuditEvent,
    OnboardingInvitation,
)
from app.modules.presence.models import ProfilePresenceConsentAudit, ProfilePresencePreference
from app.modules.progress.models import ProgressUpdate
from app.modules.social.models import (
    ClientFollow,
    CommentImage,
    PostComment,
    PostImage,
    PostLike,
    ProfileImage,
    SocialModerationAudit,
    SocialProfile,
)
from app.modules.training.models import (
    TrainingAdaptationOperation,
    TrainingAdaptationProposal,
    TrainingAiConversation,
    TrainingAiMessage,
    TrainingPlan,
    TrainingPlanItem,
    TrainingPlanVersion,
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
        if session.scalar(select(Account).where(Account.email == email)):
            raise DuplicateEmailError
        if pending is not None:
            if pending.operation != CREATE:
                raise ClientIdentityProvisioningError
            # Registrations attempted before the non-blocking flow have a
            # CREATE record but no local account/client. Preserve their
            # reconciliation identifier and convert them to the LINK path.
            client = Client(name=name, account=Account(email=email, account_active=True))
            session.add(client)
            session.flush()
            pending.operation = LINK
            pending.name = None
            pending.account_id = client.account.id
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise ClientIdentityProvisioningError from error
            session.refresh(client, attribute_names=["account"])
            return summary_from_client(client)

        client = Client(name=name, account=Account(email=email, account_active=True))
        session.add(client)
        session.flush()
        pending = ClientIdentityReconciliation(
            operation=LINK, email=email, account_id=client.account.id
        )
        session.add(pending)
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
        elif email != client.account.email:
            if session.scalar(select(Account).where(Account.email == email)):
                raise DuplicateEmailError
            pending = session.scalar(
                select(ClientIdentityReconciliation).where(
                    ClientIdentityReconciliation.account_id == client.account.id
                )
            )
            if pending is not None:
                pending.email = email
        client.name, client.account.email = name, email
        if account_active is not None:
            client.account.account_active = account_active
        self._commit_client(session)
        return summary_from_client(client)

    def erase(self, session: Session, client_id: UUID) -> bool:
        """Irreversibly erase the approved client's local and Keycloak identity data."""
        client = self._client(session, client_id)
        if client is None:
            return False
        subject = client.account.keycloak_subject
        if subject:
            self.provisioner.delete_identity(subject)
        conversation_ids = select(OnboardingAiConversation.id).where(
            OnboardingAiConversation.client_id == client.id
        )
        training_conversation_ids = select(TrainingAiConversation.id).where(
            TrainingAiConversation.client_id == client.id
        )
        proposal_ids = select(TrainingAdaptationProposal.id).where(
            TrainingAdaptationProposal.client_id == client.id
        )
        version_ids = select(TrainingPlanVersion.id).where(
            TrainingPlanVersion.client_id == client.id
        )
        session.execute(
            delete(OnboardingAiMessage).where(
                OnboardingAiMessage.conversation_id.in_(conversation_ids)
            )
        )
        session.execute(
            delete(OnboardingAiConversation).where(OnboardingAiConversation.client_id == client.id)
        )
        session.execute(
            delete(OnboardingAuditEvent).where(OnboardingAuditEvent.client_id == client.id)
        )
        session.execute(
            delete(OnboardingInvitation).where(OnboardingInvitation.client_id == client.id)
        )
        session.execute(delete(Onboarding).where(Onboarding.client_id == client.id))
        session.execute(
            delete(TrainingAiMessage).where(
                TrainingAiMessage.conversation_id.in_(training_conversation_ids)
            )
        )
        session.execute(
            delete(TrainingAiConversation).where(TrainingAiConversation.client_id == client.id)
        )
        session.execute(
            delete(TrainingAdaptationOperation).where(
                TrainingAdaptationOperation.proposal_id.in_(proposal_ids)
            )
        )
        session.execute(
            delete(TrainingAdaptationProposal).where(
                TrainingAdaptationProposal.client_id == client.id
            )
        )
        session.execute(
            delete(TrainingPlanItem).where(TrainingPlanItem.version_id.in_(version_ids))
        )
        session.execute(
            delete(TrainingPlanVersion).where(TrainingPlanVersion.client_id == client.id)
        )
        session.execute(delete(TrainingPlan).where(TrainingPlan.client_id == client.id))
        erased_post_ids = select(ProgressUpdate.id).where(ProgressUpdate.client_id == client.id)
        erased_comment_ids = select(PostComment.id).where(
            (PostComment.client_id == client.id) | (PostComment.progress_update_id.in_(erased_post_ids))
        )
        session.execute(delete(SocialModerationAudit).where(SocialModerationAudit.target_id.in_(erased_comment_ids)))
        session.execute(delete(PostLike).where(PostLike.client_id == client.id))
        session.execute(delete(PostLike).where(PostLike.progress_update_id.in_(erased_post_ids)))
        session.execute(delete(CommentImage).where(CommentImage.comment_id.in_(erased_comment_ids)))
        session.execute(delete(PostImage).where(PostImage.progress_update_id.in_(erased_post_ids)))
        session.execute(delete(PostComment).where(PostComment.client_id == client.id))
        session.execute(
            delete(PostComment).where(PostComment.progress_update_id.in_(erased_post_ids))
        )
        session.execute(
            delete(SocialModerationAudit).where(SocialModerationAudit.target_id == client.id)
        )
        session.execute(
            delete(SocialModerationAudit).where(
                SocialModerationAudit.target_id.in_(erased_post_ids)
            )
        )
        session.execute(delete(SocialModerationAudit).where(SocialModerationAudit.target_id.in_(erased_comment_ids)))
        session.execute(
            delete(ClientFollow).where(
                (ClientFollow.follower_client_id == client.id)
                | (ClientFollow.followed_client_id == client.id)
            )
        )
        session.execute(delete(ProfileImage).where(ProfileImage.client_id == client.id))
        session.execute(delete(SocialProfile).where(SocialProfile.client_id == client.id))
        session.execute(delete(ProgressUpdate).where(ProgressUpdate.client_id == client.id))
        session.execute(
            delete(ProfilePresenceConsentAudit).where(
                ProfilePresenceConsentAudit.client_id == client.id
            )
        )
        session.execute(
            delete(ProfilePresencePreference).where(
                ProfilePresencePreference.client_id == client.id
            )
        )
        session.execute(delete(AccessPassageEvent).where(AccessPassageEvent.client_id == client.id))
        session.execute(
            delete(ClientAccessReference).where(ClientAccessReference.client_id == client.id)
        )
        session.execute(
            delete(ClientIdentityReconciliation).where(
                ClientIdentityReconciliation.account_id == client.account.id
            )
        )
        session.delete(client)
        session.delete(client.account)
        session.commit()
        return True

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
