"""Source-bound, explicitly confirmed revisions of a client's current health report.

The model proposes an interpretation; the client reviews the complete affected
field pair before persistence. A pending proposal lives in the existing expiring
chat, not in a second medical record. The caller owns the reply transaction.
"""

import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.modules.clients.models import Client
from app.modules.memory.service import source_sentences, utc
from app.modules.onboarding.draft_service import ClientOnboardingScope, OnboardingDraftService
from app.modules.onboarding.models import Onboarding
from app.modules.onboarding.schema import OnboardingCompletionData
from app.modules.training.models import TrainingAiConversation, TrainingAiMessage

PAIRS = {
    "has_limitations_or_complaints": "limitations_or_complaints",
    "uses_medications": "medications",
    "has_health_conditions": "health_conditions",
}
LABELS = {
    "has_limitations_or_complaints": "dores ou limitações atuais",
    "uses_medications": "uso atual de medicamentos",
    "has_health_conditions": "condições de saúde informadas",
}


class HealthUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    action: Literal["propose", "confirm", "cancel", "clarify"]
    field: Literal["has_limitations_or_complaints", "uses_medications", "has_health_conditions"]
    kind: Literal["corrected", "resolved", "changed"]
    present: bool
    details: str | None = Field(default=None, min_length=1, max_length=2000)
    quote: str = Field(min_length=1, max_length=2000)


class HealthUpdateError(Exception):
    def __init__(self, code="health_update_invalid", status=422):
        self.code, self.status = code, status
        super().__init__(code)


def normalized(value):
    return " ".join(value.split())


def folded(value):
    return "".join(
        c for c in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(c)
    )


def health_values(record):
    return {key: getattr(record, key) for pair in PAIRS.items() for key in pair}


def ambiguous(value):
    return bool(
        re.search(
            r"\?|\b(talvez|acho|nao sei|nao tenho certeza|se eu|mas|porem|exceto)\b",
            folded(value),
        )
    )


def confirmation(value):
    """Guard a model-interpreted confirmation against contradictory source text.

    Consent wording is interpreted by the router, not a fixed yes/no dictionary.
    The backend also requires the complete current utterance and a valid,
    revision-bound proposal previously displayed in this same conversation.
    """
    value = folded(normalized(value))
    if ambiguous(value) or re.search(
        r"\b(nunca|cancele|cancela|espere|ainda|continua|discordo|negativo)\b|"
        r"\b(de jeito nenhum|de forma alguma|nao mesmo|agora nao)\b|"
        r"\bnao\s+(confirmo|autorizo|pode|salve|salvar|atualize|atualizar|"
        r"corrija|corrigir|concordo|quero|estou de acordo)\b",
        value,
    ):
        return False
    return bool(value.strip(" .!")) and value.strip(" .!") != "nao"


def current_record(session, client_id):
    record = session.scalar(
        select(Onboarding)
        .where(Onboarding.client_id == client_id)
        .execution_options(populate_existing=True)
    )
    if record is None or record.status != "completed":
        raise HealthUpdateError()
    return record


def pending_update(session, client_id, source, metadata, cutoff=None):
    """Reload only the last own-conversation proposal, bound to its original event."""
    if not metadata:
        return None
    try:
        event_id = UUID(metadata["source_event_id"])
        proposed = HealthUpdate.model_validate(metadata["proposal"])
    except (ValueError, TypeError, KeyError):
        return None
    event = session.scalar(
        select(TrainingAiMessage).where(
            TrainingAiMessage.id == event_id,
            TrainingAiMessage.conversation_id == source.conversation_id,
            TrainingAiMessage.role == "user",
            TrainingAiMessage.sequence < source.sequence,
        )
    )
    if (
        event is None
        or utc(event.created_at) <= datetime.now(UTC) - timedelta(days=30)
        or (cutoff and utc(event.created_at) <= utc(cutoff))
        or proposed.quote not in normalized(event.content)
    ):
        return None
    record = current_record(session, client_id)
    if (
        metadata.get("before") != health_values(record)
        or metadata.get("record_updated_at") != utc(record.updated_at).isoformat()
    ):
        return None
    return metadata


def report_source(session, client_id, source, quote, record, sources, cutoff):
    """Resolve model evidence only within the bounded, backend-owned chat context."""
    event_ids = {source.id}
    for item in sources:
        try:
            event_ids.add(UUID(str(item.get("event_id"))))
        except (ValueError, TypeError):
            continue
    events = session.scalars(
        select(TrainingAiMessage)
        .join(TrainingAiConversation)
        .where(
            TrainingAiConversation.client_id == client_id,
            TrainingAiMessage.conversation_id == source.conversation_id,
            TrainingAiMessage.id.in_(event_ids),
            TrainingAiMessage.role == "user",
            TrainingAiMessage.sequence <= source.sequence,
        )
        .order_by(TrainingAiMessage.sequence.desc())
    )
    for event in events:
        if (
            utc(event.created_at) <= datetime.now(UTC) - timedelta(days=30)
            or (cutoff and utc(event.created_at) <= utc(cutoff))
            or (event.id != source.id and utc(event.created_at) < utc(record.updated_at))
        ):
            continue
        # Whole sentences retain negation and uncertainty. The entire message
        # remains the ambiguity check, including qualifications in another sentence.
        candidates = [normalized(event.content), *source_sentences(event.content)]
        for value in candidates:
            if quote.rstrip(" .!") == value.rstrip(" .!"):
                return event, value
    raise HealthUpdateError()


def proposal(session, client_id, source, update, *, sources=(), cutoff=None):
    record = current_record(session, client_id)
    quote = normalized(update.quote)
    source, quote = report_source(session, client_id, source, quote, record, sources, cutoff)
    update = update.model_copy(update={"quote": quote})
    if ambiguous(source.content) or re.search(
        r"\b(minha mae|meu pai|meu amigo|minha amiga)\b", folded(source.content)
    ):
        return None
    # A generic answer to a mobility question cannot silently mean a named
    # complaint has resolved. Ask the difference instead of clearing the group.
    if (
        not update.present
        and update.field == "has_limitations_or_complaints"
        and record.has_limitations_or_complaints
        and not re.search(
            r"\b(dor|dores|joelho|lesao|queixa|problema|registro|cadastro)\b", folded(quote)
        )
    ):
        return None
    if update.present != bool(update.details):
        raise HealthUpdateError()
    changes = {update.field: update.present, PAIRS[update.field]: update.details}
    values = OnboardingDraftService.completion_data(record).model_dump()
    OnboardingCompletionData.model_validate({**values, **changes})
    if all(getattr(record, key) == value for key, value in changes.items()):
        return None
    return {
        "proposal": update.model_dump(),
        "before": health_values(record),
        "record_updated_at": utc(record.updated_at).isoformat(),
        "source_event_id": str(source.id),
    }


def confirmation_message(pending):
    update = HealthUpdate.model_validate(pending["proposal"])
    old = pending["before"].get(PAIRS[update.field]) or "nenhuma informação positiva"
    new = update.details if update.present else "nenhum relato atual nessa categoria"
    reason = {
        "corrected": "correção de uma informação anterior",
        "resolved": "problema anterior que você relata ter passado",
        "changed": "mudança na sua situação atual",
    }[update.kind]
    return (
        f"No cadastro, {LABELS[update.field]}: {old}.\n"
        f"Vou atualizar para: {new}. Motivo: {reason}.\n"
        "Confirma que essa é a informação completa e atual dessa categoria? "
        "Se ainda houver outra queixa ou informação, diga qual antes de confirmar."
    )


def apply_confirmed(session, client_id, source, pending):
    # Called after the shared client lock and domain-revision check, in the
    # same transaction as the successful chat reply and any draft proposal.
    if not confirmation(source.content):
        raise HealthUpdateError()
    if not pending_update(session, client_id, source, pending):
        raise HealthUpdateError("assistant_state_conflict", 409)
    update = HealthUpdate.model_validate(pending["proposal"])
    record = current_record(session, client_id)
    setattr(record, update.field, update.present)
    setattr(record, PAIRS[update.field], update.details)
    record.updated_at = datetime.now(UTC)
    OnboardingDraftService.completion_data(record)
    account_id = session.scalar(select(Client.account_id).where(Client.id == client_id))
    OnboardingDraftService._audit(
        session,
        record,
        ClientOnboardingScope(client_id, account_id),
        f"health_report_{update.kind}",
        (update.field, PAIRS[update.field]),
    )
