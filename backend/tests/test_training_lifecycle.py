from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from training_fixtures import instructor

from app.database import Base
from app.modules.clients.models import Account, Client
from app.modules.training.models import TrainingPlan, TrainingPlanVersion
from app.modules.training.schema import TrainingPlanItemInput, TrainingPlanVersionInput
from app.modules.training.service import (
    ActiveTrainingProposalExistsError,
    ConcurrentTrainingUpdateError,
    ImmutableTrainingVersionError,
    TrainingLifecycleService,
)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    value = sessionmaker(bind=engine, expire_on_commit=False)()
    instructor(value, "instructor-1")
    instructor(value, "instructor-2", "Outra")
    try:
        yield value
    finally:
        value.close()
        Base.metadata.drop_all(engine)


def data(name: str = "Força") -> TrainingPlanVersionInput:
    return TrainingPlanVersionInput(
        name=name,
        objective="Ganhar força",
        items=[
            TrainingPlanItemInput(
                exercise_name="Agachamento",
                sets=3,
                repetitions="8",
                load_guidance="Carga confortável",
                rest_seconds=90,
            )
        ],
    )


def client_id(session: Session):
    client = Client(
        name="Cliente",
        account=Account(
            email="client@example.test", keycloak_subject="client", account_active=True
        ),
    )
    session.add(client)
    session.commit()
    return client.id


def test_initial_proposal_approval_activation_and_immutable_history(session: Session) -> None:
    service = TrainingLifecycleService()
    initial = service.create_proposal(
        session,
        client_id=client_id(session),
        data=data(),
        created_by="instructor-1",
        origin="instructor",
    )
    assert initial.version_number == 1 and initial.status == "proposal"
    approved = service.approve(
        session,
        plan_id=initial.plan_id,
        version_number=1,
        actor="instructor-1",
        expected_revision=1,
    )
    current = approved
    assert current.status == "current" and current.approved_by == "instructor-1"
    with pytest.raises(ImmutableTrainingVersionError):
        service.revise(
            session,
            plan_id=current.plan_id,
            version_number=1,
            data=data("Outro"),
            actor="instructor-1",
            expected_revision=1,
        )


def test_client_cannot_have_two_proposals_even_with_different_origins(session: Session) -> None:
    service = TrainingLifecycleService()
    client = client_id(session)
    first = service.create_proposal(
        session,
        client_id=client,
        data=data("Rascunho do instrutor"),
        created_by="instructor-1",
        origin="instructor",
    )

    with pytest.raises(ActiveTrainingProposalExistsError):
        service.create_proposal(
            session,
            client_id=client,
            data=data("Rascunho da IA"),
            created_by="ai",
            origin="ai",
        )

    assert service.find_proposal(session, client_id=client).id == first.id


def test_new_current_supersedes_previous_and_conflicts_are_rejected(session: Session) -> None:
    service = TrainingLifecycleService()
    first = service.create_proposal(
        session,
        client_id=client_id(session),
        data=data(),
        created_by="instructor-1",
        origin="instructor",
    )
    first = service.approve(
        session, plan_id=first.plan_id, version_number=1, actor="instructor-1", expected_revision=1
    )
    second = service.create_revision(
        session,
        plan_id=first.plan_id,
        version_number=1,
        data=data("Evolução"),
        actor="instructor-2",
    )
    with pytest.raises(ConcurrentTrainingUpdateError):
        service.revise(
            session,
            plan_id=second.plan_id,
            version_number=2,
            data=data(),
            actor="instructor-2",
            expected_revision=99,
        )
    second = service.approve(
        session, plan_id=second.plan_id, version_number=2, actor="instructor-2", expected_revision=1
    )
    statuses = session.scalars(
        select(TrainingPlanVersion.status)
        .where(TrainingPlanVersion.plan_id == first.plan_id)
        .order_by(TrainingPlanVersion.version_number)
    ).all()
    assert statuses == ["superseded", "current"]


def test_activating_a_different_plan_supersedes_the_client_previous_current_plan(
    session: Session,
) -> None:
    service = TrainingLifecycleService()
    client = client_id(session)
    first = service.create_proposal(
        session,
        client_id=client,
        data=data("Primeiro"),
        created_by="instructor-1",
        origin="instructor",
    )
    first = service.approve(
        session, plan_id=first.plan_id, version_number=1, actor="instructor-1", expected_revision=1
    )
    second = service.create_proposal(
        session,
        client_id=client,
        data=data("Segundo"),
        created_by="instructor-1",
        origin="instructor",
    )
    second = service.approve(
        session, plan_id=second.plan_id, version_number=1, actor="instructor-1", expected_revision=1
    )
    assert first.status == "superseded"
    assert (
        session.scalar(
            select(TrainingPlanVersion.status).where(TrainingPlanVersion.plan_id == second.plan_id)
        )
        == "current"
    )
    plans = session.scalars(select(TrainingPlan).where(TrainingPlan.client_id == client)).all()
    assert [plan.is_current for plan in plans] == [False, True]
