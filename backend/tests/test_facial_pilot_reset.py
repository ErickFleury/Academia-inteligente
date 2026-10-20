import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from test_biometric_access import known_client
from test_biometric_access_postgres import services
from test_training_review_postgres import sessions as sessions

from app.modules.clients.models import Account, Client
from app.modules.equipment.models import EquipmentImage, EquipmentModel, EquipmentUnit
from app.modules.knowledge.models import ReferencePassage, ReferenceSource, ReferenceVersion
from app.modules.memory.models import ClientMemoryFact
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
        known_client(session, enrollment, access)
        session.add(
            ClientMemoryFact(
                client_id=session.scalar(select(Client.id)),
                category="preference",
                text="Prefiro treinar cedo.",
                attribution="client_report",
                reported_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        reference = ReferenceSource(title="Preserved shared manual")
        session.add(reference)
        session.flush()
        version = ReferenceVersion(
            source_id=reference.id, number=1, media_type="text/plain", raw_content=b"fixture"
        )
        session.add(version)
        session.flush()
        session.add(
            ReferencePassage(
                version_id=version.id,
                position=1,
                location="text",
                content="Shared fixture",
                embedding=[1, 0],
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
        clear_database(session, {"bootstrap", "service"})
        session.commit()
        session.expire_all()
        assert session.get(EquipmentModel, model_id).name == "Preserved equipment"
        assert session.get(EquipmentUnit, unit_id).label == "Preserved unit"
        assert session.get(EquipmentImage, model_id).content == b"preserved-photo"
        assert session.scalars(select(Account.keycloak_subject)).all() == ["bootstrap"]
        counts = table_counts(session)
        assert all(counts[name] == 0 for name in RESET_TABLES)
        assert (
            counts["ai_reference_source"]
            == counts["ai_reference_version"]
            == counts["ai_reference_passage"]
            == 1
        )
        clear_database(session, {"bootstrap", "service"})
        session.commit()
        assert table_counts(session) == counts
