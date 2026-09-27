"""One reconciliation workflow for both roles of an application-owned Account.

The existing durable records remain compatible with interrupted older operations.
They are cleared together only after identity, first access, and roles succeed.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, object_session

from app.modules.clients.models import (
    Account,
    ClientIdentityReconciliation,
    EmployeeIdentityReconciliation,
)
from app.modules.identity.keycloak_admin import (
    ClientIdentityProvisioner,
    KeycloakIdentityConflictError,
    KeycloakProvisioningError,
)

Pending = ClientIdentityReconciliation | EmployeeIdentityReconciliation


def pending_records(session: Session, account_id: UUID) -> list[Pending]:
    records: list[Pending] = []
    for model in (ClientIdentityReconciliation, EmployeeIdentityReconciliation):
        records.extend(session.scalars(select(model).where(model.account_id == account_id)).all())
    return sorted(records, key=lambda item: (item.created_at, str(item.id)))


def identity_provisioned(account: Account) -> bool:
    session = object_session(account)
    return bool(
        account.keycloak_subject
        and session is not None
        and not pending_records(session, account.id)
    )


def lock_account(session: Session, account_id: UUID) -> Account:
    # All identity writers lock the same row, including the two provisioning endpoints.
    account = session.scalar(
        select(Account)
        .where(Account.id == account_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if account is None:
        raise KeycloakProvisioningError("Account no longer exists")
    session.expire(account, ["client", "employee", "person_profile"])
    # Callers may have eagerly loaded a role before waiting for this lock.
    # Refresh those identity-map objects so a concurrent change is not overwritten.
    for related in (account.client, account.employee, account.person_profile):
        if related is not None:
            session.refresh(related)
    return account


def queue_reconciliation(
    session: Session, account: Account, *, employee: bool = False, refresh_intent: bool = False
) -> None:
    """Enqueue in the same transaction as authoritative local changes; never call I/O."""
    with session.no_autoflush:
        records = pending_records(session, account.id)
    if not records:
        if employee:
            record = EmployeeIdentityReconciliation(account_id=account.id, email=account.email)
        else:
            record = ClientIdentityReconciliation(
                account_id=account.id, email=account.email, operation="sync"
            )
        session.add(record)
    elif refresh_intent:
        for record in records:
            record.email = account.email
            if isinstance(record, ClientIdentityReconciliation):
                record.operation = "sync"


def active_roles(account: Account) -> set[str]:
    roles: set[str] = set()
    if account.client and account.client.active:
        roles.add("client")
    if (
        account.employee
        and account.employee.active
        and account.employee.specialization == "instructor"
    ):
        roles.update({"employee", "instructor"})
    return roles


def reconcile_account(
    session: Session, account_id: UUID, provisioner: ClientIdentityProvisioner
) -> None:
    try:
        _reconcile_account(session, account_id, provisioner)
    except SQLAlchemyError as error:
        # Local intent was already committed before I/O. A failed completion
        # transaction must not erase that intent or expose database details.
        session.rollback()
        raise KeycloakProvisioningError("Identity reconciliation remains pending") from error


def _reconcile_account(
    session: Session, account_id: UUID, provisioner: ClientIdentityProvisioner
) -> None:
    account = lock_account(session, account_id)
    records = pending_records(session, account_id)
    if not records:
        # A concurrent successful retry may already have completed the work.
        session.commit()
        return
    profile = account.person_profile
    if profile is None:
        raise KeycloakProvisioningError("Account personal data is unavailable")
    # Preserve the intent of an email update queued by the previous implementation.
    for record in records:
        if isinstance(record, ClientIdentityReconciliation) and record.operation == "email_update":
            account.email = record.email
    roles = active_roles(account)
    try:
        if account.keycloak_subject:
            provisioner.update_client_identity(
                account.keycloak_subject, account.email, profile.first_name, profile.surname
            )
        else:
            # Older versions could leave two different markers on one Account.
            # Only markers persisted for THIS Account may recover an external user.
            for index, record in enumerate(records):
                try:
                    if account.employee:
                        subject = provisioner.ensure_employee_identity(
                            account.email,
                            profile.first_name,
                            profile.surname,
                            record.id,
                            record.keycloak_subject,
                            roles,
                            True,
                        )
                    else:
                        subject = provisioner.ensure_client_identity(
                            account.email,
                            profile.first_name,
                            profile.surname,
                            record.id,
                            record.keycloak_subject,
                        )
                    # Persist the external reference before the final role operation.
                    record.keycloak_subject = subject
                    break
                except KeycloakIdentityConflictError:
                    if index == len(records) - 1:
                        raise
                except KeycloakProvisioningError as error:
                    if error.subject:
                        record.keycloak_subject = error.subject
                    raise
            account.keycloak_subject = subject
        provisioner.reconcile_application_roles(account.keycloak_subject, roles)
    except KeycloakProvisioningError:
        # Keep the accepted local update and recovery marker, including any subject.
        session.commit()
        raise
    account.account_active = bool(roles)
    for record in records:
        session.delete(record)
    session.commit()
