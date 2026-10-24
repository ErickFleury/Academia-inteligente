"""Plan retrieval must leave room to fill gaps found in the actual first results."""

import pytest
from test_assistant_runtime import Agent, ReferenceTool, owner
from test_assistant_runtime import rollout as rollout
from test_clients import database_session as database_session
from test_plan_evidence import passage

from app.modules.assistant.runtime import AssistantError, AssistantRun
from app.modules.knowledge.prescription_evidence import duration_block_items, prescription_gaps
from app.modules.knowledge.service import merge_plan_references


def test_reference_merge_preserves_ranked_anchors_full_conditions_and_stable_ties():
    first = [passage(f"Initial background {index}.") for index in range(5)]
    second = [passage(f"Additional background {index}.") for index in range(5)]
    assert merge_plan_references(second, first) == [
        second[0],
        first[0],
        second[1],
        first[1],
        second[2],
    ]
    assert merge_plan_references([], first) == first
    assert merge_plan_references(first[:1], first) == first
    conditional = passage("Only for experienced adults: 3 sets of 8 repetitions; rest 90 seconds.")
    second[-1] = conditional
    selected = merge_plan_references(second, first)
    assert conditional in selected
    assert selected[0] is second[0] and selected[1] is first[0]
    assert (
        next(row for row in selected if row["passage_id"] == conditional["passage_id"])
        is conditional
    )
    assert len({row["passage_id"] for row in selected}) == len(selected) == 5


def test_full_plan_context_expands_only_after_an_evidence_gap(database_session):
    client = owner(database_session)
    first = [passage(f"Original evidence {i}.") for i in range(5)]
    second = [passage(f"Follow-up evidence {i}.") for i in range(5)]
    neighbors = [passage(f"Complete applicability condition {i}.") for i in range(2)]

    class Search(ReferenceTool):
        expansions = 0

        def search(self, session, query, **kwargs):
            self.queries.append(query)
            return first if len(self.queries) == 1 else second

        def expand_plan_context(self, session, references, *, limit=12):
            self.expansions += 1
            assert limit == 12 and len(references) == 10
            return references + neighbors

    search = Search()
    run = AssistantRun(
        database_session,
        client.id,
        "initial_plan",
        provider=Agent(route={"query": "beginner program"}),
        knowledge=search,
    )
    run.prepare({})
    assert len(run.references) == 5 and search.expansions == 0
    assert run._search_for_evidence("beginner exercise prescription")
    assert len(run.references) == 12 and search.expansions == 1
    assert {row["passage_id"] for row in run.references} == {
        row["passage_id"] for row in first + second + neighbors
    }
    assert len(run.context["reference_passages"]) == 12
    assert run.budget.retrievals == 2
    assert not run._search_for_evidence("third search")
    assert search.expansions == 1
    run.provider.citations = [f"R{i}" for i in range(1, 13)]
    assert run.specialist().plan["items"]
    assert len(run.citations) == 12


def test_rebuild_fills_evidence_gap_and_saves_only_the_owned_draft(database_session, monkeypatch):
    from uuid import uuid4

    from test_draft_rebuild import setup

    from app.modules.assistant import runtime
    from app.modules.training.chat_service import TrainingChatService

    general = passage("Adults can walk. Strengthening is recommended but doses are absent.")
    programming = passage("Squat: 3 sets of 8 repetitions, rest 90 seconds; body weight.")

    class Search(ReferenceTool):
        def search(self, session, query, **kwargs):
            self.queries.append(query)
            return [programming] if "prescription" in query else [general]

    search = Search()
    search.prescription_gaps = prescription_gaps
    draft, _, _ = setup(database_session, search)
    monkeypatch.setattr(runtime, "KnowledgeService", lambda: search)

    class Rebuilder(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            if role == "orchestrator" and "allowed_specialist" in context:
                self.route = (
                    {"plan_action": "rebuild_draft"}
                    if context["allowed_specialist"] == "training_chat"
                    else {"query": "adult physical activity", "technique_query": "activity options"}
                )
            result = super().structured(context, instructions, schema, type_, role=role)
            if role == "initial_plan" and not any(
                "3 sets" in ref["content"] for ref in context["reference_passages"]
            ):
                return type_.model_validate(
                    {
                        "result": None,
                        "citation_ids": [],
                        "grounding": "clarification",
                        "clarification": {
                            "reason": "insufficient_evidence",
                            "explanation": "Falta dosagem.",
                            "next_step": "Revisar proposta.",
                            "evidence_query": "strength prescription technique",
                        },
                    }
                )
            return result

    agent = Rebuilder()
    agent.citations = ["R1"]
    response = TrainingChatService(agent).submit_for_subject(
        database_session, "owner", message="Refaça meu treino completo.", client_request_id=uuid4()
    )
    assert "Refiz seu rascunho" in response.messages[-1].content
    assert draft.revision == 2 and draft.status == "proposal"
    assert search.queries == ["adult physical activity", "strength prescription technique"]
    assert len(agent.calls) == 5  # Chat route, plan route, gap, generation and review.


@pytest.mark.parametrize("available", [True, False])
def test_second_search_uses_observed_gap_instead_of_speculative_activity_query(
    database_session, available
):
    client = owner(database_session)
    general = passage("Adults can walk; strengthening is also recommended. No strength doses here.")
    programming = passage("For resistance exercises: 3 sets of 8 repetitions; rest 90 seconds.")
    technique = passage("Seção: Squat\nStarting Position: stand upright. Use body weight.")

    class Search(ReferenceTool):
        def search(self, session, query, **kwargs):
            self.queries.append(query)
            if query == "resistance training sets repetitions rest technique":
                assert kwargs["prefer_technique"] is True
                return [technique, programming] if available else []
            return [general]

    search = Search()

    class CoverageAgent(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            response = super().structured(context, instructions, schema, type_, role=role)
            if role == "initial_plan" and not any(
                "3 sets" in row["content"] for row in context["reference_passages"]
            ):
                return type_.model_validate(
                    {
                        "result": None,
                        "citation_ids": [],
                        "grounding": "clarification",
                        "clarification": {
                            "reason": "insufficient_evidence",
                            "explanation": "Falta programação.",
                            "next_step": "Revisar treino.",
                            "evidence_query": "resistance training sets repetitions rest technique",
                        },
                    }
                )
            return response

    agent = CoverageAgent(
        route={
            "query": "adult physical activity duration intensity",
            "technique_query": "adult physical activity options",
        }
    )
    agent.citations = ["R1", "R3"]
    run = AssistantRun(
        database_session, client.id, "initial_plan", provider=agent, knowledge=search
    )
    run.prepare({"current_user_message": "Monte um treino completo."})
    if available:
        result = run.specialist()
        assert result.plan["items"]
    else:
        with pytest.raises(AssistantError, match="assistant_clarification_required"):
            run.specialist()
        assert run.clarification["reason"] == "insufficient_evidence"
    assert search.queries == [
        "adult physical activity duration intensity",
        "resistance training sets repetitions rest technique",
    ]
    assert run.budget.retrievals == 2
    assert len(run.references) <= 5
    if available:
        assert technique in run.citations and programming in run.citations
        assert run.budget.calls == 4  # Router, coverage/gap, generation, review.
    else:
        assert run.citations == []
        assert run.budget.calls == 2


@pytest.mark.parametrize(
    "case", ["supported", "duration", "sets", "rest", "applicability", "conflict"]
)
def test_review_receives_continuous_block_semantics_without_waiving_other_checks(
    database_session, rollout, case
):
    client = owner(database_session)
    rollout.passages = [passage("Caminhada moderada: 20 minutos de atividade contínua.")]
    rollout.prescription_gaps = prescription_gaps

    class ContinuousAgent(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            response = super().structured(context, instructions, schema, type_, role=role)
            if role == "initial_plan":
                response.result.plan["items"][0].update(
                    {
                        "exercise_name": "Caminhada",
                        "sets": 1,
                        "repetitions": "20 minutos",
                        "rest_seconds": 0,
                        "load_guidance": "Intensidade moderada",
                    }
                )
                changes = {
                    "duration": {"repetitions": "30 minutos"},
                    "sets": {"sets": 2},
                    "rest": {"rest_seconds": 60},
                }.get(case, {})
                response.result.plan["items"][0].update(changes)
            if "cited_passages" in context:
                assert context["duration_block_items"] == [1]
                # The representation contract accompanies the actual review call.
                assert "sets=1" in instructions and "rest_seconds=0" in instructions
                assert "não significa proibir pausas" in instructions
                if case == "applicability":
                    response.prescription_checks[0].applicable = False
            return response

    agent = ContinuousAgent(route={"query": "caminhada duração intensidade"})
    agent.citations = ["R1"]
    agent.review_conflict = case == "conflict"
    run = AssistantRun(database_session, client.id, "initial_plan", provider=agent)
    run.prepare({})
    if case == "supported":
        assert run.specialist().plan["items"][0]["repetitions"] == "20 minutos"
    else:
        with pytest.raises(AssistantError, match="assistant_clarification_required"):
            run.specialist()
        if case in {"duration", "sets", "rest"}:
            assert not any("cited_passages" in context for _, context, _ in agent.calls)


def test_duration_block_metadata_does_not_classify_repetition_sets_or_intervals():
    items = [
        {"sets": 1, "repetitions": "20 minutos", "rest_seconds": 0},
        {"sets": 2, "repetitions": "30 segundos", "rest_seconds": 0},
        {"sets": 1, "repetitions": "20 minutos", "rest_seconds": 60},
        {"sets": 1, "repetitions": "20", "rest_seconds": 0},
        {"sets": 1, "repetitions": "1 hora", "rest_seconds": 0},
    ]
    assert duration_block_items(items) == [1, 5]


def test_gap_search_preserves_quantities_and_named_activities_in_generation_context(
    database_session,
):
    client = owner(database_session)
    weekly = passage("Adults: 75 minutes of vigorous activity per week. You may divide the time.")
    activities = passage("You can walk, cycle or dance.")
    first = [
        weekly,
        passage("150 minutes of moderate activity per week."),
        activities,
        passage("General benefits."),
        passage("General wellbeing."),
    ]
    technique = passage("Seção: Seated Row\nStarting Position: sit upright. Pull the handles.")
    dose = passage("For applicable adults: 2 sets of 8 repetitions, rest 90 seconds between sets.")
    second = [
        technique,
        passage("More sets may improve strength."),
        passage("Definitions of set structure and movement technique."),
        passage("Seção: Other Row\nStarting Position: stand upright."),
        dose,
    ]

    class Search(ReferenceTool):
        def search(self, session, query, **kwargs):
            self.queries.append(query)
            return first if len(self.queries) == 1 else second

    search = Search()

    class InspectingAgent(Agent):
        def structured(self, context, instructions, schema, type_, *, role):
            if role == "initial_plan":
                contents = {row["content"] for row in context["reference_passages"]}
                assert {
                    weekly["content"],
                    activities["content"],
                    technique["content"],
                    dose["content"],
                } <= contents
                assert len(contents) == 10
                assert context["source_allocation_options"]
                assert any(
                    row["sets"] and row["repetitions"] and row["rest_seconds"]
                    for row in context["source_prescription_parameters"]
                )
            return super().structured(context, instructions, schema, type_, role=role)

    agent = InspectingAgent(route={"query": "adult physical activity"})
    agent.citations = ["R1"]
    run = AssistantRun(
        database_session, client.id, "initial_plan", provider=agent, knowledge=search
    )
    run.prepare({})
    run.context["client_answers"] = {
        "weekly_availability": {"value": 2},
        "session_duration": {"value": 60},
    }
    assert run._search_for_evidence("strength prescription technique")
    assert run.specialist().plan["items"]
    assert run.budget.retrievals == 2
