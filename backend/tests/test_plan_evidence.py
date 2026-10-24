"""Plan evidence selection, abstention and applicability contracts."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from test_assistant_runtime import Agent, ReferenceTool, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_training_chat import complete_onboarding

from app.modules.assistant.runtime import AssistantError, AssistantRun
from app.modules.onboarding.models import Onboarding
from app.modules.training.models import TrainingPlanVersion


def passage(content):
    return {
        "passage_id": str(uuid4()),
        "source_id": str(uuid4()),
        "version_id": str(uuid4()),
        "title": "Synthetic reference",
        "version": 1,
        "location": "text",
        "content": content,
    }


def test_plan_router_uses_own_goal_experience_and_restrictions_not_measurements(database_session):
    client = owner(database_session)
    complete_onboarding(database_session, "owner")
    onboarding = database_session.scalar(select(Onboarding))
    provider = Agent(route={"query": "treinamento resistido séries repetições descanso"})
    run = AssistantRun(database_session, client.id, "initial_plan", provider=provider)
    run.prepare({})
    brief = provider.calls[0][1]["plan_brief"]
    assert brief["training_goal"] == onboarding.training_goal
    assert brief["training_experience"] == onboarding.training_experience
    assert brief["authoritative_health_records"]["limitations_or_complaints"] == "Joelho sensível"
    assert "height_cm" not in brief and "weight_kg" not in brief
    assert brief["population"] == "not_established"
    assert run.route.needs_references is True


def test_two_plan_queries_merge_unique_evidence_with_stable_bounded_labels(database_session):
    client = owner(database_session)
    first = [passage(f"Programming {i}") for i in range(5)]
    second = [first[0], passage("Technique"), passage("Precautions")]

    class Search(ReferenceTool):
        def search(self, session, query, **kwargs):
            self.queries.append(query)
            assert kwargs["prefer_technique"] is (len(self.queries) == 2)
            return first if len(self.queries) == 1 else second

    search = Search()
    provider = Agent(
        route={
            "query": "resistance training sets repetitions rest",
            "technique_query": "squat technique precautions",
        }
    )
    run = AssistantRun(
        database_session, client.id, "initial_plan", provider=provider, knowledge=search
    )
    run.prepare({})
    assert len(search.queries) == run.budget.retrievals == 1
    assert run.context["planned_complementary_query"] == "squat technique precautions"
    assert run._search_for_evidence(run.context["planned_complementary_query"])
    assert len(search.queries) == run.budget.retrievals == 2
    assert len(run.references) == 7
    assert len({r["passage_id"] for r in run.references}) == 7
    assert second[1] in run.references and second[2] in run.references
    assert [r["passage_id"] for r in run.context["reference_passages"]] == [
        f"R{i}" for i in range(1, 8)
    ]


def test_invalid_second_query_never_reaches_retrieval(database_session, rollout):
    client = owner(database_session)
    provider = Agent(route={"query": "treino", "technique_query": "email pessoa@example.test"})
    run = AssistantRun(database_session, client.id, "initial_plan", provider=provider)
    with pytest.raises(AssistantError, match="reference_query_invalid"):
        run.prepare({})
    assert rollout.queries == []


def test_plan_measurements_are_corrected_before_any_embedding(database_session, rollout):
    client = owner(database_session)

    class Correcting(Agent):
        def structured(self, context, *args, **kwargs):
            self.route = {"query": "emagrecer altura 170 peso 90"}
            if "validation_feedback" in context:
                self.route["query"] = "treinamento resistido séries repetições descanso"
            return super().structured(context, *args, **kwargs)

    provider = Correcting()
    run = AssistantRun(database_session, client.id, "initial_plan", provider=provider)
    run.prepare({})
    assert len(provider.calls) == 2
    assert rollout.queries == ["treinamento resistido séries repetições descanso"]


def test_plan_measurement_correction_is_bounded(database_session, rollout):
    client = owner(database_session)
    provider = Agent(route={"query": "height 170 weight 90"})
    run = AssistantRun(database_session, client.id, "initial_plan", provider=provider)
    with pytest.raises(AssistantError, match="reference_query_invalid"):
        run.prepare({})
    assert len(provider.calls) == 2
    assert rollout.queries == []


@pytest.mark.parametrize("role", ["initial_plan", "adaptation"])
def test_plan_cannot_bypass_evidence_by_routing_as_record(database_session, role):
    client = owner(database_session)
    provider = Agent()
    run = AssistantRun(database_session, client.id, role, provider=provider)
    run.prepare({})
    with pytest.raises(AssistantError, match="assistant_clarification_required"):
        run.specialist()
    assert len(provider.calls) == 1
    assert database_session.scalar(select(TrainingPlanVersion)) is None


@pytest.mark.parametrize("role", ["initial_plan", "adaptation"])
def test_insufficient_sources_allow_null_result_without_fabricated_plan(
    database_session, rollout, role
):
    client = owner(database_session)
    rollout.passages = [passage("General exercise benefits; no prescription details.")]

    class Abstaining(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            if role != "orchestrator":
                self.schemas.append(schema)
                return type_.model_validate(
                    {"result": None, "citation_ids": [], "grounding": "clarification"}
                )
            return super().structured(context, instructions, schema, type_, role=role)

    provider = Abstaining(route={"query": "exercise benefits", "needs_references": True})
    run = AssistantRun(database_session, client.id, role, provider=provider)
    run.prepare({})
    with pytest.raises(AssistantError, match="assistant_clarification_required"):
        run.specialist()
    assert {"type": "null"} in provider.schemas[-1]["properties"]["result"]["anyOf"]
    assert len(provider.calls) == 1  # No final review of a nonexistent draft.
    assert database_session.scalar(select(TrainingPlanVersion)) is None


def test_review_receives_restrictions_and_still_rejects_unsupported_plan(database_session, rollout):
    client = owner(database_session)
    complete_onboarding(database_session, "owner")
    rollout.passages = [passage("General benefits for healthy adults.")]
    provider = Agent(route={"query": "training prescription", "needs_references": True})
    provider.citations = ["R1"]
    provider.review_supported = False
    provider.review_unsupported_claims = ["Unsupported prescription"]
    run = AssistantRun(database_session, client.id, "initial_plan", provider=provider)
    run.prepare({})
    with pytest.raises(AssistantError, match="assistant_clarification_required"):
        run.specialist()
    review = provider.calls[-1][1]
    assert (
        review["client_constraints"]["authoritative_health_records"]["limitations_or_complaints"]
        == "Joelho sensível"
    )
    assert review["client_constraints"]["population"] == "not_established"
    assert not run.citations


@pytest.mark.parametrize("grounding", ["record", "references"])
def test_null_plan_cannot_claim_to_be_grounded(database_session, rollout, grounding):
    client = owner(database_session)
    rollout.passages = [passage("Synthetic exercise instructions.")]

    class Invalid(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            if role != "orchestrator":
                return type_.model_validate(
                    {"result": None, "citation_ids": ["R1"], "grounding": grounding}
                )
            return super().structured(context, instructions, schema, type_, role=role)

    run = AssistantRun(
        database_session, client.id, "initial_plan", provider=Invalid(route={"query": "training"})
    )
    run.prepare({})
    with pytest.raises(AssistantError, match="malformed_structured_output"):
        run.specialist()


def test_duplicate_plan_query_uses_only_one_retrieval(database_session, rollout):
    client = owner(database_session)
    query = "training prescription"
    run = AssistantRun(
        database_session,
        client.id,
        "initial_plan",
        provider=Agent(route={"query": query, "technique_query": query}),
    )
    run.prepare({})
    assert rollout.queries == [query]
    assert run.budget.retrievals == 1


def test_clarification_route_does_not_search_or_generate(database_session, rollout):
    client = owner(database_session)
    provider = Agent(
        route={
            "specialist": "clarify",
            "query": "training prescription",
            "technique_query": "exercise technique",
        }
    )
    run = AssistantRun(database_session, client.id, "initial_plan", provider=provider)
    run.prepare({})
    with pytest.raises(AssistantError, match="assistant_clarification_required"):
        run.specialist()
    assert rollout.queries == []
    assert len(provider.calls) == 1


@pytest.mark.parametrize("repetitions", ["Heatmap", "gym:8", "gymnastic movement, 8 repetitions"])
def test_initial_plan_rejects_nonsense_dose_before_review(database_session, rollout, repetitions):
    client = owner(database_session)
    rollout.passages = [passage("Synthetic exercise: 2 sets of 8 repetitions, rest 90 seconds.")]

    class Nonsense(Agent):
        def structured(self, *args, **kwargs):
            result = super().structured(*args, **kwargs)
            if kwargs["role"] == "initial_plan":
                result.result.plan["items"][0]["repetitions"] = repetitions
            return result

    provider = Nonsense(route={"query": "exercise prescription"})
    provider.citations = ["R1"]
    run = AssistantRun(database_session, client.id, "initial_plan", provider=provider)
    run.prepare({})
    with pytest.raises(AssistantError, match="malformed_structured_output"):
        run.specialist()
    assert len(provider.calls) == 2


def test_personal_schedule_and_questions_never_reach_plan_retrieval(database_session, rollout):
    client = owner(database_session)
    for query in ["treino emagrecer 19 anos 3 dias 1 hora", "Quais exercícios você prefere?"]:
        provider = Agent(route={"query": query})
        run = AssistantRun(database_session, client.id, "initial_plan", provider=provider)
        with pytest.raises(AssistantError, match="reference_query_invalid"):
            run.prepare({})
    assert rollout.queries == []


def test_specialist_can_retrieve_missing_evidence_before_referral(database_session):
    from app.integrations.ai_budget import current_budget

    client = owner(database_session)
    initial = passage("General training background")
    additional = passage("Synthetic prescription supporting the requested exercise")

    class Search(ReferenceTool):
        def search(self, session, query, **kwargs):
            self.queries.append(query)
            return [additional] if "prescription" in query else [initial]

    class AgentWithSearch(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            if role == "initial_plan" and context["reference_searches_remaining"]:
                budget = current_budget.get()
                reserved = budget.reserve(100, 1000)
                budget.reconcile_output(reserved, 100)
                return type_.model_validate(
                    {
                        "result": None,
                        "citation_ids": [],
                        "grounding": "clarification",
                        "clarification": {
                            "reason": "insufficient_evidence",
                            "explanation": "Falta dosagem.",
                            "next_step": "Consultar referências.",
                            "evidence_query": "exercise prescription",
                        },
                    }
                )
            return super().structured(context, instructions, schema, type_, role=role)

    search = Search()
    agent = AgentWithSearch(route={"query": "exercise background"})
    agent.citations = ["R1"]
    run = AssistantRun(
        database_session, client.id, "initial_plan", provider=agent, knowledge=search
    )
    run.prepare({})
    result = run.specialist()
    assert result.plan["items"]
    assert search.queries == ["exercise background", "exercise prescription"]
    assert run.budget.retrievals == 2
    assert run.references[0] == additional
    assert run.citations == [additional]


def test_unsupported_item_detail_overrides_a_positive_overall_verdict(database_session, rollout):
    client = owner(database_session)
    rollout.passages = [passage("Synthetic prescription")]

    class IncorrectOverallVerdict(Agent):
        def structured(self, context, *args, **kwargs):
            result = super().structured(context, *args, **kwargs)
            if "cited_passages" in context:
                result.prescription_checks[0].rest_supported = False
                result.prescription_checks[0].gap = "O intervalo proposto não aparece na fonte."
            return result

    agent = IncorrectOverallVerdict(route={"query": "prescription"})
    agent.citations = ["R1"]
    run = AssistantRun(database_session, client.id, "initial_plan", provider=agent)
    run.prepare({})
    with pytest.raises(AssistantError, match="assistant_clarification_required"):
        run.specialist()
    assert run.clarification["reason"] == "unsupported_guidance"
    assert not run.citations


def test_review_feedback_repairs_a_supported_plan_within_the_same_budget(database_session, rollout):
    client = owner(database_session)
    rollout.passages = [passage("Synthetic prescription: rest 120 seconds.")]

    class RepairingAgent(Agent):
        reviews = 0

        def structured(self, context, *args, **kwargs):
            result = super().structured(context, *args, **kwargs)
            if kwargs["role"] == "initial_plan" and context.get("plan_review_feedback"):
                result.result.plan["items"][0]["rest_seconds"] = 120
            if "cited_passages" in context:
                self.reviews += 1
                if self.reviews == 1:
                    result.prescription_checks[0].rest_supported = False
            return result

    agent = RepairingAgent(route={"query": "prescription"})
    agent.citations = ["R1"]
    run = AssistantRun(database_session, client.id, "initial_plan", provider=agent)
    run.prepare({})
    result = run.specialist()
    assert result.plan["items"][0]["rest_seconds"] == 120
    assert agent.reviews == 2 and run.budget.calls == 5


def test_review_does_not_start_a_repair_without_time_for_validation(database_session, rollout):
    from time import monotonic

    from app.integrations.ai_budget import current_budget

    client = owner(database_session)
    rollout.passages = [passage("Synthetic prescription")]

    class LateRejection(Agent):
        def structured(self, context, *args, **kwargs):
            result = super().structured(context, *args, **kwargs)
            if "cited_passages" in context:
                current_budget.get().started = monotonic() - 46
                result.prescription_checks[0].rest_supported = False
            return result

    agent = LateRejection(route={"query": "prescription"})
    agent.citations = ["R1"]
    run = AssistantRun(database_session, client.id, "initial_plan", provider=agent)
    run.prepare({})
    with pytest.raises(AssistantError, match="assistant_clarification_required"):
        run.specialist()
    assert run.budget.calls == 3
    assert "intervalos de descanso" in run.clarification["explanation"]


def test_missing_item_checks_cannot_bypass_plan_review(database_session, rollout):
    client = owner(database_session)
    rollout.passages = [passage("Synthetic prescription")]

    class MissingChecks(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            result = super().structured(context, instructions, schema, type_, role=role)
            if "cited_passages" in context:
                count = len(context["answer"]["plan"]["items"])
                assert schema["properties"]["prescription_checks"]["minItems"] == count
                assert schema["properties"]["prescription_checks"]["maxItems"] == count
                result.prescription_checks = []
            return result

    agent = MissingChecks(route={"query": "prescription"})
    agent.citations = ["R1"]
    run = AssistantRun(database_session, client.id, "initial_plan", provider=agent)
    run.prepare({})
    with pytest.raises(AssistantError, match="malformed_structured_output"):
        run.specialist()


def test_old_memory_age_does_not_establish_current_population(database_session):
    from datetime import UTC, datetime, timedelta

    from app.modules.memory.models import ClientMemoryFact

    client = owner(database_session)
    old = datetime.now(UTC) - timedelta(days=800)
    database_session.add(
        ClientMemoryFact(
            client_id=client.id,
            category="health_report",
            text="Idade relatada: 63 anos",
            attribution="client_report",
            reported_at=old,
            updated_at=old,
            answer_data={"field": "age", "question": "Qual é sua idade?", "value": 63},
        )
    )
    database_session.commit()
    run = AssistantRun(database_session, client.id, "initial_plan", provider=Agent())
    run.prepare({})
    assert run.plan_brief["population"] == "not_established"
    assert "age" in run.unanswered_client_fields


def test_real_source_guard_overrides_a_model_that_approves_invented_doses(
    database_session, rollout
):
    from app.modules.knowledge.prescription_evidence import prescription_gaps

    client = owner(database_session)
    rollout.passages = [passage("Adultos: faça 150 minutos de atividade física por semana.")]
    rollout.prescription_gaps = prescription_gaps
    agent = Agent(route={"query": "prescription"})
    agent.citations = ["R1"]
    run = AssistantRun(database_session, client.id, "initial_plan", provider=agent)
    run.prepare({})
    with pytest.raises(AssistantError, match="assistant_clarification_required"):
        run.specialist()
    assert "quantidade de séries" in run.clarification["explanation"]
    assert "intervalos de descanso" in run.clarification["explanation"]
    assert not run.citations


@pytest.mark.parametrize("with_resistance_doses", [False, True])
def test_continuous_only_evidence_cannot_generate_a_bundle_of_alternatives(
    database_session, rollout, with_resistance_doses
):
    from app.modules.assistant.client_questions import render_questions

    client = owner(database_session)
    content = "Você pode caminhar. Faça 150 minutos por semana. Pode dividir a prática."
    if with_resistance_doses:
        content += " Agachamento: 2 séries de 8 repetições, descanso de 90 segundos."
    rollout.passages = [passage(content)]

    class InspectingAgent(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            if role == "initial_plan":
                properties = schema["properties"]["result"]["anyOf"][0]["properties"]["plan"][
                    "properties"
                ]
                if with_resistance_doses:
                    assert properties["items"]["maxItems"] == 100
                    assert "enum" not in properties["objective"]
                else:
                    assert properties["items"]["maxItems"] == 1
                    fields = properties["items"]["items"]["properties"]
                    assert fields["exercise_name"]["enum"] == ["Caminhada"]
                    assert fields["repetitions"]["enum"] == ["50 minutos"]
                    assert properties["objective"]["enum"] == [
                        "150 minutos por semana em 3 dias de 50 minutos."
                    ]
                    # A source-backed candidate remains optional: refusal is
                    # available when it does not fit the goal or restrictions.
                    assert {"type": "null"} in schema["properties"]["result"]["anyOf"]
                return type_.model_validate(
                    {
                        "result": None,
                        "grounding": "clarification",
                        "citation_ids": [],
                        "clarification": None,
                    }
                )
            return super().structured(context, instructions, schema, type_, role=role)

    run = AssistantRun(
        database_session,
        client.id,
        "initial_plan",
        provider=InspectingAgent(route={"query": "atividade física duração intensidade"}),
    )
    fields = ["weekly_availability", "session_duration"]
    run.prepare(
        {
            "current_user_message": "3\n60 minutos",
            "recent_messages": [
                {
                    "role": "assistant",
                    "content": render_questions(fields),
                    "clarification": {
                        "reason": "missing_client_information",
                        "missing_fields": fields,
                    },
                }
            ],
        }
    )
    with pytest.raises(AssistantError, match="assistant_clarification_required"):
        run.specialist()
