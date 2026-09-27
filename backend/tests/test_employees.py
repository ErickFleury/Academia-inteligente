from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.modules.clients.models import Account, Client, Employee, PersonProfile
from app.modules.clients.service import validate_client_data
from app.modules.employees.service import EmployeeService, normalize_cnpj


class FakeProvisioner:
    def __init__(self) -> None:
        self.first_access: list[bool] = []
        self.role_updates: list[set[str]] = []

    def ensure_employee_identity(
        self, email, first_name, surname, reconciliation_id, subject, roles, send_first_access
    ):
        self.first_access.append(send_first_access)
        self.role_updates.append(roles)
        return subject or "employee-subject"

    def update_client_identity(self, subject, email, first_name, surname):
        return None

    def reconcile_application_roles(self, subject, roles):
        self.role_updates.append(roles)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    current = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield current
    finally:
        current.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def person(**changes):
    data = {
        "first_name": "Maria",
        "surname": "Aparecida da Silva",
        "email": "maria@example.test",
        "cpf": "529.982.247-25",
        "phone": "11998765432",
        "postal_code": "01001000",
        "street": "Praça da Sé",
        "number": "1",
        "complement": None,
        "neighborhood": "Sé",
        "city": "São Paulo",
        "state": "SP",
    }
    data.update(changes)
    return validate_client_data(**data)


def test_instructor_can_share_an_active_client_account_and_reconcile_roles(
    session: Session,
) -> None:
    account = Account(email="maria@example.test", account_active=True)
    account.person_profile = PersonProfile(
        first_name="Maria",
        surname="Aparecida da Silva",
        cpf="52998224725",
        phone="11998765432",
        postal_code="01001000",
        street="Praça da Sé",
        number="1",
        complement=None,
        neighborhood="Sé",
        city="São Paulo",
        state="SP",
    )
    account.client = Client(name="Maria Aparecida da Silva", active=True)
    session.add(account)
    session.commit()
    fake = FakeProvisioner()
    service = EmployeeService(fake)

    employee = service.create(session, person(), "11.222.333/0001-81", "instructor")
    assert employee.employee_active is True
    assert session.scalar(select(Employee)).account_id == account.id
    service.provision_existing(session, employee.id)
    assert fake.first_access == [True]
    assert fake.role_updates[-1] == {"client", "employee", "instructor"}

    service.update(session, employee.id, None, None, False, False, None)
    assert fake.role_updates[-1] == {"client"}
    assert session.scalar(select(Account)).account_active is True


def test_existing_identity_does_not_repeat_first_access_email(session: Session) -> None:
    fake = FakeProvisioner()
    service = EmployeeService(fake)
    employee = service.create(session, person(), None, "instructor")
    stored = session.scalar(select(Employee))
    stored.account.keycloak_subject = "existing-subject"
    session.commit()

    service.provision_existing(session, employee.id)
    assert fake.first_access == []
    assert fake.role_updates == [{"employee", "instructor"}]


@pytest.mark.parametrize("cnpj", ["11.222.333/0001-81", "11222333000181"])
def test_valid_cnpj_is_normalized(cnpj: str) -> None:
    assert normalize_cnpj(cnpj) == "11222333000181"


def test_invalid_cnpj_is_rejected() -> None:
    with pytest.raises(Exception):
        normalize_cnpj("11.222.333/0001-80")
