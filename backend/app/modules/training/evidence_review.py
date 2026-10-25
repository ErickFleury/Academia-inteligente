"""Authenticated human review records; registration never promotes runtime policy."""

import json
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.clients.models import Account, Employee
from app.modules.knowledge.bootstrap import CATALOG_PATH
from app.modules.training.evidence_review_models import EvidenceJudgment, EvidenceSeal
from app.modules.training.evidence_review_schema import JudgmentInput, SealInput
from app.modules.training.owner_approval import artifact_owner_approval
from app.modules.training.prescription_accounting import AccountingMethod
from app.modules.training.prescription_contract import (
    DevelopmentExecutionContract,
    PrescriptionRejection,
    record_hash,
)
from app.modules.training.prescription_policy import PolicyCatalog

ROOT = Path(__file__).parent
MAX_RECORD_BYTES = 262_144  # Transport/storage bound, not a scientific threshold.


class EvidenceReviewError(Exception):
    def __init__(self, status, code):
        self.status, self.code = status, code
        super().__init__(code)


def _bounded(value):
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError):
        raise EvidenceReviewError(422, "invalid_review_record") from None
    if len(encoded) > MAX_RECORD_BYTES:
        raise EvidenceReviewError(422, "review_record_too_large")


def prescription_bundle_hash(bundle):
    """Bind clinical content, excluding only explicit approval bookkeeping."""
    content = deepcopy(bundle)
    items = [
        content["policies"]["dictionary"],
        content["accounting"],
        *content["policies"]["policies"],
    ]
    for item in items:
        for key in ("status", "review_records", "review_due_at", "owner_authorization_id"):
            item.pop(key, None)
    content["execution"].pop("status", None)
    return record_hash(content)


def current_artifacts():
    """Only packaged public evidence and global draft contracts; no client data."""
    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        proposals = json.loads((ROOT / "review-rule-candidates.json").read_text(encoding="utf-8"))
        bundle = {
            "policies": json.loads(
                (ROOT / "prescription-policies.json").read_text(encoding="utf-8")
            ),
            "execution": json.loads(
                (ROOT / "prescription-execution.json").read_text(encoding="utf-8")
            ),
            "accounting": json.loads(
                (ROOT / "prescription-accounting.json").read_text(encoding="utf-8")
            ),
        }
    except (OSError, ValueError):
        raise EvidenceReviewError(503, "review_artifacts_unavailable") from None
    artifacts = {}
    for source in catalog["sources"]:
        ready = source.get("review_status") == "approved" and bool(source.get("chunks"))
        artifacts["source:" + source["id"]] = {
            "kind": "source",
            "title": source["title"],
            "data": source,
            "missing_items": [],
            "sections": [
                {"label": "Referência", "text": source["url"]},
                {
                    "label": "Licença de reutilização",
                    "text": source.get("license", "Não verificada"),
                },
                {
                    "label": "Limite da revisão técnica",
                    "text": "A licença e a extração não comprovam aprovação científica.",
                },
                {
                    "label": "Material de consulta",
                    "text": (
                        "Há trechos no catálogo. A elegibilidade de cada prescrição é separada."
                        if ready
                        else "Há somente referência bibliográfica. "
                        "Um parecer científico não autoriza "
                        "ingestão ou uso no RAG; consulte a fonte original para avaliá-la."
                    ),
                },
                *[{"label": c["section"], "text": c["content"]} for c in source.get("chunks", [])],
            ],
        }
    for proposal in proposals["rules"]:
        profiles = [
            profile
            for profile in proposals["profiles"]
            if proposal["id"]
            in {identifier for ids in profile["dimensions"].values() for identifier in ids}
            | set(profile.get("accounting", []))
            | set(profile.get("protocol_alternatives", []))
        ]
        references = [s for s in proposals["sources"] if s["id"] in proposal.get("sources", [])]
        artifacts["rule:" + proposal["id"]] = {
            "kind": "rule_proposal",
            "title": "Regra proposta: " + proposal["id"],
            "data": {
                "registry_version": proposals["version"],
                "runtime_eligible": False,
                "proposal": proposal,
                "sources": references,
                "profiles": profiles,
            },
            "missing_items": [],
            "sections": [
                {
                    "label": "Natureza da proposta",
                    "text": (
                        "Anotação de pesquisa para análise profissional. "
                        "Não é política executável nem autorização de uso no RAG."
                    ),
                },
                {
                    "label": "Referências para análise",
                    "text": "\n".join(s["url"] for s in references),
                },
                {
                    "label": "Abrangência",
                    "text": (
                        f"Proposta relacionada a {len(profiles)} famílias de objetivos. "
                        "Confira a população e as lacunas no artefato completo."
                    ),
                },
            ],
        }
    policies = bundle["policies"].get("policies", [])
    dictionary = bundle["policies"].get("dictionary", {})
    missing = []
    if not policies or any(
        not p.get("exact_goal_mappings") or p.get("unresolved_decisions") for p in policies
    ):
        missing.append("Objetivos, aplicabilidade e decisões pendentes precisam ser resolvidos.")
    dimensions = {
        "selection",
        "volume",
        "intensity",
        "frequency",
        "progression",
        "rest",
        "restrictions",
    }
    if any({d.get("dimension") for d in p.get("decisions", [])} != dimensions for p in policies):
        missing.append("As sete dimensões de prescrição precisam de decisões documentadas.")
    if not dictionary.get("exercises"):
        missing.append("O dicionário de exercícios precisa ser preenchido para revisão.")
    if not bundle["execution"].get("contracts"):
        missing.append(
            "Os contratos de execução e de autoridade das informações estão incompletos."
        )
    if not bundle["accounting"].get("mappings"):
        missing.append("O método de contabilização de volume está incompleto.")
    try:
        proposed = PolicyCatalog.model_validate(bundle["policies"])
        accounting = AccountingMethod.model_validate(bundle["accounting"])
        contracts = [
            DevelopmentExecutionContract.model_validate(c) for c in bundle["execution"]["contracts"]
        ]
        if accounting.dictionary_version != proposed.dictionary.version or {
            c.policy_id for c in contracts
        } != {p.id for p in proposed.policies}:
            missing.append("As versões e os vínculos entre os contratos precisam ser corrigidos.")
        if any(
            ref.certainty == "not_assessed"
            for p in proposed.policies
            if p.approval_basis != "owner_decision"
            for d in p.decisions
            for ref in d.evidence
        ):
            missing.append("A certeza das evidências dos contratos ainda precisa ser avaliada.")
    except (ValidationError, KeyError, TypeError):
        missing.append("Os campos obrigatórios dos contratos precisam ser preenchidos e validados.")
    artifacts["prescription-bundle"] = {
        "kind": "prescription_bundle",
        "title": "Políticas e contratos de prescrição",
        "data": bundle,
        "missing_items": missing,
        "sections": [
            {"label": "Políticas propostas", "text": str(len(policies))},
            {"label": "Exercícios documentados", "text": str(len(dictionary.get("exercises", [])))},
            {
                "label": "Contratos executáveis",
                "text": str(len(bundle["execution"].get("contracts", []))),
            },
            {
                "label": "Liberação",
                "text": "Pareceres não publicam políticas nem liberam a geração para alunos.",
            },
        ],
    }
    for identifier, artifact in artifacts.items():
        artifact.update(
            id=identifier,
            sha256=(
                prescription_bundle_hash(artifact["data"])
                if artifact["kind"] == "prescription_bundle"
                else record_hash(artifact["data"])
            ),
        )
    return artifacts


def require_instructor(session, identity):
    employee = session.scalar(
        select(Employee)
        .join(Account)
        .where(
            Account.keycloak_subject == identity.subject,
            Account.account_active,
            Employee.active,
            Employee.specialization == "instructor",
        )
    )
    if (
        "instructor" not in identity.roles
        or employee is None
        or employee.account.person_profile is None
    ):
        raise EvidenceReviewError(403, "active_instructor_required")
    profile = employee.account.person_profile
    return f"{profile.first_name} {profile.surname}".strip()


def _protocol_artifact(row):
    data = {
        key: row[key] for key in ("protocol", "artifact_hashes", "case_count", "payload_sha256")
    }
    return {
        "id": "seal-protocol:" + str(row["id"]),
        "kind": "evaluation_protocol",
        "title": "Protocolo de avaliação: " + row["protocol"]["title"],
        "data": data,
        "sha256": record_hash(data),
        "missing_items": [],
        "sections": [
            {"label": "Responsável pela custódia", "text": row["custodian_name"]},
            {
                "label": "Protocolo público",
                "text": "Esta consulta contém métodos e orçamento, sem os casos nem as respostas.",
            },
        ],
    }


def review_artifacts(session):
    items = current_artifacts()
    rows = session.execute(
        select(*_seal_columns())
        .order_by(EvidenceSeal.created_at.desc(), EvidenceSeal.id.desc())
        .limit(100)
    ).mappings()
    for row in rows:
        artifact = _protocol_artifact(row)
        items[artifact["id"]] = artifact
    return items


def _artifact(identifier, expected=None, session=None):
    if identifier.startswith("seal-protocol:") and session is not None:
        try:
            seal_id = UUID(identifier.removeprefix("seal-protocol:"))
        except ValueError:
            raise EvidenceReviewError(404, "review_artifact_not_found") from None
        row = (
            session.execute(select(*_seal_columns()).where(EvidenceSeal.id == seal_id))
            .mappings()
            .one_or_none()
        )
        artifact = _protocol_artifact(row) if row else None
    else:
        artifact = current_artifacts().get(identifier)
    if artifact is None:
        raise EvidenceReviewError(404, "review_artifact_not_found")
    if expected is not None and artifact["sha256"] != expected:
        raise EvidenceReviewError(409, "review_artifact_changed")
    return artifact


def judgment_out(row, subject=None):
    return {
        "id": row.id,
        "artifact_id": row.artifact_id,
        "artifact_sha256": row.artifact_sha256,
        "reviewer_name": row.reviewer_name,
        "function": row.function,
        "decision": row.decision,
        "created_at": row.created_at,
        "assessment": row.payload,
        "is_current": row.is_current,
        "can_supersede": row.is_current and row.reviewer_subject == subject,
        "human_review_record": {
            "identity": row.reviewer_subject,
            "role": row.function,
            "competence": row.payload["competence"],
            "conflicts": row.payload["conflicts"],
            "independent": row.payload.get("independent_assessment", False),
            "reviewed_at": row.created_at.date().isoformat(),
            "artifact_sha256": row.artifact_sha256,
            "record_locator": f"/training/evidence-review/judgments/{row.id}",
        },
    }


def get_judgment(session, identity, judgment_id):
    require_instructor(session, identity)
    row = session.get(EvidenceJudgment, judgment_id)
    if row is None:
        raise EvidenceReviewError(404, "review_record_not_found")
    return judgment_out(row, identity.subject)


def artifact_out(session, artifact, *, details, subject=None):
    judgments = session.scalars(
        select(EvidenceJudgment)
        .where(EvidenceJudgment.artifact_id == artifact["id"])
        .order_by(EvidenceJudgment.created_at.desc(), EvidenceJudgment.id.desc())
        .limit(100)
    ).all()
    current = session.scalars(
        select(EvidenceJudgment).where(
            EvidenceJudgment.artifact_id == artifact["id"],
            EvidenceJudgment.artifact_sha256 == artifact["sha256"],
            EvidenceJudgment.is_current,
        )
    ).all()
    effective = [r for r in current if r.decision != "approved" or _review_current(r)]
    base = [r for r in effective if r.function != "adjudicator"]
    adjudications = [r for r in effective if r.function == "adjudicator"]
    resolved = (
        len(adjudications) == 1
        and adjudications[0].decision == "approved"
        and _review_current(adjudications[0])
        and {str(r.id) for r in base}.issubset(
            set(adjudications[0].payload.get("resolves_judgment_ids", []))
        )
    )
    complete = (
        {r.function for r in base} == {"methodological", "professional"}
        and len({r.reviewer_subject for r in base}) >= 2
        and (resolved or not adjudications and all(r.decision == "approved" for r in base))
        and not artifact["missing_items"]
        and all(_review_current(r) for r in base if r.decision == "approved")
        and all(r.payload.get("independent_assessment") is True for r in effective)
    )
    return {
        "id": artifact["id"],
        "kind": artifact["kind"],
        "title": artifact["title"],
        "sha256": artifact["sha256"],
        "approval_ready": not artifact["missing_items"],
        "missing_items": artifact["missing_items"],
        "sections": artifact["sections"] if details else [],
        "content": artifact["data"] if details else None,
        "judgments": [judgment_out(r, subject) for r in judgments] if details else [],
        "independence_complete": complete,
        "owner_approval": artifact_owner_approval(artifact),
    }


def _review_current(row):
    due = row.payload.get("review_due_at")
    try:
        return isinstance(due, str) and date.fromisoformat(due) > datetime.now(UTC).date()
    except ValueError:
        return False


def require_current_runtime_reviews(session, groups):
    """A file cannot resurrect superseded, expired or fabricated app approvals."""
    artifact = _artifact("prescription-bundle")
    if not artifact_out(session, artifact, details=False)["independence_complete"]:
        raise PrescriptionRejection("insufficient_support", "professional_contract_review_required")
    current = session.scalars(
        select(EvidenceJudgment).where(
            EvidenceJudgment.artifact_id == artifact["id"],
            EvidenceJudgment.artifact_sha256 == artifact["sha256"],
            EvidenceJudgment.is_current,
        )
    ).all()
    effective = [r for r in current if r.decision != "approved" or _review_current(r)]
    records = {row.id: row for row in effective}
    adjudications = {row.id for row in effective if row.function == "adjudicator"}
    prefix = "/training/evidence-review/judgments/"
    for reviews, deadline in groups:
        referenced = set()
        approved_deadlines = []
        for review in reviews:
            try:
                locator = review.record_locator
                if not locator.startswith(prefix):
                    raise ValueError("unverified_review_reference")
                row = records[UUID(locator[len(prefix) :])]
                if review.model_dump(mode="json") != judgment_out(row)["human_review_record"]:
                    raise ValueError("review_reference_mismatch")
                referenced.add(row.id)
                if row.decision == "approved":
                    approved_deadlines.append(date.fromisoformat(row.payload["review_due_at"]))
            except (KeyError, TypeError, ValueError):
                raise PrescriptionRejection(
                    "insufficient_support", "professional_review_not_current"
                ) from None
        if (
            not reviews
            or not adjudications.issubset(referenced)
            or not approved_deadlines
            or deadline is not None
            and deadline > min(approved_deadlines)
        ):
            raise PrescriptionRejection(
                "insufficient_support", "professional_review_scope_or_deadline"
            )


def register_judgment(session, identity, identifier, data: JudgmentInput):
    name = require_instructor(session, identity)
    payload = data.model_dump(mode="json")
    _bounded(payload)
    request_hash = record_hash({"artifact_id": identifier, "assessment": payload})
    existing = session.scalar(
        select(EvidenceJudgment).where(
            EvidenceJudgment.reviewer_subject == identity.subject,
            EvidenceJudgment.request_id == data.request_id,
        )
    )
    artifact = _artifact(identifier, data.expected_artifact_sha256, session)
    if existing:
        if existing.request_sha256 != request_hash:
            raise EvidenceReviewError(409, "review_request_conflict")
        return judgment_out(existing, identity.subject)
    if data.decision == "approved" and artifact["missing_items"]:
        raise EvidenceReviewError(422, "review_artifact_incomplete")
    previous = session.scalar(
        select(EvidenceJudgment)
        .where(
            EvidenceJudgment.artifact_id == identifier,
            EvidenceJudgment.artifact_sha256 == artifact["sha256"],
            EvidenceJudgment.reviewer_subject == identity.subject,
            EvidenceJudgment.is_current,
        )
        .with_for_update()
    )
    if previous is not None and (
        data.supersedes_judgment_id != previous.id or data.function != previous.function
    ):
        raise EvidenceReviewError(409, "one_independent_review_per_person")
    if previous is None and data.supersedes_judgment_id is not None:
        raise EvidenceReviewError(409, "review_registration_conflict")
    if data.function == "adjudicator":
        references = session.scalars(
            select(EvidenceJudgment).where(
                EvidenceJudgment.id.in_(data.resolves_judgment_ids),
                EvidenceJudgment.artifact_id == identifier,
                EvidenceJudgment.artifact_sha256 == artifact["sha256"],
                EvidenceJudgment.is_current,
                EvidenceJudgment.function.in_(["methodological", "professional"]),
            )
        ).all()
        if (
            len(references) != len(set(data.resolves_judgment_ids))
            or {r.function for r in references} != {"methodological", "professional"}
            or len({r.reviewer_subject for r in references}) < 2
            or any(r.payload.get("independent_assessment") is not True for r in references)
        ):
            raise EvidenceReviewError(422, "adjudication_references_invalid")
    row = EvidenceJudgment(
        request_id=data.request_id,
        artifact_id=identifier,
        artifact_sha256=artifact["sha256"],
        reviewer_subject=identity.subject,
        reviewer_name=name,
        function=data.function,
        decision=data.decision,
        request_sha256=request_hash,
        supersedes_id=previous.id if previous else None,
        payload=payload,
    )
    if previous:
        previous.is_current = False
        session.flush([previous])
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.scalar(
            select(EvidenceJudgment).where(
                EvidenceJudgment.reviewer_subject == identity.subject,
                EvidenceJudgment.request_id == data.request_id,
            )
        )
        if existing and existing.request_sha256 == request_hash:
            return judgment_out(existing, identity.subject)
        raise EvidenceReviewError(409, "review_registration_conflict") from None
    return judgment_out(row, identity.subject)


def _seal_columns():
    # Do not load held-out case/reference content for metadata listings.
    return [
        EvidenceSeal.id,
        EvidenceSeal.custodian_subject,
        EvidenceSeal.custodian_name,
        EvidenceSeal.protocol,
        EvidenceSeal.artifact_hashes,
        EvidenceSeal.attestations,
        EvidenceSeal.case_count,
        EvidenceSeal.payload_sha256,
        EvidenceSeal.created_at,
    ]


def seal_out(row, subject):
    return {
        key: row[key]
        for key in (
            "id",
            "custodian_name",
            "protocol",
            "artifact_hashes",
            "attestations",
            "case_count",
            "payload_sha256",
            "created_at",
        )
    } | {"can_read_cases": row["custodian_subject"] == subject}


def list_seals(session, identity):
    require_instructor(session, identity)
    rows = session.execute(
        select(*_seal_columns())
        .order_by(EvidenceSeal.created_at.desc(), EvidenceSeal.id.desc())
        .limit(100)
    ).mappings()
    return [seal_out(row, identity.subject) for row in rows]


def register_seal(session, identity, data: SealInput):
    name = require_instructor(session, identity)
    payload = data.model_dump(mode="json")
    _bounded(payload)
    request_hash = record_hash(payload)
    existing = (
        session.execute(
            select(*_seal_columns(), EvidenceSeal.request_sha256).where(
                EvidenceSeal.custodian_subject == identity.subject,
                EvidenceSeal.request_id == data.request_id,
            )
        )
        .mappings()
        .one_or_none()
    )
    if existing:
        if existing["request_sha256"] != request_hash:
            raise EvidenceReviewError(409, "seal_request_conflict")
        return seal_out(existing, identity.subject)
    for identifier, expected_hash in data.artifact_hashes.items():
        _artifact(identifier, expected_hash, session)
    cases = [case.model_dump(mode="json") for case in data.cases]
    row = EvidenceSeal(
        request_id=data.request_id,
        custodian_subject=identity.subject,
        custodian_name=name,
        request_sha256=request_hash,
        protocol=data.protocol.model_dump(mode="json"),
        artifact_hashes=data.artifact_hashes,
        attestations={
            "synthetic_only": data.synthetic_only,
            "independent_and_unexposed": data.independent_and_unexposed,
            "understands_no_release": data.understands_no_release,
        },
        case_count=len(cases),
        payload_sha256=record_hash(cases),
        private_cases=cases,
    )
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = (
            session.execute(
                select(*_seal_columns(), EvidenceSeal.request_sha256).where(
                    EvidenceSeal.custodian_subject == identity.subject,
                    EvidenceSeal.request_id == data.request_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        if existing and existing["request_sha256"] == request_hash:
            return seal_out(existing, identity.subject)
        raise EvidenceReviewError(409, "seal_registration_conflict") from None
    public = (
        session.execute(select(*_seal_columns()).where(EvidenceSeal.id == row.id)).mappings().one()
    )
    return seal_out(public, identity.subject)


def private_cases(session, identity, seal_id):
    require_instructor(session, identity)
    row = (
        session.execute(
            select(
                EvidenceSeal.id,
                EvidenceSeal.payload_sha256,
                EvidenceSeal.private_cases,
            ).where(EvidenceSeal.id == seal_id, EvidenceSeal.custodian_subject == identity.subject)
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise EvidenceReviewError(404, "seal_not_found")
    if record_hash(row["private_cases"]) != row["payload_sha256"]:
        raise EvidenceReviewError(503, "sealed_payload_integrity_error")
    return {"id": row["id"], "payload_sha256": row["payload_sha256"], "cases": row["private_cases"]}
