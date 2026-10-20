"""Manual local inference smoke test using synthetic fixtures in a disposable schema.

This is never collected by pytest. All ordinary automated tests retain controlled
providers. Existing test factories supply synthetic records, not fake AI outputs.
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from test_training_chat import create_client  # noqa: E402
from test_training_generation import complete_onboarding  # noqa: E402
from training_fixtures import instructor  # noqa: E402

import app.main  # noqa: E402, F401 -- register domain models
from app.database import Base  # noqa: E402
from app.modules.assistant.runtime import AssistantError  # noqa: E402
from app.modules.knowledge.service import KnowledgeService  # noqa: E402
from app.modules.memory.service import MemoryService  # noqa: E402
from app.modules.onboarding.conversation_service import OnboardingConversationService  # noqa: E402
from app.modules.onboarding.draft_service import OnboardingDraftService  # noqa: E402
from app.modules.training.adaptation_service import TrainingAdaptationService  # noqa: E402
from app.modules.training.chat_service import TrainingChatService  # noqa: E402
from app.modules.training.generation_service import InitialTrainingGenerationService  # noqa: E402
from app.modules.training.models import TrainingAiMessage, TrainingPlanVersion  # noqa: E402
from app.modules.training.service import TrainingLifecycleService  # noqa: E402


def run():
    if (
        os.getenv("AI_PROVIDER", "ollama") != "ollama"
        or os.getenv("AI_EMBEDDING_PROVIDER", "ollama") != "ollama"
    ):
        raise SystemExit("Explicit local adapters are required.")
    report = {"started_at": datetime.now(UTC).isoformat(), "synthetic_only": True, "steps": []}
    path = Path(sys.argv[1])
    if path.exists():
        raise SystemExit("Use a new report path.")
    schema = "eval_workflows_" + uuid4().hex
    admin = create_engine(os.environ["DATABASE_URL"])
    with admin.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        os.environ["DATABASE_URL"], connect_args={"options": f"-csearch_path={schema}"}
    )

    def step(name, operation):
        started = monotonic()
        try:
            value = operation()
            row = {"step": name, "status": "success", "result": value}
        except Exception as error:
            row = {"step": name, "status": "failure", "error_type": type(error).__name__}
            if isinstance(error, AssistantError):
                row["error"] = error.code
        row["seconds"] = round(monotonic() - started, 3)
        report["steps"].append(row)
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
        print(json.dumps(row, ensure_ascii=False, default=str), flush=True)
        return row["status"] == "success"

    try:
        Base.metadata.create_all(engine)
        sessions = sessionmaker(bind=engine, expire_on_commit=False)
        with sessions() as session:
            client = create_client(session, "pilot-client", "pilot@example.test")
            client_id = client.id
            instructor(session, "pilot-instructor")
        os.environ["AI_ORCHESTRATION_ENABLED"] = "true"
        os.environ["AI_ORCHESTRATION_CLIENT_IDS"] = str(client_id)
        knowledge = KnowledgeService()
        with sessions() as session:
            version = knowledge.upload(
                session,
                title="Protocolo sintético do piloto de software",
                media_type="text/plain",
                raw=(
                    "Material fictício exclusivo para avaliação do software, não prescrição. "
                    "No cenário de teste, o plano inicial deve ser uma proposta para revisão "
                    "do instrutor. O protocolo demonstrativo de força tem agachamento sem "
                    "carga, duas séries de oito repetições, e remada com elástico, duas séries "
                    "de dez repetições. Descanso de sessenta segundos entre séries. "
                    "Não inclui saltos. Para o pedido explícito de descanso maior neste cenário, "
                    "proponha noventa segundos, mantendo exercícios, carga e repetições. "
                    "Toda alteração exige confirmação do cliente e aprovação do instrutor."
                ).encode(),
            )
        knowledge.import_next(sessions)
        with sessions() as session:
            knowledge.transition(session, version["id"], "activate", version["revision"])

        def onboarding():
            with sessions() as session:
                scope = OnboardingDraftService().resolve_client_scope(session, "pilot-client")
                service = OnboardingConversationService()
                service.submit(
                    session, scope, message="Quero ganhar força.", client_request_id=uuid4()
                )
                state = service.state(session, scope)
                return {
                    "reply": state.messages[-1].content,
                    "completion_ready": state.completion_ready,
                }

        step("onboarding", onboarding)
        with sessions() as session:
            complete_onboarding(
                session,
                "pilot-client",
                has_limitations_or_complaints=False,
                limitations_or_complaints=None,
                has_health_conditions=False,
                health_conditions=None,
            )

        def memory_chat():
            with sessions() as session:
                request_id = uuid4()
                service = TrainingChatService()
                state = service.submit_for_subject(
                    session,
                    "pilot-client",
                    message="Prefiro treinar de manhã.",
                    client_request_id=request_id,
                )
                retried = service.submit_for_subject(
                    session,
                    "pilot-client",
                    message="Ignored retry input",
                    client_request_id=request_id,
                )
                assert len(retried.messages) == len(state.messages)
                facts = MemoryService.snapshot(session, client_id)
                preference = next(
                    f for f in facts["facts"] if f["text"] == "Prefiro treinar de manhã."
                )
                changed = MemoryService().edit(
                    session,
                    client_id,
                    preference["id"],
                    facts["revision"],
                    "Prefiro treinar à tarde.",
                )
                cleared = MemoryService().edit(
                    session, client_id, preference["id"], changed["revision"]
                )
                assert all(f["id"] != preference["id"] for f in cleared["facts"])
                return {"reply": state.messages[-1].content, "retry_and_memory_controls": "passed"}

        step("training_chat_memory_retry_forget", memory_chat)

        def generate():
            with sessions() as session:
                service = InitialTrainingGenerationService()
                plan = service.generate_for_subject(session, "pilot-client")
                assert plan.status == "proposal" and plan.approved_by is None
                assert service.generate_for_subject(session, "pilot-client").id == plan.id
                result = {
                    "name": plan.name,
                    "status": plan.status,
                    "citations": plan.reference_citations,
                }
                approved = TrainingLifecycleService().approve(
                    session,
                    plan_id=plan.plan_id,
                    version_number=plan.version_number,
                    actor="pilot-instructor",
                    expected_revision=plan.revision,
                )
                assert approved.status == "current"
                return result

        generated = step("initial_plan_and_instructor_review", generate)

        def adapt():
            with sessions() as session:
                request_id = uuid4()
                started_chat = monotonic()
                TrainingChatService().submit_for_subject(
                    session,
                    "pilot-client",
                    message="Quero aumentar o descanso para noventa segundos entre as séries.",
                    client_request_id=request_id,
                )
                chat_seconds = monotonic() - started_chat
                service = TrainingAdaptationService()
                started_adaptation = monotonic()
                adaptation = service.generate(
                    session,
                    "pilot-client",
                    source_client_request_id=request_id,
                    client_request_id=uuid4(),
                    reason="Aumentar somente o descanso para 90 segundos",
                )
                adaptation_seconds = monotonic() - started_adaptation
                assert adaptation.status == "proposed"
                accepted = service.client_decide(session, "pilot-client", adaptation.id, True)
                assert accepted.status == "pending_instructor_review"
                draft = session.get(TrainingPlanVersion, accepted.resulting_version_id)
                assert draft.status == "proposal" and draft.approved_by is None
                return {
                    "explanation": adaptation.explanation,
                    "status": accepted.status,
                    "chat_request_seconds": round(chat_seconds, 3),
                    "adaptation_request_seconds": round(adaptation_seconds, 3),
                }

        if generated:
            step("adaptation_and_client_review", adapt)
        with sessions() as session:
            report["retained_synthetic_messages"] = len(
                session.scalars(select(TrainingAiMessage)).all()
            )
        report["completed_at"] = datetime.now(UTC).isoformat()
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
        if any(row["status"] != "success" for row in report["steps"]):
            raise SystemExit("One or more workflow checks failed; see the synthetic report.")
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


if __name__ == "__main__":
    run()
