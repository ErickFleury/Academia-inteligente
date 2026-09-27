"""Client registration, identity provisioning, and lookup business rules."""

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.clients.models import Account, Client, ClientIdentityReconciliation, PersonProfile
from app.modules.identity.keycloak_admin import (
    ClientIdentityProvisioner,
    KeycloakAdminClient,
    KeycloakIdentityConflictError,
    KeycloakProvisioningError,
)
from app.modules.identity.reconciliation import (
    identity_provisioned,
    lock_account,
    pending_records,
    queue_reconciliation,
    reconcile_account,
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
    ClientFollowRequest,
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
CREATE, LINK = "create", "link_existing"


class DuplicateEmailError(Exception):
    pass


class ClientValidationError(Exception):
    pass


class ClientIdentityProvisioningError(Exception):
    pass


class ClientIdentityConflictError(Exception):
    pass


@dataclass(frozen=True)
class ClientData:
    first_name: str
    surname: str
    email: str
    cpf: str
    phone: str
    postal_code: str
    street: str
    number: str
    complement: str | None
    neighborhood: str
    city: str
    state: str

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.surname}"


@dataclass(frozen=True)
class ClientSummary(ClientData):
    id: UUID
    client_active: bool
    identity_provisioned: bool
    created_at: datetime


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _required_text(value: str, field: str, maximum: int) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ClientValidationError(f"{field} is required")
    if len(normalized) > maximum:
        raise ClientValidationError(f"{field} must contain at most {maximum} characters")
    return normalized


def _optional_text(value: str | None, field: str, maximum: int) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    if len(normalized) > maximum:
        raise ClientValidationError(f"{field} must contain at most {maximum} characters")
    return normalized or None


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def normalize_cpf(value: str) -> str:
    cpf = _digits(value)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        raise ClientValidationError("A valid CPF is required")
    for length in (9, 10):
        total = sum(
            int(digit) * weight for digit, weight in zip(cpf[:length], range(length + 1, 1, -1))
        )
        digit = (total * 10) % 11
        if digit == 10:
            digit = 0
        if digit != int(cpf[length]):
            raise ClientValidationError("A valid CPF is required")
    return cpf


def normalize_phone(value: str) -> str:
    phone = _digits(value)
    if len(phone) not in {10, 11}:
        raise ClientValidationError("A valid phone number is required")
    return phone


def normalize_postal_code(value: str) -> str:
    postal_code = _digits(value)
    if len(postal_code) != 8:
        raise ClientValidationError("A valid CEP is required")
    return postal_code


def validate_client_data(
    *,
    first_name: str,
    surname: str,
    email: str,
    cpf: str,
    phone: str,
    postal_code: str,
    street: str,
    number: str,
    complement: str | None,
    neighborhood: str,
    city: str,
    state: str,
) -> ClientData:
    normalized_email = normalize_email(email)
    if not email_pattern.fullmatch(normalized_email):
        raise ClientValidationError("A valid e-mail address is required")
    if len(normalized_email) > 320:
        raise ClientValidationError("E-mail must contain at most 320 characters")
    normalized_state = state.strip().upper()
    if len(normalized_state) != 2 or not normalized_state.isalpha():
        raise ClientValidationError("A valid state is required")
    return ClientData(
        first_name=_required_text(first_name, "First name", 100),
        surname=_required_text(surname, "Surname", 200),
        email=normalized_email,
        cpf=normalize_cpf(cpf),
        phone=normalize_phone(phone),
        postal_code=normalize_postal_code(postal_code),
        street=_required_text(street, "Street", 200),
        number=_required_text(number, "Number", 40),
        complement=_optional_text(complement, "Complement", 200),
        neighborhood=_required_text(neighborhood, "Neighborhood", 150),
        city=_required_text(city, "City", 120),
        state=normalized_state,
    )


def summary_from_client(client: Client) -> ClientSummary:
    profile = client.account.person_profile
    if profile is None:
        raise ClientValidationError("Client personal data is unavailable")
    return ClientSummary(
        first_name=profile.first_name,
        surname=profile.surname,
        email=client.account.email,
        cpf=profile.cpf,
        phone=profile.phone,
        postal_code=profile.postal_code,
        street=profile.street,
        number=profile.number,
        complement=profile.complement,
        neighborhood=profile.neighborhood,
        city=profile.city,
        state=profile.state,
        id=client.id,
        client_active=client.active,
        identity_provisioned=identity_provisioned(client.account),
        created_at=client.created_at,
    )


class ClientService:
    def __init__(self, provisioner: ClientIdentityProvisioner | None = None) -> None:
        self.provisioner = provisioner or KeycloakAdminClient()

    def create(self, session: Session, data: ClientData) -> ClientSummary:
        email = data.email
        pending = session.scalar(
            select(ClientIdentityReconciliation).where(ClientIdentityReconciliation.email == email)
        )
        email_account = session.scalar(select(Account).where(Account.email == email))
        cpf_profile = session.scalar(select(PersonProfile).where(PersonProfile.cpf == data.cpf))
        if email_account is not None or cpf_profile is not None:
            if (
                email_account is None
                or cpf_profile is None
                or email_account.id != cpf_profile.account_id
                or email_account.client is not None
            ):
                raise DuplicateEmailError
            account = lock_account(session, email_account.id)
            if (
                account.client is not None
                or account.email != data.email
                or account.person_profile.cpf != data.cpf
            ):
                raise DuplicateEmailError
            account.account_active = True
            client = Client(name=account.person_profile.full_name, active=True, account=account)
            session.add(client)
            session.flush()
            queue_reconciliation(session, account)
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                raise ClientIdentityProvisioningError from error
            return summary_from_client(client)
        if pending is not None:
            if pending.operation != CREATE:
                raise ClientIdentityProvisioningError
            # Registrations attempted before the non-blocking flow have a
            # CREATE record but no local account/client. Preserve their
            # reconciliation identifier and convert them to the LINK path.
            account = Account(email=email, account_active=True)
            account.person_profile = self._person_profile(data)
            client = Client(name=data.name, active=True, account=account)
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

        account = Account(email=email, account_active=True)
        account.person_profile = self._person_profile(data)
        client = Client(name=data.name, active=True, account=account)
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
        statement: Select[tuple[Client]] = select(Client).options(
            joinedload(Client.account).joinedload(Account.person_profile)
        )
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
        if client is None:
            return None
        account = lock_account(session, client.account_id)
        # Do not replace legacy pending email intent when merely retrying.
        if not pending_records(session, account.id):
            queue_reconciliation(session, account)
        self._commit_client(session)
        try:
            reconcile_account(session, account.id, self.provisioner)
        except KeycloakIdentityConflictError as error:
            raise ClientIdentityConflictError from error
        except KeycloakProvisioningError as error:
            raise ClientIdentityProvisioningError from error
        return summary_from_client(client)

    def update(
        self,
        session: Session,
        client_id: UUID,
        *,
        first_name: str | None,
        surname: str | None,
        email: str | None,
        cpf: str | None,
        phone: str | None,
        postal_code: str | None,
        street: str | None,
        number: str | None,
        complement: str | None,
        complement_provided: bool,
        neighborhood: str | None,
        city: str | None,
        state: str | None,
        client_active: bool | None,
    ) -> ClientSummary | None:
        client = self._client(session, client_id)
        if client is None:
            return None
        if (
            all(
                value is None
                for value in (
                    first_name,
                    surname,
                    email,
                    cpf,
                    phone,
                    postal_code,
                    street,
                    number,
                    complement,
                    neighborhood,
                    city,
                    state,
                    client_active,
                )
            )
            and not complement_provided
        ):
            raise ClientValidationError("At least one client field must be provided")
        lock_account(session, client.account_id)
        profile = client.account.person_profile
        if profile is None:
            raise ClientValidationError("Client personal data is unavailable")
        data = validate_client_data(
            first_name=first_name if first_name is not None else profile.first_name,
            surname=surname if surname is not None else profile.surname,
            email=email if email is not None else client.account.email,
            cpf=cpf if cpf is not None else profile.cpf,
            phone=phone if phone is not None else profile.phone,
            postal_code=postal_code if postal_code is not None else profile.postal_code,
            street=street if street is not None else profile.street,
            number=number if number is not None else profile.number,
            complement=complement if complement_provided else profile.complement,
            neighborhood=neighborhood if neighborhood is not None else profile.neighborhood,
            city=city if city is not None else profile.city,
            state=state if state is not None else profile.state,
        )
        existing_profile = session.scalar(
            select(PersonProfile).where(
                PersonProfile.cpf == data.cpf, PersonProfile.account_id != client.account_id
            )
        )
        if existing_profile is not None:
            raise DuplicateEmailError
        if session.scalar(
            select(Account).where(Account.email == data.email, Account.id != client.account_id)
        ):
            raise DuplicateEmailError
        self._apply_person_profile(profile, data)
        client.name, client.account.email = data.name, data.email
        if client_active is not None:
            client.active = client_active
        client.account.account_active = bool(
            client.active or (client.account.employee and client.account.employee.active)
        )
        queue_reconciliation(session, client.account, refresh_intent=True)
        self._commit_client(session)
        if client.account.keycloak_subject:
            return self.provision_existing(session, client_id)
        return summary_from_client(client)

    def erase(self, session: Session, client_id: UUID) -> bool:
        """Irreversibly erase the approved client's local and Keycloak identity data."""
        client = self._client(session, client_id)
        if client is None:
            return False
        account = lock_account(session, client.account_id)
        shared = account.employee is not None
        subject = account.keycloak_subject
        if subject and not shared:
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
            (PostComment.client_id == client.id)
            | (PostComment.progress_update_id.in_(erased_post_ids))
        )
        session.execute(
            delete(SocialModerationAudit).where(
                SocialModerationAudit.target_id.in_(erased_comment_ids)
            )
        )
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
        session.execute(
            delete(SocialModerationAudit).where(
                SocialModerationAudit.target_id.in_(erased_comment_ids)
            )
        )
        session.execute(
            delete(ClientFollow).where(
                (ClientFollow.follower_client_id == client.id)
                | (ClientFollow.followed_client_id == client.id)
            )
        )
        session.execute(
            delete(ClientFollowRequest).where(
                (ClientFollowRequest.requester_client_id == client.id)
                | (ClientFollowRequest.requested_client_id == client.id)
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
        if shared:
            # Keep the provisioning marker even when it originated in client creation.
            # The employee retry endpoint can finish the same Account operation.
            queue_reconciliation(session, account, employee=True)
            account.account_active = account.employee.active
        else:
            session.execute(
                delete(ClientIdentityReconciliation).where(
                    ClientIdentityReconciliation.account_id == account.id
                )
            )
        session.delete(client)
        if not shared:
            session.delete(account)
        session.commit()
        if shared:
            session.expire(account, ["client"])
            if subject:
                try:
                    reconcile_account(session, account.id, self.provisioner)
                except KeycloakProvisioningError as error:
                    raise ClientIdentityProvisioningError from error
        return True

    @staticmethod
    def _client(session: Session, client_id: UUID) -> Client | None:
        return session.scalar(
            select(Client)
            .options(
                joinedload(Client.account).joinedload(Account.person_profile),
                joinedload(Client.account).joinedload(Account.employee),
            )
            .where(Client.id == client_id)
        )

    @staticmethod
    def _person_profile(data: ClientData) -> PersonProfile:
        return PersonProfile(
            first_name=data.first_name,
            surname=data.surname,
            cpf=data.cpf,
            phone=data.phone,
            postal_code=data.postal_code,
            street=data.street,
            number=data.number,
            complement=data.complement,
            neighborhood=data.neighborhood,
            city=data.city,
            state=data.state,
        )

    @staticmethod
    def _apply_person_profile(profile: PersonProfile, data: ClientData) -> None:
        profile.first_name = data.first_name
        profile.surname = data.surname
        profile.cpf = data.cpf
        profile.phone = data.phone
        profile.postal_code = data.postal_code
        profile.street = data.street
        profile.number = data.number
        profile.complement = data.complement
        profile.neighborhood = data.neighborhood
        profile.city = data.city
        profile.state = data.state

    @staticmethod
    def _commit_client(session: Session) -> None:
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise DuplicateEmailError from error
