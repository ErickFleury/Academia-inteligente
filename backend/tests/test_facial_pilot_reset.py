import os

import pytest
from sqlalchemy import select, text
from test_biometric_access import known_client
from test_biometric_access_postgres import services
from test_knowledge import FakeEmbeddings, catalog_source
from test_training_review_postgres import sessions as sessions

from app.modules.clients.models import Account
from app.modules.equipment.models import EquipmentImage, EquipmentModel, EquipmentUnit
from app.modules.knowledge.bootstrap import seed_catalog
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeSource
from app.modules.training.prescription_development import DevelopmentInputConfirmation
from scripts.reset_facial_pilot import RESET_TABLES, clear_database, protected_users, table_counts


def test_bootstrap_and_service_users_are_preserved_and_disabled_admin_aborts():
    class Identity:
        def _access_token(self):
            return "synthetic"

        def _request(self, *args):
            return [{"name": "admin"}]

    users = [
        {"id": "bootstrap", "username": "owner", "enabled": True},
        {"id": "service", "serviceAccountClientId": "provisioner"},
        {"id": "test", "username": "test", "enabled": True},
    ]
    assert protected_users(Identity(), users, "owner") == {"bootstrap", "service"}
    users[0]["enabled"] = False
    with pytest.raises(RuntimeError):
        protected_users(Identity(), users, "owner")


@pytest.mark.skipif(os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in")
def test_explicit_reset_preserves_equipment_and_bootstrap_and_is_idempotent(sessions):
    enrollment, access = services()
    with sessions() as session:
        _, client_id = known_client(session, enrollment, access)
        seed_catalog(
            session,
            FakeEmbeddings(),
            {
                "version": 1,
                "sources": [catalog_source("public-kept"), catalog_source("private-erased")],
            },
        )
        private_source = session.get(KnowledgeSource, "private-erased")
        private_source.client_id, private_source.catalog_managed = client_id, False
        session.add(
            DevelopmentInputConfirmation(
                client_id=client_id, origin_sha256="a" * 64, snapshot={"synthetic": True}
            )
        )
        session.add(Account(keycloak_subject="bootstrap", email="admin@example.test"))
        model = EquipmentModel(name="Preserved equipment")
        session.add(model)
        session.flush()
        unit = EquipmentUnit(equipment_model_id=model.id, label="Preserved unit")
        session.add(unit)
        session.add(
            EquipmentImage(
                equipment_model_id=model.id,
                content=b"preserved-photo",
                media_type="image/webp",
                width=1,
                height=1,
            )
        )
        session.commit()
        model_id, unit_id = model.id, unit.id
        public_source = dict(
            session.execute(
                select(KnowledgeSource.__table__).where(KnowledgeSource.id == "public-kept")
            )
            .mappings()
            .one()
        )
        public_chunk = dict(
            session.execute(
                select(KnowledgeChunk.__table__).where(KnowledgeChunk.source_id == "public-kept")
            )
            .mappings()
            .one()
        )
        clear_database(session, {"bootstrap", "service"})
        session.commit()
        session.expire_all()
        assert session.get(EquipmentModel, model_id).name == "Preserved equipment"
        assert session.get(EquipmentUnit, unit_id).label == "Preserved unit"
        assert session.get(EquipmentImage, model_id).content == b"preserved-photo"
        assert session.scalars(select(Account.keycloak_subject)).all() == ["bootstrap"]
        assert (
            dict(session.execute(select(KnowledgeSource.__table__)).mappings().one())
            == public_source
        )
        assert (
            dict(session.execute(select(KnowledgeChunk.__table__)).mappings().one()) == public_chunk
        )
        counts = table_counts(session)
        assert all(counts[name] == 0 for name in RESET_TABLES)
        clear_database(session, {"bootstrap", "service"})
        session.commit()
        assert table_counts(session) == counts


@pytest.mark.skipif(os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in")
def test_reset_still_refuses_unreviewed_schema_changes(sessions):
    with sessions() as session:
        session.add(Account(keycloak_subject="retained", email="retained@example.test"))
        session.execute(text("CREATE TABLE unreviewed_extension (id INTEGER PRIMARY KEY)"))
        session.commit()
        with pytest.raises(RuntimeError, match="review the reset table allowlist"):
            clear_database(session, set())
        assert session.scalars(select(Account.keycloak_subject)).all() == ["retained"]
