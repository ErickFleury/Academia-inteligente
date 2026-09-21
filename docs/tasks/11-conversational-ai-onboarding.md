# Task 11 — Conversational AI Onboarding

## Objective

Add an authenticated, resumable AI conversation that progressively gathers the
approved onboarding information and persists authoritative structured fields
without replacing the secure-link/form experience.

## Requirements covered

- EXT-RF-AI-01: EXT-CA-AI-01.1–EXT-CA-AI-01.8.
- RF-11/RF-12 criteria are integration-verified only for AI-to-structured-field
  mapping; Task 10 retains ownership of schema, validation, persistence, and
  health-data authorization.
- RF-13 remains owned by Task 12.

## Related rules and constraints

- RN-05/RN-11/RN-29: resolve the authenticated client server-side and isolate
  conversations, structured answers, and AI context absolutely.
- RN-23/RN-30: do not leak health/prompts in logs or present diagnosis.
- RNF01/RNF03/RNF05/RNF06: mobile-usable processing/resume states, controlled
  provider failures, and a replaceable AI adapter.
- DEC-06, DEC-08, and DEC-18 are **blocking** for schema/editability,
  conversation/AI contracts, and sensitive-data handling/retention.
- DEC-19 approves this extension but does not resolve those implementation
  decisions.
- Task 08 and `docs/frontend-design.md` govern the client chat and progress UI.

## Prerequisites

- Tasks 06, 08, and 10 complete; Tasks 07, 09, and 10 provide the coexisting
  secure-link/form path and the authoritative structured onboarding schema.
- Relevant DEC-06, DEC-08, and DEC-18 resolutions recorded. Stop if any missing
  decision would require inventing fields, medical rules, retention, or provider
  behavior.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; `docs/requirements.md` sections 1–4, 7.1.1, 8, 9.2, and 11;
`docs/product-extensions.md` EXT-RF-AI-01; RF-11–RF-13 and their CA; RN-05,
RN-11, RN-23, RN-29, RN-30; RNF01, RNF03, RNF05, RNF06; DEC-06, DEC-08,
DEC-18, and DEC-19.

## Scope

- Implement an authenticated own-client conversation/session and message flow
  behind the provider-independent AI adapter.
- Ask progressive questions only from the approved Task 10 schema and map
  validated answers into that client's structured onboarding draft.
- Preserve structured fields as authoritative. Ambiguous, missing, or invalid
  answers remain incomplete and are explained; chat text alone is insufficient.
- Support safe resume after navigation/re-authentication according to the
  approved retention policy and show processing/controlled failure states.
- Build the conversation from shared client/chat patterns: readable message
  width, clear sender distinction, persistent input, generating/error/retry
  states, and visible structured onboarding progress. Keep the form and chat
  visually coherent and fully usable on phone, tablet, and desktop.
- Reuse Task 10 validation and authorization rather than duplicating medical or
  field rules. Keep the Task 07 invitation/Task 09 link and Task 10 form usable.
- Expose a stable readiness result for Task 12, but do not mark onboarding
  complete in this task.

## Out of scope

- Inventing schema fields, diagnoses, health severity criteria, or completing
  onboarding/training generation.
- Replacing the secure-link/form flow.
- Cross-client or administrative conversation browsing, live-provider
  dependency in automated tests, or storing provider credentials in domain data.

## Acceptance criteria

- EXT-CA-AI-01.1–EXT-CA-AI-01.8 are verified.
- Direct API requests cannot select another client by supplying a client ID;
  ownership derives from the authenticated Keycloak subject linkage.
- A provider timeout/malformed response leaves prior structured values intact,
  reports a controlled failure, and allows safe resume/retry.
- Form edits and conversational answers use the same authoritative validation
  and produce a coherent draft without silent overwrites.

## Tests

Use a fake AI adapter. Add backend tests for identity resolution, progressive
question/answer mapping, structured validation, resume, conflict handling,
cross-client isolation, sensitive logging, malformed output, timeout, and
idempotent retry. Add frontend tests for mobile conversation, incomplete-field,
resume, processing, and controlled-error states. Integration-test coexistence
with the form and readiness handoff without a live AI provider.

## Completion requirements

- Verify all extension acceptance criteria and integration boundaries without
  claiming RF-13 completion.
- Document context selection, persistence/retention behavior, and form/chat
  conflict handling from the approved decisions.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests/results, important decisions, and unresolved
  issues. Do not commit or push unless explicitly requested.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/11-conversational-ai-onboarding.md`, then only the requirements and
extension sections/IDs listed under Required reading. Inspect the existing
repository before modifying files. Implement only this task, preserving the
secure-link/form onboarding path and structured data as authoritative. Follow
`docs/frontend-design.md` and reuse Task 08 shared shell/chat components; do
not create an independent chatbot style. Check phone, tablet, and desktop.
Stop and ask if DEC-06, DEC-08, DEC-18, or another unresolved item requires a
material human decision. Run relevant backend, frontend, and integration tests,
review the Git diff, and provide the required completion report. Do not commit
or push.
