"""Shared lifecycle mechanics and persistence with an isolated default adapter.

The default adapter refuses ordinary databases/accounts. Operational use replaces
its boundary and context adapters; professional and release approvals stay external.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base
from app.integrations.ai import AiProviderError
from app.integrations.embeddings import EmbeddingProviderError
from app.modules.clients.models import Account, Client, Employee
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.knowledge.service import KnowledgeResult
from app.modules.onboarding.draft_service import OnboardingDraftService
from app.modules.onboarding.models import Onboarding
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.prescription_contract import (
    InputSnapshot,
    PrescriptionRejection,
    TypedPrescription,
    fact_is_current,
    record_hash,
)
from app.modules.training.prescription_validation import validate_development_prescription
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.service import TrainingLifecycleService

EntryPoint = Literal[
    "initial", "targeted", "rebuild", "chat_edit", "adaptation", "correction", "prose"
]
ENTRY_POINTS = {"initial", "targeted", "rebuild", "chat_edit", "adaptation", "correction", "prose"}


def build_prescription_writer_context(context, preflight, evaluated_revision):
    snapshot = context["snapshot"]
    confirmation = snapshot.facts.get("schedule_confirmed")
    schedule = (
        snapshot.schedule.model_dump(mode="json")
        if snapshot.schedule is not None
        and fact_is_current(confirmation, datetime.now(UTC))
        and confirmation.value is True
        else None
    )
    permitted_rules = [
        r for r in context["execution"].rules if r.decision_id in preflight["permitted_rule_ids"]
    ]
    choices = {key for rule in permitted_rules for key in rule.allowed_exercises}
    instruction_keys = {key for rule in permitted_rules for key in rule.permitted_instruction_keys}
    policy = next(p for p in context["catalog"].policies if p.id == context["execution"].policy_id)
    dictionary = context["catalog"].dictionary.model_dump(mode="json")
    dictionary["exercises"] = [e for e in dictionary["exercises"] if e["key"] in choices]
    return {
        "current_revision": evaluated_revision,
        "expected_revision": evaluated_revision,
        "schema_version": context["execution"].schema_version,
        "accounting_method_version": context["accounting"].version,
        "input_snapshot_sha256": preflight["input_snapshot_sha256"],
        "policy_version": preflight["policy_version"],
        "dictionary_version": context["catalog"].dictionary.version,
        "facts": {
            key: {
                name: value
                for name, value in fact.items()
                if name not in {"source_actor_subject", "confirmed_by_subject"}
            }
            for key, fact in snapshot.model_dump(mode="json")["facts"].items()
        },
        "confirmed_schedule": schedule,
        "evidence": preflight["evidence"].as_context(),
        "dictionary": dictionary,
        "branch_id": policy.branch_id,
        "goal_mappings": policy.exact_goal_mappings,
        "rule_dimensions": {
            d.id: d.dimension for d in policy.decisions if d.id in preflight["permitted_rule_ids"]
        },
        "rules": {
            **context["execution"].model_dump(mode="json"),
            "rules": [rule.model_dump(mode="json") for rule in permitted_rules],
            "instructions": {
                key: value.model_dump(mode="json")
                for key, value in context["execution"].instructions.items()
                if key in instruction_keys
            },
        },
    }


class DevelopmentValidationRecord(Base):
    __tablename__ = "training_prescription_development_validation"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    version_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("training_plan_version.id"))
    client_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("client.id"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32))
    entry_point: Mapped[str] = mapped_column(String(32))
    request_id: Mapped[UUID | None] = mapped_column(Uuid, index=True)
    actor: Mapped[str] = mapped_column(String(255))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class DevelopmentInputConfirmation(Base):
    __tablename__ = "training_prescription_development_confirmation"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    client_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("client.id"), index=True)
    origin_sha256: Mapped[str] = mapped_column(String(64), index=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class PrescriptionAdaptationValidation(Base):
    __tablename__ = "training_prescription_adaptation_validation"

    proposal_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("training_adaptation_proposal.id"), primary_key=True
    )
    client_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("client.id"), index=True)
    base_revision: Mapped[int] = mapped_column(Integer)
    base_content_sha256: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


def _input_origin(snapshot):
    value = snapshot.model_dump(mode="json")
    for fact in value["facts"].values():
        fact.pop("confirmed_at", None)
    return record_hash(value)


OUTCOME_COPY = {
    "restriction_conflict": (
        "A proposta conflita com uma restrição revisada. Peça uma avaliação ao instrutor."
    ),
    "missing_input": (
        "Faltam informações confirmadas para este pedido. Revise os dados com o instrutor."
    ),
    "insufficient_support": (
        "Não foi possível gerar uma proposta com evidências suficientes para este pedido. "
        "Peça ao instrutor uma avaliação e a elaboração do treino."
    ),
    "technical_unavailability": (
        "Não foi possível consultar os serviços de treino agora. "
        "Tente novamente ou peça ao instrutor a elaboração do treino."
    ),
}


class IsolatedPrescriptionService:
    purpose = "isolated_development"

    def __init__(self, *, client_ids: set[UUID], context_supplier):
        self.client_ids = frozenset(client_ids)
        self.context_supplier = context_supplier
        self.lifecycle = TrainingLifecycleService()

    def onboarding_snapshot(self, session, identity, *, client_id, required_fields: set[str]):
        self._owner(session, identity, client_id)
        service = OnboardingDraftService()
        if not service.has_valid_completed_onboarding(session, client_id):
            raise PrescriptionRejection("missing_input", "completed_onboarding_required")
        onboarding = session.scalar(select(Onboarding).where(Onboarding.client_id == client_id))
        values = service.completion_data(onboarding).model_dump()
        if not required_fields <= values.keys():
            raise PrescriptionRejection("missing_input", "fact_unavailable_in_onboarding")

        def utc(value):
            return value.replace(tzinfo=UTC) if value.tzinfo is None else value

        observed = utc(onboarding.updated_at)
        confirmed = utc(onboarding.completed_at)
        return InputSnapshot(
            client_id=client_id,
            facts={
                key: {
                    "value": values[key],
                    "source": "onboarding",
                    "source_id": str(onboarding.id),
                    "source_revision": observed.isoformat(),
                    "source_actor_role": "client_owner",
                    "confirmed_by": "client_owner",
                    "source_actor_subject": identity.subject,
                    "confirmed_by_subject": identity.subject,
                    "observed_at": observed,
                    "confirmed_at": confirmed,
                }
                for key in sorted(required_fields)
                if values[key] is not None
            },
        )

    def _context(self, session, client_id):
        context = self.context_supplier()
        snapshot = context["snapshot"]
        if snapshot.client_id != client_id:
            raise PrescriptionRejection("missing_input", "input_owner_mismatch")
        record = session.scalar(
            select(DevelopmentInputConfirmation)
            .where(
                DevelopmentInputConfirmation.client_id == client_id,
                DevelopmentInputConfirmation.origin_sha256 == _input_origin(snapshot),
            )
            .order_by(DevelopmentInputConfirmation.created_at.desc())
        )
        if record is not None:
            context["snapshot"] = InputSnapshot.model_validate(record.snapshot)
        return context

    def confirm_inputs(self, session, identity, *, client_id, expected_snapshot_hash):
        self._owner(session, identity, client_id)
        context = self.context_supplier()
        snapshot = context["snapshot"].model_copy(deep=True)
        if snapshot.client_id != client_id or record_hash(snapshot) != expected_snapshot_hash:
            raise PrescriptionRejection("missing_input", "confirmation_snapshot_changed")
        requirements = {r.key: r for r in context["execution"].input_requirements}
        now = datetime.now(UTC)
        for key, fact in snapshot.facts.items():
            requirement = requirements.get(key)
            if (
                requirement is None
                or not requirement.collection_approved
                or "client_owner" not in requirement.allowed_actor_roles
                or fact.source != requirement.source
                or fact.conflict
                or fact.observed_at > now
                or fact.valid_until is not None
                and fact.valid_until <= now
            ):
                raise PrescriptionRejection("missing_input", "confirmation_requires_resolution")
            fact.confirmed_at = now
            fact.confirmed_by = "client_owner"
            fact.confirmed_by_subject = identity.subject
        try:
            session.add(
                DevelopmentInputConfirmation(
                    client_id=client_id,
                    origin_sha256=_input_origin(context["snapshot"]),
                    snapshot=snapshot.model_dump(mode="json"),
                )
            )
            session.commit()
            return {
                "status": "confirmed",
                "input_snapshot_sha256": record_hash(snapshot),
                "purpose": self.purpose,
            }
        except Exception:
            session.rollback()
            raise

    def _boundary(self, session: Session, client_id: UUID):
        engine = session.get_bind()
        if engine.dialect.name == "sqlite":
            isolated = engine.url.database in (None, "", ":memory:")
        elif engine.dialect.name == "postgresql":
            from sqlalchemy import text

            schema = session.scalar(text("SELECT current_schema()"))
            isolated = isinstance(schema, str) and schema.startswith("test_prescription_")
        else:
            isolated = False
        client = (
            session.get(Client, client_id) if isolated and client_id in self.client_ids else None
        )
        if (
            client is None
            or not client.account.keycloak_subject
            or not client.account.keycloak_subject.startswith("prescription-dev-")
        ):
            raise PermissionError("prescription_development_scope_required")
        return client

    def _owner(self, session, identity, client_id):
        client = self._boundary(session, client_id)
        if (
            "client" not in identity.roles
            or client.account.keycloak_subject != identity.subject
            or not client.active
            or not client.account.account_active
        ):
            raise PermissionError("prescription_development_owner_required")
        return client

    @staticmethod
    def _instructor(session, identity):
        if "instructor" not in identity.roles:
            raise PermissionError("instructor_required")
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
        if employee is None or employee.account.person_profile is None:
            raise PermissionError("active_instructor_required")
        return employee

    def _version(self, session, client_id, version_id, expected_revision):
        self._boundary(session, client_id)
        version = session.scalar(
            select(TrainingPlanVersion)
            .where(
                TrainingPlanVersion.id == version_id,
                TrainingPlanVersion.client_id == client_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if version is None or version.revision != expected_revision:
            raise PrescriptionRejection("insufficient_support", "stale_revision")
        return version

    @staticmethod
    def _record(session, version):
        return session.scalar(
            select(DevelopmentValidationRecord)
            .where(
                DevelopmentValidationRecord.version_id == version.id,
                DevelopmentValidationRecord.revision == version.revision,
            )
            .order_by(
                DevelopmentValidationRecord.created_at.desc(), DevelopmentValidationRecord.id.desc()
            )
        )

    def _validate_saved(self, session, version):
        record = self._record(session, version)
        if record is None or record.kind != "qualified":
            raise PrescriptionRejection("insufficient_support", "legacy_or_unvalidated_draft")
        if (
            record_hash(self.lifecycle.content(session, version))
            != record.payload["rendered_content_sha256"]
        ):
            raise PrescriptionRejection("insufficient_support", "saved_content_changed")
        candidate = TypedPrescription.model_validate(record.payload["typed_content"])
        candidate.expected_revision = version.revision
        context = self._context(session, version.client_id)
        context.pop("candidate", None)
        context["client_id"] = version.client_id
        context["current_revision"] = version.revision
        result = validate_development_prescription(candidate=candidate, **context)
        if result["rendered_content_sha256"] != record.payload["rendered_content_sha256"]:
            raise PrescriptionRejection(
                "insufficient_support", "saved_projection_requires_revalidation"
            )
        if result["display_sha256"] != record.payload["display_sha256"]:
            raise PrescriptionRejection(
                "insufficient_support", "saved_projection_requires_revalidation"
            )
        if result["writer_configuration_sha256"] != record.payload["writer_configuration_sha256"]:
            raise PrescriptionRejection("insufficient_support", "writer_configuration_changed")
        return result

    @staticmethod
    def _save_record(
        session,
        version,
        result,
        actor,
        entry_point,
        *,
        request_id=None,
        revision=None,
        kind="qualified",
    ):
        target_revision = version.revision if revision is None else revision
        if kind == "qualified":
            result = {
                **result,
                "base_revision": result["evaluated_revision"],
                "evaluated_revision": target_revision,
            }
        record = DevelopmentValidationRecord(
            version_id=version.id,
            client_id=version.client_id,
            revision=target_revision,
            kind=kind,
            actor=actor,
            entry_point=entry_point,
            request_id=request_id,
            payload=result,
        )
        session.add(record)
        session.flush()
        return record

    @staticmethod
    def _success(version, result, *, include_review=False):
        visible = {
            key: value
            for key, value in result.items()
            if key
            in {
                "prescription_eligibility",
                "purpose",
                "scope",
                "projection",
                "instructions",
                "citations",
                "knowledge_status",
                "knowledge_limitations",
                "approval_basis",
                "professional_review_performed",
            }
        }
        if include_review:
            visible.update(
                {
                    key: result[key]
                    for key in (
                        "trace",
                        "policy_version",
                        "validator_version",
                        "evaluated_revision",
                    )
                }
            )
        return {
            "purpose": "isolated_development",
            "status": "accepted",
            "version_id": str(version.id),
            "revision": version.revision,
            "requires_instructor_review": version.status == "proposal",
            "prescription": visible,
        }

    @staticmethod
    def _failure(error):
        return {
            "purpose": "isolated_development",
            "status": "rejected",
            "category": error.category,
            "reason_codes": [error.reason],
            "message": OUTCOME_COPY[error.category],
            "next_action": error.action,
            "issues": error.issues,
        }

    def prepare(self, session, client_id, evaluated_revision, provider, *, require_complete=False):
        context = self._context(session, client_id)
        context.pop("candidate", None)
        context["client_id"] = client_id
        context["current_revision"] = evaluated_revision
        preflight = validate_development_prescription(candidate=None, **context)
        writer_context = build_prescription_writer_context(context, preflight, evaluated_revision)
        if require_complete and writer_context["confirmed_schedule"] is None:
            raise PrescriptionRejection("missing_input", "weekly_schedule_missing")
        raw_candidate = provider(writer_context)
        if isinstance(raw_candidate, TypedPrescription):
            raw_candidate = raw_candidate.model_dump()
        candidate = TypedPrescription.model_validate(raw_candidate)
        if require_complete and candidate.scope != "plan_revision":
            raise PrescriptionRejection("insufficient_support", "complete_adaptation_required")
        # Re-resolve all backend-owned inputs and evidence after provider return.
        fresh = self._context(session, client_id)
        fresh.pop("candidate", None)
        fresh.update(client_id=client_id, current_revision=evaluated_revision)
        result = validate_development_prescription(candidate=candidate, **fresh)
        return result

    def generate(
        self,
        session: Session,
        identity: AuthenticatedIdentity,
        *,
        client_id: UUID,
        request_id: UUID,
        entry_point: EntryPoint,
        provider,
        expected_revision: int | None = None,
        base_version_id: UUID | None = None,
        adaptation_confirmed: bool = False,
        commit: bool = True,
    ):
        self._owner(session, identity, client_id)
        if entry_point not in ENTRY_POINTS:
            raise ValueError("unknown_prescriptive_entry_point")
        attempt = session.begin_nested() if session.in_nested_transaction() else None
        try:
            if entry_point == "adaptation" and not adaptation_confirmed:
                raise PrescriptionRejection("missing_input", "adaptation_confirmation_required")
            self.lifecycle._lock_client(session, client_id)
            replay = session.scalar(
                select(DevelopmentValidationRecord)
                .where(
                    DevelopmentValidationRecord.client_id == client_id,
                    DevelopmentValidationRecord.request_id == request_id,
                )
                .order_by(DevelopmentValidationRecord.created_at.desc())
            )
            if replay is not None:
                version = self._version(session, client_id, replay.version_id, replay.revision)
                if (
                    version is None
                    or version.status != "proposal"
                    or replay.revision != version.revision
                ):
                    raise PrescriptionRejection("insufficient_support", "stale_replay")
                outcome = self._success(version, self._validate_saved(session, version))
                if attempt is not None:
                    attempt.commit()
                return outcome
            draft = self.lifecycle.find_proposal(session, client_id=client_id)
            if draft is not None and entry_point in ("initial", "targeted"):
                draft = self._version(session, client_id, draft.id, draft.revision)
                outcome = self._success(draft, self._validate_saved(session, draft))
                if attempt is not None:
                    attempt.commit()
                return outcome
            base = None
            if base_version_id is not None:
                base = self._version(session, client_id, base_version_id, expected_revision)
                if base.status != "current" or entry_point != "adaptation" or draft is not None:
                    raise PrescriptionRejection("insufficient_support", "invalid_adaptation_base")
                self._validate_saved(session, base)
            if entry_point == "adaptation" and base is None:
                raise PrescriptionRejection("insufficient_support", "adaptation_base_required")
            evaluated_revision = (
                draft.revision if draft is not None else (base.revision if base else None)
            )
            if evaluated_revision != expected_revision:
                raise PrescriptionRejection("insufficient_support", "stale_revision")
            result = self.prepare(
                session, client_id, evaluated_revision, provider, require_complete=base is not None
            )
            data = TrainingPlanVersionInput.model_validate(result["projection"])
            knowledge = KnowledgeResult(
                result["citations"], result["knowledge_status"], result["knowledge_limitations"]
            )
            if draft is not None:
                version = self.lifecycle.revise(
                    session,
                    plan_id=draft.plan_id,
                    version_number=draft.version_number,
                    actor="ai",
                    data=data,
                    expected_revision=expected_revision,
                    commit=False,
                )
            elif base is not None:
                version = self.lifecycle.create_revision(
                    session,
                    plan_id=base.plan_id,
                    version_number=base.version_number,
                    actor="ai",
                    origin="ai",
                    data=data,
                    expected_revision=expected_revision,
                    commit=False,
                )
            else:
                version = self.lifecycle.create_proposal(
                    session,
                    client_id=client_id,
                    data=data,
                    origin="ai",
                    created_by="ai",
                    knowledge=knowledge,
                    commit=False,
                )
            version.citations = knowledge.citations
            version.knowledge_status = knowledge.knowledge_status
            version.knowledge_limitations = knowledge.knowledge_limitations
            self._save_record(
                session, version, result, identity.subject, entry_point, request_id=request_id
            )
            if attempt is not None:
                attempt.commit()
            if commit:
                session.commit()
            else:
                session.flush()
            return self._success(version, result)
        except (AiProviderError, EmbeddingProviderError, TimeoutError, OSError):
            attempt.rollback() if attempt is not None else session.rollback()
            return self._failure(
                PrescriptionRejection("technical_unavailability", "provider_unavailable")
            )
        except (PrescriptionRejection, ValidationError) as error:
            attempt.rollback() if attempt is not None else session.rollback()
            if isinstance(error, ValidationError):
                error = PrescriptionRejection("insufficient_support", "invalid_typed_candidate")
            return self._failure(error)
        except Exception:
            if attempt is not None and attempt.is_active:
                attempt.rollback()
            else:
                session.rollback()
            raise

    def submit(self, session, identity, *, client_id, version_id, expected_revision):
        self._owner(session, identity, client_id)
        version = self._version(session, client_id, version_id, expected_revision)
        try:
            result = self._validate_saved(session, version)
            revision = version.revision + (1 if version.submitted_for_review_at is None else 0)
            self._save_record(
                session, version, result, identity.subject, "submission", revision=revision
            )
            self.lifecycle.submit_for_review(
                session,
                subject=identity.subject,
                version_id=version.id,
                expected_revision=expected_revision,
            )
            session.commit()
            return self._success(version, result)
        except Exception:
            session.rollback()
            raise

    def review(self, session, identity, *, client_id, version_id, expected_revision):
        self._boundary(session, client_id)
        self._instructor(session, identity)
        version = self._version(session, client_id, version_id, expected_revision)
        return self._success(version, self._validate_saved(session, version), include_review=True)

    def assume_manual(self, session, identity, *, client_id, version_id, expected_revision, reason):
        self._boundary(session, client_id)
        employee = self._instructor(session, identity)
        version = self._version(session, client_id, version_id, expected_revision)
        if (
            version.status != "proposal"
            or not isinstance(reason, str)
            or not reason.strip()
            or len(reason) > 500
        ):
            raise ValueError("saved_draft_and_manual_reason_required")
        try:
            previous = self._record(session, version)
            version.citations = []
            version.knowledge_status = "insufficient_evidence"
            version.knowledge_limitations = (
                "Conteúdo assumido manualmente pelo instrutor; sem qualificação atual de IA."
            )
            version.revision += 1
            version.submitted_for_review_at = datetime.now(UTC)
            version.responsible_employee_id = employee.id
            version.responsible_name = employee.account.person_profile.full_name
            self._save_record(
                session,
                version,
                {
                    "purpose": self.purpose,
                    "reason": reason.strip(),
                    "prior_record_id": str(previous.id) if previous else None,
                    "ai_origin": version.origin,
                    "original_creator": version.created_by,
                    "rendered_content_sha256": record_hash(
                        self.lifecycle.content(session, version)
                    ),
                },
                identity.subject,
                "manual_assumption",
                kind="manual",
            )
            session.commit()
            return {
                "status": "manual",
                "revision": version.revision,
                "purpose": self.purpose,
                "requires_instructor_review": True,
            }
        except Exception:
            session.rollback()
            raise

    def approve(self, session, identity, *, client_id, version_id, expected_revision):
        self._boundary(session, client_id)
        self._instructor(session, identity)
        version = self._version(session, client_id, version_id, expected_revision)
        try:
            record = self._record(session, version)
            if record is not None and record.kind == "manual":
                result = {
                    "manual": True,
                    "lineage_record_id": str(record.id),
                    "rendered_content_sha256": record_hash(
                        self.lifecycle.content(session, version)
                    ),
                }
                kind = "manual"
            else:
                result, kind = self._validate_saved(session, version), "qualified"
            self._save_record(
                session,
                version,
                result,
                identity.subject,
                "approval",
                revision=version.revision + 1,
                kind=kind,
            )
            self.lifecycle.approve(
                session,
                plan_id=version.plan_id,
                version_number=version.version_number,
                actor=identity.subject,
                expected_revision=expected_revision,
            )
            return {
                "status": "approved",
                "revision": version.revision,
                "purpose": "isolated_development",
                "manual": kind == "manual",
            }
        except Exception:
            session.rollback()
            raise

    def revise_manual(self, session, identity, *, client_id, version_id, expected_revision, data):
        self._boundary(session, client_id)
        self._instructor(session, identity)
        version = self._version(session, client_id, version_id, expected_revision)
        previous = self._record(session, version)
        try:
            self.lifecycle.revise(
                session,
                plan_id=version.plan_id,
                version_number=version.version_number,
                actor=identity.subject,
                data=data,
                expected_revision=expected_revision,
                commit=False,
            )
            self._save_record(
                session,
                version,
                {
                    "prior_record_id": str(previous.id) if previous else None,
                    "ai_origin": version.origin,
                    "original_creator": version.created_by,
                    "rendered_content_sha256": record_hash(
                        self.lifecycle.content(session, version)
                    ),
                },
                identity.subject,
                "manual_edit",
                kind="manual",
            )
            session.commit()
            return {
                "status": "manual",
                "revision": version.revision,
                "purpose": "isolated_development",
                "requires_instructor_review": True,
            }
        except Exception:
            session.rollback()
            raise
