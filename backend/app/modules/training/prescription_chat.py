"""Backend-rendered chat output for the evidence-qualified development rollout."""

from app.modules.training.prescription_runtime import OperationalPrescriptionService
from app.modules.training.presentation import proposal_preview


def operational_reply(service, session, subject, client_id, context, request_id):
    message = context["current_user_message"]
    runtime = OperationalPrescriptionService(
        session=session,
        client_id=client_id,
        subject=subject,
        request=message,
        knowledge_service=service._knowledge,
    )
    draft = service._lifecycle.find_proposal(session, client_id=client_id)
    requested = (
        context["rules"]["may_update_ai_draft"]
        or service._requests_exercise_suggestion(message)
        or service._requests_initial_plan(message, context["recent_messages"])
    )
    if requested:
        if not context["onboarding_completed"]:
            return service._initial_plan_guidance(context)
        # All actionable output is rendered from the exact persisted typed result.
        # Free-form provider prose cannot introduce an unvalidated prescription.
        with session.begin_nested():
            draft = runtime.generate_version(
                service._provider,
                replace_existing=draft is not None,
                commit=False,
                entry_point="chat_edit" if context["rules"]["may_update_ai_draft"] else None,
                request_id=request_id,
            )
        return (
            "Sua proposta está disponível para conferência. Ela depende da revisão "
            "e aprovação do instrutor antes de se tornar seu treino atual.\n\n"
            + proposal_preview(session, draft)
        )
    if draft is not None:
        runtime._validate_saved(session, draft)
        return (
            "Você pode conferir a proposta em Meu treino, pedir uma alteração "
            "ou enviá-la para revisão do instrutor."
        )
    if context["current_training_plan"] is not None:
        return (
            "Seu treino atual permanece disponível em Meu treino. Para mudar exercícios "
            "ou informar uma dificuldade, descreva o pedido ao instrutor. Uma adaptação "
            "precisa de confirmação e revisão antes de alterar seu plano."
        )
    return service._initial_plan_guidance(context)


def replay_reply(service, session, subject, client_id, request_id):
    from sqlalchemy import select

    from app.modules.training.prescription_contract import PrescriptionRejection
    from app.modules.training.prescription_development import DevelopmentValidationRecord

    record = session.scalar(
        select(DevelopmentValidationRecord)
        .where(
            DevelopmentValidationRecord.client_id == client_id,
            DevelopmentValidationRecord.request_id == request_id,
        )
        .order_by(DevelopmentValidationRecord.created_at.desc())
    )
    if record is None:
        return "Consulte Meu treino para conferir sua ficha e solicitar a revisão do instrutor."
    runtime = OperationalPrescriptionService(
        session=session,
        client_id=client_id,
        subject=subject,
        knowledge_service=service._knowledge,
    )
    draft = runtime._version(session, client_id, record.version_id, record.revision)
    if draft.status != "proposal":
        raise PrescriptionRejection("insufficient_support", "stale_replay")
    runtime._validate_saved(session, draft)
    return "Sua proposta depende da revisão do instrutor.\n\n" + proposal_preview(session, draft)
