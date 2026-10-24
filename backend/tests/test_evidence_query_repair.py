"""Invalid tool-query syntax must not masquerade as missing training evidence."""

import pytest
from test_assistant_runtime import Agent, ReferenceTool, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_plan_evidence import passage

from app.modules.assistant.runtime import AssistantError, AssistantRun

LONG_QUERY = (
    "programação e técnica de força para adultos iniciantes e dose "
    "de condicionamento cardiovascular"
)
COMPACT_QUERY = "programação técnica força adultos iniciantes dose condicionamento cardiovascular"


def test_observed_thirteen_word_gap_query_retrieves_and_resumes_plan(database_session):
    class Search(ReferenceTool):
        def search(self, session, query, **kwargs):
            self.queries.append(query)
            return [passage("Programming and execution guidance")]

    class CoverageAgent(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            result = super().structured(context, instructions, schema, type_, role=role)
            if role == "initial_plan" and context["reference_searches_remaining"]:
                return type_.model_validate(
                    {
                        "result": None,
                        "grounding": "clarification",
                        "citation_ids": [],
                        "clarification": {
                            "reason": "insufficient_evidence",
                            "explanation": "Falta execução.",
                            "next_step": "Buscar orientação.",
                            "evidence_query": LONG_QUERY,
                        },
                    }
                )
            return result

    search = Search()
    agent = CoverageAgent(route={"query": "beginner resistance programming"})
    agent.citations = ["R1"]
    run = AssistantRun(
        database_session,
        owner(database_session).id,
        "initial_plan",
        provider=agent,
        knowledge=search,
    )
    run.prepare({})
    assert run.specialist().plan["items"]
    assert search.queries == ["beginner resistance programming", COMPACT_QUERY]
    assert run.budget.retrievals == 2
    assert run.budget.calls == 4  # No extra model call for grammatical compaction.
    assert not run._search_for_evidence("third search")


@pytest.mark.parametrize(
    "invalid",
    [
        LONG_QUERY + " pessoa@example.test",
        LONG_QUERY + " altura 175",
        LONG_QUERY + " peso 75",
        LONG_QUERY + " 30 anos",
        LONG_QUERY + "?",
    ],
)
def test_private_or_question_queries_are_not_sanitized_into_embedding_requests(
    database_session, invalid
):
    search = ReferenceTool()
    agent = Agent(route={"query": "beginner programming"})
    run = AssistantRun(
        database_session,
        owner(database_session).id,
        "initial_plan",
        provider=agent,
        knowledge=search,
    )
    run.prepare({})
    with pytest.raises(AssistantError, match="reference_query_invalid"):
        run._search_for_evidence(invalid)
    assert search.queries == ["beginner programming"]
    assert run.budget.retrievals == run.budget.calls == 1


@pytest.mark.parametrize("repair_valid", [True, False])
def test_content_heavy_query_gets_one_bounded_repair(database_session, repair_valid):
    long = (
        "beginner adult resistance programming exercise selection technique repetitions sets "
        "rest frequency intensity progression conditioning"
    )
    repaired = "beginner resistance exercise selection technique progression"

    class RepairAgent(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            if "query_to_shorten" in context:
                from app.integrations.ai_budget import current_budget

                budget = current_budget.get()
                reserved = budget.reserve(100, 256)
                budget.reconcile_output(reserved, 20)
                self.calls.append((role, context, instructions))
                return type_.model_validate({"query": repaired if repair_valid else long})
            return super().structured(context, instructions, schema, type_, role=role)

    search = ReferenceTool()
    search.passages = [passage("Programming")]
    agent = RepairAgent(route={"query": "beginner programming"})
    run = AssistantRun(
        database_session,
        owner(database_session).id,
        "initial_plan",
        provider=agent,
        knowledge=search,
    )
    run.prepare({})
    if repair_valid:
        assert run._search_for_evidence(long)
        assert search.queries == ["beginner programming", repaired]
    else:
        with pytest.raises(AssistantError, match="reference_query_invalid"):
            run._search_for_evidence(long)
        with pytest.raises(AssistantError, match="reference_query_invalid"):
            run._search_for_evidence(long)
        assert search.queries == ["beginner programming"]
    assert run.budget.calls == 2
    assert len([c for c in agent.calls if "query_to_shorten" in c[1]]) == 1


def test_compaction_preserves_negation_and_population_qualifiers(database_session):
    run = AssistantRun(
        database_session,
        owner(database_session).id,
        "initial_plan",
        provider=Agent(),
        knowledge=ReferenceTool(),
    )
    assert (
        run._prepare_evidence_query(
            "técnica de exercícios para os adultos iniciantes e com equipamento mas sem impacto"
        )
        == "técnica exercícios adultos iniciantes com equipamento mas sem impacto"
    )
    assert run.budget.calls == 0


def test_query_repair_cannot_exceed_generation_budget(database_session):
    run = AssistantRun(
        database_session,
        owner(database_session).id,
        "initial_plan",
        provider=Agent(),
        knowledge=ReferenceTool(),
    )
    run.budget.calls = 6
    with pytest.raises(AssistantError, match="generation_call_limit"):
        run._search_for_evidence(
            "beginner adult resistance programming exercise selection technique repetitions "
            "sets rest frequency intensity progression conditioning"
        )
    assert run.budget.calls == 6
    assert run.budget.retrievals == 0
