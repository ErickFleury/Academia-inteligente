"""Execute the new migration without fabricating policies or old qualification."""

import os
import runpy
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, MetaData, Table, Uuid, create_engine, inspect, select, text


@pytest.fixture(params=["sqlite", "postgresql"])
def migration_engine(request):
    if request.param == "sqlite":
        engine = create_engine("sqlite://")
        try:
            yield engine
        finally:
            engine.dispose()
        return
    if os.getenv("TEST_POSTGRES") != "1":
        pytest.skip("Isolated PostgreSQL opt-in")
    schema = "test_prescription_migration_" + uuid4().hex
    admin = create_engine(os.environ["DATABASE_URL"])
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"options": f"-csearch_path={schema} -clock_timeout=5000"},
    )
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_prescription_migration_creates_empty_tables_and_preserves_existing_data(migration_engine):
    engine = migration_engine
    metadata = MetaData()
    parents = [
        Table(name, metadata, Column("id", Uuid(), primary_key=True))
        for name in ("client", "training_plan_version", "training_adaptation_proposal")
    ]
    retained_id = uuid4()
    with engine.begin() as connection:
        metadata.create_all(connection)
        for parent in parents:
            connection.execute(parent.insert().values(id=retained_id))
        migration = runpy.run_path(
            str(
                Path(__file__).parents[1]
                / "alembic"
                / "versions"
                / "20261023_35_prescription_validation.py"
            )
        )
        with Operations.context(MigrationContext.configure(connection)):
            migration["upgrade"]()
        tables = {
            name
            for name in inspect(connection).get_table_names()
            if name.startswith("training_prescription_")
        }
        assert len(tables) == 3
        for table in tables:
            assert connection.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one() == 0
        inspector = inspect(connection)
        for table in tables:
            assert inspector.get_foreign_keys(table)
            assert inspector.get_indexes(table)
        for parent in parents:
            assert connection.execute(select(parent.c.id)).scalar_one() == retained_id
        with Operations.context(MigrationContext.configure(connection)):
            migration["downgrade"]()
        assert not tables.intersection(inspect(connection).get_table_names())
        for parent in parents:
            assert connection.execute(select(parent.c.id)).scalar_one() == retained_id
