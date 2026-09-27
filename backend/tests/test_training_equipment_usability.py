from uuid import uuid4

import pytest
from sqlalchemy import select
from test_equipment_operational import equipment
from test_training_generation import FakeProvider, complete_onboarding, proposal
from test_training_lifecycle import client_id, data
from test_training_lifecycle import session as session
from test_training_review import api as api

from app.integrations.ai import _training_schema
from app.modules.equipment.models import EquipmentModel
from app.modules.equipment.service import EquipmentService
from app.modules.training.generation_service import (
    InitialTrainingGenerationService,
    InvalidTrainingGenerationError,
)
from app.modules.training.models import TrainingPlan, TrainingPlanVersion
from app.modules.training.service import InvalidTrainingContentError, TrainingLifecycleService


def machine_content(model):
    content = data()
    content.items[0].equipment_model_id = model.id
    content.items[0].equipment_requirement = model.name
    return content


def create(session, content):
    return TrainingLifecycleService().create_proposal(
        session,
        client_id=client_id(session),
        data=content,
        created_by="instructor-1",
        origin="instructor",
    )


def approve(session, version):
    return TrainingLifecycleService().approve(
        session,
        plan_id=version.plan_id,
        version_number=version.version_number,
        actor="instructor-1",
        expected_revision=version.revision,
    )


@pytest.mark.parametrize(
    "invalid", ["unknown", "inactive", "zero", "out_of_order", "missing", "missing_description"]
)
def test_new_manual_and_generated_machine_items_are_rejected_atomically(session, invalid):
    model, unit = equipment(session)
    content = machine_content(model)
    if invalid == "unknown":
        content.items[0].equipment_model_id = uuid4()
    elif invalid == "inactive":
        model.active = False
    elif invalid == "zero":
        unit.active = False
    elif invalid == "out_of_order":
        unit.operational_state = "out_of_order"
    elif invalid == "missing":
        content.items[0].equipment_model_id = None
    else:
        content.items[0].equipment_requirement = ""
    session.commit()
    owner = client_id(session)
    with pytest.raises(InvalidTrainingContentError):
        TrainingLifecycleService().create_proposal(
            session, client_id=owner, data=content, created_by="instructor-1", origin="instructor"
        )
    complete_onboarding(session, "client")
    service = InitialTrainingGenerationService(
        provider=FakeProvider(proposal(**content.model_dump(mode="json")))
    )
    with pytest.raises(InvalidTrainingGenerationError):
        service.generate_for_subject(session, "client")
    assert session.scalars(select(TrainingPlan)).all() == []
    assert session.scalars(select(TrainingPlanVersion)).all() == []


def test_initial_context_is_minimal_usable_and_bounded_and_schema_carries_reference(session):
    usable, _ = equipment(session)
    blocked = EquipmentService().create_model(session, "Fora de serviço", None, None, True)
    unit = EquipmentService().create_unit(session, blocked.id, "Private unit label", True)
    EquipmentService().set_operational_state(session, unit.id, "out_of_order", 1)
    client_id(session)
    complete_onboarding(session, "client")
    provider = FakeProvider(proposal(**machine_content(usable).model_dump(mode="json")))
    draft = InitialTrainingGenerationService(provider=provider).generate_for_subject(
        session, "client"
    )
    assert provider.contexts[0]["active_equipment_models"] == [
        {"id": str(usable.id), "name": usable.name}
    ]
    assert TrainingLifecycleService.content(session, draft).items[0].equipment_model_id == usable.id
    schema = _training_schema()["properties"]["plan"]["properties"]["items"]["items"]
    assert {"equipment_model_id", "equipment_requirement"}.issubset(schema["required"])
    for index in range(105):
        model = EquipmentService().create_model(session, f"Modelo {index}", None, None, True)
        EquipmentService().create_unit(session, model.id, None, True)
    assert len(EquipmentService().training_context(session)) == 100


def test_provider_time_outage_is_revalidated_after_response(session):
    model, unit = equipment(session)
    client_id(session)
    complete_onboarding(session, "client")

    class OutageProvider(FakeProvider):
        def generate_training(self, context):
            EquipmentService().set_operational_state(session, unit.id, "out_of_order", 1)
            return super().generate_training(context)

    service = InitialTrainingGenerationService(
        provider=OutageProvider(proposal(**machine_content(model).model_dump(mode="json")))
    )
    with pytest.raises(InvalidTrainingGenerationError):
        service.generate_for_subject(session, "client")
    assert session.scalars(select(TrainingPlanVersion)).all() == []


def test_saved_new_item_is_not_grandfathered_at_approval_or_subsequent_save(session, api):
    model, unit = equipment(session)
    draft = create(session, machine_content(model))
    EquipmentService().set_operational_state(session, unit.id, "out_of_order", 1)
    http, _ = api
    body = {**machine_content(model).model_dump(mode="json"), "expected_revision": 1}
    path = f"/training/plans/{draft.plan_id}/versions/1"
    assert http.patch(path, body).status_code == 422
    assert http.post(path + "/approve", {"expected_revision": 1}).status_code == 422
    session.refresh(draft)
    assert draft.status == "proposal" and draft.revision == 1
    assert not session.get(TrainingPlan, draft.plan_id).is_current


def test_unchanged_approved_items_survive_outage_but_edits_and_duplicates_do_not(session):
    model, unit = equipment(session)
    original = machine_content(model)
    current = approve(session, create(session, original))
    service = TrainingLifecycleService()
    EquipmentService().set_operational_state(session, unit.id, "out_of_order", 1)
    EquipmentService().update_model(
        session, model.id, name="Renamed", description=None, image_url=None, active=False
    )
    draft = service.create_revision(
        session, plan_id=current.plan_id, version_number=1, data=original, actor="instructor-1"
    )
    for field, value in [
        ("sets", 4),
        ("exercise_name", "Outro exercício"),
        ("equipment_requirement", "Outra descrição"),
    ]:
        changed = original.model_copy(deep=True)
        setattr(changed.items[0], field, value)
        with pytest.raises(InvalidTrainingContentError):
            service.revise(
                session,
                plan_id=draft.plan_id,
                version_number=2,
                data=changed,
                actor="instructor-1",
                expected_revision=1,
            )
    duplicated = original.model_copy(deep=True)
    duplicated.items.append(original.items[0].model_copy())
    with pytest.raises(InvalidTrainingContentError):
        service.revise(
            session,
            plan_id=draft.plan_id,
            version_number=2,
            data=duplicated,
            actor="instructor-1",
            expected_revision=1,
        )
    updated = original.model_copy(deep=True)
    updated.name = "Revisado"
    service.revise(
        session,
        plan_id=draft.plan_id,
        version_number=2,
        data=updated,
        actor="instructor-1",
        expected_revision=1,
    )
    approve(session, draft)
    assert service.content(session, current) == original
    assert service.content(session, draft).items == original.items
    assert session.get(EquipmentModel, model.id).name == "Renamed"


def test_usable_selector_is_bounded_minimal_and_authenticated(session, api):
    http, _ = api
    models = [equipment(session)[0] for _ in range(3)]
    first = http.get("/instructor/equipment/usable-models?limit=2").json()
    assert len(first["items"]) == 2 and first["next_cursor"]
    assert all(set(item) == {"id", "name"} for item in first["items"])
    last = http.get(
        "/instructor/equipment/usable-models?limit=2&cursor=" + first["next_cursor"]
    ).json()
    assert len(last["items"]) == 1 and last["next_cursor"] is None
    assert {item["id"] for item in first["items"] + last["items"]} == {
        str(model.id) for model in models
    }
    assert http.get("/instructor/equipment/usable-models?limit=101").status_code == 422
