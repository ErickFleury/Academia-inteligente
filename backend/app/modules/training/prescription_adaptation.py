"""Validate complete typed adaptations while retaining RF-19's existing review queue."""

from sqlalchemy import select

from app.modules.training.models import TrainingAdaptationProposal, TrainingPlanItem
from app.modules.training.prescription_contract import (
    PrescriptionRejection,
    TypedPrescription,
    record_hash,
)
from app.modules.training.prescription_development import PrescriptionAdaptationValidation
from app.modules.training.prescription_runtime import OperationalPrescriptionService
from app.modules.training.prescription_validation import validate_development_prescription
from app.modules.training.schema import AdaptationOperationInput, TrainingPlanVersionInput
from app.modules.training.service import ActiveTrainingProposalExistsError, TrainingLifecycleService


def validate_adaptation(session, service, proposal, subject):
    record = session.get(PrescriptionAdaptationValidation, proposal.id)
    if record is None:
        raise PrescriptionRejection("insufficient_support", "unvalidated_adaptation")
    base = service._current(session, proposal.client_id)
    runtime = OperationalPrescriptionService(
        session=session,
        client_id=proposal.client_id,
        subject=subject,
        knowledge_service=service._knowledge,
    )
    if base.id != proposal.base_version_id or base.revision != record.base_revision:
        raise PrescriptionRejection("insufficient_support", "adaptation_base_changed")
    if record_hash(runtime.lifecycle.content(session, base)) != record.base_content_sha256:
        raise PrescriptionRejection("insufficient_support", "adaptation_base_changed")
    runtime._validate_saved(session, base)
    context = runtime._context(session, proposal.client_id)
    context.pop("candidate", None)
    context.update(client_id=proposal.client_id, current_revision=base.revision)
    candidate = TypedPrescription.model_validate(record.payload["typed_content"])
    result = validate_development_prescription(candidate=candidate, **context)
    if record_hash(service._apply(session, base, proposal)) != result["rendered_content_sha256"]:
        raise PrescriptionRejection("insufficient_support", "adaptation_content_changed")
    return runtime, result


def generate_adaptation(
    session, service, subject, *, source_client_request_id, client_request_id, reason
):
    client_id = service._client_id(session, subject)
    lifecycle = TrainingLifecycleService()
    lifecycle._lock_client(session, client_id)
    existing = session.scalar(
        select(TrainingAdaptationProposal).where(
            TrainingAdaptationProposal.client_id == client_id,
            TrainingAdaptationProposal.client_request_id == client_request_id,
        )
    )
    if existing is not None:
        if existing.status != "proposed":
            raise PrescriptionRejection("insufficient_support", "stale_adaptation_replay")
        validate_adaptation(session, service, existing, subject)
        return existing
    base = service._current(session, client_id)
    if lifecycle.find_proposal(session, client_id=client_id):
        raise ActiveTrainingProposalExistsError
    source = service._source_message(session, client_id, source_client_request_id)
    runtime = OperationalPrescriptionService(
        session=session,
        client_id=client_id,
        subject=subject,
        request=source.content + "\n" + reason,
        knowledge_service=service._knowledge,
    )
    runtime._validate_saved(session, base)
    base_record = runtime._record(session, base)
    runtime.reviewer = getattr(service._provider, "assess_training", None)

    def write(context):
        from app.modules.training.prescription_selection import retry_provider

        return retry_provider(
            lambda: service._provider.generate_prescription(
                {
                    **context,
                    "training_request": runtime.request,
                    "required_scope": "plan_revision",
                    "current_prescription": base_record.payload["typed_content"],
                }
            )
        )

    result = runtime.prepare(session, client_id, base.revision, write, require_complete=True)
    projection = TrainingPlanVersionInput.model_validate(result["projection"])
    original = lifecycle.content(session, base)
    if (projection.name, projection.objective) != (original.name, original.objective):
        raise PrescriptionRejection("insufficient_support", "adaptation_goal_or_title_changed")
    positions = list(
        session.scalars(
            select(TrainingPlanItem.position)
            .where(TrainingPlanItem.version_id == base.id)
            .order_by(TrainingPlanItem.position)
        )
    )
    operations = []
    for index, item in enumerate(projection.items):
        old = original.items[index] if index < len(original.items) else None
        if old == item:
            continue
        operations.append(
            AdaptationOperationInput(
                operation_type="add"
                if old is None
                else "adjust"
                if old.exercise_name == item.exercise_name
                else "replace",
                target_position=positions[index] if old is not None else None,
                item={
                    **item.model_dump(mode="json"),
                    "is_existing_exercise": old is not None
                    and old.exercise_name == item.exercise_name,
                },
            )
        )
    for index in range(len(projection.items), len(original.items)):
        operations.append(
            AdaptationOperationInput(operation_type="remove", target_position=positions[index])
        )
    if not operations:
        raise PrescriptionRejection("insufficient_support", "adaptation_has_no_change")
    service._validate_operations(session, base, operations)
    proposal = TrainingAdaptationProposal(
        client_id=client_id,
        base_version_id=base.id,
        source_client_request_id=source_client_request_id,
        client_request_id=client_request_id,
        reason=reason.strip(),
        explanation="Proposta estruturada para sua revisão e a do instrutor.",
        status="proposed",
        citations=result["citations"],
        knowledge_status=result["knowledge_status"],
        knowledge_limitations=result["knowledge_limitations"],
    )
    session.add(proposal)
    session.flush()
    service._replace_operations(session, proposal, operations)
    session.flush()
    if record_hash(service._apply(session, base, proposal)) != result["rendered_content_sha256"]:
        raise PrescriptionRejection("insufficient_support", "adaptation_projection_mismatch")
    session.add(
        PrescriptionAdaptationValidation(
            proposal_id=proposal.id,
            client_id=client_id,
            base_revision=base.revision,
            base_content_sha256=record_hash(original),
            payload=result,
        )
    )
    session.commit()
    return proposal
