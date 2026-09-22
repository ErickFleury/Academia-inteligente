from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_database_session
from app.integrations.ai import AiProviderError, AiTrainingChatResponse
from app.modules.clients.models import Account, Client
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding.draft_service import OnboardingDraftService
from app.modules.onboarding.schema import OnboardingDraftUpdate
from app.modules.training.chat_service import (
    TrainingChatNotFoundError,
    TrainingChatService,
    TrainingChatUnavailableError,
)
from app.modules.training.models import TrainingAiConversation, TrainingAiMessage, TrainingPlan
from app.modules.training.schema import ManualPlanCreate, TrainingPlanItemInput
from app.modules.training.service import TrainingLifecycleService


class FakeProvider:
    def __init__(self, result: AiTrainingChatResponse | Exception) -> None:
        self.result = result
        self.calls = 0
        self.contexts: list[dict[str, object]] = []

    def training_chat(self, context: dict[str, object]) -> AiTrainingChatResponse:
        self.calls += 1
        self.contexts.append(context)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class RetryProvider(FakeProvider):
    def __init__(self) -> None:
        super().__init__(AiTrainingChatResponse(assistant_message="Vamos revisar seu exercício."))
        self.fail_once = True

    def training_chat(self, context: dict[str, object]) -> AiTrainingChatResponse:
        self.calls += 1
        self.contexts.append(context)
        if self.fail_once:
            self.fail_once = False
            raise AiProviderError("timeout", retryable=True)
        return self.result


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    value = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield value
    finally:
        value.close()
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


def create_current_plan(session: Session, client: Client) -> None:
    lifecycle = TrainingLifecycleService()
    proposal = lifecycle.create_proposal(
        session,
        client_id=client.id,
        data=ManualPlanCreate(
            client_id=str(client.id),
            name="Força inicial",
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
        ),
        created_by="instrutor",
        origin="instructor",
    )
    approved = lifecycle.approve(
        session,
        plan_id=proposal.plan_id,
        version_number=proposal.version_number,
        actor="instrutor",
        expected_revision=proposal.revision,
    )
    lifecycle.activate(
        session,
        plan_id=approved.plan_id,
        version_number=approved.version_number,
        expected_revision=approved.revision,
    )


def complete_onboarding(session: Session, subject: str) -> None:
    service = OnboardingDraftService()
    scope = service.resolve_client_scope(session, subject)
    service.save_draft(
        session,
        scope,
        OnboardingDraftUpdate(
            training_goal="Ganhar força",
            training_experience="beginner",
            height_cm=170,
            weight_kg="70.5",
            has_limitations_or_complaints=True,
            limitations_or_complaints="Joelho sensível",
            uses_medications=False,
            has_health_conditions=False,
        ),
    )
    service.complete_draft(session, scope)


def test_chat_is_client_scoped_persisted_and_never_mutates_plan(session: Session) -> None:
    ada = create_client(session, "ada", "ada@example.test")
    create_client(session, "grace", "grace@example.test")
    create_current_plan(session, ada)
    complete_onboarding(session, "ada")
    provider = FakeProvider(
        AiTrainingChatResponse(assistant_message="Faça o movimento com controle.")
    )
    service = TrainingChatService(provider)

    state = service.submit_for_subject(
        session, "ada", message="Como faço o agachamento?", client_request_id=uuid4()
    )

    assert [message.role for message in state.messages] == ["user", "assistant"]
    assert state.messages[-1].content == "Faça o movimento com controle."
    assert provider.contexts[0]["current_training_plan"] == {
        "name": "Força inicial",
        "objective": "Ganhar força",
        "items": [
            {
                "exercise_name": "Agachamento",
                "sets": 3,
                "repetitions": "8",
                "load_guidance": "Carga confortável",
                "rest_seconds": 90,
            }
        ],
    }
    assert "grace@example.test" not in str(provider.contexts[0])
    assert session.scalars(select(TrainingPlan)).all()[0].is_current is True
    with pytest.raises(TrainingChatNotFoundError):
        service.state_for_subject(session, "missing")
    assert service.state_for_subject(session, "grace").messages == []


def test_idempotent_message_does_not_call_provider_or_create_duplicates(session: Session) -> None:
    create_client(session, "ada", "ada@example.test")
    provider = FakeProvider(AiTrainingChatResponse(assistant_message="Resposta em português."))
    service = TrainingChatService(provider)
    request_id = uuid4()

    first = service.submit_for_subject(
        session, "ada", message="Tenho uma dúvida", client_request_id=request_id
    )
    second = service.submit_for_subject(
        session, "ada", message="Tenho uma dúvida", client_request_id=request_id
    )

    assert len(first.messages) == len(second.messages) == 2
    assert provider.calls == 1
    assert len(session.scalars(select(TrainingAiMessage)).all()) == 2


def test_retry_and_failure_leave_training_plan_unchanged(session: Session) -> None:
    ada = create_client(session, "ada", "ada@example.test")
    create_current_plan(session, ada)
    retry = RetryProvider()
    service = TrainingChatService(retry)
    service.submit_for_subject(
        session, "ada", message="Explique meu treino", client_request_id=uuid4()
    )
    assert retry.calls == 2

    unavailable = TrainingChatService(
        FakeProvider(AiProviderError("configuration", retryable=False))
    )
    with pytest.raises(TrainingChatUnavailableError):
        unavailable.submit_for_subject(
            session, "ada", message="Outra dúvida", client_request_id=uuid4()
        )
    plan = session.scalar(select(TrainingPlan).where(TrainingPlan.client_id == ada.id))
    assert plan is not None and plan.is_current is True


def test_expired_raw_chat_is_purged_without_deleting_training_plan(session: Session) -> None:
    ada = create_client(session, "ada", "ada@example.test")
    create_current_plan(session, ada)
    service = TrainingChatService(FakeProvider(AiTrainingChatResponse(assistant_message="Certo.")))
    service.submit_for_subject(session, "ada", message="Olá", client_request_id=uuid4())
    conversation = session.scalar(select(TrainingAiConversation))
    assert conversation is not None
    conversation.raw_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    for message in session.scalars(select(TrainingAiMessage)).all():
        message.created_at = datetime.now(UTC) - timedelta(days=31)
    session.commit()

    assert service.state_for_subject(session, "ada").messages == []
    plan = session.scalar(select(TrainingPlan).where(TrainingPlan.client_id == ada.id))
    assert plan is not None and plan.is_current is True
    assert session.scalar(select(TrainingAiConversation)).summary is None


def test_health_context_is_minimized_to_relevant_client_question(session: Session) -> None:
    create_client(session, "ada", "ada@example.test")
    complete_onboarding(session, "ada")
    provider = FakeProvider(AiTrainingChatResponse(assistant_message="Converse com seu instrutor."))
    service = TrainingChatService(provider)
    service.submit_for_subject(
        session, "ada", message="Explique minhas séries", client_request_id=UUID(int=1)
    )
    assert "limitations_or_complaints" not in provider.contexts[0]["relevant_onboarding"]
    service.submit_for_subject(
        session, "ada", message="Tenho dor no joelho", client_request_id=UUID(int=2)
    )
    assert (
        provider.contexts[1]["relevant_onboarding"]["limitations_or_complaints"]
        == "Joelho sensível"
    )


class FakeIdentityProvider:
    def __init__(self, identity: AuthenticatedIdentity) -> None:
        self.identity = identity

    def get_identity(self, access_token: str) -> AuthenticatedIdentity:
        del access_token
        return self.identity


def request_chat(app, authorization: str | None) -> int:
    sent: list[dict[str, object]] = []
    headers = [] if authorization is None else [(b"authorization", authorization.encode())]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/training/chat",
        "raw_path": b"/training/chat",
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    return next(message["status"] for message in sent if message["type"] == "http.response.start")


def test_raw_training_chat_endpoint_requires_the_client_role(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.main import create_app

    create_client(session, "ada", "ada@example.test")
    app = create_app()

    def override_database_session() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    assert request_chat(app, None) == 401
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(
            AuthenticatedIdentity("instructor", "i@example.test", ("instructor",))
        ),
    )
    assert request_chat(app, "Bearer token") == 403
    app.dependency_overrides.clear()
