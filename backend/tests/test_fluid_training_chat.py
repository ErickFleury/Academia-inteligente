"""The training assistant asks relevant questions beyond a fixed field catalog."""

from uuid import uuid4

from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_plan_evidence import passage
from test_training_chat import complete_onboarding

from app.modules.training.chat_service import TrainingChatService
from app.modules.training.generation_service import InitialTrainingGenerationService


class LocationAgent(Agent):
    def structured(self, context, instructions, schema, type_, *, role):
        if role == "orchestrator" and context.get("current_user_message") == "Em casa":
            self.route["answer_updates"] = [
                {
                    "field": "training_location",
                    "status": "answered",
                    "value": "Em casa",
                    "quote": "Em casa",
                    "source_index": context["answer_sources"][-1]["index"],
                }
            ]
        if role == "initial_plan":
            detail = {
                "reason": "missing_client_information",
                "explanation": "",
                "next_step": "Perguntar local",
            }
            if "questions" in schema["properties"]["clarification"]["anyOf"][0]["properties"]:
                detail["questions"] = [
                    {
                        "field": "training_location",
                        "text": "Você pretende treinar em casa, na academia ou ao ar livre?",
                    }
                ]
            return type_.model_validate(
                {
                    "result": None,
                    "grounding": "clarification",
                    "citation_ids": [],
                    "clarification": detail,
                }
            )
        return super().structured(context, instructions, schema, type_, role=role)


def test_model_can_ask_a_relevant_question_outside_the_old_catalog(database_session, rollout):
    owner(database_session)
    complete_onboarding(database_session, "owner")
    rollout.passages = [passage("Synthetic evidence")]
    agent = LocationAgent(route={"query": "atividade física exercícios"})
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    result = service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    assert (
        result.messages[-1].content == "Você pretende treinar em casa, na academia ou ao ar livre?"
    )


def test_natural_generation_intent_uses_existing_lifecycle(database_session, rollout):
    from sqlalchemy import select

    from app.modules.training.models import TrainingPlanVersion

    owner(database_session)
    complete_onboarding(database_session, "owner")
    rollout.passages = [passage("Synthetic supported prescription")]
    agent = Agent(route={"plan_action": "generate_initial_plan", "query": "prescrição exercícios"})
    agent.citations = ["R1"]
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    message = "Quero uma rotina organizada para começar na próxima semana."
    assert not service._requests_initial_plan(message, [])
    result = service.submit_for_subject(
        database_session, "owner", message=message, client_request_id=uuid4()
    )
    assert "Criei seu rascunho" in result.messages[-1].content
    assert database_session.scalar(select(TrainingPlanVersion)).status == "proposal"
    service.submit_for_subject(
        database_session, "owner", message=message, client_request_id=uuid4()
    )
    assert len(database_session.scalars(select(TrainingPlanVersion)).all()) == 1


def test_current_answers_survive_evidence_gap_and_transcript_expiry(database_session, rollout):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select
    from test_semantic_client_answers import FREE_REPLY, SemanticAgent

    from app.modules.assistant.runtime import AssistantRun
    from app.modules.memory.service import MemoryService
    from app.modules.training.models import TrainingAiConversation

    client = owner(database_session)
    complete_onboarding(database_session, "owner")
    agent = SemanticAgent()
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    rollout.passages = [passage("Synthetic reference")]
    service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    rollout.passages = []
    # Generation cannot proceed, but the current personal answers remain valid.
    result = service.submit_for_subject(
        database_session, "owner", message=FREE_REPLY, client_request_id=uuid4()
    )
    assert result.messages[-1].clarification["reason"] == "insufficient_evidence"
    facts = MemoryService.snapshot(database_session, client.id)["facts"]
    assert len(facts) == 5
    assert all("source_text" not in str(fact) for fact in facts)
    conversation = database_session.scalar(select(TrainingAiConversation))
    conversation.raw_expires_at = datetime.now(UTC) - timedelta(days=1)
    database_session.commit()
    service.purge_expired_content(database_session)
    run = AssistantRun(database_session, client.id, "initial_plan", provider=Agent())
    run.prepare({"current_user_message": "Gere meu treino"})
    assert not run.context.get("recent_messages")
    assert run.context["client_answers"]["age"]["value"] == 31
    assert run.context["client_answers"]["session_duration"]["value"] == 60


def test_dynamic_answer_and_forgetting(database_session, rollout):
    from sqlalchemy import select

    from app.modules.assistant.runtime import AssistantRun
    from app.modules.memory.models import ClientMemoryFact
    from app.modules.memory.service import MemoryService

    client = owner(database_session)
    complete_onboarding(database_session, "owner")
    rollout.passages = [passage("Synthetic evidence")]
    agent = LocationAgent(
        route={"query": "atividade física exercícios", "followup_action": "resume"}
    )
    # PlanRoute only: the first request and continuation both run generation.
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    service.submit_for_subject(
        database_session, "owner", message="Em casa", client_request_id=uuid4()
    )
    fact = database_session.scalar(select(ClientMemoryFact))
    assert fact.answer_data["field"] == "training_location"
    assert fact.answer_data["value"] == "Em casa"
    state = MemoryService.snapshot(database_session, client.id)
    MemoryService().edit(database_session, client.id, fact.id, state["revision"])
    run = AssistantRun(database_session, client.id, "training_chat", provider=Agent())
    context = service._context(
        database_session,
        client.id,
        service._conversation(database_session, client.id),
        "Continuar",
        uuid4(),
    )
    run.prepare(context)
    assert "training_location" not in run.context["client_answers"]


def test_older_same_chat_message_is_available_as_provenance(database_session, rollout):
    from app.modules.assistant.runtime import AssistantRun

    client = owner(database_session)
    service = TrainingChatService(Agent())
    service.submit_for_subject(
        database_session,
        "owner",
        message="Minha rotina permite treinar em casa.",
        client_request_id=uuid4(),
    )
    for _ in range(4):
        service.submit_for_subject(
            database_session, "owner", message="Obrigado", client_request_id=uuid4()
        )
    context = service._context(
        database_session,
        client.id,
        service._conversation(database_session, client.id),
        "Sobre minha rotina em casa",
        uuid4(),
    )
    agent = Agent()
    run = AssistantRun(database_session, client.id, "training_chat", provider=agent)
    run.prepare(context)
    sources = agent.calls[0][1]["answer_sources"]
    assert any(
        s["text"] == "Minha rotina permite treinar em casa." and s["event_id"] for s in sources
    )
    assert len(sources) <= 11


def test_technical_prescription_cannot_be_asked_as_personal_question():
    import pytest
    from pydantic import ValidationError

    from app.modules.assistant.client_questions import ClientQuestion

    with pytest.raises(ValidationError):
        ClientQuestion(field="dose", text="Quantas séries devo prescrever?")


def test_natural_draft_edit_is_grounded_and_never_approved(database_session, rollout):
    from test_training_lifecycle import data

    from app.modules.training.service import TrainingLifecycleService

    class EditAgent(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            result = super().structured(context, instructions, schema, type_, role=role)
            if role == "training_chat":
                result.result.draft_update = data("Rotina revista").model_dump(mode="json")
            return result

    client = owner(database_session)
    draft = TrainingLifecycleService().create_proposal(
        database_session, client_id=client.id, data=data(), created_by="ai", origin="ai"
    )
    agent = EditAgent(
        route={
            "plan_action": "edit_draft",
            "query": "prescrição exercícios",
            "needs_references": True,
        }
    )
    agent.citations = ["R1"]
    rollout.passages = [passage("Synthetic supported prescription")]
    result = TrainingChatService(agent).submit_for_subject(
        database_session,
        "owner",
        message="Essa versão precisa ficar mais alinhada à minha rotina.",
        client_request_id=uuid4(),
    )
    assert "Atualizei o rascunho" in result.messages[-1].content
    assert draft.status == "proposal" and draft.revision == 2


def test_continuation_command_is_not_a_personal_answer():
    from test_ordered_client_answers import question_context

    from app.modules.assistant.client_questions import client_answers

    assert not client_answers(question_context("pode continuar", ["current_limitation_impact"]))
    context = {
        "recent_messages": [
            {
                "role": "assistant",
                "content": "Onde você treina?",
                "clarification": {
                    "reason": "missing_client_information",
                    "missing_fields": ["training_location"],
                    "questions": [{"field": "training_location", "text": "Onde você treina?"}],
                },
            }
        ],
        "current_user_message": "gere meu treino",
    }
    assert not client_answers(context)


def test_compact_answers_cannot_restore_a_forgotten_source(database_session):
    from datetime import UTC, datetime, timedelta

    import pytest

    from app.modules.memory.service import MemoryError, MemoryService

    client = owner(database_session)
    memory = MemoryService()
    event_id = uuid4()
    occurred_at = datetime.now(UTC) - timedelta(days=1)
    answers = {
        "training_location": {
            "source_event_id": str(event_id),
            "source_text": "Em casa",
            "question": "Onde você treina?",
            "value": "Em casa",
        }
    }
    memory.apply(
        database_session,
        client.id,
        0,
        [],
        event_id=event_id,
        occurred_at=occurred_at,
        message="Em casa",
        answers=answers,
    )
    database_session.commit()
    state = memory.snapshot(database_session, client.id)
    cleared = memory.edit(database_session, client.id, state["facts"][0]["id"], state["revision"])
    with pytest.raises(MemoryError, match="memory_event_expired"):
        memory.apply(
            database_session,
            client.id,
            cleared["revision"],
            [],
            event_id=event_id,
            occurred_at=occurred_at,
            message="Em casa",
            answers=answers,
        )
    assert memory.snapshot(database_session, client.id)["facts"] == []
