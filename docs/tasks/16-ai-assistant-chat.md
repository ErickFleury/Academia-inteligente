# Task 16 — AI Assistant Chat

## Objective

Provide an isolated authenticated-client chat that uses the client's permitted
onboarding and training context, while handling AI outages safely.

## Requirements covered

- RF-18: CA-18.1–CA-18.4.

## Related rules and constraints

- RN-05/RN-29: conversations and AI context are strictly client-scoped.
- RN-16: chat responses cannot silently alter an approved sheet.
- RN-23: sensitive prompts/responses must not leak through logs.
- RN-30: responses are not medical diagnoses.
- RNF01, RNF05, RNF06: show processing, map failures cleanly, and use the AI adapter boundary.
- DEC-08 is **blocking** for chat request/response contracts, context rules, provider behavior, and error handling.
- DEC-07 is **non-blocking for read-only chat**; any detected change request remains inert until Task 17 and the approval flow exist.

## Prerequisites

- Tasks 06, 08, 14, and 15 complete. The caller must resolve through the Task 06
  Keycloak subject linkage; do not treat a database-only client as authenticated.
- Chat-relevant DEC-08 decisions recorded.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; RF-18 and CA-18.1–CA-18.4; RF-16/RF-17 for current/history boundaries; RF-32/RF-33 only to constrain optional future client-visible equipment context; RN-05, RN-16, RN-23, RN-29, RN-30; RNF01, RNF05, RNF06; DEC-07, DEC-08, DEC-18; `docs/requirements.md` sections 2.2, 3.1, 4.1, 7.1.1, 9.2, and 11.

## Scope

Implement authenticated message submission, approved conversation
persistence/retention, safe context assembly, adapter invocation, and a
responsive chat interface with processing and controlled-error states. Context
may include only functionally necessary permitted data from the authenticated
client's onboarding, current plan, and approved plan history. Client-visible
exercise/equipment information may be added only through an implemented,
authorized catalog contract; this task does not create that catalog. Ensure this
slice is read-only with respect to training versions.

Reuse Task 08 ClientShell and Task 11 chat conventions/components rather than an unrelated chatbot style. Distinguish user and assistant, keep message widths readable and input accessible, and show generating/error/retry states. Present plan context without overwhelming the conversation; check phone, tablet, and desktop.

## Out of scope

- Applying training changes (Task 17), medical diagnosis, provider selection, or broad chat features absent from RF-18.
- Cross-client/admin conversation browsing.
- Sending any unrelated client's onboarding, sheet, or messages to the adapter.
- Making Task 21 equipment functionality a prerequisite or inventing equipment
  data when its catalog has not been implemented.

## Acceptance criteria

- CA-18.1: an authenticated client sends a message and receives a successful adapter response.
- CA-18.2: only the current sheet and permitted onboarding context for that client are supplied when needed.
- CA-18.3: conversations/messages never appear in another client's context.
- CA-18.4: provider unavailability produces a controlled error and leaves training state unchanged.

## Tests

Use a fake AI adapter. Add successful chat, context-selection, cross-client isolation, unauthorized access, timeout/failure, sensitive-log, and “no training mutation” regression tests, plus focused UI state tests. Run and report results.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then `docs/tasks/16-ai-assistant-chat.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this authenticated client-facing chat, deriving the client from the Keycloak subject and limiting context to that client's permitted data. Follow `docs/frontend-design.md` and reuse Task 08 shell and Task 11 chat components; check phone, tablet, and desktop. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
