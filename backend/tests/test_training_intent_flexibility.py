"""Current-turn intent and native flexibility, with no external-service dependency."""

import json
from io import BytesIO
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_owner_rag import owner_case as owner_case
from test_owner_rag import session as session

from app.integrations import ai
from app.integrations.ai import AiTrainingGenerationResponse
from app.modules.training import owner_rag
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.knowledge_query import training_knowledge_query
from app.modules.training.models import TrainingAiMessage, TrainingPlanVersion
from app.modules.training.owner_rag_schema import resolve_plan
from app.modules.training.prescription_contract import PrescriptionRejection
from app.modules.training.request_intent import goal_families, requested_goal
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.service import TrainingLifecycleService


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Gere uma ficha de treino de flexibilidade.\n\n", ["mobility_flexibility"]),
        ("Você\nGere uma ficha de treino de flexibilidade.", ["mobility_flexibility"]),
        ("Gere flexibilidade; chego de transporte público.", ["mobility_flexibility"]),
        ("Gere alongamentos sem perder força", ["mobility_flexibility"]),
        ("Não quero força nem hipertrofia, só flexibilidade", ["mobility_flexibility"]),
        ("Quero hipertrofia, não quero força", ["hypertrophy"]),
        ("Antes queria hipertrofia, agora quero mobilidade", ["mobility_flexibility"]),
        ("Não tenho limitações e quero flexibilidade", ["mobility_flexibility"]),
        ("Sem limitações; quero flexibilidade", ["mobility_flexibility"]),
        ("Força não, flexibilidade sim", ["mobility_flexibility"]),
        ("Quero força e hipertrofia", ["strength", "hypertrophy"]),
        ("Quero mobilidade, flexibilidade e alongamentos", ["mobility_flexibility"]),
        ("Reforçado e transporte", []),
    ],
)
def test_positive_current_goal_mentions_are_token_bounded(message, expected):
    assert goal_families(message) == expected


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Você\nGere uma ficha de treino de flexibilidade.", True),
        ("Cliente:\nGere três fichas de flexibilidade", True),
        ("  VOCÊ\r\nGere um treino ABC", True),
        ("Você\nGere\numa ficha\nde flexibilidade", True),
        ("Gere uma ficha de flexibilidade, não quero hipertrofia", True),
        ("Você\nNão gere uma ficha de treino de flexibilidade", False),
        ("Você\nSe eu pedir, gere um treino", False),
        ("Assistente\nGere uma ficha", False),
        ("Como funciona uma ficha de flexibilidade?", False),
    ],
)
def test_copied_client_role_header_does_not_hide_explicit_generation(message, expected):
    assert TrainingChatService._requests_initial_plan(message, []) is expected


def test_priority_is_not_inferred_and_an_explicit_primary_goal_is_preserved():
    with pytest.raises(PrescriptionRejection, match="goal_priority_confirmation_required"):
        requested_goal("Gere força e flexibilidade", "Hipertrofia")
    assert (
        requested_goal("Flexibilidade como objetivo principal e força secundária", "Hipertrofia")
        == "Flexibilidade"
    )
    assert (
        requested_goal("Força e flexibilidade; objetivo principal é flexibilidade", "Hipertrofia")
        == "Flexibilidade"
    )
    with pytest.raises(PrescriptionRejection, match="training_goal_confirmation_required"):
        owner_rag.goal_family("desconhecido")


def test_flexibility_retrieval_does_not_import_strength_or_an_old_goal():
    query = training_knowledge_query(
        "Gere uma ficha de flexibilidade",
        {"training_goal": "Hipertrofia", "training_experience": "beginner"},
        {"scope": "unspecified", "goal": "Flexibilidade"},
    )
    assert "stretching" in query and "range of motion" in query
    assert "resistido" not in query and "força" not in query and "Hipertrofia" not in query
    assert "Gere" not in query and "beginner" not in query


def flex_wire(context):
    label = context.get("training_session", {}).get("label", "A")
    choices = {
        "A": ["chest_stretch", "standing_calf_stretch", "seated_trunk_rotation_stretch"],
        "B": [
            "cross_body_shoulder_stretch",
            "standing_quadriceps_stretch",
            "seated_trunk_rotation_stretch",
        ],
        "C": ["chest_stretch", "seated_hamstring_stretch", "seated_trunk_rotation_stretch"],
    }
    return {
        "name": "Flexibilidade",
        "objective": context["effective_training_goal"],
        "items": [
            {
                "exercise_name": f"{key} (Dia {label})",
                "holds": 2,
                "hold_seconds": 30,
                "side": "each_side",
                "rest_seconds": 30,
                "intensity_instruction_key": "comfortable_range_without_pain",
                "equipment_requirement": None,
                "equipment_model_id": None,
            }
            for key in choices[label]
        ],
    }


@pytest.mark.parametrize(
    "message,labels",
    [
        ("Você\nGere uma ficha de treino de flexibilidade.", ["A"]),
        ("Gere uma ficha de treino de flexibilidade para um dia..", ["A"]),
        ("Gere flexibilidade em três dias, fichas A/B/C", list("ABC")),
    ],
)
def test_flexibility_chat_overrides_old_goals_and_preserves_original_text_and_replay(
    session, owner_case, message, labels
):
    _, generation, writer, source, _ = owner_case
    draft = generation.generate_for_subject(session, "rag-owner")
    chat = TrainingChatService(
        provider=writer, generation_service=generation, knowledge_service=generation._knowledge
    )
    chat.submit_for_subject(
        session,
        "rag-owner",
        message="Gere um treino de força e hipertrofia",
        client_request_id=uuid4(),
    )

    def write(context):
        writer.calls += 1
        assert context["owner_rag_basis"]["goal_family"] == "mobility_flexibility"
        assert all(
            e["mode"] == "flexibility" for e in context["owner_exercise_dictionary"]["exercises"]
        )
        return AiTrainingGenerationResponse(
            plan=flex_wire(context),
            citations=[source["chunks"][0]["id"]],
            knowledge_status="supported",
        )

    writer.generate_training = write
    key = uuid4()
    result = chat.submit_for_subject(session, "rag-owner", message=message, client_request_id=key)
    assert "Qual deve ser o principal" not in result.messages[-1].content
    assert "2 × 30 s; cada lado" in result.messages[-1].content
    assert "30 s entre sustentações" in result.messages[-1].content
    content = TrainingLifecycleService().content(session, draft)
    assert len(content.items) == 3 * len(labels) and draft.revision == 2
    assert all(i.sets is None and i.dose_details.mode == "flexibility" for i in content.items)
    assert (
        session.scalar(
            select(TrainingAiMessage.content).where(TrainingAiMessage.client_request_id == key)
        )
        == message
    )
    owner_rag.validate_saved(session, draft, content)
    calls = writer.calls
    chat.submit_for_subject(session, "rag-owner", message="Reenvio", client_request_id=key)
    assert writer.calls == calls and draft.revision == 2


def test_actual_writer_schema_contains_holds_and_side_and_materializes_typed_dose(
    owner_case, monkeypatch
):
    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {"training_request": "Flexibilidade"}, evidence, {"training_goal": "Hipertrofia"}
    )
    requests = []

    def respond(request, timeout):
        requests.append(json.loads(request.data))
        plan = flex_wire(context)
        plan["name"] = "FLEXIBILITY_PROPOSAL"
        answer = {
            "plan": plan,
            "citations": [evidence.chunks[0]["chunk_id"]],
            "knowledge_status": "supported",
            "knowledge_limitations": "",
        }
        return BytesIO(json.dumps({"message": {"content": json.dumps(answer)}}).encode())

    monkeypatch.setattr(ai, "urlopen", respond)
    provider = ai.OllamaOnboardingProvider(ai.OllamaConfig("http://local", "writer", 30))
    response = provider.generate_training(context)
    properties = requests[0]["format"]["properties"]["plan"]["properties"]["items"]["items"][
        "properties"
    ]
    assert "repetitions" not in properties and "sets" not in properties
    assert {"holds", "hold_seconds", "side"} <= properties.keys()
    content = TrainingPlanVersionInput.model_validate(resolve_plan(response.plan, context))
    assert content.name == "Flexibilidade"
    owner_rag.validate_candidate(content, context)
    assert content.items[0].repetitions == "2 × 30 s; cada lado"


def test_resistance_content_cannot_be_relabeled_as_flexibility_and_old_draft_is_preserved(
    session, owner_case
):
    _, generation, writer, source, _ = owner_case
    draft = generation.generate_for_subject(session, "rag-owner")
    before = TrainingLifecycleService().content(session, draft)

    def invalid(context):
        writer.calls += 1
        row = {**before.items[0].model_dump(mode="json"), "exercise_name": "chest_stretch (Dia A)"}
        return AiTrainingGenerationResponse(
            plan={"name": "Flexibilidade", "objective": "Flexibilidade", "items": [row]},
            citations=[source["chunks"][0]["id"]],
            knowledge_status="supported",
        )

    writer.generate_training = invalid
    with pytest.raises(PrescriptionRejection, match="invalid_typed_candidate"):
        generation.generate_for_subject(
            session,
            "rag-owner",
            training_request="Gere flexibilidade para um dia",
            replace_existing=True,
        )
    assert TrainingLifecycleService().content(session, draft) == before and draft.revision == 1
    assert writer.calls == 3 and session.scalar(select(TrainingPlanVersion)) is draft


@pytest.mark.parametrize(
    "field,value", [("holds", True), ("hold_seconds", 0), ("side", "both"), ("hold_seconds", -30)]
)
def test_bad_hold_quantity_or_side_receives_one_global_correction_before_save(
    session, owner_case, field, value
):
    _, generation, writer, source, _ = owner_case
    contexts = []

    def write(context):
        contexts.append(context)
        plan = flex_wire(context)
        if len(contexts) == 1:
            plan["items"][0][field] = value
        return AiTrainingGenerationResponse(
            plan=plan, citations=[source["chunks"][0]["id"]], knowledge_status="supported"
        )

    writer.generate_training = write
    draft = generation.generate_for_subject(
        session, "rag-owner", training_request="Gere flexibilidade"
    )
    assert len(contexts) == 2
    issue = contexts[1]["selection_correction"]["issues"][0]
    assert issue["position"] == 1 and issue["field"] == field
    assert draft.status == "proposal"


def test_full_body_flexibility_requires_regions_instead_of_resistance_patterns(owner_case):
    from app.modules.training.owner_rag_schema import (
        constrain_session_schema,
        constrain_writer_schema,
    )

    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {
            "training_request": "Flexibilidade de corpo inteiro",
            "training_focus": {"scope": "full_body"},
        },
        evidence,
        {"training_goal": "Força"},
    )
    schema = ai._training_schema()
    constrain_writer_schema(schema, context)
    constrain_session_schema(schema, context)
    day = schema["properties"]["plan"]["properties"]["sessions"]["properties"]["A"]
    assert set(day["required"]) == {
        "flexibility_upper",
        "flexibility_lower",
        "flexibility_trunk",
        "accessories",
    }
    assert day["properties"]["accessories"]["maxItems"] == 0
    rows = flex_wire(context).pop("items")
    plan = {
        "name": "Flexibilidade",
        "objective": "Flexibilidade",
        "sessions": {
            "A": {
                "flexibility_upper": [rows[0]],
                "flexibility_lower": [rows[1]],
                "flexibility_trunk": [rows[2]],
                "accessories": [],
            }
        },
    }
    content = TrainingPlanVersionInput.model_validate(resolve_plan(plan, context))
    owner_rag.validate_candidate(content, context)
    plan["sessions"]["A"]["flexibility_trunk"] = []
    from app.modules.training.completeness import IncompleteTrainingPlanError

    with pytest.raises(IncompleteTrainingPlanError):
        owner_rag.validate_candidate(
            TrainingPlanVersionInput.model_validate(resolve_plan(plan, context)), context
        )


@pytest.mark.parametrize(
    "sides,valid",
    [
        (["left", "right"], True),
        (["left", "left"], False),
        (["each_side", "right"], False),
        (["bilateral", "left"], False),
    ],
)
def test_distinct_flexibility_sides_are_not_competing_prescriptions(owner_case, sides, valid):
    from app.modules.training.selection import (
        RedundantTrainingExerciseError,
        validate_exercise_selection,
    )

    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {"training_request": "Flexibilidade"}, evidence, {"training_goal": "Força"}
    )
    plan = flex_wire(context)
    row = plan["items"][0]
    plan["items"] = [{**row, "side": side} for side in sides]
    content = TrainingPlanVersionInput.model_validate(resolve_plan(plan, context))
    if valid:
        validate_exercise_selection(content)
    else:
        with pytest.raises(RedundantTrainingExerciseError):
            validate_exercise_selection(content)


def test_splitting_sides_does_not_make_a_copied_selection_a_distinct_day(owner_case):
    from app.modules.training.completeness import (
        IncompleteTrainingPlanError,
        validate_session_variation,
    )

    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {"training_request": "Flexibilidade"}, evidence, {"training_goal": "Força"}
    )
    plan = flex_wire(context)
    before = TrainingPlanVersionInput.model_validate(resolve_plan(plan, context))
    rows = []
    for row in plan["items"]:
        rows.extend([{**row, "side": side} for side in ("left", "right")])
    plan["items"] = rows
    after = TrainingPlanVersionInput.model_validate(resolve_plan(plan, context))
    with pytest.raises(IncompleteTrainingPlanError):
        validate_session_variation(
            after,
            {
                **context,
                "training_session": {"label": "A"},
                "previous_sessions": [{"label": "B", "plan": before.model_dump(mode="json")}],
            },
        )
