"""Real concurrent edits during model inference, using disposable schemas."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_knowledge_postgres import postgres_sessions as postgres_sessions
from test_knowledge_postgres import pytestmark as pytestmark
from test_memory import add
from test_training_chat import complete_onboarding
from test_training_generation import proposal

from app.integrations.ai_budget import current_budget
from app.modules.assistant.runtime import AssistantError
from app.modules.clients.models import Client
from app.modules.memory.service import MemoryService
from app.modules.training.chat_service import TrainingChatDraftUpdateError, TrainingChatService
from app.modules.training.generation_service import InitialTrainingGenerationService
from app.modules.training.models import TrainingAiMessage, TrainingPlan, TrainingPlanVersion
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.service import TrainingLifecycleService


@pytest.fixture
def plan_chat(postgres_sessions, rollout):
    with postgres_sessions() as session:
        owner(session)
        complete_onboarding(session, "owner")
    rollout.passages = [
        {
            "passage_id": str(uuid4()),
            "version_id": str(uuid4()),
            "source_id": str(uuid4()),
            "title": "Manual de treinamento",
            "version": 1,
            "location": "text",
            "content": "Toda proposta exige aprovação do instrutor.",
        }
    ]
    agent = Agent(route={"query": "treino", "needs_references": True})
    agent.citations = ["R1"]
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    return service, agent


def test_rag_plan_request_from_chat_commits_reply_and_one_proposal(postgres_sessions, plan_chat):
    service, agent = plan_chat
    request_id = uuid4()
    with postgres_sessions() as session:
        state = service.submit_for_subject(
            session, "owner", message="Quero criar um novo treino", client_request_id=request_id
        )
        assert "Criei seu rascunho" in state.messages[-1].content
    with postgres_sessions() as session:
        replay = service.submit_for_subject(
            session, "owner", message="Ignored retry", client_request_id=request_id
        )
        assert replay == state
        drafts = session.scalars(select(TrainingPlanVersion)).all()
        assert len(drafts) == 1 and drafts[0].status == "proposal"
        assert drafts[0].reference_citations
        assert len(session.scalars(select(TrainingAiMessage)).all()) == 2
    assert [call[0] for call in agent.calls] == ["orchestrator", "initial_plan", "orchestrator"]


@pytest.mark.parametrize("failure", ["provider", "equipment", "reply"])
def test_rag_plan_chat_failure_is_atomic_and_retryable(
    postgres_sessions, plan_chat, monkeypatch, failure
):
    service, agent = plan_chat
    request_id = uuid4()
    original_structured = agent.structured

    def structured(*args, **kwargs):
        output = original_structured(*args, **kwargs)
        if failure == "equipment" and kwargs["role"] == "initial_plan":
            output.result.plan["items"][0]["equipment_model_id"] = str(uuid4())
            output.result.plan["items"][0]["equipment_requirement"] = "Unavailable equipment"
        return output

    original_summary = service._bounded_summary

    def summary(session, conversation_id, exclude=None):
        if failure == "reply" and exclude is None:
            raise RuntimeError("simulated reply persistence failure")
        return original_summary(session, conversation_id, exclude)

    monkeypatch.setattr(agent, "structured", structured)
    monkeypatch.setattr(service, "_bounded_summary", summary)
    agent.fail = failure == "provider"
    error = {
        "provider": AssistantError,
        "equipment": TrainingChatDraftUpdateError,
        "reply": RuntimeError,
    }[failure]
    with postgres_sessions() as session:
        with pytest.raises(error):
            service.submit_for_subject(
                session, "owner", message="Quero criar um novo treino", client_request_id=request_id
            )
        session.rollback()
    with postgres_sessions() as session:
        assert not session.scalars(select(TrainingPlan)).all()
        assert not session.scalars(select(TrainingPlanVersion)).all()
        messages = session.scalars(select(TrainingAiMessage)).all()
        assert len(messages) == 1 and messages[0].role == "user"
        assert messages[0].client_request_id == request_id
    agent.fail = False
    monkeypatch.setattr(agent, "structured", original_structured)
    monkeypatch.setattr(service, "_bounded_summary", original_summary)
    with postgres_sessions() as session:
        service.submit_for_subject(
            session, "owner", message="Ignored retry", client_request_id=request_id
        )
    with postgres_sessions() as session:
        assert len(session.scalars(select(TrainingPlanVersion)).all()) == 1
        assert len(session.scalars(select(TrainingAiMessage)).all()) == 2


def test_rag_plan_chat_releases_lock_and_rejects_concurrent_memory_edit(
    postgres_sessions, plan_chat
):
    service, agent = plan_chat
    with postgres_sessions() as session:
        client_id = session.scalar(select(Client.id))
        initial = add(session, client_id, occurred_at=datetime.now(UTC) - timedelta(days=1))
    entered, resume = Event(), Event()

    def hold_inference():
        entered.set()
        assert resume.wait(8)

    agent.hook = hold_inference

    def conversation():
        with postgres_sessions() as session:
            return service.submit_for_subject(
                session, "owner", message="Quero criar um novo treino", client_request_id=uuid4()
            )

    with ThreadPoolExecutor(max_workers=1) as executor:
        task = executor.submit(conversation)
        assert entered.wait(5)
        try:
            with postgres_sessions() as direct:
                MemoryService().edit(
                    direct,
                    client_id,
                    initial["facts"][0]["id"],
                    initial["revision"],
                    "Prefiro treinar à tarde.",
                )
        finally:
            resume.set()
        with pytest.raises(AssistantError, match="memory_conflict"):
            task.result(timeout=5)
    with postgres_sessions() as session:
        assert not session.scalars(select(TrainingPlanVersion)).all()
        messages = session.scalars(select(TrainingAiMessage)).all()
        assert len(messages) == 1 and messages[0].role == "user"


@pytest.mark.parametrize("change", ["memory", "plan"])
def test_concurrent_edit_finishes_during_inference_and_invalidates_reply(postgres_sessions, change):
    with postgres_sessions() as session:
        client = owner(session)
        client_id = client.id
        initial = add(session, client_id, occurred_at=datetime.now(UTC) - timedelta(days=1))
        complete_onboarding(session, "owner")
        draft = InitialTrainingGenerationService(provider=Agent()).generate_for_subject(
            session, "owner"
        )
        plan_id, revision = draft.plan_id, draft.revision
        initial = MemoryService.snapshot(session, client_id)
    entered, resume = Event(), Event()
    provider = Agent()

    def hold_inference():
        entered.set()
        assert resume.wait(8)

    provider.hook = hold_inference

    def conversation():
        with postgres_sessions() as session:
            return TrainingChatService(provider).submit_for_subject(
                session, "owner", message="Olá", client_request_id=uuid4()
            )

    with ThreadPoolExecutor(max_workers=1) as executor:
        task = executor.submit(conversation)
        assert entered.wait(5)
        try:
            # Test connections have a 5s lock timeout. If inference still held
            # the client lock, this edit would fail before the model is resumed.
            with postgres_sessions() as direct:
                if change == "memory":
                    MemoryService().edit(
                        direct,
                        client_id,
                        initial["facts"][0]["id"],
                        initial["revision"],
                        "Prefiro treinar à tarde.",
                    )
                else:
                    TrainingLifecycleService().revise(
                        direct,
                        plan_id=plan_id,
                        version_number=1,
                        data=TrainingPlanVersionInput.model_validate(
                            proposal(name="Revisado pelo instrutor").plan
                        ),
                        actor="instructor",
                        expected_revision=revision,
                    )
        finally:
            resume.set()
        with pytest.raises(AssistantError, match="memory_conflict|assistant_state_conflict"):
            task.result(timeout=5)
    with postgres_sessions() as session:
        assert (
            session.scalar(select(TrainingAiMessage).where(TrainingAiMessage.role == "assistant"))
            is None
        )
        assert (
            session.scalar(select(TrainingAiMessage).where(TrainingAiMessage.role == "user"))
            is not None
        )


def test_commit_lock_wait_respects_remaining_request_deadline(postgres_sessions):
    with postgres_sessions() as session:
        client_id = owner(session).id
    with postgres_sessions() as blocker, postgres_sessions() as conversation:
        provider = Agent()

        def hold_client_lock():
            blocker.scalar(select(Client.id).where(Client.id == client_id).with_for_update())
            current_budget.get().started = monotonic() - 29.9

        provider.hook = hold_client_lock
        started = monotonic()
        with pytest.raises(AssistantError, match="deadline_exceeded"):
            TrainingChatService(provider).submit_for_subject(
                conversation, "owner", message="Olá", client_request_id=uuid4()
            )
        assert monotonic() - started < 1.5
        blocker.rollback()
    with postgres_sessions() as session:
        assert (
            session.scalar(select(TrainingAiMessage).where(TrainingAiMessage.role == "assistant"))
            is None
        )
