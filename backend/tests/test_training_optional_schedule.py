"""Requested day labels survive focus, RAG generation, correction and chat."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from test_owner_rag import owner_case as owner_case
from test_owner_rag import session as session

from app.integrations import ai
from app.integrations.ai import (
    AiTrainingChatResponse,
    AiTrainingGenerationResponse,
    AiTrainingRequestFocus,
)
from app.modules.onboarding.models import Onboarding
from app.modules.training import owner_rag
from app.modules.training.chat_service import TrainingChatService
from app.modules.training.completeness import requested_training_schedule
from app.modules.training.focus import analyze_training_focus
from app.modules.training.owner_rag_load import LOAD_GUIDANCE
from app.modules.training.owner_rag_schema import (
    constrain_session_schema,
    constrain_session_variation,
    constrain_writer_schema,
    dictionary,
    resolve_plan,
)
from app.modules.training.prescription_contract import PrescriptionRejection
from app.modules.training.presentation import proposal_preview
from app.modules.training.service import TrainingLifecycleService


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Gere hipertrofia em três dias diferentes (treinos A, B, C).", list("ABC")),
        ("Quero força em 3 dias.", list("ABC")),
        ("Quero treino ABC", list("ABC")),
        ("Quero fichas A/B/C", list("ABC")),
        ("Bíceps em três dias", list("ABC")),
        ("Quero hipertrofia em duas vezes por semana", list("AB")),
        ("Uma ficha de treino para três dias", list("ABC")),
        ("Quero treinos A e C", list("AC")),
        ("Quero treino em um dia", ["A"]),
        ("Quero hipertrofia, três séries", []),
        ("Quero hipertrofia", []),
        ("Quero três dias de descanso", []),
    ],
)
def test_explicit_sessions_do_not_depend_on_model_focus(message, expected):
    assert (
        requested_training_schedule(message, {"scope": "unspecified"})["session_labels"] == expected
    )


@pytest.mark.parametrize(
    "message",
    [
        "Quero 2 dias e treinos A/B/C",
        "Quero 8 dias",
        "Quero 0 dias",
        "Quero 2 dias ou 3 dias",
        "Quero fichas A, A, B",
    ],
)
def test_conflicting_or_unsupported_schedule_asks_for_clarification(message):
    with pytest.raises(PrescriptionRejection, match="training_schedule_confirmation_required"):
        requested_training_schedule(message)


def grouped_plan(context, *, copied=False, labels=None):
    selected = labels or context["training_schedule"]["session_labels"]
    choices = {
        "A": ["bodyweight_squat", "push_up", "dumbbell_row"],
        "B": ["goblet_squat", "dumbbell_floor_press", "dumbbell_row"],
        "C": ["stationary_lunge", "dumbbell_overhead_press", "abdominal_curlup"],
    }
    exercises = {e["key"]: e for e in dictionary()["exercises"]}
    return {
        "name": "Rotina solicitada",
        "objective": context["effective_training_goal"],
        "sessions": {
            label: [
                {
                    "exercise_name": key,
                    "sets": 3,
                    "repetitions": "8-12",
                    "load_guidance": LOAD_GUIDANCE[exercises[key]["load_capability"]],
                    "rest_seconds": 120,
                    "equipment_requirement": None,
                    "equipment_model_id": None,
                }
                for key in choices["A" if copied else label]
            ]
            for label in selected
        },
    }


def attach_writer(writer, source, *, first_missing=False, copied=False, always_bad=False):
    def write(context):
        writer.calls += 1
        writer.contexts.append(context)
        bad = always_bad or writer.calls == 1
        plan = grouped_plan(
            context,
            labels=["B"] if first_missing and bad else None,
            copied=copied and (always_bad or writer.calls == 2),
        )
        return AiTrainingGenerationResponse(
            plan=plan, citations=[source["chunks"][0]["id"]], knowledge_status="supported"
        )

    writer.generate_training = write


def test_three_day_schema_requires_separate_nonempty_day_containers(owner_case):
    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {"training_request": "Hipertrofia em três dias"}, evidence, {"training_goal": "Força"}
    )
    schema = ai._training_schema()
    constrain_writer_schema(schema, context)
    constrain_session_schema(schema, context)
    plan = schema["properties"]["plan"]
    assert "items" not in plan["properties"]
    sessions = plan["properties"]["sessions"]
    assert sessions["required"] == list("ABC") and sessions["additionalProperties"] is False
    for label, items in sessions["properties"].items():
        assert items["minItems"] == 1
        assert all(
            name.endswith(f"(Dia {label})")
            for name in items["items"]["properties"]["exercise_name"]["enum"]
        )
    assert len(resolve_plan(grouped_plan(context), context)["items"]) == 9


def test_goal_words_cannot_become_anatomical_focus():
    calls = []

    def analyze(context):
        calls.append(context)
        return (
            AiTrainingRequestFocus(scope="targeted", muscle_groups=["muscular"])
            if len(calls) == 1
            else AiTrainingRequestFocus(scope="unspecified", muscle_groups=[])
        )

    result = analyze_training_focus(
        analyze, "Hipertrofia muscular em três dias", allowed_muscle_groups=["bíceps", "peito"]
    )
    assert result["scope"] == "unspecified" and calls[0]["focus_constraints"]["allowed_scopes"] == [
        "unspecified"
    ]


def test_owner_full_body_uses_whole_routine_instruction_when_no_single_session_is_requested(
    owner_case,
):
    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {
            "training_request": "Corpo inteiro para força em três dias",
            "training_focus": {"scope": "full_body"},
        },
        evidence,
        {"training_goal": "Força"},
    )
    instructions = []
    provider = ai.OllamaOnboardingProvider()
    provider._call = lambda ctx, instruction, schema, result_type: instructions.append(instruction)
    provider.generate_training(context)
    assert instructions == [ai._TRAINING_GENERATION]


def test_explicit_goal_and_abc_override_wrong_model_goal_and_onboarding_without_rewriting_it(
    session, owner_case
):
    client, service, writer, source, _ = owner_case
    onboarding = session.scalar(select(Onboarding).where(Onboarding.client_id == client.id))
    onboarding.training_goal = "Hipertrofia"
    session.commit()
    writer.analyze_training_request = lambda context: AiTrainingRequestFocus(
        scope="unspecified", muscle_groups=[], goal="Hipertrofia"
    )
    attach_writer(writer, source)
    draft = service.generate_for_subject(
        session, "rag-owner", training_request="Gere força em três dias (treinos A, B, C)."
    )
    assert draft.citations[0]["owner_rag"]["goal_family"] == "strength"
    assert draft.citations[0]["owner_rag"]["session_labels"] == list("ABC")
    assert writer.contexts[0]["training_focus"]["goal"] == "Força"
    assert onboarding.training_goal == "Hipertrofia"
    assert writer.calls == 3 and len(writer.review_contexts) == 3
    text = proposal_preview(session, draft)
    assert all(f"Treino {label}" in text for label in "ABC")


@pytest.mark.parametrize("defect", ["missing", "copied"])
def test_missing_or_copied_days_receive_one_whole_routine_correction(session, owner_case, defect):
    _, service, writer, source, _ = owner_case
    attach_writer(writer, source, first_missing=defect == "missing", copied=defect == "copied")
    draft = service.generate_for_subject(
        session, "rag-owner", training_request="Hipertrofia em três dias"
    )
    assert writer.calls == 4 and draft.citations[0]["owner_rag"]["session_labels"] == list("ABC")
    assert len(writer.review_contexts) == (3 if defect == "missing" else 4)


def test_failed_abc_replacement_preserves_previous_draft(session, owner_case):
    _, service, writer, source, _ = owner_case
    draft = service.generate_for_subject(session, "rag-owner")
    before = TrainingLifecycleService().content(session, draft)
    writer.calls = 0
    attach_writer(writer, source, first_missing=True, always_bad=True)
    with pytest.raises(PrescriptionRejection, match="invalid_typed_candidate"):
        service.generate_for_subject(
            session, "rag-owner", training_request="Hipertrofia em três dias"
        )
    assert (
        writer.calls == 2
        and TrainingLifecycleService().content(session, draft) == before
        and draft.revision == 1
    )


def test_mixed_goals_return_a_chat_clarification_and_preserve_the_draft(session, owner_case):
    _, generation, writer, _, _ = owner_case
    draft = generation.generate_for_subject(session, "rag-owner")
    before = TrainingLifecycleService().content(session, draft)
    chat = TrainingChatService(
        provider=writer, generation_service=generation, knowledge_service=generation._knowledge
    )
    result = chat.submit_for_subject(
        session,
        "rag-owner",
        message="Gere uma ficha de treino de força e hipertrofia em três dias A/B/C",
        client_request_id=uuid4(),
    )
    assert "Qual deve ser o principal" in result.messages[-1].content
    assert writer.calls == 1 and TrainingLifecycleService().content(session, draft) == before


def test_chat_can_change_single_sheet_to_abc_and_replay_without_regeneration(session, owner_case):
    _, generation, writer, source, _ = owner_case
    draft = generation.generate_for_subject(session, "rag-owner")
    contexts = []

    def write(context):
        contexts.append(context)
        return AiTrainingChatResponse(
            assistant_message="Rascunho atualizado.",
            draft_update=grouped_plan(context),
            citations=[source["chunks"][0]["id"]],
            knowledge_status="supported",
        )

    writer.training_chat = write
    chat = TrainingChatService(
        provider=writer, generation_service=generation, knowledge_service=generation._knowledge
    )
    key = uuid4()
    chat.submit_for_subject(
        session,
        "rag-owner",
        message="Atualize o rascunho para três dias, fichas A/B/C",
        client_request_id=key,
    )
    assert draft.revision == 2 and draft.citations[0]["owner_rag"]["session_labels"] == list("ABC")
    chat.submit_for_subject(session, "rag-owner", message="Reenvio", client_request_id=key)
    assert len(contexts) == 1


@pytest.mark.parametrize(
    "message,labels,family",
    [
        ("Gere um treino ABC", list("ABC"), "strength"),
        ("Gere um treino de hipertrofia", ["A"], "hypertrophy"),
        ("Gere um treino duas vezes por semana", list("AB"), "strength"),
        ("Gere fichas A/B/C de hipertrofia", list("ABC"), "hypertrophy"),
        ("Gere três fichas A/B/C de hipertrofia", list("ABC"), "hypertrophy"),
        ("Gere 3 treinos A/B/C", list("ABC"), "strength"),
    ],
)
def test_explicit_chat_schedule_or_goal_cannot_reuse_the_old_single_sheet(
    session, owner_case, message, labels, family
):
    _, generation, writer, source, _ = owner_case
    draft = generation.generate_for_subject(session, "rag-owner")

    def write(context):
        writer.calls += 1
        selected = context["training_schedule"]["session_labels"] or ["A"]
        plan = grouped_plan(context, labels=selected)
        plan["items"] = [item for rows in plan.pop("sessions").values() for item in rows]
        return AiTrainingGenerationResponse(
            plan=plan, citations=[source["chunks"][0]["id"]], knowledge_status="supported"
        )

    writer.generate_training = write
    chat = TrainingChatService(
        provider=writer, generation_service=generation, knowledge_service=generation._knowledge
    )
    key = uuid4()
    chat.submit_for_subject(session, "rag-owner", message=message, client_request_id=key)
    assert draft.revision == 2
    assert writer.calls == 1 + len(labels)
    from app.modules.training.completeness import split_training_day

    content = TrainingLifecycleService().content(session, draft)
    assert sorted({split_training_day(item.exercise_name)[0] for item in content.items}) == labels
    assert draft.citations[0]["owner_rag"]["goal_family"] == family
    chat.submit_for_subject(session, "rag-owner", message="Reenvio", client_request_id=key)
    assert writer.calls == 1 + len(labels) and draft.revision == 2


@pytest.mark.parametrize("restricted", [False, True, "contradictory"])
def test_multiday_reviewer_schema_binds_global_positions_to_each_day(
    owner_case, monkeypatch, restricted
):
    import json
    from io import BytesIO

    from app.modules.training.completeness import training_review_context
    from app.modules.training.schema import TrainingPlanVersionInput

    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {"training_request": "Hipertrofia em três dias"}, evidence, {"training_goal": "Força"}
    )
    plan = TrainingPlanVersionInput.model_validate(resolve_plan(grouped_plan(context), context))
    context = training_review_context(plan, context)
    payload = {
        "sessions": {
            label: {
                "label": label,
                "complete": True,
                "issues": [],
                "repetition_recommendation": None,
                "item_issues": [],
            }
            for label in "ABC"
        }
    }
    if restricted:
        payload["sessions"]["B"].update(
            complete=restricted == "contradictory",
            issues=["restriction_not_respected"],
            item_issues=[{"position": 4, "reason": "restriction_not_respected"}],
        )
    requests = []

    def response(request, **kwargs):
        requests.append(json.loads(request.data))
        return BytesIO(json.dumps({"message": {"content": json.dumps(payload)}}).encode())

    monkeypatch.setattr(ai, "urlopen", response)
    result = ai.OllamaOnboardingProvider().assess_training(context)
    assert [s.label for s in result.sessions] == list("ABC")
    schema = requests[0]["format"]["properties"]["sessions"]
    assert schema["required"] == list("ABC")
    passed = schema["properties"]["B"]["anyOf"][0]["properties"]
    assert passed["complete"]["enum"] == [True]
    assert passed["issues"]["maxItems"] == passed["item_issues"]["maxItems"] == 0
    assert schema["properties"]["B"]["anyOf"][1]["properties"]["item_issues"]["items"][
        "properties"
    ]["position"]["enum"] == [4, 5, 6]
    assert context["review_index"][3]["exercise_key"] == "goblet_squat"
    assert (
        "restriction_not_respected"
        in schema["properties"]["B"]["anyOf"][1]["properties"]["issues"]["items"]["enum"]
    )
    if restricted:
        from app.modules.training.completeness import (
            IncompleteTrainingPlanError,
            validate_assessment,
        )

        with pytest.raises(IncompleteTrainingPlanError):
            validate_assessment(result, context)


def test_explicit_generation_refreshes_an_obsolete_binding_instead_of_a_cache_refusal(
    session, owner_case
):
    _, service, writer, _, _ = owner_case
    draft = service.generate_for_subject(session, "rag-owner")
    from copy import deepcopy

    citations = deepcopy(draft.citations)
    citations[0]["owner_rag"]["writer_configuration_sha256"] = "0" * 64
    draft.citations = citations
    session.commit()
    refreshed = service.generate_for_subject(session, "rag-owner")
    assert refreshed.id == draft.id and refreshed.revision == 2 and writer.calls == 2


@pytest.mark.parametrize("value", ["8-12", "16-20", "1", "1000-1001", "1-999999", "9-9"])
def test_transport_repetition_pattern_keeps_valid_ranges_without_clinical_limits(owner_case, value):
    import re

    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare({}, evidence, {"training_goal": "Força"})
    schema = ai._training_schema()
    constrain_writer_schema(schema, context)
    pattern = schema["properties"]["plan"]["properties"]["items"]["items"]["properties"][
        "repetitions"
    ]["pattern"]
    assert re.fullmatch(pattern, value)
    assert not re.fullmatch(pattern, "8-1")


def full_body_plan(context):
    from app.modules.training.completeness import FULL_BODY_PATTERNS

    choices = {
        "A": ["push_up", "dumbbell_row", "bodyweight_squat", "hip_bridge", "abdominal_curlup"],
        "B": [
            "dumbbell_floor_press",
            "dumbbell_row",
            "goblet_squat",
            "dumbbell_rdl",
            "abdominal_curlup",
        ],
        "C": [
            "dumbbell_overhead_press",
            "dumbbell_row",
            "stationary_lunge",
            "hip_bridge",
            "abdominal_curlup",
        ],
    }
    exercises = {e["key"]: e for e in dictionary()["exercises"]}
    sessions = {}
    for label in context["training_schedule"]["session_labels"] or ["A"]:
        sessions[label] = {
            pattern: [
                {
                    "exercise_name": key,
                    "sets": 3,
                    "repetitions": "8-12",
                    "rest_seconds": 120,
                    "load_guidance": LOAD_GUIDANCE[exercises[key]["load_capability"]],
                    "equipment_requirement": None,
                    "equipment_model_id": None,
                }
            ]
            for pattern, key in zip(FULL_BODY_PATTERNS, choices[label])
        }
        sessions[label]["accessories"] = []
    return {
        "name": "Corpo inteiro",
        "objective": context["effective_training_goal"],
        "sessions": sessions,
    }


def test_full_body_coverage_is_checked_before_any_potentially_false_positive_review(
    session, owner_case
):
    from app.modules.training.generation_service import InvalidTrainingGenerationError

    _, service, writer, source, _ = owner_case
    writer.analyze_training_request = lambda ctx: AiTrainingRequestFocus(
        scope="full_body", muscle_groups=[]
    )
    attach_writer(writer, source)
    with pytest.raises(InvalidTrainingGenerationError):
        service.generate_for_subject(
            session, "rag-owner", training_request="Força de corpo inteiro em três dias"
        )
    assert writer.calls == 2 and not getattr(writer, "review_contexts", [])


@pytest.mark.parametrize("three_days", [False, True])
def test_full_body_pattern_slots_cover_each_day_and_remain_bound_on_reuse(
    session, owner_case, three_days
):
    from app.modules.training.completeness import FULL_BODY_PATTERNS

    _, service, writer, source, evidence = owner_case
    request = "Treino de corpo inteiro para força" + (" em três dias" if three_days else "")
    writer.analyze_training_request = lambda ctx: AiTrainingRequestFocus(
        scope="full_body", muscle_groups=[]
    )

    def write(context):
        writer.calls += 1
        return AiTrainingGenerationResponse(
            plan=full_body_plan(context),
            citations=[source["chunks"][0]["id"]],
            knowledge_status="supported",
        )

    writer.generate_training = write
    draft = service.generate_for_subject(session, "rag-owner", training_request=request)
    assert draft.citations[0]["owner_rag"]["focus_scope"] == "full_body"
    owner_rag.validate_saved(session, draft, TrainingLifecycleService().content(session, draft))
    context = owner_rag.prepare(
        {"training_request": request, "training_focus": {"scope": "full_body"}},
        evidence,
        {"training_goal": "Força"},
    )
    schema = ai._training_schema()
    constrain_writer_schema(schema, context)
    constrain_session_schema(schema, context)
    days = schema["properties"]["plan"]["properties"]["sessions"]["properties"]
    assert list(days) == (list("ABC") if three_days else ["A"])
    assert all(
        set(day["required"]) == {*FULL_BODY_PATTERNS, "accessories"} for day in days.values()
    )
    assert schema["$defs"]["OwnerRagSlot_upper_pull"]["properties"]["exercise_name"]["enum"] == [
        "dumbbell_row"
    ]


def test_full_body_pattern_slot_cannot_relabel_a_movement_as_another_pattern(owner_case):
    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {
            "training_request": "Força de corpo inteiro em três dias",
            "training_focus": {"scope": "full_body"},
        },
        evidence,
        {"training_goal": "Força"},
    )
    plan = full_body_plan(context)
    plan["sessions"]["A"]["upper_push"][0]["exercise_name"] = "dumbbell_row"
    with pytest.raises(PrescriptionRejection, match="invalid_typed_candidate"):
        resolve_plan(plan, context)


def test_chat_full_body_request_keeps_scope_without_an_extra_focus_call(owner_case):
    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {"current_user_message": "Atualize o treino para corpo inteiro em três dias"},
        evidence,
        {"training_goal": "Força"},
    )
    assert context["training_focus"]["scope"] == "full_body"
    assert context["owner_rag_basis"]["focus_scope"] == "full_body"
    assert context["training_schedule"]["session_labels"] == list("ABC")


def test_session_fragments_cannot_reset_the_routine_content_correction_allowance(
    session, owner_case
):
    from app.modules.training.prescription_budget import attempt_budget

    _, service, writer, source, _ = owner_case

    def write(context):
        writer.calls += 1
        plan = grouped_plan(context)
        label = context["training_schedule"]["session_labels"][0]
        if writer.calls == 1 or label == "B":
            plan["sessions"][label][0]["repetitions"] = "]"
        return AiTrainingGenerationResponse(
            plan=plan, citations=[source["chunks"][0]["id"]], knowledge_status="supported"
        )

    writer.generate_training = write
    with attempt_budget(30) as budget:
        with pytest.raises(PrescriptionRejection, match="invalid_typed_candidate"):
            service.generate_for_subject(
                session, "rag-owner", training_request="Hipertrofia em três dias"
            )
        assert budget.content_corrections == 1 and budget.counts["writer"] == 3
    assert writer.calls == 3


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Força e hipertrofia. Objetivo principal: hipertrofia.", "hypertrophy"),
        ("Hipertrofia como objetivo principal e força secundária.", "hypertrophy"),
        ("Força e hipertrofia, prioridade: força.", "strength"),
    ],
)
def test_primary_goal_cues_do_not_invert_the_requested_priority(message, expected):
    assert owner_rag.goal_family(owner_rag.requested_goal(message, "Hipertrofia")) == expected


def test_duplicate_prescriptions_report_exact_positions_without_selecting_a_dose():
    from app.modules.training.schema import TrainingPlanVersionInput
    from app.modules.training.selection import (
        RedundantTrainingExerciseError,
        validate_exercise_selection,
    )

    row = {
        "exercise_name": "Agachamento (Dia A)",
        "sets": 2,
        "repetitions": "8-12",
        "load_guidance": "Peso corporal",
        "rest_seconds": 120,
    }
    plan = TrainingPlanVersionInput(
        name="Força", objective="Força", items=[row, {**row, "sets": 3}]
    )
    with pytest.raises(RedundantTrainingExerciseError) as caught:
        validate_exercise_selection(plan)
    assert caught.value.issues[0]["position"] == 2
    assert caught.value.issues[0]["duplicate_of"] == 1


@pytest.mark.parametrize("full_body", [False, True])
def test_wire_variation_excludes_a_prior_identity_but_preserves_required_patterns(
    owner_case, full_body
):
    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare(
        {
            "training_request": "Hipertrofia",
            "training_focus": {"scope": "full_body" if full_body else "unspecified"},
        },
        evidence,
        {"training_goal": "Hipertrofia"},
    )
    previous = {"bodyweight_squat", "push_up", "dumbbell_row", "hip_bridge", "abdominal_curlup"}
    context["training_schedule"] = {"session_labels": ["B"]}
    context["previous_session_exercise_keys"] = {"A": sorted(previous)}
    schema = ai._training_schema()
    constrain_writer_schema(schema, context)
    constrain_session_schema(schema, context)
    constrain_session_variation(schema, context)
    branches = schema["properties"]["plan"]["anyOf"]

    def identities(node):
        found = set()
        if isinstance(node, dict):
            names = node.get("properties", {}).get("exercise_name", {}).get("enum", [])
            found.update(name.split(" (Dia ")[0] for name in names)
            for value in node.values():
                found.update(identities(value))
        elif isinstance(node, list):
            for value in node:
                found.update(identities(value))
        return found

    assert len(branches) >= 2
    for branch in branches:
        allowed = identities(branch)
        assert previous - allowed
        assert allowed <= {e["key"] for e in dictionary()["exercises"]}
        if full_body:
            assert {"dumbbell_row", "abdominal_curlup"} <= allowed
            slots = branch["properties"]["sessions"]["properties"]["B"]["properties"]
            assert all(
                slot["items"]["properties"]["exercise_name"]["enum"] for slot in slots.values()
            )
