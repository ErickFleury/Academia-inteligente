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
