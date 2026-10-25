"""Owner-authorized assisted RAG over the existing proposal/review workflow.

This is consultation-backed drafting, not compiled prescription qualification.
Independent evaluation is optional under the owner's recorded governance change.
"""

import json
import os
from functools import wraps
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from sqlalchemy import select

from app.modules.knowledge.models import KnowledgeSource
from app.modules.knowledge.service import KnowledgeResult, source_is_reviewed
from app.modules.training.owner_approval import (
    approved_research_context,
    artifact_owner_approval,
    load_owner_approval,
)
from app.modules.training.owner_rag_load import validate_candidate as validate_load
from app.modules.training.prescription_budget import attempt_budget
from app.modules.training.prescription_contract import PrescriptionRejection, record_hash
from app.modules.training.request_intent import goal_families as goal_families
from app.modules.training.request_intent import goal_family, requested_goal

AUTHORIZATION_PATH = Path(__file__).with_name("owner-rag-authorization.json")
NOTICE = (
    "Proposta assistida por RAG, autorizada pelo proprietário, sem parecer profissional "
    "ou avaliação independente. As fontes são de consulta; a ficha depende da revisão "
    "do instrutor antes da ativação."
)

Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class RagBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    authorization_id: str
    goal_family: str
    onboarding_sha256: Hash
    onboarding_keys: list[str]
    source_hashes: dict[str, Hash]
    rule_hashes: dict[str, Hash]
    provided_passage_ids: list[str]
    exercise_dictionary_sha256: Hash
    exercise_dictionary_version: str
    writer_configuration_sha256: Hash
    professional_review_performed: Literal[False]
    independent_evaluation_performed: Literal[False]
    compiled_prescription_qualification: Literal[False]
    content_sha256: Hash
    preserved_item_hashes: list[Hash] = Field(default_factory=list)
    session_labels: list[str] = Field(default_factory=list)
    focus_scope: Literal["unspecified", "targeted", "full_body"] = "unspecified"


def enabled():
    return os.getenv("TRAINING_EVIDENCE_MODE", "legacy") == "owner_rag"


def onboarding_hash(values):
    return record_hash(TypeAdapter(dict).dump_python(values, mode="json"))


def authorized_attempt(operation):
    @wraps(operation)
    def execute(*args, **kwargs):
        if not enabled():
            return operation(*args, **kwargs)
        timeout = float(
            os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")
            if os.getenv("AI_PROVIDER") == "ollama"
            else os.getenv("AI_TIMEOUT_SECONDS", "10")
        )
        with attempt_budget(timeout):
            return operation(*args, **kwargs)

    return execute


def authorization():
    from app.modules.training.owner_approval import APPROVAL_PATH
    from app.modules.training.owner_rag_schema import dictionary_hash

    try:
        data = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
        registry = load_owner_approval()
        if (
            data["status"] != "approved"
            or not isinstance(data["decision_id"], str)
            or not data["decision_id"].strip()
            or data["mode"] != "owner_rag"
            or data["authority"] != "project_owner"
            or registry is None
            or registry.status != "approved"
            or data["source_rule_decision_id"] != registry.decision_id
            or data["source_rule_registry_sha256"]
            != record_hash(json.loads(APPROVAL_PATH.read_text(encoding="utf-8")))
            or data["writer_configuration_sha256"] != record_hash(configuration())
            or data["writer_configuration_sha256"] != record_hash(data["writer_configuration"])
            or data["exercise_dictionary_sha256"] != dictionary_hash()
            or data["professional_review_performed"] is not False
            or data["independent_evaluation_required"] is not False
            or data["independent_evaluation_performed"] is not False
            or data["compiled_prescription_qualification"] is not False
            or data["automatic_plan_activation_authorized"] is not False
        ):
            raise ValueError("owner_rag_authorization_changed")
        return data
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        raise PrescriptionRejection(
            "insufficient_support", "current_owner_rag_authorization_required"
        ) from None


def configuration():
    from app.modules.training.prescription_runtime import writer_configuration

    current = writer_configuration()
    return {
        "provider": current["provider"],
        "model": current["model"],
        "contract": "owner-assisted-rag-12",
        "instruction_version": "owner-rag-13",
        "sampling_temperature": 0,
        "structured_reasoning": False,
        "context_character_budget": 35000,
    }


def validate_candidate(plan, context):
    validate_load(plan, context)
    from app.modules.training.completeness import validate_full_body_coverage

    validate_full_body_coverage(plan, context)
    if context.get("effective_training_goal") and goal_families(plan.objective) != [
        context["owner_rag_basis"]["goal_family"]
    ]:
        raise PrescriptionRejection(
            "insufficient_support",
            "invalid_typed_candidate",
            issues=[
                {
                    "field": "objective",
                    "reason": "requested_goal_required",
                    "allowed": [context["effective_training_goal"]],
                }
            ],
        )


def requires_regeneration(version):
    """An obsolete binding can be replaced only through explicit generation."""
    if version.origin != "ai":
        return False
    auth = authorization()
    binding = next((c["owner_rag"] for c in version.citations if c.get("owner_rag")), {})
    if not isinstance(binding, dict):
        return True
    return (
        binding.get("authorization_id") != auth["decision_id"]
        or binding.get("writer_configuration_sha256") != auth["writer_configuration_sha256"]
        or binding.get("exercise_dictionary_sha256") != auth["exercise_dictionary_sha256"]
    )


def prepare(context, evidence, onboarding, *, focus=None):
    if not enabled():
        return context
    from app.modules.training.evidence_review import current_artifacts

    auth = authorization()
    from app.modules.training.owner_rag_load import requires_measurement

    request = (
        context.get("training_request")
        or context.get("current_user_message")
        or context.get("source_client_message")
    )
    if requires_measurement(request):
        raise PrescriptionRejection("missing_input", "measured_baseline_required_for_external_load")
    if evidence.knowledge_status == "unavailable":
        raise PrescriptionRejection("technical_unavailability", "retrieval_unavailable")
    if evidence.knowledge_status != "supported" or not evidence.chunks:
        raise PrescriptionRejection(
            "insufficient_support", "eligible_consultation_sources_required"
        )
    artifacts, registry = current_artifacts(), load_owner_approval()
    for chunk in evidence.chunks:
        artifact = artifacts.get("source:" + chunk["source_id"])
        if artifact is None or artifact_owner_approval(artifact, registry) is None:
            raise PrescriptionRejection("insufficient_support", "owner_source_approval_changed")
        passage = next(
            (p for p in artifact["data"].get("chunks", []) if p["id"] == chunk["chunk_id"]), None
        )
        if (
            passage is None
            or passage["content"] != chunk["content"]
            or passage["section"] != chunk["section"]
        ):
            raise PrescriptionRejection("insufficient_support", "owner_source_passage_changed")
    family = goal_family(requested_goal(request or "", onboarding.get("training_goal", "")))
    research = approved_research_context(family)
    active_rules = {key for keys in research["profile"]["dimensions"].values() for key in keys}
    active_rules.update(research["profile"].get("accounting", []))
    research["rules"] = [
        {key: value for key, value in rule.items() if key != "sources"}
        for rule in research["rules"]
        if rule["id"] in active_rules
    ]
    research["instructions_pt_br"] = (
        "Use as regras aceitas pelo proprietário aplicáveis a este pedido e os trechos "
        "de consulta recebidos. Preserve o objetivo e as restrições informadas. "
        "Não combine protocolos alternativos nem invente medidas, diagnósticos ou "
        "certeza clínica. Cite os chunk_id efetivamente usados. A proposta assistida "
        "depende da revisão do instrutor. Não declare parecer profissional "
        "ou avaliação independente."
        " Em exercise_name selecione o identificador do dicionário. Em musculação, use "
        "repetições numéricas como 8 ou 8-12; em flexibilidade, use sustentações em segundos "
        "com lado explícito. Quando training_schedule não indicar dias, elabore "
        "somente uma sessão A; a frequência citada num estudo não confirma dias do aluno."
        " Em load_guidance use somente a opção qualitativa correspondente a load_capability: "
        "bodyweight usa Peso corporal; external_unmeasured usa "
        "Halteres; carga a definir na revisão do instrutor. Nunca informe kg, libras, "
        "pesos por extenso ou capacidade medida. Carga ainda não definida não altera o objetivo."
        " Preserve TODAS as fichas de training_schedule.session_labels, independentemente "
        "do foco ser corpo inteiro ou localizado. Cada ficha precisa de exercícios próprios "
        "e revisão; não distribua apenas um exercício por dia para preencher as letras. "
        "Não copie a seleção inteira entre fichas. Sem agenda pedida, mantenha uma sessão A."
    )
    from app.modules.training.owner_rag_schema import dictionary_hash, scoped_dictionary

    result = {
        **context,
        "owner_approved_research": research,
        "owner_training_mode": "flexibility" if family == "mobility_flexibility" else "resistance",
        "owner_exercise_dictionary": scoped_dictionary(
            focus, mode="flexibility" if family == "mobility_flexibility" else "resistance"
        ),
        "effective_training_goal": requested_goal(
            request or "", onboarding.get("training_goal", "")
        ),
    }
    if family == "mobility_flexibility":
        research["instructions_pt_br"] += (
            " Este pedido é de flexibilidade, não de musculação. Selecione alongamentos "
            "do dicionário e preencha holds, hold_seconds, side e rest_seconds; "
            "são sustentações por lado e recuperação entre sustentações, não séries de "
            "musculação. Use somente a amplitude confortável da instrução permitida, "
            "sem inventar amplitude medida, tolerância observada ou diagnóstico. "
            "Escolha uma decomposição coerente das regras aceitas recebidas; "
            "associações agregadas não são limites individuais obrigatórios."
        )
    from app.modules.training.completeness import requested_training_schedule, split_training_day
    from app.modules.training.focus import explicit_full_body_request

    if not result.get("training_focus") and explicit_full_body_request(request or ""):
        result["training_focus"] = {
            "scope": "full_body",
            "muscle_groups": [],
            "goal": result["effective_training_goal"],
        }

    if "training_schedule" not in result:
        schedule = requested_training_schedule(request or "")
        existing = context.get("editable_training_draft") or context.get("base_plan")
        if not schedule["session_labels"] and existing:
            schedule = {
                "session_labels": sorted(
                    {split_training_day(i["exercise_name"])[0] for i in existing["items"]} - {""}
                )
            }
        result["training_schedule"] = schedule
    if context.get("base_plan"):
        from app.modules.training.completeness import split_training_day

        labels = {
            split_training_day(item["exercise_name"])[0] for item in context["base_plan"]["items"]
        }
        if labels == {""} and not result["training_schedule"]["session_labels"]:
            result["owner_preserve_unlabeled"] = True
        elif "" not in labels and not result["training_schedule"]["session_labels"]:
            result["owner_exercise_labels"] = sorted(labels)
    from app.modules.training.schema import TrainingPlanItemInput

    preserved = [
        record_hash(
            TrainingPlanItemInput.model_validate(
                {key: value for key, value in item.items() if key != "position"}
            )
        )
        for item in context.get("base_plan", {}).get("items", [])
    ]
    chunks = list(evidence.chunks)
    result["knowledge"] = {**evidence.as_context(), "chunks": evidence.as_context()["chunks"]}
    while len(json.dumps(result, default=str, ensure_ascii=False)) > 35000 and len(chunks) > 1:
        chunks.pop()
        result["knowledge"]["chunks"] = result["knowledge"]["chunks"][:-1]
    if len(json.dumps(result, default=str, ensure_ascii=False)) > 35000:
        raise PrescriptionRejection("insufficient_support", "owner_rag_context_budget_exceeded")
    result.update(
        {
            "owner_rag_basis": {
                "authorization_id": auth["decision_id"],
                "goal_family": family,
                "onboarding_sha256": onboarding_hash(onboarding),
                "onboarding_keys": sorted(onboarding),
                "source_hashes": {
                    c["source_id"]: artifacts["source:" + c["source_id"]]["sha256"] for c in chunks
                },
                "provided_passage_ids": [c["chunk_id"] for c in chunks],
                "exercise_dictionary_sha256": dictionary_hash(),
                "exercise_dictionary_version": result["owner_exercise_dictionary"]["version"],
                "writer_configuration_sha256": auth["writer_configuration_sha256"],
                "rule_hashes": {
                    r["id"]: artifacts["rule:" + r["id"]]["sha256"] for r in research["rules"]
                },
                "professional_review_performed": False,
                "independent_evaluation_performed": False,
                "compiled_prescription_qualification": False,
                "preserved_item_hashes": preserved,
                "session_labels": result.get("training_schedule", {}).get("session_labels", []),
                "focus_scope": (focus or result.get("training_focus") or {}).get(
                    "scope", "unspecified"
                ),
            },
        }
    )
    return result


def bind(knowledge, context, plan):
    basis = context.get("owner_rag_basis")
    if basis is None:
        return knowledge
    validate_candidate(plan, context)
    from app.modules.training.completeness import validate_requested_sessions

    validate_requested_sessions(plan, context)
    if not knowledge.citations:
        raise PrescriptionRejection("insufficient_support", "consultation_citations_required")
    if any(c["chunk_id"] not in basis["provided_passage_ids"] for c in knowledge.citations):
        raise PrescriptionRejection("insufficient_support", "unprovided_owner_rag_citation")
    binding = RagBinding.model_validate({**basis, "content_sha256": record_hash(plan)}).model_dump(
        mode="json"
    )
    return KnowledgeResult(
        [{**citation, "owner_rag": binding} for citation in knowledge.citations],
        knowledge.knowledge_status,
        NOTICE + " " + knowledge.knowledge_limitations,
    )


def validate_saved(session, version, content, *, onboarding=None):
    """No writer call and no historical rewrite when checking current proposal reuse."""
    from datetime import UTC, datetime

    from app.modules.training.evidence_review import current_artifacts

    citations = version.citations
    try:
        bindings = [
            RagBinding.model_validate(citation.get("owner_rag")).model_dump(mode="json")
            for citation in citations
        ]
    except (ValidationError, TypeError, AttributeError):
        raise PrescriptionRejection("insufficient_support", "owner_rag_binding_invalid") from None
    if not bindings or not all(bindings):
        raise PrescriptionRejection("insufficient_support", "owner_rag_generation_required")
    auth, artifacts, registry = authorization(), current_artifacts(), load_owner_approval()
    first = bindings[0]
    if (
        any(binding != first for binding in bindings)
        or first["authorization_id"] != auth["decision_id"]
        or first["content_sha256"] != record_hash(content)
        or first["exercise_dictionary_sha256"] != auth["exercise_dictionary_sha256"]
        or first["writer_configuration_sha256"] != auth["writer_configuration_sha256"]
    ):
        raise PrescriptionRejection(
            "insufficient_support", "owner_rag_content_or_authorization_changed"
        )
    if onboarding is not None and first["onboarding_sha256"] != onboarding_hash(
        {key: onboarding.get(key) for key in first["onboarding_keys"]}
    ):
        raise PrescriptionRejection("missing_input", "owner_rag_inputs_changed")
    from app.modules.training.owner_rag_schema import dictionary

    validate_candidate(
        content,
        {
            "owner_rag_basis": first,
            "owner_exercise_dictionary": dictionary(),
            "training_focus": {"scope": first["focus_scope"]},
        },
    )
    from app.modules.training.completeness import validate_requested_sessions

    validate_requested_sessions(
        content, {"training_schedule": {"session_labels": first["session_labels"]}}
    )
    for prefix, name in (("source:", "source_hashes"), ("rule:", "rule_hashes")):
        for key, expected in first[name].items():
            artifact = artifacts.get(prefix + key)
            if (
                artifact is None
                or artifact["sha256"] != expected
                or artifact_owner_approval(artifact, registry) is None
            ):
                raise PrescriptionRejection("insufficient_support", "owner_rag_support_changed")
    for citation in citations:
        if (
            citation["chunk_id"] not in first["provided_passage_ids"]
            or citation["source_id"] not in first["source_hashes"]
        ):
            raise PrescriptionRejection("insufficient_support", "owner_rag_binding_invalid")
        source = session.scalar(
            select(KnowledgeSource).where(KnowledgeSource.id == citation["source_id"])
        )
        if (
            source is None
            or source.client_id is not None
            or not source_is_reviewed(source, datetime.now(UTC).date())
            or source.review_due_at <= datetime.now(UTC).date()
        ):
            raise PrescriptionRejection(
                "insufficient_support", "owner_rag_source_no_longer_eligible"
            )
    return first


def current_onboarding(session, client_id):
    from app.modules.onboarding.draft_service import OnboardingDraftService
    from app.modules.onboarding.models import Onboarding

    service = OnboardingDraftService()
    if not service.has_valid_completed_onboarding(session, client_id):
        raise PrescriptionRejection("missing_input", "completed_onboarding_required")
    row = session.scalar(
        select(Onboarding)
        .where(Onboarding.client_id == client_id)
        .execution_options(populate_existing=True)
    )
    return service.completion_data(row).model_dump()
