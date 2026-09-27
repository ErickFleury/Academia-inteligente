"""Application-owned account and client persistence models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Account(Base):
    __tablename__ = "account"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    keycloak_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    account_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    password_recovery_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    client: Mapped["Client"] = relationship(back_populates="account", uselist=False)
    employee: Mapped["Employee"] = relationship(back_populates="account", uselist=False)
    person_profile: Mapped["PersonProfile | None"] = relationship(
        back_populates="account", uselist=False, cascade="all, delete-orphan"
    )


class PersonProfile(Base):
    """Authoritative personal data shared by future client/employee roles."""

    __tablename__ = "person_profile"

    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("account.id"), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    surname: Mapped[str] = mapped_column(String(200), nullable=False)
    cpf: Mapped[str] = mapped_column(String(11), unique=True, nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(11), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(8), nullable=False)
    street: Mapped[str] = mapped_column(String(200), nullable=False)
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    complement: Mapped[str | None] = mapped_column(String(200))
    neighborhood: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    account: Mapped[Account] = relationship(back_populates="person_profile")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.surname}"


class Client(Base):
    __tablename__ = "client"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("account.id"), unique=True, nullable=False
    )
    # Compatibility snapshot for existing domain modules. PersonProfile is the
    # only editable authority and ClientService always derives this value from it.
    name: Mapped[str] = mapped_column(String(300), index=True)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    account: Mapped[Account] = relationship(back_populates="client")


class Employee(Base):
    """Instructor specialization linked to an Account and shared PersonProfile."""

    __tablename__ = "employee"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("account.id"), unique=True, nullable=False
    )
    specialization: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="instructor"
    )
    cnpj: Mapped[str | None] = mapped_column(String(14))
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    account: Mapped[Account] = relationship(back_populates="employee")


class ClientIdentityReconciliation(Base):
    """Durable state for a client identity operation awaiting completion."""

    __tablename__ = "client_identity_reconciliation"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str | None] = mapped_column(String(200))
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("account.id"), unique=True
    )
    keycloak_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class EmployeeIdentityReconciliation(Base):
    __tablename__ = "employee_identity_reconciliation"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("account.id"), unique=True)
    keycloak_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
