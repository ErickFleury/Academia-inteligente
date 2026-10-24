"""Draft edits share plan limits without resetting consumed work or losing evidence."""

from time import monotonic

import pytest
from test_assistant_runtime import Agent, ReferenceTool, owner
from test_clients import database_session as database_session
from test_plan_evidence import passage

from app.integrations import ai
from app.integrations.ai_budget import ExecutionBudget
from app.modules.assistant.runtime import AssistantError, AssistantRun


@pytest.mark.parametrize("preauthorized", [False, True])
def test_draft_edit_promotes_existing_budget_without_reset(database_session, preauthorized):
    client = owner(database_session)
    budget = ExecutionBudget(
        started=monotonic() - 5, calls=1, retrievals=1, input_tokens=1000, output_tokens=50
    )
    started = budget.started
    agent = Agent(route={"plan_action": "none" if preauthorized else "edit_draft"})
    with budget.scope():
        run = AssistantRun(database_session, client.id, "training_chat", provider=agent)
        run.prepare(
            {
                "current_user_message": "Em vez de caminhada, pode ser subir escadas?",
                "editable_training_draft": {"items": []},
                "rules": {"may_update_ai_draft": preauthorized},
            }
        )
    assert run.budget is budget
    assert budget.plan is True
    assert budget.started == started and budget.calls == 2
    assert budget.retrievals == 1
    assert budget.input_tokens > 1000 and budget.output_tokens == 75
    assert budget.plan_seconds - 10 < budget.remaining() <= budget.plan_seconds - 5
    # This input exceeds the conversation ceiling but fits the plan ceiling.
    budget.reserve(33000, 100)
    assert budget.calls == 3


@pytest.mark.parametrize("has_draft, action", [(True, "none"), (False, "edit_draft")])
def test_conversation_or_missing_draft_does_not_gain_plan_budget(
    database_session, has_draft, action
):
    client = owner(database_session)
    run = AssistantRun(
        database_session, client.id, "training_chat", provider=Agent(route={"plan_action": action})
    )
    run.prepare(
        {
            "editable_training_draft": {"items": []} if has_draft else None,
            "rules": {"may_update_ai_draft": False},
        }
    )
    assert run.budget.plan is False
    assert run.context["rules"]["may_update_ai_draft"] is False


def test_draft_prompt_omits_unused_derivations_but_preserves_evidence_and_restrictions(
    database_session,
):
    client = owner(database_session)
    search = ReferenceTool()
    search.passages = [
        passage("Caminhada: 150 minutos moderados por semana. Pode dividir a prática.")
    ]
    agent = Agent(
        route={"plan_action": "edit_draft", "query": "caminhada", "needs_references": True}
    )
    agent.citations = ["R1"]
    context = {
        "current_user_message": "Ajuste meu rascunho.",
        "editable_training_draft": {"name": "Rascunho", "items": []},
        "relevant_onboarding": {"limitations_or_complaints": "Relato que deve ser preservado"},
        "rules": {"may_update_ai_draft": False},
    }
    run = AssistantRun(
        database_session, client.id, "training_chat", provider=agent, knowledge=search
    )
    run.prepare(context)
    # A plain response without an update/structured clarification is invalid
    # for an authorized edit, even when the provider ignores its JSON schema.
    with pytest.raises(AssistantError, match="malformed_structured_output"):
        run.specialist()
    _, prompt, instructions = next(call for call in agent.calls if call[0] == "training_chat")
    assert "source_allocation_options" not in prompt
    assert "source_prescription_parameters" not in prompt
    assert prompt["reference_passages"][0]["content"] == search.passages[0]["content"]
    assert prompt["editable_training_draft"] == context["editable_training_draft"]
    assert prompt["relevant_onboarding"] == context["relevant_onboarding"]
    assert instructions.count(ai._CONVERSATIONAL_STYLE) == 1
