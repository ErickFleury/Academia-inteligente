import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from sqlalchemy import event
from test_equipment_operational import equipment
from test_training_equipment_usability import approve, create, machine_content
from test_training_review_postgres import sessions as sessions
from training_fixtures import instructor

from app.modules.equipment.models import EquipmentModel, EquipmentUnit
from app.modules.equipment.service import EquipmentService
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.service import InvalidTrainingContentError

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


@pytest.mark.parametrize("change", ["outage", "unit_deactivation", "model_deactivation"])
def test_approval_waits_for_inventory_writer_and_rechecks_committed_state(sessions, change):
    with sessions() as session:
        instructor(session, "instructor-1")
        model, unit = equipment(session)
        draft = create(session, machine_content(model))
        model_id, unit_id, version_id = model.id, unit.id, draft.id
    attempted_lock = Event()

    def approval():
        with sessions() as session:
            # Deliberately retain stale inventory in the identity map.
            old_model = session.get(EquipmentModel, model_id)
            old_unit = session.get(EquipmentUnit, unit_id)
            assert old_model.active and old_unit.operational_state == "operational"
            version = session.get(TrainingPlanVersion, version_id)

            def before_execute(connection, cursor, statement, parameters, context, many):
                if "FROM equipment_model" in statement and "FOR UPDATE" in statement:
                    attempted_lock.set()

            event.listen(session.connection(), "before_cursor_execute", before_execute)
            try:
                approve(session, version)
                return "approved"
            except InvalidTrainingContentError:
                session.rollback()
                return "rejected"

    with sessions() as writer, ThreadPoolExecutor(max_workers=1) as pool:
        EquipmentService.lock_models(writer, {model_id})
        if change == "model_deactivation":
            writer.get(EquipmentModel, model_id).active = False
        elif change == "unit_deactivation":
            writer.get(EquipmentUnit, unit_id).active = False
        else:
            writer.get(EquipmentUnit, unit_id).operational_state = "out_of_order"
        writer.flush()
        result = pool.submit(approval)
        try:
            assert attempted_lock.wait(10)
            assert not result.done()
        finally:
            writer.commit()
        assert result.result(timeout=10) == "rejected"
    with sessions() as session:
        draft = session.get(TrainingPlanVersion, version_id)
        assert draft.status == "proposal" and draft.revision == 1


def test_existing_item_migration_preserves_legacy_content_and_reference_round_trip(sessions):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import select, text
    from test_training_lifecycle import data

    from app.modules.training.models import TrainingPlanItem

    with sessions() as session:
        instructor(session, "instructor-1")
        draft = create(session, data())
        identifier = draft.id
        # Reconstruct the pre-22 columns in this disposable test schema only.
        for table, column in [
            ("training_plan_item", "equipment_requirement"),
            ("training_plan_item", "equipment_model_id"),
            ("training_plan_version", "responsible_name"),
            ("training_plan_version", "responsible_employee_id"),
        ]:
            session.execute(text(f"ALTER TABLE {table} DROP COLUMN {column} CASCADE"))
        path = next(Path("alembic/versions").glob("20260927_22_*.py"))
        specification = importlib.util.spec_from_file_location("training_migration", path)
        migration = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(migration)
        migration.op = Operations(MigrationContext.configure(session.connection()))
        migration.upgrade()
        session.commit()
        session.expire_all()
        item = session.scalar(
            select(TrainingPlanItem).where(TrainingPlanItem.version_id == identifier)
        )
        assert item.exercise_name == "Agachamento"
        assert item.equipment_model_id is None and item.equipment_requirement is None
        model, _ = equipment(session)
        item.equipment_model_id, item.equipment_requirement = model.id, model.name
        session.commit()
        session.expire_all()
        assert item.equipment_model_id == model.id and item.equipment_requirement == "Leg Press"
