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
    assert len(search.queries) == run.budget.retrievals == 2
    assert len(run.references) == 5
    assert len({r["passage_id"] for r in run.references}) == 5
    assert second[1] in run.references and second[2] in run.references
    assert [r["passage_id"] for r in run.context["reference_passages"]] == [
        f"R{i}" for i in range(1, 6)
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
