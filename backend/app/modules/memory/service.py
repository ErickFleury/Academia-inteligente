"""Own-client memory, optimistic updates and source-bound conversational proposals."""

import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update

from app.modules.clients.models import Account, Client
from app.modules.memory.models import ClientMemoryFact

Category = Literal["health_report", "preference", "training_goal"]


class MemoryError(Exception):
    def __init__(self, code, status=409):
        super().__init__(code)
        self.code, self.status = code, status


class MemoryChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["add", "correct", "forget"]
    fact_id: UUID | None = None
    category: Category | None = None
    text: str | None = Field(default=None, min_length=1, max_length=400)
    evidence: str = Field(min_length=1, max_length=1000)


def normalized(value):
    return " ".join(value.split())


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class MemoryService:
    @staticmethod
    def client_id_for_subject(session, subject):
        client_id = session.scalar(
            select(Client.id)
            .join(Account)
            .where(
                Account.keycloak_subject == subject,
                Account.account_active.is_(True),
                Client.active.is_(True),
            )
        )
        if client_id is None:
            raise MemoryError("memory_client_not_found", 401)
        return client_id

    @staticmethod
    def snapshot(session, client_id):
        state = session.execute(
            select(Client.memory_revision, Client.memory_event_after).where(Client.id == client_id)
        ).first()
        if state is None:
            raise MemoryError("memory_client_not_found", 401)
        facts = session.scalars(
            select(ClientMemoryFact)
            .where(ClientMemoryFact.client_id == client_id)
            .order_by(ClientMemoryFact.reported_at, ClientMemoryFact.id)
            .execution_options(populate_existing=True)
        ).all()
        return {
            "revision": state.memory_revision,
            "event_after": state.memory_event_after,
            "facts": [
                {
                    "id": str(f.id),
                    "category": f.category,
                    "text": f.text,
                    "attribution": f.attribution,
                    "reported_at": utc(f.reported_at).isoformat(),
                    "updated_at": utc(f.updated_at).isoformat(),
                }
                for f in facts
            ],
        }

    @staticmethod
    def validate_revision(session, client_id, revision, *, event_after=None):
        values = {"memory_revision": Client.memory_revision + 1}
        if event_after is not None:
            values["memory_event_after"] = event_after
        changed = session.execute(
            update(Client)
            .where(Client.id == client_id, Client.memory_revision == revision)
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        if changed.rowcount != 1:
            raise MemoryError("memory_conflict")

    @staticmethod
    def _facts(session, client_id):
        return {
            str(f.id): f
            for f in session.scalars(
                select(ClientMemoryFact)
                .where(ClientMemoryFact.client_id == client_id)
                .execution_options(populate_existing=True)
            )
        }

    @staticmethod
    def _capacity(facts):
        if len(facts) > 50 or sum(len(f.text) for f in facts.values()) > 8000:
            raise MemoryError("memory_capacity")

    def edit(self, session, client_id, fact_id, revision, text=None):
        """Independent of model availability; the caller chooses correction or deletion."""
        now = datetime.now(UTC)
        with session.begin_nested():
            self.validate_revision(session, client_id, revision, event_after=now)
            facts = self._facts(session, client_id)
            fact = facts.get(str(fact_id))
            if fact is None:
                raise MemoryError("memory_not_found", 404)
            if text is None:
                session.delete(fact)
            else:
                value = normalized(text)
                if not value or len(value) > 400:
                    raise MemoryError("memory_invalid", 422)
                fact.text, fact.attribution = value, "client_edit"
                fact.updated_at, fact.reported_at, fact.source_event_id = now, now, None
                self._capacity(facts)
        session.commit()
        return self.snapshot(session, client_id)

    def apply(self, session, client_id, revision, changes, *, event_id, occurred_at, message):
        """Stage changes in the caller's transaction; rollback never leaves partial facts.

        Only whole, extractive first-person sentences from this new user event
        can become reports. No summaries or earlier chat messages are accepted.
        Evidence is validated in memory and is not persisted as a second quote.
        """
        if len(changes) > 10:
            raise MemoryError("memory_invalid", 422)
        with session.begin_nested():
            state = self.snapshot(session, client_id)
            if state["revision"] != revision:
                raise MemoryError("memory_conflict")
            if changes and state["event_after"] and utc(occurred_at) <= utc(state["event_after"]):
                raise MemoryError("memory_event_expired")
            self.validate_revision(
                session, client_id, revision, event_after=occurred_at if changes else None
            )
            facts = self._facts(session, client_id)
            sentences = {normalized(s) for s in re.split(r"(?<=[.!?])\s+|\n+", message.strip())}
            now = datetime.now(UTC)
            for change in changes:
                evidence = normalized(change.evidence)
                if evidence not in sentences:
                    raise MemoryError("memory_evidence_invalid", 422)
                fact = facts.get(str(change.fact_id)) if change.fact_id else None
                if change.action != "add" and fact is None:
                    raise MemoryError("memory_not_found", 404)
                if change.action == "forget":
                    if not re.match(
                        r"^(por favor[, ]+)?"
                        r"(esqueça|esqueca|apague|remova|não guarde|nao guarde)\b",
                        evidence,
                        re.I,
                    ):
                        raise MemoryError("memory_evidence_invalid", 422)
                    session.delete(fact)
                    del facts[str(fact.id)]
                    continue
                value = normalized(change.text or "")
                if value != evidence or not change.category or len(value) > 400:
                    raise MemoryError("memory_evidence_invalid", 422)
                if (
                    "?" in value
                    or re.search(
                        r"\b(talvez|acho que|poderia|se eu|não sei|nao sei)\b", value, re.I
                    )
                    or not re.match(
                        r"^(eu\s+)?(não\s+|nao\s+)?"
                        r"(tenho|prefiro|quero|gosto|sinto|estou|uso|busco|preciso|fui|"
                        r"meu objetivo|minha meta|minha preferência|minha rotina|meus treinos|"
                        r"minhas limitações|minha saúde)\b",
                        value,
                        re.I,
                    )
                ):
                    raise MemoryError("memory_evidence_uncertain", 422)
                if change.action == "add":
                    if change.fact_id is not None:
                        raise MemoryError("memory_invalid", 422)
                    if any(f.text.casefold() == value.casefold() for f in facts.values()):
                        continue
                    fact = ClientMemoryFact(client_id=client_id)
                    session.add(fact)
                    # Assign an ID before flush without exposing partially valid data.
                    fact.id = uuid4()
                    facts[str(fact.id)] = fact
                fact.text, fact.category, fact.attribution = value, change.category, "client_report"
                fact.source_event_id, fact.reported_at, fact.updated_at = event_id, occurred_at, now
            self._capacity(facts)
            session.flush()
