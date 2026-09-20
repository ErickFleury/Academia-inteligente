# Task 13 — AI Assistant Chat

## Objective

Provide an isolated client chat that uses the current training sheet and, when approved/needed, that client's onboarding context, while handling AI outages safely.

## Requirements covered

- RF-18: CA-18.1–CA-18.4.

## Related rules and constraints

- RN-05/RN-29: conversations and AI context are strictly client-scoped.
- RN-16: chat responses cannot silently alter an approved sheet.
- RN-23: sensitive prompts/responses must not leak through logs.
- RN-30: responses are not medical diagnoses.
- RNF01, RNF05, RNF06: show processing, map failures cleanly, and use the AI adapter boundary.
- DEC-08 is **blocking** for chat request/response contracts, context rules, provider behavior, and error handling.
- DEC-07 is **non-blocking for read-only chat**; any detected change request remains inert until Task 14 and the approval flow exist.

## Prerequisites

- Tasks 11 and 12 complete.
- Chat-relevant DEC-08 decisions recorded.

## Required reading

Read `AGENTS.md`; RF-18 and CA-18.1–CA-18.4; RN-05, RN-16, RN-23, RN-29, RN-30; RNF01, RNF05, RNF06; DEC-07 and DEC-08; sections 4.1, 6.2, and 10.

## Scope

Implement authenticated message submission, the approved conversation persistence/retention behavior, safe context assembly, adapter invocation, and a responsive chat interface with processing and controlled-error states. Ensure this slice is read-only with respect to training versions.

## Out of scope

- Applying training changes (Task 14), medical diagnosis, provider selection, or broad chat features absent from RF-18.
- Cross-client/admin conversation browsing.
- Sending any unrelated client's onboarding, sheet, or messages to the adapter.

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

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/13-ai-assistant-chat.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
