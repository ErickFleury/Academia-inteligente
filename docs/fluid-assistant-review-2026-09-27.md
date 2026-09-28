# Fluid assistant implementation review — 2026-09-27

Scope: EXT-RF-AI-01, RF-11–13 and RF-18–19, with the owner-approved fluid
assistant amendment in requirements.md. No model, dependency or schema migration.

## Onboarding checkpoint

Each client message is extracted into expiring interview working state in the
existing conversation summary column. Only supported current-message facts are
merged. Explicit measurements also have conservative source-based normalization;
unknown, negated and target measurements are not current measurements. Other
answers survive short model context windows, reloads and targeted corrections.
Conflicting values require confirmation; ambiguous corrections ask for the field.
The screen displays collected answers and permits corrections until completion.
The authoritative draft is written only when all required answers are verified;
completion remains a separate explicit client action. Form edits take precedence.

A client row lock serializes chat/form writes, and the working state/reply commit
together. A failed provider call retains the original message for retry but does
not change verified answers. Concurrent duplicate requests are idempotent. The
existing five-day interview retention also applies to working state; authoritative
form answers remain subject to their existing lifecycle.

Validation: full backend suite passed (448 tests at the initial checkpoint),
plus additional targeted measurement and real PostgreSQL concurrency tests.
Frontend suite: 202 passed, two authentication tests initially inherited LAN OIDC
settings; both passed with the expected localhost OIDC settings (33 targeted
app/onboarding tests). Production frontend build passed. Existing large-bundle
warning remains. No unrelated formatting changes were made.

A synthetic local Ollama check exposed an unreliable weight correction; direct
source normalization was added so this explicit case does not rely on the model.
Automated tests use fake providers and never require live AI. Real client data
was not modified. Free-form interpretation remains model-dependent; unsupported
answers stay unfilled or require clarification rather than being guessed.

Final onboarding targeted run: 72 passed. The local Ollama synthetic multi-fact
and negated-old-weight correction checks both passed after normalization.

## Training assistant checkpoint

Older context now contains bounded, whole client statements with timestamps,
rebuilt from retained messages. It never treats assistant suggestions as reported
client facts or recursively summarizes generated summaries. Recent corrections
take precedence in the prompt; ambiguous or missing context asks for clarification.
Long statements are omitted whole when they cannot fit, so truncation cannot
remove a negation or revive a superseded older claim. Health-related follow-ups
can use recent client context while completed onboarding remains immutable.
Expired statements also invalidate cached summaries in active conversations.

A conservative Portuguese request check permits draft writes only for explicit
training-change requests or a direct confirmation of a preceding draft question.
Advice questions, personal-data corrections and problem reports alone do not
permit edits. Unrecognized requests may require clearer wording; this is not a
semantic proof of intent. Equipment/content validation, single-proposal selection,
revision checks and instructor approval remain in force. Successful draft changes
and their controlled Portuguese confirmation commit in one transaction. Common
unsupported model claims of saved changes are replaced with accurate feedback;
arbitrary generated prose is still model-dependent.

Chat requests are serialized per client. Retries retain their original message;
older failed requests cannot be replayed over newer turns. Frontend changes keep
multiline composition, expose initial-load errors and explain the draft boundary.

Validation: full backend run passed 471 tests including PostgreSQL integration;
after tightening advice/request distinction, 61 relevant tests passed (including
three additional request cases). Training-chat UI: five tests and production build
passed. Synthetic local Ollama preserved a morning preference while correcting
three training days to two, and returned no draft mutation. No live client data,
model version, dependencies, database schema or Keycloak configuration changed.

Final onboarding review additionally covered “acho que”/“pode ser” uncertainty
about existing values: readiness is blocked without erasing other answers, and
“I don't remember” keeps an already focused clarification on the same field.
The 48-test onboarding/evidence run passed; this follow-up is checkpoint c964d97.

Final frontend regression run: all 206 tests across 33 files passed with isolated
localhost API/OIDC settings. The build had already passed after the final frontend
changes. Existing Vite bundle-size warning remains; no unrelated bundle work was
included. No unresolved implementation blockers. Conversational interpretation
and response wording remain model-dependent, bounded by the validation described
above; these checks do not establish perfect natural-language understanding.

Changed areas: backend onboarding evidence/state/orchestration, draft and response
contracts; AI adapter prompts; training chat context/orchestration and transactional
revision support; both frontend conversation pages and onboarding API types;
regression/concurrency tests; canonical/supporting requirements and this report.
