import importlib.util
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from test_training_review_postgres import sessions as sessions

from app.modules.equipment.models import EquipmentUnit
from app.modules.equipment.service import EquipmentService, EquipmentStateConflictError

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


def test_migration_populates_existing_units_and_enforces_state(sessions):
    with sessions() as session:
        service = EquipmentService()
        model = service.create_model(session, "Leg Press", None, None, True)
        unit = service.create_unit(session, model.id, "A", True)
        identifier = unit.id
        specification = importlib.util.spec_from_file_location(
            "operational_migration",
            Path("alembic/versions/20260927_25_equipment_operational_state.py"),
        )
        migration = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(migration)
        migration.op = Operations(MigrationContext.configure(session.connection()))
        migration.downgrade()
        migration.upgrade()
        session.commit()
        session.expire_all()
        unit = session.get(EquipmentUnit, identifier)
        assert (
            unit.operational_state == "operational"
            and unit.operational_revision == 1
            and unit.active
        )
        assert service.catalog(session)[0].active_quantity == 1
        with pytest.raises(IntegrityError):
            session.execute(text("UPDATE equipment_unit SET operational_state='free'"))
        session.rollback()


def test_two_operational_updates_cannot_overwrite_stale_revision(sessions):
    service = EquipmentService()
    with sessions() as session:
        model = service.create_model(session, "Leg Press", None, None, True)
        unit_id = service.create_unit(session, model.id, "A", True).id
    ready = Barrier(2)

    def update(_):
        with sessions() as session:
            ready.wait(timeout=10)
            try:
                service.set_operational_state(session, unit_id, "out_of_order", 1)
                return "success"
            except EquipmentStateConflictError:
                session.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(update, range(2))) == ["conflict", "success"]


def test_parallel_batches_generate_distinct_unit_labels(sessions):
    service = EquipmentService()
    with sessions() as session:
        model_id = service.create_model(session, "Esteira", None, None, True).id
    ready = Barrier(2)

    def add(_):
        with sessions() as session:
            ready.wait(timeout=10)
            return [u.label for u in service.create_units(session, model_id, 3, "EST")]

    with ThreadPoolExecutor(max_workers=2) as pool:
        labels = [label for batch in pool.map(add, range(2)) for label in batch]
    assert len(set(labels)) == 6


def test_equipment_details_migration_preserves_inventory(sessions):
    with sessions() as session:
        service = EquipmentService()
        model = service.create_model(session, "Esteira", None, None, True, initial_quantity=2)
        identifier = model.id
        spec = importlib.util.spec_from_file_location(
            "equipment_details", Path("alembic/versions/20260927_30_equipment_details_images.py")
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        migration.op = Operations(MigrationContext.configure(session.connection()))
        migration.downgrade()
        migration.upgrade()
        session.commit()
        session.expire_all()
        assert service.model(session, identifier).brand is None
        assert service.catalog(session)[0].active_quantity == 2
