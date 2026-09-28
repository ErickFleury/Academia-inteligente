# AI onboarding premature readiness — investigation and repair

Scope: EXT-RF-AI-01, RF-11–RF-13 and the dependent RF-15 prerequisite;
EXT-CA-AI-01.2/.3/.5/.6/.7, CA-13.1/.2, RN-11/29/30 and RNF04/06.
DEC-06/08/18 retain the schema, separate final extraction, explicit completion,
client isolation and five-day raw-conversation retention rules.

## Finding

The owner-identified conversation contained a greeting and one objective answer.
The assistant then claimed readiness and populated all required physical/training
and health fields. The audit showed one draft save for every schema field. The
record remained `draft`, with no completion timestamp: the assistant's readiness
claim was premature, but the explicit completion endpoint had not been called.
No personal identifiers, message content or health values are reproduced here.

The backend previously accepted the provider's `ready` signal followed by any
schema-valid complete extraction. Type/range validation did not establish that
values came from the client. The extraction schema also required non-null physical
and boolean values, and its context duplicated the current user message and
included the unverified current assistant reply.

## Correction

- Missing extracted answers can be null; silence is never a negative health answer.
- New extracted values require a retained, same-conversation client-message
  sequence and literal source quote. Assistant claims and fabricated citations
  cannot supply facts. Citations are transient and are not added to the health
  record, audit logs or long-term storage.
- Source checks verify measurements/units, literal free text and explicit
  categories. Fixed experience/health categories follow verified client words,
  even if the provider labels them incorrectly. Surrounding client text prevents
  dropping a negation or treating a target weight as a reported current weight.
- Short answers apply only to the matching preceding question. Unsupported or
  ambiguous information stays incomplete and triggers one clarification question.
- Failed/incomplete extraction leaves the authoritative draft unchanged. Only a
  fully grounded, schema-valid extraction writes it atomically. It remains a draft
  until the client explicitly reviews and completes it through the existing flow.
- Extraction receives the bounded retained transcript once, with stable sequence
  references; it does not receive a synthetic duplicate user message or the current
  unverified assistant reply. Retries use the original persisted user message.
- A cached readiness reply cannot override a subsequently incomplete draft.

No new dependency, database migration, provider/model switch, frontend feature or
training-plan mutation is introduced. Conservative checks can request clarification
for wording they cannot establish confidently; the existing form remains available.

## Verification

Regression coverage includes objective-only fabricated completion, invented quotes,
assistant-sourced facts, unknown health answers, question-specific short answers,
unit normalization, negation/target measurements, source/category disagreement,
existing form reuse, idempotent retry bodies, stale cached readiness and a seven-answer
interview with a provider that prematurely claims readiness on every turn. The API
regression verifies that unsupported extraction cannot unlock `/onboarding/me/completion`.

Final validation: **442 backend tests passed**, including PostgreSQL integration.
Repository-wide Ruff lint passed; format checks passed for all eight changed
Python files. The broader format check also identified pre-existing formatting
in `scripts/biometric_preflight.py`, `tests/test_admin_dashboard.py` and
`tests/test_onboarding_drafts.py`; those unrelated files were left unchanged.
Git whitespace validation passed. No frontend code changed.

Manual, synthetic checks against the configured local Ollama provider confirmed
that an objective-only message stays incomplete and a complete explicit example
can become ready with the client's actual categories preserved. An intermediate
check exposed a model category mismatch despite a correct quote; the final source
normalization handles that case. These smoke checks wrote no client data and did
not call an external AI provider.

## Owner-authorized data repair

After the owner explicitly approved repairing the identified draft, the backend
was restarted to load the fix. A transaction verified that the draft was still
editable and that neither its original four messages nor its audit history had
changed since inspection. It preserved the objective directly from the client's
answer, cleared unsupported fields, retained the original messages, appended a
Portuguese correction and resumed with the experience question. A non-sensitive
`owner_authorized_ai_draft_repair` audit event records the operation. The record
remains a draft, cannot satisfy the training-generation prerequisite, and has no
completion timestamp. No account, plan or other client's record was reset.

The owner can refresh the assistant page and continue. Existing ambiguous wording
may need clarification or correction through the form; AI readiness still cannot
replace the client's explicit final review/completion.
