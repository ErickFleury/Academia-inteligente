from collections.abc import Generator
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.modules.clients.models import Account, Client
from app.modules.onboarding.draft_service import (
    OnboardingDraftService,
    OnboardingDraftValidationError,
)
from app.modules.onboarding.models import Onboarding, OnboardingAuditEvent
from app.modules.onboarding.schema import OnboardingDraftUpdate


@pytest.fixture
def database_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def create_client(session: Session, subject: str, email: str) -> Client:
    client = Client(
        name=email.split("@")[0],
        account=Account(email=email, keycloak_subject=subject, account_active=True),
    )
    session.add(client)
    session.commit()
    return client


def scope_for(service: OnboardingDraftService, session: Session, subject: str):
    return service.resolve_client_scope(session, subject)


def test_partial_draft_is_created_and_reloaded_without_sensitive_audit_values(
    database_session: Session,
) -> None:
    service = OnboardingDraftService()
    client = create_client(database_session, "client-ada", "ada@example.test")
    scope = scope_for(service, database_session, "client-ada")

    saved = service.save_draft(
        database_session,
        scope,
        OnboardingDraftUpdate(training_goal="  Ganhar força  ", height_cm=170),
    )

    database_session.expire_all()
    reloaded = service.get_or_create_draft(database_session, scope)
    audit_events = database_session.scalars(select(OnboardingAuditEvent)).all()

    assert saved.client_id == client.id
    assert reloaded.training_goal == "Ganhar força"
    assert reloaded.height_cm == 170
    assert reloaded.weight_kg is None
    assert reloaded.status == "draft"
    assert [event.action for event in audit_events] == [
        "onboarding_draft_created",
        "onboarding_draft_saved",
    ]
    assert all("Ganhar força" not in str(event.__dict__) for event in audit_events)
    assert audit_events[-1].changed_fields == "height_cm,training_goal"


def test_valid_physical_data_persists_and_invalid_values_are_rejected(
    database_session: Session,
) -> None:
    service = OnboardingDraftService()
    create_client(database_session, "client-ada", "ada@example.test")
    scope = scope_for(service, database_session, "client-ada")

    saved = service.save_draft(
        database_session,
        scope,
        OnboardingDraftUpdate(height_cm=300, weight_kg=Decimal("499.99")),
    )

    assert saved.height_cm == 300
    assert saved.weight_kg == Decimal("499.99")
    with pytest.raises(ValidationError):
        OnboardingDraftUpdate(height_cm=0)
    with pytest.raises(ValidationError):
        OnboardingDraftUpdate(height_cm=301)
    with pytest.raises(ValidationError):
        OnboardingDraftUpdate(weight_kg=Decimal("500.01"))
    with pytest.raises(ValidationError):
        OnboardingDraftUpdate(weight_kg=Decimal("70.123"))


@pytest.mark.parametrize(
    ("boolean_field", "detail_field"),
    [
        ("has_limitations_or_complaints", "limitations_or_complaints"),
        ("uses_medications", "medications"),
        ("has_health_conditions", "health_conditions"),
    ],
)
def test_true_conditional_answers_require_nonblank_details(
    database_session: Session, boolean_field: str, detail_field: str
) -> None:
    service = OnboardingDraftService()
    create_client(database_session, "client-ada", "ada@example.test")
    scope = scope_for(service, database_session, "client-ada")

    with pytest.raises(OnboardingDraftValidationError):
        service.save_draft(database_session, scope, OnboardingDraftUpdate(**{boolean_field: True}))
    with pytest.raises(OnboardingDraftValidationError):
        service.save_draft(
            database_session,
            scope,
            OnboardingDraftUpdate(**{boolean_field: True, detail_field: "   "}),
        )

    saved = service.save_draft(
        database_session,
        scope,
        OnboardingDraftUpdate(**{boolean_field: True, detail_field: "Informação relatada"}),
    )
    assert getattr(saved, detail_field) == "Informação relatada"


def test_client_scope_isolation_and_ordinary_profile_models_do_not_contain_health_fields(
    database_session: Session,
) -> None:
    service = OnboardingDraftService()
    first = create_client(database_session, "client-ada", "ada@example.test")
    second = create_client(database_session, "client-grace", "grace@example.test")

    service.save_draft(
        database_session,
        scope_for(service, database_session, "client-ada"),
        OnboardingDraftUpdate(uses_medications=True, medications="Medicação privada"),
    )
    second_draft = service.get_or_create_draft(
        database_session, scope_for(service, database_session, "client-grace")
    )

    assert second_draft.client_id == second.id
    assert second_draft.medications is None
    assert database_session.scalar(
        select(Onboarding).where(Onboarding.client_id == first.id)
    ).medications == "Medicação privada"
    assert "medications" not in Client.__dict__
    assert "medications" not in Account.__dict__
    assert "health_conditions" not in Client.__dict__


def test_completion_boundary_requires_all_fields_and_conditional_details(
    database_session: Session,
) -> None:
    service = OnboardingDraftService()
    create_client(database_session, "client-ada", "ada@example.test")
    scope = scope_for(service, database_session, "client-ada")
    onboarding = service.get_or_create_draft(database_session, scope)

    with pytest.raises(OnboardingDraftValidationError):
        service.completion_data(onboarding)

    completed_ready = service.save_draft(
        database_session,
        scope,
        OnboardingDraftUpdate(
            training_goal="Melhorar condicionamento",
            training_experience="beginner",
            height_cm=170,
            weight_kg=Decimal("70.50"),
            has_limitations_or_complaints=False,
            uses_medications=False,
            has_health_conditions=True,
            health_conditions="Histórico relatado",
        ),
    )
    completion = service.completion_data(completed_ready)

    assert completion.training_goal == "Melhorar condicionamento"
    assert completion.health_conditions == "Histórico relatado"
