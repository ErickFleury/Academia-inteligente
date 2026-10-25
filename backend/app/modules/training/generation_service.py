"""Initial AI proposal generation over completed, client-owned onboarding."""

from typing import Callable

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.ai import (
    AiProviderError,
    AiTrainingGenerationResponse,
    TrainingGenerationProvider,
    training_generation_provider_from_environment,
)
from app.integrations.ai_diagnostics import record_retry, record_turn
from app.modules.equipment.service import EquipmentService
from app.modules.knowledge.service import KnowledgeCitationError, KnowledgeContext, KnowledgeService
from app.modules.onboarding.draft_service import (
    ClientOnboardingScope,
    OnboardingDraftService,
)
from app.modules.onboarding.models import Onboarding
from app.modules.training import owner_rag
from app.modules.training.completeness import (
    IncompleteTrainingPlanError,
    requested_training_schedule,
    split_training_day,
    validate_exercise_names,
)
from app.modules.training.focus import InvalidTrainingFocusError, analyze_training_focus
from app.modules.training.knowledge_query import retrieve_training_knowledge
from app.modules.training.schema import TrainingPlanVersionInput
from app.modules.training.selection import (
    RedundantTrainingExerciseError,
    exercise_selection_correction,
    request_selected_training,
)
from app.modules.training.service import (
    ActiveTrainingProposalExistsError,
    InvalidTrainingContentError,
    TrainingLifecycleService,
)


class CompletedOnboardingRequiredError(Exception):
    """Generation is allowed only after authoritative onboarding completion."""


class TrainingGenerationUnavailableError(Exception):
    """The external AI adapter could not produce a usable response."""


class InvalidTrainingGenerationError(Exception):
    """The provider response did not satisfy the approved plan schema."""


class InitialTrainingGenerationService:
    """Validates external output before creating the client's sole proposal version."""

    def __init__(
        self,
        *,
        provider: TrainingGenerationProvider | None = None,
        draft_service: OnboardingDraftService | None = None,
        lifecycle_service: TrainingLifecycleService | None = None,
        knowledge_service: KnowledgeService | None = None,
    ) -> None:
        self._provider = provider or training_generation_provider_from_environment()
        self._drafts = draft_service or OnboardingDraftService()
        self._lifecycle = lifecycle_service or TrainingLifecycleService()
        self._knowledge = knowledge_service or KnowledgeService()

    def generate_for_subject(
        self,
        session: Session,
        subject: str,
        *,
        commit: bool = True,
        training_request: str = "",
        replace_existing: bool = False,
    ):
        scope = self._drafts.resolve_client_scope(session, subject)
        return self.generate_for_scope(
            session,
            scope,
            commit=commit,
            training_request=training_request,
            replace_existing=replace_existing,
        )

    @owner_rag.authorized_attempt
    def generate_for_scope(
        self,
        session: Session,
        scope: ClientOnboardingScope,
        *,
        commit: bool = True,
        training_request: str = "",
        replace_existing: bool = False,
    ):
        onboarding = session.scalar(
            select(Onboarding).where(Onboarding.client_id == scope.client_id)
        )
        if onboarding is None or not self._drafts.has_valid_completed_onboarding(
            session, scope.client_id
        ):
            raise CompletedOnboardingRequiredError

        from app.modules.training.prescription_runtime import (
            OperationalPrescriptionService,
            enforcement_enabled,
        )

        if enforcement_enabled():
            from app.modules.clients.models import Account

            owner = session.get(Account, scope.account_id)
            return OperationalPrescriptionService(
                session=session,
                client_id=scope.client_id,
                subject=owner.keycloak_subject,
                request=training_request,
                knowledge_service=self._knowledge,
            ).generate_version(self._provider, replace_existing=replace_existing, commit=commit)

        # Every client has at most one proposal, regardless of its creator.
        # Only valid content may be reused; legacy resource-only drafts must be regenerated.
        existing = self._lifecycle.find_proposal(session, client_id=scope.client_id)
        invalid_existing = existing is not None and self._lifecycle.has_invalid_exercises(
            session, existing
        )
        if (
            owner_rag.enabled()
            and existing is not None
            and owner_rag.requires_regeneration(existing)
        ):
            invalid_existing = True
        if (
            owner_rag.enabled()
            and existing is not None
            and existing.origin == "ai"
            and not any(c.get("owner_rag") for c in existing.citations)
        ):
            invalid_existing = True
        if (
            existing is not None
            and not replace_existing
            and not invalid_existing
            and not (owner_rag.enabled() and training_request.strip())
        ):
            if owner_rag.enabled() and existing.origin == "ai":
                owner_rag.validate_saved(
                    session,
                    existing,
                    self._lifecycle.content(session, existing),
                    onboarding=self._drafts.completion_data(onboarding).model_dump(),
                )
            return existing
        expected_revision = existing.revision if existing else None

        onboarding_data = self._drafts.completion_data(onboarding).model_dump()
        effective_goal = (
            owner_rag.requested_goal(training_request, onboarding_data["training_goal"])
            if owner_rag.enabled()
            else None
        )
        schedule = requested_training_schedule(training_request)
        focus_options = {}
        if owner_rag.enabled():
            from app.modules.training.owner_rag_schema import dictionary

            focus_options["allowed_muscle_groups"] = sorted(
                {g for e in dictionary()["exercises"] for g in e["groups"]}
            )
        try:
            focus = (
                analyze_training_focus(
                    lambda focus_context: self._retry(
                        lambda: self._provider.analyze_training_request(focus_context),
                        stage="focus",
                    ),
                    training_request,
                    **focus_options,
                )
                if training_request
                else None
            )
        except InvalidTrainingFocusError:
            raise InvalidTrainingGenerationError from None
        if focus is not None and effective_goal is not None:
            focus["goal"] = effective_goal

        # `completion_data` is the shared form/conversation-independent source
        # of truth. The provider never receives another client's data or identity.
        context = {
            "training_request": training_request,
            "training_focus": focus,
            "training_schedule": schedule,
            "active_equipment_models": EquipmentService().training_context(session),
            "completed_onboarding": onboarding_data,
            "proposal_rules": {
                "status": "proposal",
                "must_not_approve_or_activate": True,
                "instructor_review_required": True,
                "client_submission_required": True,
            },
        }
        onboarding_data = context["completed_onboarding"]
        evidence = retrieve_training_knowledge(
            self._knowledge,
            session,
            scope.client_id,
            training_request,
            onboarding_data,
            focus=focus,
        )
        context["knowledge"] = evidence.as_context()
        context = owner_rag.prepare(context, evidence, onboarding_data, focus=focus)
        # Keep the actual requested scope beside the final writing instruction.
        context["training_focus"] = context.pop("training_focus")
        context["training_request"] = context.pop("training_request")
        if invalid_existing:
            try:
                previous = self._lifecycle.content(session, existing)
            except InvalidTrainingContentError:
                # Malformed legacy structure has no reusable sheet; regenerate from onboarding.
                pass
            else:
                try:
                    validate_exercise_names(previous)
                except IncompleteTrainingPlanError as error:
                    context["selection_correction"] = exercise_selection_correction(
                        previous, error.issues
                    )
                    # Names/positions explain the defect; do not prime the writer to copy
                    # the complete invalid legacy prescription as its new output template.
                    context["selection_correction"]["rejected_plan"] = {
                        "name": previous.name,
                        "objective": previous.objective,
                    }
        try:
            response = self._generate_complete_routine(context, evidence)
            proposal = TrainingPlanVersionInput.model_validate(response.plan)
            knowledge = evidence.resolve_citations(
                response.citations,
                (
                    response.knowledge_status
                    if "knowledge_status" in response.model_fields_set
                    else None
                ),
            )
            knowledge = owner_rag.bind(knowledge, context, proposal)
            if owner_rag.enabled():
                from types import SimpleNamespace

                session.refresh(onboarding)
                owner_rag.validate_saved(
                    session,
                    SimpleNamespace(citations=knowledge.citations),
                    proposal,
                    onboarding=self._drafts.completion_data(onboarding).model_dump(),
                )
        except (
            ValidationError,
            KnowledgeCitationError,
            RedundantTrainingExerciseError,
            IncompleteTrainingPlanError,
        ) as error:
            record_turn(
                reason=(
                    "incomplete_training_plan"
                    if isinstance(error, IncompleteTrainingPlanError)
                    else "invalid_training_schema"
                    if isinstance(error, ValidationError)
                    else "invalid_training_citations"
                    if isinstance(error, KnowledgeCitationError)
                    else "redundant_exercise_prescription"
                )
            )
            raise InvalidTrainingGenerationError from error

        # Validation happens before lifecycle persistence, so malformed output
        # cannot create a partial plan or version.
        try:
            if existing is not None:
                revised = self._lifecycle.revise(
                    session,
                    plan_id=existing.plan_id,
                    version_number=existing.version_number,
                    data=proposal,
                    actor="ai",
                    expected_revision=expected_revision,
                    commit=False,
                    standalone=True,
                )
                revised.citations = list(knowledge.citations)
                revised.knowledge_status = knowledge.knowledge_status
                revised.knowledge_limitations = knowledge.knowledge_limitations
                if commit:
                    session.commit()
                else:
                    session.flush()
                return revised
            return self._lifecycle.create_proposal(
                session,
                client_id=scope.client_id,
                data=proposal,
                created_by="ai",
                origin="ai",
                knowledge=knowledge,
                commit=commit,
            )
        except ActiveTrainingProposalExistsError:
            # Another request created the sole draft while the provider was running.
            existing = self._lifecycle.find_proposal(session, client_id=scope.client_id)
            if existing is not None and not self._lifecycle.has_invalid_exercises(
                session, existing
            ):
                if owner_rag.enabled() and existing.origin == "ai":
                    owner_rag.validate_saved(
                        session,
                        existing,
                        self._lifecycle.content(session, existing),
                        onboarding=self._drafts.completion_data(onboarding).model_dump(),
                    )
                return existing
            raise InvalidTrainingGenerationError from None
        except InvalidTrainingContentError:
            record_turn(reason="invalid_training_equipment")
            raise InvalidTrainingGenerationError from None

    def _generate_complete_routine(self, context: dict, evidence: KnowledgeContext):
        labels = context["training_schedule"]["session_labels"]
        if len(labels) < 2 or (owner_rag.enabled() and len(labels) > 3):
            return self._generate_session(context)
        responses = []
        statuses = []
        citations = []
        for label in labels:
            session_context = {
                **context,
                "training_session": {"label": label, "all_session_labels": labels},
                "training_schedule": {"session_labels": [label]},
                "previous_sessions": [
                    {"label": previous_label, "plan": previous.plan}
                    for previous_label, previous in zip(labels, responses)
                ],
            }
            if owner_rag.enabled():
                from app.modules.training.owner_rag_schema import exercise_for_name

                session_context["previous_session_exercise_keys"] = {
                    previous_label: [
                        (exercise_for_name(item["exercise_name"], context) or {}).get("key")
                        for item in previous.plan["items"]
                    ]
                    for previous_label, previous in zip(labels, responses)
                }
                # Keep shared source/onboarding prompt prefixes stable between days.
                schedule = session_context.pop("training_schedule")
                session_context["training_schedule"] = schedule
            response = self._generate_session(session_context)
            knowledge = evidence.resolve_citations(
                response.citations,
                response.knowledge_status
                if "knowledge_status" in response.model_fields_set
                else None,
            )
            responses.append(response)
            statuses.append(knowledge.knowledge_status)
            citations.extend(citation["chunk_id"] for citation in knowledge.citations)
        # No session is persisted independently. The complete combined content
        # passes the ordinary plan/citation validation before the sole draft changes.
        priority = {"supported": 0, "insufficient_evidence": 1, "outdated": 2, "unavailable": 3}
        return AiTrainingGenerationResponse(
            plan={
                "name": f"Rotina de {len(labels)} fichas"
                if owner_rag.enabled()
                else f"Corpo inteiro — {len(labels)} dias",
                "objective": responses[0].plan["objective"],
                "items": [item for response in responses for item in response.plan["items"]],
            },
            citations=list(dict.fromkeys(citations)),
            knowledge_status=max(statuses, key=priority.get),
        )

    def _generate_session(self, context: dict):
        def write(selected_context):
            response = self._retry(lambda: self._provider.generate_training(selected_context))
            if owner_rag.enabled():
                from app.modules.training.owner_rag_schema import resolve_plan

                response = response.model_copy(
                    update={"plan": resolve_plan(response.plan, selected_context)}
                )
            label = selected_context.get("training_session", {}).get("label")
            items = response.plan.get("items")
            if label and isinstance(items, list):
                # The server requested exactly this session. Assign its label
                # without altering any prescription or overwriting a conflicting
                # provider-assigned day, which the ordinary validator rejects.
                items = [
                    {**item, "exercise_name": f"{item['exercise_name']} (Dia {label})"}
                    if isinstance(item, dict)
                    and isinstance(item.get("exercise_name"), str)
                    and not split_training_day(item["exercise_name"])[0]
                    else item
                    for item in items
                ]
                response = response.model_copy(update={"plan": {**response.plan, "items": items}})
            return response

        return request_selected_training(
            write,
            context,
            plan_field="plan",
            repair_domain_errors=owner_rag.enabled(),
            candidate_validator=owner_rag.validate_candidate if owner_rag.enabled() else None,
            assess=(
                lambda review_context: self._retry(
                    lambda: self._provider.assess_training(review_context), stage="review"
                )
            ),
        )

    @staticmethod
    def _retry(operation: Callable[[], object], stage="writer"):
        for attempt in range(2):
            try:
                from app.modules.training.prescription_budget import CURRENT_BUDGET

                budget = CURRENT_BUDGET.get()
                return budget.call(stage, operation) if budget is not None else operation()
            except AiProviderError as error:
                record_retry(error.category, will_retry=not attempt and error.retryable)
                if attempt or not error.retryable:
                    if (
                        owner_rag.enabled()
                        and stage == "writer"
                        and error.category == "malformed_structured_output"
                    ):
                        from app.modules.training.prescription_contract import PrescriptionRejection

                        raise PrescriptionRejection(
                            "insufficient_support",
                            "invalid_typed_candidate",
                            issues=[
                                {"field": "candidate", "reason": "malformed_structured_output"}
                            ],
                        ) from None
                    raise TrainingGenerationUnavailableError from None
        raise TrainingGenerationUnavailableError
