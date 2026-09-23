from collections.abc import Generator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.modules.clients.models import Account, Client, ClientIdentityReconciliation
from app.modules.clients.service import ClientService
from app.modules.onboarding.models import (
    Onboarding,
    OnboardingAiConversation,
    OnboardingAiMessage,
    OnboardingAuditEvent,
    OnboardingInvitation,
)
from app.modules.progress.models import ProgressUpdate
from app.modules.training.models import (
    TrainingAdaptationOperation,
    TrainingAdaptationProposal,
    TrainingAiConversation,
    TrainingAiMessage,
    TrainingPlan,
    TrainingPlanItem,
    TrainingPlanVersion,
)


class DeletingProvisioner:
    def __init__(self) -> None:
        self.deleted_subjects: list[str] = []

    def delete_identity(self, subject: str) -> None:
        self.deleted_subjects.append(subject)


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


def test_erasure_removes_every_client_owned_record(session: Session) -> None:
    account = Account(
        email="erase@example.test", keycloak_subject="erase-subject", account_active=True
    )
    client = Client(name="Erase", account=account)
    session.add(client)
    session.flush()
    now = datetime.now(timezone.utc)
    onboarding = Onboarding(client_id=client.id, status="completed")
    session.add(onboarding)
    session.flush()
    onboarding_chat = OnboardingAiConversation(client_id=client.id)
    training_chat = TrainingAiConversation(client_id=client.id)
    plan = TrainingPlan(client_id=client.id, is_current=True)
    session.add_all([onboarding_chat, training_chat, plan])
    session.flush()
    version = TrainingPlanVersion(
        plan_id=plan.id,
        client_id=client.id,
        version_number=1,
        status="current",
        name="Plano",
        objective="Objetivo",
        origin="instructor",
        created_by="instructor",
    )
    session.add(version)
    session.flush()
    proposal = TrainingAdaptationProposal(
        client_id=client.id,
        base_version_id=version.id,
        source_client_request_id=uuid4(),
        client_request_id=uuid4(),
        reason="Razão",
        explanation="Explicação",
        status="proposed",
    )
    session.add_all(
        [
            OnboardingInvitation(
                client_id=client.id,
                purpose="onboarding",
                token_hash="a" * 64,
                issued_at=now,
                expires_at=now,
                delivery_status="sent",
            ),
            OnboardingAuditEvent(
                onboarding_id=onboarding.id,
                client_id=client.id,
                actor_account_id=account.id,
                action="saved",
                succeeded=True,
            ),
            OnboardingAiMessage(
                conversation_id=onboarding_chat.id, role="user", content="dados", sequence=1
            ),
            TrainingAiMessage(
                conversation_id=training_chat.id, role="user", content="chat", sequence=1
            ),
            TrainingPlanItem(
                version_id=version.id,
                position=1,
                exercise_name="Agachamento",
                sets=3,
                repetitions="8",
                load_guidance="Leve",
                rest_seconds=60,
            ),
            proposal,
            ProgressUpdate(client_id=client.id, content=None, visibility="shared", deleted_at=now),
            ClientIdentityReconciliation(
                operation="link_existing", email=account.email, account_id=account.id
            ),
        ]
    )
    session.flush()
    session.add(
        TrainingAdaptationOperation(
            proposal_id=proposal.id, position=1, operation_type="remove", target_position=1
        )
    )
    session.commit()

    provisioner = DeletingProvisioner()
    assert ClientService(provisioner=provisioner).erase(session, client.id) is True
    assert provisioner.deleted_subjects == ["erase-subject"]
    for model in (
        Account,
        Client,
        ClientIdentityReconciliation,
        Onboarding,
        OnboardingInvitation,
        OnboardingAuditEvent,
        OnboardingAiConversation,
        OnboardingAiMessage,
        TrainingPlan,
        TrainingPlanVersion,
        TrainingPlanItem,
        TrainingAiConversation,
        TrainingAiMessage,
        TrainingAdaptationProposal,
        TrainingAdaptationOperation,
        ProgressUpdate,
    ):
        assert session.scalars(select(model)).all() == []
