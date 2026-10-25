"""Operational adapters over the tested validator and existing training lifecycle.

No research candidate is promoted here. Approved policy, execution, accounting,
dictionary, confirmed inputs and current retrieved support are all required.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError

from app.modules.clients.models import Client
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.knowledge.bootstrap import CATALOG_PATH
from app.modules.knowledge.models import KnowledgeSource
from app.modules.knowledge.service import KnowledgeService
from app.modules.onboarding.draft_service import OnboardingDraftService
from app.modules.onboarding.models import Onboarding
from app.modules.training.focus import (
    InvalidTrainingFocusError,
    _normalized,
    analyze_training_focus,
)
from app.modules.training.knowledge_query import retrieve_training_knowledge
from app.modules.training.models import TrainingPlanVersion
from app.modules.training.prescription_accounting import AccountingMethod
from app.modules.training.prescription_contract import (
    DevelopmentExecutionContract,
    PrescriptionRejection,
    TypedPrescription,
    record_hash,
)
from app.modules.training.prescription_development import (
    DevelopmentInputConfirmation,
    IsolatedPrescriptionService,
)
from app.modules.training.prescription_policy import PolicyCatalog

ROOT = Path(__file__).parent


def enforcement_enabled() -> bool:
    from app.modules.training.owner_rag import enabled

    # Compiled qualification is separate from the owner's assisted-RAG mode.
    return (
        not enabled() and os.getenv("TRAINING_PRESCRIPTION_GATE_ENABLED", "false").lower() == "true"
    )


def writer_configuration() -> dict:
    kind = os.getenv("AI_PROVIDER", "openai")
    return {
        "provider": kind,
        "model": os.getenv("OLLAMA_MODEL", "qwen3:8b")
        if kind == "ollama"
        else os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
        "contract": "typed-prescription-1",
        "instruction_version": "operational-prescription-2",
    }


class OperationalPrescriptionService(IsolatedPrescriptionService):
    """Reuse domain mechanics while replacing the isolated account/context adapters."""

    purpose = "operational"

    def __init__(
        self,
        *,
        session,
        client_id: UUID,
        subject: str,
        request: str = "",
        knowledge_service=None,
        context_supplier=None,
    ):
        self.session, self.client_id, self.subject = session, client_id, subject
        self.request = request
        self.knowledge = knowledge_service or KnowledgeService()
        super().__init__(
            client_ids={client_id}, context_supplier=context_supplier or self._operational_context
        )

    def _boundary(self, session, client_id):
        if client_id != self.client_id:
            raise PermissionError("prescription_client_scope_required")
        client = session.get(Client, client_id)
        if client is None or not client.active or not client.account.account_active:
            raise PermissionError("active_client_required")
        return client

    def _context(self, session, client_id):
        context = super()._context(session, client_id)
        if context["execution"].purpose != "operational":
            raise PrescriptionRejection("insufficient_support", "operational_contract_required")
        if context["execution"].writer_configuration_sha256 != record_hash(writer_configuration()):
            raise PrescriptionRejection("insufficient_support", "writer_configuration_changed")
        return context

    @staticmethod
    def _success(version, result, *, include_review=False):
        outcome = IsolatedPrescriptionService._success(
            version, result, include_review=include_review
        )
        outcome["purpose"] = "operational"
        return outcome

    @staticmethod
    def _failure(error):
        return {**IsolatedPrescriptionService._failure(error), "purpose": "operational"}

    def _operational_context(self):
        try:
            return self._build_operational_context()
        except PrescriptionRejection:
            raise
        except (OSError, ValueError, KeyError, TypeError):
            raise PrescriptionRejection(
                "technical_unavailability", "prescription_configuration_unavailable"
            ) from None

    def _build_operational_context(self, *, collect_only=False, requested_goal=None):
        session, client_id = self.session, self.client_id
        client = self._boundary(session, client_id)
        onboarding_service = OnboardingDraftService()
        if not onboarding_service.has_valid_completed_onboarding(session, client_id):
            raise PrescriptionRejection("missing_input", "completed_onboarding_required")
        onboarding = session.scalar(select(Onboarding).where(Onboarding.client_id == client_id))
        values = onboarding_service.completion_data(onboarding).model_dump()
        policy_document = json.loads(
            (ROOT / "prescription-policies.json").read_text(encoding="utf-8")
        )
        catalog = PolicyCatalog.model_validate(policy_document)
        latest = session.scalar(
            select(DevelopmentInputConfirmation)
            .where(DevelopmentInputConfirmation.client_id == client_id)
            .order_by(DevelopmentInputConfirmation.created_at.desc())
        )
        confirmed_goal = None
        if latest is not None:
            from app.modules.training.prescription_contract import InputSnapshot

            prior_goal = InputSnapshot.model_validate(latest.snapshot).facts.get("training_goal")
            if prior_goal is not None and prior_goal.source == "request":
                confirmed_goal = prior_goal.value
        goal = str(requested_goal or confirmed_goal or values["training_goal"]).strip().casefold()
        choices = [
            p
            for p in catalog.policies
            if p.status == "approved"
            and goal in {g.casefold() for g in p.exact_goal_mappings}
            and values["training_experience"] in p.experience_levels
        ]
        if len(choices) != 1:
            raise PrescriptionRejection("insufficient_support", "approved_goal_policy_required")
        policy = choices[0]
        bundle = json.loads((ROOT / "prescription-execution.json").read_text(encoding="utf-8"))
        contracts = [DevelopmentExecutionContract.model_validate(c) for c in bundle["contracts"]]
        contracts = [
            c for c in contracts if c.policy_id == policy.id and c.purpose == "operational"
        ]
        if len(contracts) != 1:
            raise PrescriptionRejection("insufficient_support", "operational_contract_required")
        execution = contracts[0]
        if execution.writer_configuration_sha256 != record_hash(writer_configuration()):
            raise PrescriptionRejection("insufficient_support", "writer_configuration_changed")
        owner = AuthenticatedIdentity(client.account.keycloak_subject, "", ("client",))
        snapshot = self.onboarding_snapshot(
            session,
            owner,
            client_id=client_id,
            required_fields={
                r.key for r in execution.input_requirements if r.source == "onboarding"
            },
        )
        if latest is not None:
            from app.modules.training.prescription_contract import InputSnapshot

            prior = InputSnapshot.model_validate(latest.snapshot)
            allowed = {
                r.key
                for r in execution.input_requirements
                if r.source == "request" and r.collection_approved
            }
            snapshot.facts.update(
                {k: f for k, f in prior.facts.items() if k in allowed and f.source == "request"}
            )
            snapshot.schedule = prior.schedule
        accounting_document = json.loads(
            (ROOT / "prescription-accounting.json").read_text(encoding="utf-8")
        )
        accounting = AccountingMethod.model_validate(accounting_document)
        from app.modules.training.evidence_review import (
            EvidenceReviewError,
            require_current_runtime_reviews,
        )

        try:
            if policy.approval_basis == "owner_decision":
                from app.modules.training.prescription_authorization import verify_owner_bundle

                verify_owner_bundle(
                    {
                        "policies": policy_document,
                        "execution": bundle,
                        "accounting": accounting_document,
                    },
                    policy.owner_authorization_id,
                )
            else:
                require_current_runtime_reviews(
                    session,
                    [
                        (policy.review_records, policy.review_due_at),
                        (catalog.dictionary.review_records, None),
                        (accounting.review_records, accounting.review_due_at),
                    ],
                )
        except (EvidenceReviewError, SQLAlchemyError):
            raise PrescriptionRejection(
                "technical_unavailability", "professional_review_storage_unavailable"
            ) from None
        from app.modules.knowledge.service import KnowledgeContext

        if not collect_only:
            from app.modules.training.prescription_contract import fact_is_current

            for requirement in execution.input_requirements:
                if not fact_is_current(snapshot.facts.get(requirement.key), datetime.now(UTC)):
                    raise PrescriptionRejection(
                        "missing_input"
                        if requirement.missing_action == "clarify"
                        else "insufficient_support",
                        "required_input_missing_stale_or_conflicting",
                        issues=[
                            {
                                "field": requirement.key,
                                "reason": "required_input_missing_stale_or_conflicting",
                            }
                        ],
                    )
        retrieval_values = {**values, "training_goal": goal}
        evidence = (
            KnowledgeContext.empty()
            if collect_only
            else retrieve_training_knowledge(
                self.knowledge, session, client_id, self.request, retrieval_values
            )
        )
        # Re-read live review state, so a packaged file cannot undo DB revocation.
        source_catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        for source in source_catalog["sources"]:
            live = session.get(KnowledgeSource, source["id"], populate_existing=True)
            if live is None or live.client_id is not None:
                source["review_status"] = "excluded"
            else:
                for key in ("review_status", "license", "commercial_use_allowed", "reviewed_by"):
                    source[key] = getattr(live, key)
                for key in ("reviewed_at", "review_due_at"):
                    value = getattr(live, key)
                    source[key] = value.isoformat() if value else None
        return dict(
            snapshot=snapshot,
            catalog=catalog,
            execution=execution,
            accounting=accounting,
            evidence=evidence,
            source_catalog=source_catalog,
        )

    def generate_version(
        self,
        provider,
        *,
        replace_existing=False,
        commit=True,
        entry_point=None,
        request_id=None,
    ):
        draft = self.lifecycle.find_proposal(self.session, client_id=self.client_id)
        self.reviewer = getattr(provider, "assess_training", None)
        identity = AuthenticatedIdentity(self.subject, "", ("client",))
        selected_entry = entry_point or ("rebuild" if replace_existing else "initial")
        focus_result = None

        def write(context):
            nonlocal focus_result
            from app.modules.training.prescription_selection import retry_provider

            if selected_entry in ("rebuild", "chat_edit") and context["confirmed_schedule"] is None:
                raise PrescriptionRejection("missing_input", "weekly_schedule_missing")
            try:
                focus = focus_result or (
                    analyze_training_focus(
                        lambda value: retry_provider(
                            lambda: provider.analyze_training_request(value), stage="focus"
                        ),
                        self.request,
                    )
                    if self.request
                    else {"scope": "unspecified", "muscle_groups": []}
                )
                focus_result = focus
            except (InvalidTrainingFocusError, AttributeError):
                raise PrescriptionRejection(
                    "missing_input", "training_focus_requires_clarification"
                ) from None
            self.requested_focus = focus
            if focus.get("goal") and _normalized(focus["goal"]) not in {
                _normalized(value) for value in context.get("goal_mappings", [])
            }:
                raise PrescriptionRejection(
                    "missing_input",
                    "goal_priority_confirmation_required",
                    issues=[
                        {"field": "training_goal", "reason": "goal_priority_confirmation_required"}
                    ],
                )
            if focus["scope"] == "targeted":
                requested = {_normalized(group) for group in focus["muscle_groups"]}
                choices = [
                    e
                    for e in context["dictionary"]["exercises"]
                    if requested.intersection({_normalized(m) for m in e["primary_muscles"]})
                ]
                if not choices:
                    raise PrescriptionRejection("insufficient_support", "unsupported_target_focus")
                context = {**context, "dictionary": {**context["dictionary"], "exercises": choices}}
            candidate = TypedPrescription.model_validate(
                retry_provider(
                    lambda: provider.generate_prescription(
                        {
                            **context,
                            "training_request": self.request,
                            "requested_focus": focus,
                            "required_scope": "plan_revision"
                            if selected_entry in ("rebuild", "chat_edit")
                            else None,
                            "current_prescription": self._record(self.session, draft).payload[
                                "typed_content"
                            ]
                            if draft
                            and self._record(self.session, draft)
                            and self._record(self.session, draft).kind == "qualified"
                            else None,
                        }
                    )
                )
            )
            if selected_entry in ("rebuild", "chat_edit") and candidate.scope != "plan_revision":
                raise PrescriptionRejection("insufficient_support", "complete_revision_required")
            if focus["scope"] == "targeted" and selected_entry in ("initial", "targeted"):
                requested = {_normalized(group) for group in focus["muscle_groups"]}
                exercises = {e["key"]: e for e in context["dictionary"]["exercises"]}
                covered = set()
                for item in (i for s in candidate.sessions for i in s.items):
                    muscles = {
                        _normalized(m)
                        for m in exercises.get(item.exercise_key, {}).get("primary_muscles", [])
                    }
                    if not muscles.intersection(requested):
                        raise PrescriptionRejection(
                            "insufficient_support", "unsupported_target_focus"
                        )
                    covered.update(muscles.intersection(requested))
                if covered != requested:
                    raise PrescriptionRejection("insufficient_support", "incomplete_target_focus")
            return candidate

        outcome = self.generate(
            self.session,
            identity,
            client_id=self.client_id,
            request_id=request_id or uuid4(),
            entry_point=selected_entry,
            expected_revision=draft.revision if draft else None,
            provider=write,
            commit=commit,
        )
        if outcome["status"] != "accepted":
            raise PrescriptionRejection(
                outcome["category"],
                outcome["reason_codes"][0],
                issues=outcome.get("issues"),
                action=outcome.get("next_action"),
            )
        return self.session.get(TrainingPlanVersion, UUID(outcome["version_id"]))

    def prepare(self, session, client_id, evaluated_revision, provider, *, require_complete=False):
        from app.modules.training.prescription_selection import prepare_with_selection

        return prepare_with_selection(
            self,
            session,
            client_id,
            evaluated_revision,
            provider,
            super().prepare,
            require_complete,
        )


def _existing_record(session, version):
    # Legacy application tests/startup may not have registered the new mapping.
    # Enforced execution never treats an absent migration as a successful pass.
    from app.modules.training.prescription_development import DevelopmentValidationRecord

    if not inspect(session.connection()).has_table(DevelopmentValidationRecord.__tablename__):
        if enforcement_enabled():
            raise PrescriptionRejection(
                "technical_unavailability", "prescription_schema_unavailable"
            )
        return None
    return IsolatedPrescriptionService._record(session, version)


def _is_isolated_record(session, version, record) -> bool:
    if not record or record.payload.get("purpose") == "operational":
        return False
    try:
        IsolatedPrescriptionService(
            client_ids={version.client_id}, context_supplier=None
        )._boundary(session, version.client_id)
    except PermissionError:
        return False
    return True


def validate_lifecycle_transition(session, version, *, actor, phase):
    """Revalidate exact content/support before the existing atomic transition."""
    from app.modules.training import owner_rag

    if any(c.get("owner_rag") for c in version.citations):
        onboarding = session.scalar(
            select(Onboarding)
            .where(Onboarding.client_id == version.client_id)
            .execution_options(populate_existing=True)
        )
        if onboarding is None:
            raise PrescriptionRejection("missing_input", "completed_onboarding_required")
        owner_rag.validate_saved(
            session,
            version,
            OperationalPrescriptionService(
                session=session, client_id=version.client_id, subject=actor
            ).lifecycle.content(session, version),
            onboarding=OnboardingDraftService().completion_data(onboarding).model_dump(),
        )
        return
    record = _existing_record(session, version)
    if _is_isolated_record(session, version, record):
        return  # The isolated service already validates and records its transition.
    if not enforcement_enabled() and record is None:
        return
    if version.origin != "ai" and record is None:
        return  # Instructor authoring remains independent of external AI/knowledge.
    runtime = OperationalPrescriptionService(
        session=session, client_id=version.client_id, subject=actor
    )
    if record is not None and record.kind == "manual":
        if record.payload.get("rendered_content_sha256") != record_hash(
            runtime.lifecycle.content(session, version)
        ):
            raise PrescriptionRejection("insufficient_support", "manual_content_changed")
        result, kind = record.payload, "manual"
    else:
        result, kind = runtime._validate_saved(session, version), "qualified"
    revision = version.revision + (
        1 if phase == "approval" or version.submitted_for_review_at is None else 0
    )
    runtime._save_record(session, version, result, actor, phase, revision=revision, kind=kind)


def record_manual_edit(session, version, *, actor):
    if not enforcement_enabled():
        from app.modules.training.prescription_development import DevelopmentValidationRecord

        if not inspect(session.connection()).has_table(DevelopmentValidationRecord.__tablename__):
            return
        previous = session.scalar(
            select(DevelopmentValidationRecord)
            .where(DevelopmentValidationRecord.version_id == version.id)
            .order_by(DevelopmentValidationRecord.created_at.desc())
        )
        if previous is None or _is_isolated_record(session, version, previous):
            return
    runtime = OperationalPrescriptionService(
        session=session, client_id=version.client_id, subject=actor
    )
    runtime._instructor(session, AuthenticatedIdentity(actor, "", ("instructor",)))
    runtime._save_record(
        session,
        version,
        {
            "purpose": "operational",
            "reason": "instructor_edited_content",
            "ai_origin": version.origin,
            "rendered_content_sha256": record_hash(runtime.lifecycle.content(session, version)),
        },
        actor,
        "manual_edit",
        kind="manual",
    )
