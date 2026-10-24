"""A personal answer resumes its pending draft edit without repeating the question."""

from uuid import uuid4

import pytest
from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_plan_evidence import passage
from test_training_chat import complete_onboarding
from test_training_lifecycle import data

from app.modules.training.chat_service import TrainingChatService
from app.modules.training.models import TrainingAiMessage
from app.modules.training.service import TrainingLifecycleService

QUESTION = "Você tem alguma limitação que afete a subida de escadas?"
FIELD = "stair_climbing_limitations"
REQUEST = "Quero substituir a caminhada por subir escadas."


class ClarifyingEditor(Agent):
    followup = "resume"
    uncertain = False
    repeat_once = False

    def structured(self, context, instructions, schema, type_, *, role):
        if role == "orchestrator" and "allowed_specialist" in context:
            assert schema["properties"]["plan_action"]["enum"] == [
                "none",
                "edit_draft",
                "rebuild_draft",
            ]
            self.route = {
                "plan_action": "edit_draft",
                "query": "subir escadas",
                "needs_references": True,
            }
            if context.get("pending_draft_edit"):
                self.route["draft_followup_action"] = self.followup
                if self.followup == "resume":
                    self.route["answer_updates"] = [
                        {
                            "field": FIELD,
                            "status": "uncertain" if self.uncertain else "answered",
                            "value": None if self.uncertain else context["current_user_message"],
                            "quote": context["current_user_message"],
                            "source_index": context["answer_sources"][-1]["index"],
                        }
                    ]
        result = super().structured(context, instructions, schema, type_, role=role)
        if role == "training_chat" and context["rules"]["may_update_ai_draft"]:
            branches = schema["properties"]["result"]["anyOf"]
            assert {"type": "null"} in branches
            assert branches[0]["properties"]["draft_update"]["type"] == "object"
            if (
                context.get("client_answers", {}).get(FIELD, {}).get("value") is not None
                and not self.repeat_once
            ):
                result.result.draft_update = data("Subir escadas").model_dump(mode="json")
            else:
                self.repeat_once = False
                return type_.model_validate(
                    {
                        "result": None,
                        "grounding": "clarification",
                        "citation_ids": [],
                        "clarification": {
                            "reason": "missing_client_information",
                            "explanation": "",
                            "next_step": "Responder",
                            "questions": [{"field": FIELD, "text": QUESTION}],
                        },
                    }
                )
        return result


def setup_edit(session, rollout):
    client = owner(session)
    draft = TrainingLifecycleService().create_proposal(
        session, client_id=client.id, data=data(), created_by="ai", origin="ai"
    )
    rollout.passages = [passage("Synthetic supported prescription")]
    agent = ClarifyingEditor()
    agent.citations = ["R1"]
    return draft, agent, TrainingChatService(agent)


def test_freeform_answer_resumes_saved_edit_after_reload(database_session, rollout):
    from app.modules.memory.service import MemoryService

    draft, agent, service = setup_edit(database_session, rollout)
    complete_onboarding(database_session, "owner")
    first = service.submit_for_subject(
        database_session, "owner", message=REQUEST, client_request_id=uuid4()
    )
    detail = first.messages[-1].clarification
    assert detail["pending_draft_edit"]["draft_id"] == str(draft.id)
    assert detail["questions"] == [{"field": FIELD, "text": QUESTION}]
    assert QUESTION in first.messages[-1].content
    database_session.expire_all()
    request_id = uuid4()
    result = TrainingChatService(agent).submit_for_subject(
        database_session, "owner", message="não tenho limitações", client_request_id=request_id
    )
    assert "Atualizei o rascunho" in result.messages[-1].content
    assert QUESTION not in result.messages[-1].content
    assert draft.revision == 2 and draft.status == "proposal"
    assert result.messages[-1].clarification is None
    again = service.submit_for_subject(
        database_session, "owner", message="não tenho limitações", client_request_id=request_id
    )
    assert again == result and draft.revision == 2
    editor_context = [c for r, c, _ in agent.calls if r == "training_chat"][-1]
    assert editor_context["pending_draft_edit"]["request"] == REQUEST
    assert editor_context["client_answers"][FIELD]["value"] == "não tenho limitações"
    facts = MemoryService.snapshot(database_session, draft.client_id)["facts"]
    assert any((fact.get("answer_data") or {}).get("field") == FIELD for fact in facts)
    assert editor_context["authoritative_health_records"]["has_limitations_or_complaints"] is True
    assert (
        editor_context["authoritative_health_records"]["limitations_or_complaints"]
        == "Joelho sensível"
    )


@pytest.mark.parametrize(
    "action,message",
    [("cancel", "Não quero mais essa alteração."), ("chat", "Qual é o horário da academia?")],
)
def test_cancel_or_topic_change_does_not_resume_pending_edit(
    database_session, rollout, action, message
):
    draft, agent, service = setup_edit(database_session, rollout)
    service.submit_for_subject(
        database_session, "owner", message=REQUEST, client_request_id=uuid4()
    )
    agent.followup = action
    result = service.submit_for_subject(
        database_session, "owner", message=message, client_request_id=uuid4()
    )
    assert draft.revision == 1
    assert result.messages[-1].clarification is None
    assert QUESTION not in result.messages[-1].content


def test_stale_pending_edit_cannot_authorize_a_changed_draft(database_session, rollout):
    from sqlalchemy import select

    draft, agent, service = setup_edit(database_session, rollout)
    service.submit_for_subject(
        database_session, "owner", message=REQUEST, client_request_id=uuid4()
    )
    draft.revision += 1
    database_session.commit()
    conversation = database_session.scalar(select(TrainingAiMessage.conversation_id))
    from app.modules.training.models import TrainingAiConversation

    context = service._context(
        database_session,
        draft.client_id,
        database_session.get(TrainingAiConversation, conversation),
        "não tenho limitações",
        uuid4(),
    )
    assert context.get("pending_draft_edit") is None


def test_answered_question_is_repaired_instead_of_republished(database_session, rollout):
    draft, agent, service = setup_edit(database_session, rollout)
    service.submit_for_subject(
        database_session, "owner", message=REQUEST, client_request_id=uuid4()
    )
    agent.repeat_once = True
    result = service.submit_for_subject(
        database_session, "owner", message="não tenho limitações", client_request_id=uuid4()
    )
    assert "Atualizei o rascunho" in result.messages[-1].content
    assert draft.revision == 2
    assert any(
        c.get("draft_clarification_repair") for r, c, _ in agent.calls if r == "training_chat"
    )


def test_uncertain_answer_keeps_pending_request_until_resolved(database_session, rollout):
    draft, agent, service = setup_edit(database_session, rollout)
    first = service.submit_for_subject(
        database_session, "owner", message=REQUEST, client_request_id=uuid4()
    )
    agent.uncertain = True
    second = service.submit_for_subject(
        database_session, "owner", message="Não sei se tenho limitações.", client_request_id=uuid4()
    )
    assert draft.revision == 1
    assert (
        second.messages[-1].clarification["pending_draft_edit"]
        == first.messages[-1].clarification["pending_draft_edit"]
    )
    agent.uncertain = False
    third = service.submit_for_subject(
        database_session, "owner", message="não tenho limitações", client_request_id=uuid4()
    )
    assert draft.revision == 2 and "Atualizei o rascunho" in third.messages[-1].content


def test_pending_request_cannot_resolve_another_clients_event(database_session, rollout):
    from sqlalchemy import select
    from test_training_chat import create_client

    from app.modules.training.models import TrainingAiConversation

    draft, agent, service = setup_edit(database_session, rollout)
    service.submit_for_subject(
        database_session, "owner", message=REQUEST, client_request_id=uuid4()
    )
    assistant = database_session.scalar(
        select(TrainingAiMessage).where(TrainingAiMessage.role == "assistant")
    )
    own_chat = database_session.get(TrainingAiConversation, assistant.conversation_id)
    other = create_client(database_session, "other", "other@example.test")
    foreign_chat = TrainingAiConversation(client_id=other.id)
    database_session.add(foreign_chat)
    database_session.flush()
    foreign = TrainingAiMessage(
        conversation_id=foreign_chat.id, role="user", content="Private request", sequence=1
    )
    database_session.add(foreign)
    database_session.flush()
    assistant.clarification = {
        **assistant.clarification,
        "pending_draft_edit": {
            **assistant.clarification["pending_draft_edit"],
            "request_event_id": str(foreign.id),
        },
    }
    database_session.commit()
    context = service._context(
        database_session, draft.client_id, own_chat, "não tenho limitações", uuid4()
    )
    assert context["pending_draft_edit"] is None
    assert "Private request" not in str(context)


def test_replacement_request_does_not_keep_the_previous_pending_command(database_session, rollout):
    draft, agent, service = setup_edit(database_session, rollout)
    first = service.submit_for_subject(
        database_session, "owner", message=REQUEST, client_request_id=uuid4()
    )
    agent.followup = "replace"
    second = service.submit_for_subject(
        database_session,
        "owner",
        message="Quero outra alteração no rascunho.",
        client_request_id=uuid4(),
    )
    assert draft.revision == 1
    before = first.messages[-1].clarification["pending_draft_edit"]
    after = second.messages[-1].clarification["pending_draft_edit"]
    assert after["request_event_id"] != before["request_event_id"]
    assert after["draft_id"] == before["draft_id"]


def test_forgetting_after_clarification_invalidates_pending_request(database_session, rollout):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select
    from test_memory import add

    from app.modules.memory.service import MemoryService
    from app.modules.training.models import TrainingAiConversation

    draft, agent, service = setup_edit(database_session, rollout)
    add(database_session, draft.client_id, occurred_at=datetime.now(UTC) - timedelta(seconds=5))
    service.submit_for_subject(
        database_session, "owner", message=REQUEST, client_request_id=uuid4()
    )
    state = MemoryService.snapshot(database_session, draft.client_id)
    MemoryService().edit(
        database_session, draft.client_id, state["facts"][0]["id"], state["revision"]
    )
    database_session.commit()
    chat = database_session.scalar(
        select(TrainingAiConversation).where(TrainingAiConversation.client_id == draft.client_id)
    )
    context = service._context(
        database_session, draft.client_id, chat, "não tenho limitações", uuid4()
    )
    assert context["pending_draft_edit"] is None


def test_expired_request_cannot_be_resumed_from_a_newer_question(database_session, rollout):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.modules.training.models import TrainingAiConversation

    draft, agent, service = setup_edit(database_session, rollout)
    service.submit_for_subject(
        database_session, "owner", message=REQUEST, client_request_id=uuid4()
    )
    request = database_session.scalar(
        select(TrainingAiMessage).where(TrainingAiMessage.role == "user")
    )
    request.created_at = datetime.now(UTC) - timedelta(days=31)
    database_session.commit()
    service.purge_expired_content(database_session)
    chat = database_session.scalar(
        select(TrainingAiConversation).where(TrainingAiConversation.client_id == draft.client_id)
    )
    context = service._context(
        database_session, draft.client_id, chat, "não tenho limitações", uuid4()
    )
    assert context["pending_draft_edit"] is None
