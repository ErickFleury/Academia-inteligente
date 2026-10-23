"""Short answers must use the preceding persisted question order."""

from uuid import uuid4

from sqlalchemy import select
from test_assistant_runtime import Agent, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_plan_evidence import passage
from test_training_chat import complete_onboarding

from app.modules.assistant.client_questions import render_questions
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.generation_service import InitialTrainingGenerationService
from app.modules.training.models import TrainingPlanVersion

FIELDS = [
    "age",
    "weekly_availability",
    "session_duration",
    "current_limitation_impact",
    "equipment_restrictions",
]


class QuestionsAgent(Agent):
    def structured(self, context, instructions, schema, type_, *, role):
        if role == "orchestrator" and "allowed_specialist" in context:
            self.route = {"query": "prescrição exercícios"}
            if context["allowed_specialist"] == "initial_plan":
                self.route["followup_action"] = "resume"
        result = super().structured(context, instructions, schema, type_, role=role)
        if role == "initial_plan":
            missing = [field for field in FIELDS if field in context["unanswered_client_fields"]]
            if missing:
                return type_.model_validate(
                    {
                        "result": None,
                        "citation_ids": [],
                        "grounding": "clarification",
                        "clarification": {
                            "reason": "missing_client_information",
                            "explanation": "",
                            "missing_fields": missing,
                            "next_step": "Responder",
                        },
                    }
                )
        return result


def test_ordered_reply_continues_plan_instead_of_repeating_all_questions(database_session, rollout):
    owner(database_session)
    complete_onboarding(database_session, "owner")
    rollout.passages = [passage("Synthetic supported prescription.")]
    agent = QuestionsAgent()
    agent.citations = ["R1"]
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    first = service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    assert first.messages[-1].content == render_questions(FIELDS)
    database_session.expire_all()
    request_id = uuid4()
    reply = service.submit_for_subject(
        database_session,
        "owner",
        message="31\n3\n1 hora\nnenhum\nnão",
        client_request_id=request_id,
    )
    assert "Criei seu rascunho" in reply.messages[-1].content
    assert database_session.scalar(select(TrainingPlanVersion)).status == "proposal"
    context = next(c for role, c, _ in reversed(agent.calls) if role == "initial_plan")
    assert context["client_answers"]["age"]["value"] == 31
    assert context["client_answers"]["weekly_availability"]["value"] == 3
    assert context["client_answers"]["session_duration"]["value"] == 60
    assert context["completed_onboarding"]["limitations_or_complaints"] == "Joelho sensível"
    calls = len(agent.calls)
    assert (
        service.submit_for_subject(
            database_session, "owner", message="ignored retry", client_request_id=request_id
        )
        == reply
    )
    assert len(agent.calls) == calls


def question_context(answer, fields=None):
    fields = FIELDS if fields is None else fields
    return {
        "current_date": "2026-10-23",
        "recent_messages": [
            {
                "role": "assistant",
                "content": render_questions(fields),
                "clarification": {"reason": "missing_client_information", "missing_fields": fields},
            }
        ],
        "current_user_message": answer,
    }


def test_ordered_binding_requires_the_actual_preceding_questions():
    from app.modules.assistant.client_questions import client_answers

    context = question_context("31\n3\n1 hora\nnenhum\nnão")
    assert len(client_answers(context)) == 5
    context["recent_messages"][0].pop("clarification")
    assert client_answers(context) == {}
    context = question_context("31\n3\n1 hora\nnenhum\nnão")
    context["recent_messages"].append({"role": "assistant", "content": "Outro assunto."})
    assert client_answers(context) == {}


def test_incomplete_or_mixed_lists_do_not_shift_answers():
    from app.modules.assistant.client_questions import client_answers

    for reply in [
        "31\n1 hora\nnenhum\nnão",
        "31\n3\n1 hora\nnenhum\nnão\nmais texto",
        "1) 31\n3\n1 hora\nnenhum\nnão",
    ]:
        assert client_answers(question_context(reply)) == {}


def test_numbered_partial_answers_match_the_explicit_question_index():
    from app.modules.assistant.client_questions import client_answers

    result = client_answers(question_context("3) 1,5 horas\n1) 31"))
    assert set(result) == {"age", "session_duration"}
    assert result["age"]["value"] == 31
    assert result["session_duration"]["value"] == 90
    assert result["session_duration"]["unit"] == "minutes"
    for reply in ["1) 31\n1) 32", "0) 31", "6) nada"]:
        assert client_answers(question_context(reply)) == {}


def test_uncertain_invalid_and_third_party_answers_remain_unresolved():
    from app.modules.assistant.client_questions import available_fields, client_answers

    context = question_context("Meu pai tem 31 anos\n9\n60\ntalvez nenhum\nnão sei")
    context["authoritative_health_records"] = {"has_limitations_or_complaints": True}
    context["client_answers"] = client_answers(context)
    assert all(item["value"] is None for item in context["client_answers"].values())
    assert set(FIELDS) <= set(available_fields(context, {}))


def test_earlier_answers_survive_a_partial_clarification_and_can_be_corrected():
    from app.modules.assistant.client_questions import client_answers

    context = question_context("31\n3\n1 hora\nnenhum\nnão")
    context["recent_messages"].extend(
        [
            {
                "role": "user",
                "content": context["current_user_message"],
                "created_at": "2026-10-23T12:00:00+00:00",
            },
            question_context("", ["weekly_availability"])["recent_messages"][0],
        ]
    )
    context["current_user_message"] = "4"
    answers = client_answers(context)
    assert answers["weekly_availability"]["value"] == 4
    assert answers["age"]["value"] == 31
    assert answers["age"]["reported_at"] == "2026-10-23T12:00:00+00:00"
    context["current_user_message"] = "não sei"
    assert client_answers(context)["weekly_availability"]["value"] is None


def test_only_unresolved_question_is_repeated_then_plan_resumes(database_session, rollout):
    owner(database_session)
    complete_onboarding(database_session, "owner")
    rollout.passages = [passage("Synthetic supported prescription.")]
    agent = QuestionsAgent()
    agent.citations = ["R1"]
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    partial = service.submit_for_subject(
        database_session,
        "owner",
        message="não sei\n3\n1 hora\nnenhum\nnão",
        client_request_id=uuid4(),
    )
    assert partial.messages[-1].content == "Qual é sua idade?"
    assert database_session.scalar(select(TrainingPlanVersion)) is None
    result = service.submit_for_subject(
        database_session, "owner", message="31", client_request_id=uuid4()
    )
    assert "Criei seu rascunho" in result.messages[-1].content
    review = next(c for role, c, _ in reversed(agent.calls) if "cited_passages" in c)
    assert review["client_constraints"]["client_answers"]["age"]["value"] == 31
    assert review["client_constraints"]["client_answers"]["session_duration"]["value"] == 60
    assert (
        review["client_constraints"]["authoritative_health_records"][
            "has_limitations_or_complaints"
        ]
        is True
    )
