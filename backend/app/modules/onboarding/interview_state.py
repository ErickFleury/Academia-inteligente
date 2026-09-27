"""Bounded, expiring interview memory; never an alternative completion contract."""

import json
import re
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.modules.onboarding.answer_evidence import (
    _DETAILS,
    _normalize,
    _topic_fields,
    measurement_values,
)
from app.modules.onboarding.models import Onboarding
from app.modules.onboarding.schema import OnboardingDraftUpdate

FIELDS = tuple(OnboardingDraftUpdate.model_fields)
CORRECTION = (
    r"\b(corrig\w*|correcao|na verdade|errei|errad[oa]|enganei|quis dizer|o correto|atualiz\w*)\b"
)
UNKNOWN = r"\b(nao sei|nao lembro|nao tenho certeza|talvez)\b"


def draft_values(onboarding: Onboarding) -> OnboardingDraftUpdate:
    return OnboardingDraftUpdate(**{name: getattr(onboarding, name) for name in FIELDS})


@dataclass
class InterviewState:
    answers: OnboardingDraftUpdate
    baseline: OnboardingDraftUpdate
    pending: list[str] = field(default_factory=list)
    needs_target: bool = False
    last_sequence: int = 0

    @classmethod
    def load(cls, raw: str | None, onboarding: Onboarding):
        current = draft_values(onboarding)
        if onboarding.status == "completed":
            return cls(current, current)
        try:
            data = json.loads(raw or "{}")
            if not isinstance(data, dict) or data.get("version") != 1:
                return cls(current, current)
            answers = OnboardingDraftUpdate.model_validate(data["answers"])
            baseline = OnboardingDraftUpdate.model_validate(data["baseline"])
            pending = [name for name in data.get("pending", []) if name in FIELDS]
            # Manual form edits always win over stale interview memory, including clears.
            values = answers.model_dump()
            for name in FIELDS:
                if getattr(current, name) != getattr(baseline, name):
                    values[name] = getattr(current, name)
                    pending = [item for item in pending if item != name]
            return cls(
                OnboardingDraftUpdate(**values),
                current,
                pending,
                bool(data.get("needs_target")),
                int(data.get("last_sequence", 0)),
            )
        except (ValueError, TypeError, KeyError, ValidationError):
            return cls(current, current)

    def dump(self) -> str:
        return json.dumps(
            {
                "version": 1,
                "answers": self.answers.model_dump(mode="json"),
                "baseline": self.baseline.model_dump(mode="json"),
                "pending": self.pending,
                "needs_target": self.needs_target,
                "last_sequence": self.last_sequence,
            },
            ensure_ascii=False,
        )

    def merge(
        self,
        candidate: OnboardingDraftUpdate,
        message: str,
        sequence: int,
        accepted: set[str],
    ) -> list[str]:
        text = _normalize(message)
        correction = bool(re.search(CORRECTION, text))
        topics = _topic_fields(text)
        previous = self.answers.model_dump()
        proposed = candidate.model_dump()
        changed = []
        blocked = set()
        for name in FIELDS:
            if name in _DETAILS and _DETAILS[name] in blocked:
                continue
            old, new = previous[name], proposed[name]
            if new == old:
                if name in accepted:
                    self.pending = [item for item in self.pending if item != name]
                continue
            if old is not None and new is not None and not correction and name not in self.pending:
                self.pending = list(dict.fromkeys([*self.pending, name]))
                blocked.add(name)
                continue
            previous[name] = new
            changed.append(name)
            self.pending = [item for item in self.pending if item != name]
        if correction:
            unresolved = topics - accepted
            self.pending = list(dict.fromkeys([*self.pending, *sorted(unresolved)]))
            if not topics and not changed:
                self.needs_target = True
        if re.search(UNKNOWN, text):
            if not topics:
                self.needs_target = True
            self.pending = list(dict.fromkeys([*self.pending, *sorted(topics)]))
        for name in ("height_cm", "weight_kg"):
            if len(measurement_values(name, message)) > 1:
                self.pending = list(dict.fromkeys([*self.pending, name]))
        if self.needs_target and topics:
            self.pending = list(dict.fromkeys([*self.pending, *sorted(topics - set(changed))]))
            self.needs_target = False
        if changed:
            self.needs_target = False
        self.answers = OnboardingDraftUpdate(**previous)
        self.last_sequence = sequence
        return changed
