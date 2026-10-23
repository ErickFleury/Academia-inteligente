"""Model interpretation is grounded in user messages, not fixed answer phrasing."""

from uuid import uuid4

from sqlalchemy import select
from test_assistant_runtime import owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_ordered_client_answers import QuestionsAgent
from test_plan_evidence import passage
from test_training_chat import complete_onboarding

from app.modules.training.chat_service import TrainingChatService
from app.modules.training.generation_service import InitialTrainingGenerationService
from app.modules.training.models import TrainingPlanVersion

FREE_REPLY = (
    "Acabei de fazer trinta e um. Consigo ir na terça, quinta e sábado. "
    "Uma horinha por visita está bom. Não tem movimento que me atrapalhe hoje. "
    "Posso usar todos os aparelhos."
)
INTERPRETATIONS = [
    ("age", "31", "Acabei de fazer trinta e um."),
    ("weekly_availability", "3", "Consigo ir na terça, quinta e sábado."),
    ("session_duration", "60", "Uma horinha por visita está bom."),
    (
        "current_limitation_impact",
        "Nenhum movimento relatado",
        "Não tem movimento que me atrapalhe hoje.",
    ),
    ("equipment_restrictions", "Nenhuma restrição relatada", "Posso usar todos os aparelhos."),
]


class SemanticAgent(QuestionsAgent):
    def __init__(self):
        super().__init__()
        self.interpretations = {FREE_REPLY: INTERPRETATIONS}
        self.action = "resume"

    def structured(self, context, instructions, schema, type_, *, role):
        result = super().structured(context, instructions, schema, type_, role=role)
        message = context.get("current_user_message")
        if role == "orchestrator" and "allowed_specialist" in context:
            if context.get("resume_initial_plan"):
                result.followup_action = self.action
        if role == "orchestrator" and message in self.interpretations:
            if "answer_updates" in schema["properties"]:
                source = context["answer_sources"][-1]["index"]
                result = type_.model_validate(
                    {
                        **result.model_dump(),
                        "answer_updates": [
                            {
                                "field": field,
                                "value": value,
                                "status": "answered",
                                "source_index": source,
                                "quote": quote,
                            }
                            for field, value, quote in self.interpretations[message]
                        ],
                    }
                )
        return result


def test_free_form_answers_generate_without_repeating_the_question_grid(database_session, rollout):
    owner(database_session)
    complete_onboarding(database_session, "owner")
    rollout.passages = [passage("Synthetic supported prescription.")]
    agent = SemanticAgent()
    agent.citations = ["R1"]
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    result = service.submit_for_subject(
        database_session, "owner", message=FREE_REPLY, client_request_id=uuid4()
    )
    assert "Criei seu rascunho" in result.messages[-1].content
    assert database_session.scalar(select(TrainingPlanVersion)).status == "proposal"
    context = next(c for role, c, _ in reversed(agent.calls) if role == "initial_plan")
    assert context["client_answers"]["age"]["value"] == 31
    assert context["client_answers"]["weekly_availability"]["value"] == 3
    assert context["client_answers"]["session_duration"]["value"] == 60
    assert context["completed_onboarding"]["has_limitations_or_complaints"] is True


def test_partial_free_form_answers_and_corrections_survive_history_window(
    database_session, rollout
):
    owner(database_session)
    complete_onboarding(database_session, "owner")
    rollout.passages = [passage("Synthetic supported prescription.")]
    agent = SemanticAgent()
    agent.citations = ["R1"]
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )

    def send(message):
        return service.submit_for_subject(
            database_session, "owner", message=message, client_request_id=uuid4()
        )

    send("Gere meu treino")
    steps = [
        ("Acabei de fazer trinta e um.", [("age", "31", "Acabei de fazer trinta e um.")]),
        (
            "Errei a idade: são trinta e dois. Vou na terça e quinta.",
            [
                ("age", "32", "Errei a idade: são trinta e dois."),
                ("weekly_availability", "2", "Vou na terça e quinta."),
            ],
        ),
        ("Uma horinha por visita está bom.", [INTERPRETATIONS[2]]),
        ("Não tem movimento que me atrapalhe hoje.", [INTERPRETATIONS[3]]),
        ("Posso usar todos os aparelhos.", [INTERPRETATIONS[4]]),
    ]
    for index, (message, updates) in enumerate(steps):
        agent.interpretations[message] = updates
        result = send(message)
        if index < len(steps) - 1:
            assert "idade" not in result.messages[-1].content
            assert result.messages[-1].clarification["client_answers"]["age"]["value"] == (
                31 if index == 0 else 32
            )
            database_session.expire_all()
    assert "Criei seu rascunho" in result.messages[-1].content
    context = next(c for role, c, _ in reversed(agent.calls) if role == "initial_plan")
    assert context["client_answers"]["age"]["value"] == 32
    assert context["client_answers"]["weekly_availability"]["value"] == 2


def test_topic_change_does_not_repeat_questions_or_generate(database_session, rollout):
    owner(database_session)
    complete_onboarding(database_session, "owner")
    rollout.passages = [passage("Synthetic supported prescription.")]
    agent = SemanticAgent()
    agent.citations = ["R1"]
    service = TrainingChatService(
        agent, generation_service=InitialTrainingGenerationService(provider=agent)
    )
    service.submit_for_subject(
        database_session, "owner", message="Gere meu treino", client_request_id=uuid4()
    )
    agent.action = "chat"
    result = service.submit_for_subject(
        database_session,
        "owner",
        message="Antes disso, o que significa hipertrofia?",
        client_request_id=uuid4(),
    )
    assert result.messages[-1].clarification is None
    assert "Qual é sua idade" not in result.messages[-1].content
    assert database_session.scalar(select(TrainingPlanVersion)) is None


def update(field="age", value="31", quote="Tenho trinta e um.", status="answered", source_index=0):
    from app.modules.assistant.answer_interpretation import AnswerUpdate

    return AnswerUpdate(
        field=field, value=value, quote=quote, status=status, source_index=source_index
    )


def test_interpretations_require_owned_literal_sources_and_valid_values():
    import pytest

    from app.modules.assistant.answer_interpretation import (
        InvalidAnswerInterpretation,
        apply_interpretations,
    )

    sources = [
        {"index": 0, "text": "Tenho trinta e um.", "reported_at": "2026-10-23T12:00:00+00:00"}
    ]
    for bad in [
        update(source_index=1),
        update(quote="Tenho cinquenta."),
        update(value="999"),
        update(value="adulto"),
    ]:
        with pytest.raises(InvalidAnswerInterpretation):
            apply_interpretations({}, [bad], sources)
    assert apply_interpretations({}, [update()], sources)["age"]["value"] == 31


def test_uncertainty_and_negation_cannot_be_dropped_from_a_quote():
    import pytest

    from app.modules.assistant.answer_interpretation import (
        InvalidAnswerInterpretation,
        apply_interpretations,
    )

    source = [{"index": 0, "text": "Talvez eu consiga três dias.", "reported_at": "2026-10-23"}]
    result = apply_interpretations(
        {}, [update("weekly_availability", "3", "consiga três dias.")], source
    )
    assert result["weekly_availability"]["value"] is None
    source[0]["text"] = "Não tenho 31 anos."
    with pytest.raises(InvalidAnswerInterpretation):
        apply_interpretations({}, [update(quote="tenho 31 anos.")], source)
    source[0]["text"] = "Meu pai tem 31 anos."
    with pytest.raises(InvalidAnswerInterpretation):
        apply_interpretations({}, [update(quote="31 anos.")], source)


def test_clear_clause_is_preserved_alongside_a_separate_uncertain_answer():
    from app.modules.assistant.answer_interpretation import apply_interpretations

    sources = [
        {
            "index": 0,
            "text": "Talvez eu consiga três dias, mas tenho trinta e um anos.",
            "reported_at": "2026-10-23",
        }
    ]
    result = apply_interpretations({}, [update(quote="tenho trinta e um anos.")], sources)
    assert result["age"]["value"] == 31


def test_saved_interpretations_do_not_cross_a_memory_reset():
    from app.modules.assistant.client_questions import client_answers

    context = {
        "answer_event_after": "2026-10-23T12:00:00+00:00",
        "recent_messages": [
            {
                "role": "assistant",
                "content": "Qual é sua idade?",
                "clarification": {
                    "client_answers": {
                        "weekly_availability": {
                            "value": 3,
                            "reported_at": "2026-10-23T11:00:00+00:00",
                        }
                    },
                },
            }
        ],
        "current_user_message": "Ainda não sei.",
    }
    assert client_answers(context) == {}


def test_a_new_uncertain_correction_reopens_only_that_field():
    from app.modules.assistant.answer_interpretation import apply_interpretations
    from app.modules.assistant.client_questions import available_fields

    previous = {
        "age": {"value": 31, "reported_at": "2026-10-22T12:00:00+00:00"},
        "weekly_availability": {"value": 3, "reported_at": "2026-10-22T12:00:00+00:00"},
    }
    quote = "Na verdade não tenho certeza da minha idade."
    sources = [{"index": 0, "text": quote, "reported_at": "2026-10-23T12:00:00+00:00"}]
    answers = apply_interpretations(previous, [update(quote=quote)], sources)
    assert answers["age"]["value"] is None
    assert answers["weekly_availability"]["value"] == 3
    remaining = available_fields({"client_answers": answers}, {})
    assert "age" in remaining and "weekly_availability" not in remaining
