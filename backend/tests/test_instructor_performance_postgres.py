"""DEC-16 bounded personal-use measurements; synthetic disposable PostgreSQL data."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

import pytest
from test_clients import AsgiClient, FakeIdentityProvider
from test_training_lifecycle import data
from test_training_review_postgres import sessions as sessions
from training_fixtures import instructor

from app.database import get_database_session
from app.main import create_app
from app.modules.clients.models import Account, Client
from app.modules.equipment.service import EquipmentService
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.onboarding.models import Onboarding
from app.modules.progress.models import ProgressUpdate
from app.modules.social.models import SocialProfile
from app.modules.training.models import TrainingAiConversation, TrainingAiMessage
from app.modules.training.service import TrainingLifecycleService

pytestmark = pytest.mark.skipif(
    os.getenv("TEST_POSTGRES") != "1", reason="Isolated PostgreSQL opt-in"
)


def test_fifty_client_internal_queries_writes_and_three_request_burst(sessions, monkeypatch):
    lifecycle = TrainingLifecycleService()
    with sessions() as session:
        instructor(session, "instructor-1")
        for index in range(50):
            owner = Client(
                name=f"Cliente sintético {index:02d}",
                account=Account(
                    email=f"synthetic-{index}@example.test", keycloak_subject=f"synthetic-{index}"
                ),
            )
            session.add(owner)
            session.flush()
            session.add(
                Onboarding(
                    client_id=owner.id,
                    status="draft",
                    training_goal="Força",
                    height_cm=170,
                    weight_kg=70,
                )
            )
            conversation = TrainingAiConversation(client_id=owner.id, summary="Resumo sintético")
            session.add(conversation)
            session.flush()
            session.add(
                TrainingAiMessage(
                    conversation_id=conversation.id,
                    role="user",
                    sequence=1,
                    content="Mensagem sintética de treino",
                )
            )
            session.add(SocialProfile(client_id=owner.id, visible_to_clients=index % 3 != 0))
            session.add(
                ProgressUpdate(
                    client_id=owner.id, content="Publicação sintética", visibility="shared"
                )
            )
            session.commit()
            version = lifecycle.create_proposal(
                session,
                client_id=owner.id,
                data=data(),
                created_by="instructor-1",
                origin="instructor",
            )
            if index < 25:
                for number in (1, 2):
                    lifecycle.approve(
                        session,
                        plan_id=version.plan_id,
                        version_number=number,
                        actor="instructor-1",
                        expected_revision=version.revision,
                    )
                    version = lifecycle.create_revision(
                        session,
                        plan_id=version.plan_id,
                        version_number=number,
                        data=data(),
                        actor="instructor-1",
                    )
            target = owner.id
        draft_plan, draft_number, draft_revision = (
            version.plan_id,
            version.version_number,
            version.revision,
        )
        equipment = EquipmentService()
        model = equipment.create_model(session, "Máquina sintética", None, None, True)
        unit = equipment.create_unit(session, model.id, "Unidade sintética", True)
        unit_id = unit.id
    app = create_app()

    def database():
        with sessions() as session:
            yield session

    app.dependency_overrides[get_database_session] = database
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(AuthenticatedIdentity("instructor-1", "test", ("instructor",))),
    )
    http = AsgiClient(app)
    metrics = {}
    for name, path in {
        "instructor_feed": "/instructor/social/feed?limit=20",
        "client_search": "/instructor/clients?search=sintetico&limit=20",
        "current_collections": "/training/collections?limit=20",
        "pending_review": "/training/pending?limit=20",
        "responsible_options": "/training/collections/responsible?limit=20",
        "onboarding_read": f"/instructor/clients/{target}/onboarding",
        "equipment_read": "/instructor/equipment?limit=20",
        "usable_equipment": "/instructor/equipment/usable-models?limit=20",
    }.items():
        samples = []
        for _ in range(10):
            start = perf_counter()
            assert http.get(path).status_code == 200
            samples.append(perf_counter() - start)
        assert sum(value <= 2 for value in samples) >= 9, (name, samples)
        metrics[name] = {
            "runs": 10,
            "under_2s": sum(value <= 2 for value in samples),
            "max_ms": round(max(samples) * 1000, 2),
        }
    for name in ["draft_save", "onboarding_save", "equipment_toggle"]:
        samples = []
        for index in range(10):
            if name == "draft_save":
                path = f"/training/plans/{draft_plan}/versions/{draft_number}"
                body = {
                    **data().model_dump(mode="json"),
                    "expected_revision": draft_revision + index,
                }
            elif name == "onboarding_save":
                path = f"/instructor/clients/{target}/onboarding"
                body = {"training_goal": f"Meta sintética {index}"}
            else:
                path = f"/instructor/equipment/units/{unit_id}/operational-state"
                body = {
                    "operational_state": "out_of_order" if index % 2 == 0 else "operational",
                    "expected_revision": index + 1,
                }
            start = perf_counter()
            assert http.patch(path, body).status_code == 200
            samples.append(perf_counter() - start)
        assert sum(value <= 2 for value in samples) >= 9, (name, samples)
        metrics[name] = {
            "runs": 10,
            "under_2s": sum(value <= 2 for value in samples),
            "max_ms": round(max(samples) * 1000, 2),
        }
    with ThreadPoolExecutor(max_workers=3) as workers:
        start = perf_counter()
        results = list(
            workers.map(lambda _: http.get("/instructor/clients?limit=20").status_code, range(3))
        )
    assert results == [200, 200, 200]
    metrics["burst"] = {"requests": 3, "total_ms": round((perf_counter() - start) * 1000, 2)}
    print("INSTRUCTOR_MEASUREMENTS=" + json.dumps(metrics, sort_keys=True))


def test_postgres_public_feed_pagination(sessions):
    from test_progress_updates import test_instructor_pagination_filters_private_posts_before_limit

    with sessions() as session:
        test_instructor_pagination_filters_private_posts_before_limit(session)
