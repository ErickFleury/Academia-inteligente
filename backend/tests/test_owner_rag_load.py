"""Unmeasured-load provenance, shared correction and immutable prior versions."""

from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_owner_rag import owner_case as owner_case
from test_owner_rag import session as session

from app.modules.training import owner_rag
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.owner_rag_load import LOAD_ERROR, LOAD_GUIDANCE, validate_candidate
from app.modules.training.owner_rag_schema import constrain_writer_schema
from app.modules.training.prescription_contract import PrescriptionRejection
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.service import TrainingLifecycleService


def test_generated_load_is_corrected_before_review_and_bound_without_other_changes(
    session, owner_case
):
    _, service, writer, _, _ = owner_case
    original = writer.generate_training

    def write(context):
        response = original(context)
        if writer.calls == 1:
            response.plan["items"][0]["load_guidance"] = "2 kg"
        return response

    writer.generate_training = write
    draft = service.generate_for_subject(session, "rag-owner")
    assert writer.calls == 2 and len(writer.review_contexts) == 1
    correction = writer.contexts[1]["selection_correction"]
    assert correction["completeness_issues"] == [
        {
            "position": 1,
            "field": "load_guidance",
            "reason": LOAD_ERROR,
            "allowed": ["Peso corporal"],
        }
    ]
    content = TrainingLifecycleService().content(session, draft)
    assert content.items[0].load_guidance == "Peso corporal"
    assert content.items[0].sets == 3 and content.items[0].repetitions == "8"
    assert draft.status == "proposal" and draft.citations[0]["owner_rag"]


@pytest.mark.parametrize(
    "invalid",
    [
        "2kg",
        "2,5 kg",
        "5 lbs",
        "dois quilos",
        "dez libras",
        "Use 50% de 1RM",
        "Carga medida de outra pessoa",
        "Halteres",
    ],
)
def test_closed_load_contract_blocks_numeric_spelled_out_and_unrestricted_bypasses(
    session, owner_case, invalid
):
    _, service, writer, _, _ = owner_case
    original = writer.generate_training

    def write(context):
        response = original(context)
        response.plan["items"][0]["load_guidance"] = invalid
        return response

    writer.generate_training = write
    with pytest.raises(PrescriptionRejection, match=LOAD_ERROR):
        service.generate_for_subject(session, "rag-owner")
    assert writer.calls == 2 and not getattr(writer, "review_contexts", [])
    assert session.scalar(select(TrainingPlanVersion)) is None


@pytest.mark.parametrize(
    "field,value",
    [("sets", 4), ("rest_seconds", 90), ("repetitions", "12"), ("exercise_name", "push_up")],
)
def test_load_correction_cannot_change_other_prescription_fields(session, owner_case, field, value):
    _, service, writer, _, _ = owner_case
    original = writer.generate_training

    def write(context):
        response = original(context)
        if writer.calls == 1:
            response.plan["items"][0]["load_guidance"] = "2 kg"
        else:
            response.plan["items"][0][field] = value
        return response

    writer.generate_training = write
    with pytest.raises(PrescriptionRejection, match="load_repair_changed_other_fields"):
        service.generate_for_subject(session, "rag-owner")
    assert writer.calls == 2 and session.scalar(select(TrainingPlanVersion)) is None


def test_schema_narrows_load_and_backend_rejects_equipment_mismatch(owner_case):
    _, _, _, _, evidence = owner_case
    context = owner_rag.prepare({}, evidence, {"training_goal": "Hipertrofia"})
    schema = {
        "properties": {"exercise_name": {}, "repetitions": {}, "load_guidance": {"type": "string"}}
    }
    constrain_writer_schema(schema, context)
    assert set(schema["properties"]["load_guidance"]["enum"]) == {
        LOAD_GUIDANCE["bodyweight"],
        LOAD_GUIDANCE["external_unmeasured"],
    }
    plan = TrainingPlanVersionInput(
        name="Hipertrofia",
        objective="Hipertrofia",
        items=[
            {
                "exercise_name": "dumbbell_row",
                "sets": 3,
                "repetitions": "8-12",
                "rest_seconds": 120,
                "load_guidance": "Peso corporal",
            }
        ],
    )
    with pytest.raises(PrescriptionRejection) as caught:
        validate_candidate(plan, context)
    assert caught.value.issues[0]["allowed"] == [LOAD_GUIDANCE["external_unmeasured"]]
    plan.items[0].load_guidance = LOAD_GUIDANCE["external_unmeasured"]
    validate_candidate(plan, context)


@pytest.mark.parametrize(
    "message",
    [
        "Quantos kg devo usar?",
        "Calcule minha carga",
        "Quero a carga em kg no supino",
        "Calcular meu 1RM",
    ],
)
def test_explicit_measured_load_requirement_is_not_repaired_by_a_qualitative_draft(
    owner_case, message
):
    _, _, writer, _, evidence = owner_case
    with pytest.raises(PrescriptionRejection, match="measured_baseline_required") as caught:
        owner_rag.prepare({"training_request": message}, evidence, {"training_goal": "Hipertrofia"})
    assert caught.value.category == "missing_input" and writer.calls == 0


def test_final_binding_still_rejects_a_provider_load_bypassing_selection(owner_case):
    _, _, writer, _, evidence = owner_case
    context = owner_rag.prepare({}, evidence, {"training_goal": "Hipertrofia"})
    response = writer.generate_training(context)
    plan = TrainingPlanVersionInput.model_validate(response.plan)
    plan.items[0].load_guidance = "2 kg"
    with pytest.raises(PrescriptionRejection, match=LOAD_ERROR):
        owner_rag.bind(evidence.resolve_citations(response.citations), context, plan)


def test_source_example_and_demographics_cannot_supply_an_individual_load(owner_case):
    _, _, writer, _, evidence = owner_case
    context = owner_rag.prepare({}, evidence, {"training_goal": "Hipertrofia", "weight_kg": 70})
    context["knowledge"]["chunks"] = [{"content": "Exemplo bibliográfico: 2 kg em um estudo."}]
    response = writer.generate_training(context)
    plan = TrainingPlanVersionInput.model_validate(response.plan)
    plan.items[0].load_guidance = "2 kg"
    with pytest.raises(PrescriptionRejection, match=LOAD_ERROR):
        validate_candidate(plan, context)


def test_failed_load_replacement_preserves_the_existing_draft_and_submission(session, owner_case):
    _, service, writer, _, _ = owner_case
    draft = service.generate_for_subject(session, "rag-owner")
    before = TrainingLifecycleService().content(session, draft)
    revision = draft.revision
    original = writer.generate_training

    def write(context):
        response = original(context)
        response.plan["items"][0]["load_guidance"] = "2 kg"
        return response

    writer.generate_training = write
    with pytest.raises(PrescriptionRejection):
        service.generate_for_subject(session, "rag-owner", replace_existing=True)
    assert TrainingLifecycleService().content(session, draft) == before
    assert draft.revision == revision and draft.submitted_for_review_at is None


def test_configuration_change_invalidates_replay_without_modifying_saved_content(
    session, owner_case, monkeypatch
):
    _, service, _, _, _ = owner_case
    draft = service.generate_for_subject(session, "rag-owner")
    before = TrainingLifecycleService().content(session, draft)
    old = owner_rag.configuration
    monkeypatch.setattr(
        owner_rag, "configuration", lambda: {**old(), "instruction_version": "unapproved"}
    )
    with pytest.raises(PrescriptionRejection):
        owner_rag.validate_saved(session, draft, before)
    assert TrainingLifecycleService().content(session, draft) == before


def test_load_and_representation_errors_share_one_correction(session, owner_case):
    _, service, writer, _, _ = owner_case
    original = writer.generate_training

    def write(context):
        response = original(context)
        if writer.calls == 1:
            response.plan["items"][0]["repetitions"] = "]"
        else:
            response.plan["items"][0]["load_guidance"] = "2 kg"
        return response

    writer.generate_training = write
    with pytest.raises(PrescriptionRejection, match=LOAD_ERROR):
        service.generate_for_subject(session, "rag-owner")
    assert writer.calls == 2 and not getattr(writer, "review_contexts", [])
    assert session.scalar(select(TrainingPlanVersion)) is None


def test_mandatory_review_cannot_get_an_extra_correction_after_load_repair(session, owner_case):
    from app.integrations.ai import AiTrainingPlanAssessment
    from app.modules.training.generation_service import InvalidTrainingGenerationError

    _, service, writer, _, _ = owner_case
    original = writer.generate_training
    reviews = []

    def write(context):
        response = original(context)
        if writer.calls == 1:
            response.plan["items"][0]["load_guidance"] = "2 kg"
        return response

    def review(context):
        reviews.append(context)
        return AiTrainingPlanAssessment(
            sessions=[{"label": "A", "complete": False, "issues": ["restriction_not_respected"]}]
        )

    writer.generate_training, writer.assess_training = write, review
    with pytest.raises(InvalidTrainingGenerationError):
        service.generate_for_subject(session, "rag-owner")
    assert writer.calls == 2 and len(reviews) == 1
    assert session.scalar(select(TrainingPlanVersion)) is None


def test_chat_edit_repairs_load_before_review_and_preserves_replay(session, owner_case):
    from app.integrations.ai import AiTrainingChatResponse
    from app.modules.training.chat_service import TrainingChatService

    _, generation, writer, source, _ = owner_case
    draft = generation.generate_for_subject(session, "rag-owner")
    content = TrainingLifecycleService().content(session, draft).model_dump(mode="json")
    contexts = []
    writer.review_contexts.clear()

    def write(context):
        contexts.append(context)
        plan = deepcopy(content)
        plan["items"][0]["load_guidance"] = "2 kg" if len(contexts) == 1 else "Peso corporal"
        return AiTrainingChatResponse(
            assistant_message="Proposta para revisão.",
            draft_update=plan,
            citations=[source["chunks"][0]["id"]],
            knowledge_status="supported",
        )

    writer.training_chat = write
    service = TrainingChatService(
        provider=writer, generation_service=generation, knowledge_service=generation._knowledge
    )
    request_id = uuid4()
    service.submit_for_subject(
        session, "rag-owner", message="Atualize a carga do rascunho.", client_request_id=request_id
    )
    assert len(contexts) == 2 and len(writer.review_contexts) == 1
    assert draft.revision == 2 and draft.citations[0]["owner_rag"]
    service.submit_for_subject(
        session, "rag-owner", message="Reenvio", client_request_id=request_id
    )
    assert len(contexts) == 2


def test_adaptation_repairs_changed_load_and_keeps_exact_approved_items(session, owner_case):
    from test_training_adaptations import (
        FakeAdaptationProvider,
        adjust_response,
        current_plan,
        source_message,
    )

    from app.modules.training.adaptation_service import TrainingAdaptationService

    client, generation, _, source, _ = owner_case
    base = current_plan(session, client)
    before = TrainingLifecycleService().content(session, base)
    source_id = uuid4()
    source_message(session, client, source_id)
    provider = FakeAdaptationProvider(adjust_response())

    def write(context):
        provider.calls += 1
        response = adjust_response()
        response.operations[0]["item"]["load_guidance"] = (
            "2 kg" if provider.calls == 1 else "Peso corporal"
        )
        response.citations = [source["chunks"][0]["id"]]
        response.knowledge_status = "supported"
        return response

    provider.generate_adaptation = write
    service = TrainingAdaptationService(provider=provider, knowledge_service=generation._knowledge)
    proposal = service.generate(
        session,
        "rag-owner",
        source_client_request_id=source_id,
        client_request_id=uuid4(),
        reason="Ajuste sintético",
    )
    assert provider.calls == 2 and len(provider.review_contexts) == 1
    result = service._apply(session, base, proposal)
    assert result.items[0].load_guidance == "Peso corporal"
    assert result.items[1] == before.items[1]
    assert proposal.citations[0]["owner_rag"]["preserved_item_hashes"]
    service.client_decide(session, "rag-owner", proposal.id, accept=True)
    assert TrainingLifecycleService().content(session, base) == before and base.status == "current"
