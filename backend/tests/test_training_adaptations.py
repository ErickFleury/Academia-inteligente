from __future__ import annotations

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.integrations.ai import AiProviderError, AiTrainingAdaptationResponse
from app.modules.clients.models import Account, Client
from app.modules.training.adaptation_service import (
    AdaptationNotFoundError,
    AdaptationStateError,
    AdaptationUnavailableError,
    TrainingAdaptationService,
)
from app.modules.training.models import (
    TrainingAdaptationProposal,
    TrainingAiConversation,
    TrainingAiMessage,
    TrainingPlan,
    TrainingPlanItem,
    TrainingPlanVersion,
)
from app.modules.training.schema import ManualPlanCreate, TrainingPlanItemInput
from app.modules.training.service import TrainingLifecycleService


class FakeAdaptationProvider:
    def __init__(self, response: AiTrainingAdaptationResponse | Exception) -> None:
        self.response = response
        self.calls = 0
        self.contexts: list[dict[str, object]] = []

    def generate_adaptation(self, context: dict[str, object]) -> AiTrainingAdaptationResponse:
        self.calls += 1
        self.contexts.append(context)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class RetryAdaptationProvider(FakeAdaptationProvider):
    def __init__(self) -> None:
        super().__init__(adjust_response())
        self.fail_once = True

    def generate_adaptation(self, context: dict[str, object]) -> AiTrainingAdaptationResponse:
        self.calls += 1
        self.contexts.append(context)
        if self.fail_once:
            self.fail_once = False
            raise AiProviderError("timeout", retryable=True)
        return self.response


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    value = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield value
    finally:
        value.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def client(session: Session, subject: str, email: str) -> Client:
    value = Client(
        name=email.split("@")[0],
        account=Account(email=email, keycloak_subject=subject, account_active=True),
    )
    session.add(value)
    session.commit()
    return value


def current_plan(session: Session, owner: Client) -> TrainingPlanVersion:
    lifecycle = TrainingLifecycleService()
    proposal = lifecycle.create_proposal(
        session,
        client_id=owner.id,
        data=ManualPlanCreate(
            client_id=str(owner.id),
            name="Força",
            objective="Ganhar força",
            items=[
                TrainingPlanItemInput(
                    exercise_name="Agachamento",
                    sets=3,
                    repetitions="8",
                    load_guidance="Carga confortável",
                    rest_seconds=90,
                ),
                TrainingPlanItemInput(
                    exercise_name="Remada",
                    sets=3,
                    repetitions="10",
                    load_guidance="Carga confortável",
                    rest_seconds=60,
                ),
            ],
        ),
        created_by="instructor-1",
        origin="instructor",
    )
    approved = lifecycle.approve(
        session,
        plan_id=proposal.plan_id,
        version_number=proposal.version_number,
        actor="instructor-1",
        expected_revision=proposal.revision,
    )
    return lifecycle.activate(
        session,
        plan_id=approved.plan_id,
        version_number=approved.version_number,
        expected_revision=approved.revision,
    )


def source_message(session: Session, owner: Client, request_id: UUID) -> None:
    conversation = TrainingAiConversation(client_id=owner.id)
    session.add(conversation)
    session.flush()
    session.add(
        TrainingAiMessage(
            conversation_id=conversation.id,
            role="user",
            content="O agachamento incomoda meu joelho.",
            sequence=1,
            client_request_id=request_id,
        )
    )
    session.commit()


def adjust_response() -> AiTrainingAdaptationResponse:
    return AiTrainingAdaptationResponse(
        explanation="Vamos reduzir a exigência do agachamento para revisão profissional.",
        operations=[
            {
                "operation_type": "adjust",
                "target_position": 1,
                "item": {
                    "exercise_name": "Agachamento",
                    "sets": 2,
                    "repetitions": "8",
                    "load_guidance": "Carga leve e confortável",
                    "rest_seconds": 90,
                    "equipment_requirement": None,
                    "is_existing_exercise": True,
                },
            }
        ],
    )


def test_client_confirmed_adaptation_creates_one_new_current_version(
    session: Session,
) -> None:
    ada = client(session, "ada", "ada@example.test")
    old_current = current_plan(session, ada)
    source_id, adaptation_id = uuid4(), uuid4()
    source_message(session, ada, source_id)
    provider = FakeAdaptationProvider(adjust_response())
    service = TrainingAdaptationService(provider)

    proposal = service.generate(
        session,
        "ada",
        source_client_request_id=source_id,
        client_request_id=adaptation_id,
        reason="O exercício incomoda meu joelho.",
    )
    duplicate = service.generate(
        session,
        "ada",
        source_client_request_id=source_id,
        client_request_id=adaptation_id,
        reason="O exercício incomoda meu joelho.",
    )
    assert proposal.id == duplicate.id
    assert provider.calls == 1
    assert old_current.status == "current"
    assert "grace@example.test" not in str(provider.contexts[0])

    service.client_decide(session, "ada", proposal.id, True)
    approved = service.instructor_decide(session, proposal.id, "instructor-2", True)
    versions = list(
        session.scalars(
            select(TrainingPlanVersion)
            .where(TrainingPlanVersion.plan_id == old_current.plan_id)
            .order_by(TrainingPlanVersion.version_number)
        )
    )
    items = list(
        session.scalars(
            select(TrainingPlanItem)
            .where(TrainingPlanItem.version_id == approved.resulting_version_id)
            .order_by(TrainingPlanItem.position)
        )
    )
    assert approved.status == "approved"
    assert old_current.status == "superseded"
    assert [version.status for version in versions] == ["superseded", "current"]
    assert [item.exercise_name for item in items] == ["Agachamento", "Remada"]
    assert items[0].sets == 2 and items[1].sets == 3
    assert versions[-1].approved_by == "instructor-2"
    with pytest.raises(AdaptationStateError):
        service.instructor_decide(session, proposal.id, "instructor-2", True)
    assert len(versions) == 2


@pytest.mark.parametrize("operation_type", ["add", "remove", "replace"])
def test_supported_operation_types_are_persisted_without_catalog_mutation(
    session: Session, operation_type: str
) -> None:
    ada = client(session, "ada", "ada@example.test")
    current_plan(session, ada)
    source_id = uuid4()
    source_message(session, ada, source_id)
    item = {
        "exercise_name": "Leg Press",
        "sets": 3,
        "repetitions": "10",
        "load_guidance": "Carga moderada",
        "rest_seconds": 90,
        "equipment_requirement": "leg press machine",
        "is_existing_exercise": False,
    }
    provider = FakeAdaptationProvider(
        AiTrainingAdaptationResponse(
            explanation="Proposta para revisão.",
            operations=[
                {
                    "operation_type": operation_type,
                    "target_position": None if operation_type == "add" else 1,
                    "item": None if operation_type == "remove" else item,
                }
            ],
        )
    )
    proposal = TrainingAdaptationService(provider).generate(
        session,
        "ada",
        source_client_request_id=source_id,
        client_request_id=uuid4(),
        reason="Quero uma alternativa.",
    )
    assert proposal.status == "proposed"
    assert session.scalar(select(TrainingPlan).where(TrainingPlan.is_current)) is not None
    assert provider.calls == 1


def test_wrong_client_and_provider_failure_create_no_proposal(session: Session) -> None:
    ada = client(session, "ada", "ada@example.test")
    grace = client(session, "grace", "grace@example.test")
    current_plan(session, ada)
    current_plan(session, grace)
    source_id = uuid4()
    source_message(session, ada, source_id)
    service = TrainingAdaptationService(FakeAdaptationProvider(adjust_response()))
    with pytest.raises(AdaptationNotFoundError):
        service.generate(
            session,
            "grace",
            source_client_request_id=source_id,
            client_request_id=uuid4(),
            reason="Quero alterar.",
        )

    unavailable = TrainingAdaptationService(
        FakeAdaptationProvider(AiProviderError("configuration", retryable=False))
    )
    with pytest.raises(AdaptationUnavailableError):
        unavailable.generate(
            session,
            "ada",
            source_client_request_id=source_id,
            client_request_id=uuid4(),
            reason="Quero alterar.",
        )
    assert session.scalars(select(TrainingAdaptationProposal)).all() == []


def test_retryable_generation_failure_retries_once(session: Session) -> None:
    ada = client(session, "ada", "ada@example.test")
    current_plan(session, ada)
    source_id = uuid4()
    source_message(session, ada, source_id)
    provider = RetryAdaptationProvider()
    proposal = TrainingAdaptationService(provider).generate(
        session,
        "ada",
        source_client_request_id=source_id,
        client_request_id=uuid4(),
        reason="Quero ajustar o treino.",
    )
    assert proposal.status == "proposed"
    assert provider.calls == 2
