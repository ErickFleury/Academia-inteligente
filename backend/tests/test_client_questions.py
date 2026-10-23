"""Render personal-data clarifications from fields, never agent-facing instructions."""

from uuid import uuid4

from test_assistant_runtime import Agent
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_training_clarifications import setup_chat

from app.modules.training.chat_service import TrainingChatService
from app.modules.training.generation_service import InitialTrainingGenerationService


class IndirectAgent(Agent):
    def structured(self, context, instructions, schema, type_, *, role):
        if role == "initial_plan":
            detail = {
                "reason": "missing_client_information",
                "explanation": "Os trechos recuperados não trazem idade e experiência do cliente.",
                "next_step": "Peça ao cliente a idade, experiência e histórico de limitações.",
            }
            definition = schema["properties"]["clarification"]["anyOf"][0]
            if "missing_fields" in definition["properties"]:
                detail["missing_fields"] = [
                    "age",
                    "training_experience",
                    "limitations_or_complaints",
                ]
            self.schemas.append(schema)
            return type_.model_validate(
                {
                    "result": None,
                    "citation_ids": [],
                    "grounding": "clarification",
                    "clarification": detail,
                }
            )
        return super().structured(context, instructions, schema, type_, role=role)


def test_agent_instructions_and_known_onboarding_fields_never_reach_client(
    database_session, rollout
):
    setup_chat(database_session, rollout)
    agent = IndirectAgent(route={"query": "treinamento prescrição"})
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    state = service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    reply = state.messages[-1]
    assert reply.content == "Qual é sua idade?"
    assert reply.clarification["explanation"] == ""
    assert reply.clarification["missing_fields"] == ["age"]
    assert reply.clarification["initial_plan_requested"] is True
    options = agent.schemas[-1]["properties"]["clarification"]["anyOf"][0]["properties"][
        "missing_fields"
    ]["items"]["enum"]
    assert "training_experience" not in options and "limitations_or_complaints" not in options
    assert "target_exercise" not in options


def test_onboarding_false_flags_and_no_experience_are_answers():
    from app.modules.assistant.client_questions import available_fields

    remaining = available_fields(
        {
            "completed_onboarding": {
                "training_experience": "none",
                "has_health_conditions": False,
                "uses_medications": False,
                "has_limitations_or_complaints": False,
            }
        },
        {},
    )
    assert not {
        "training_experience",
        "health_conditions",
        "medications",
        "limitations_or_complaints",
        "current_limitation_impact",
    } & set(remaining)


def test_explicit_recent_answers_are_excluded_but_assistant_claims_are_not():
    from app.modules.assistant.client_questions import available_fields

    context = {
        "recent_messages": [
            {"role": "assistant", "content": "Tenho 35 anos."},
            {"role": "user", "content": "Talvez eu possa treinar três dias por semana."},
        ]
    }
    assert "age" in available_fields(context, {})
    assert "weekly_availability" in available_fields(context, {})
    context["current_user_message"] = (
        "Tenho 35 anos e posso treinar três dias por semana. Tenho 45 minutos para treino."
    )
    assert not {"age", "weekly_availability", "session_duration"} & set(
        available_fields(context, {})
    )


def test_uncertain_negated_or_third_party_age_is_not_an_answer():
    from app.modules.assistant.client_questions import available_fields

    for statement in [
        "Tenho 35 anos?",
        "Não tenho 35 anos.",
        "Meu pai tem 35 anos.",
        "35 anos é a idade do meu pai.",
        "Acho que tenho 35 anos.",
    ]:
        assert "age" in available_fields({"current_user_message": statement}, {})


def test_old_memory_does_not_establish_current_age():
    from app.modules.assistant.client_questions import available_fields

    context = {
        "current_date": "2026-10-23",
        "client_memory": [
            {"text": "Tenho 35 anos.", "reported_at": "2020-01-01T00:00:00+00:00"},
        ],
    }
    assert "age" in available_fields(context, {})
    context["client_memory"][0]["reported_at"] = "2026-10-22T00:00:00+00:00"
    assert "age" not in available_fields(context, {})


def test_invalid_empty_question_selection_never_exposes_internal_prose(database_session, rollout):
    from test_assistant_runtime import owner

    from app.modules.assistant.runtime import AssistantRun, Clarification, Route

    client = owner(database_session)
    run = AssistantRun(database_session, client.id, "training_chat")
    run.route = Route(specialist="training_chat", needs_references=False)
    run.unanswered_client_fields = ["age"]
    result = run._clarify(
        "specialist",
        Clarification(
            reason="missing_client_information",
            explanation="Internal explanation",
            next_step="Peça ao cliente a experiência",
            missing_fields=["training_experience"],
        ),
    )
    assert "Não consegui identificar" in result.assistant_message
    assert "Peça ao cliente" not in result.assistant_message
    assert run.clarification["reason"] == "unspecified"
    assert run.clarification["missing_fields"] == []
