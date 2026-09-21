# Task 11 — Onboarding Completion

## Objective

Validate and atomically transition a sufficiently complete onboarding from editable draft to completed state.

## Requirements covered

- RF-13: CA-13.1–CA-13.3.

## Related rules and constraints

- RN-32: completion timestamps use the system-wide convention.
- RN-05/RN-11: completion must preserve client and health-data isolation.
- RNF01/RNF04: validation should be prompt and the state transition centralized/testable.
- DEC-06 is **blocking** for required fields, post-completion editability, and what constitutes a valid onboarding.

## Prerequisites

- Tasks 09 and 10 complete. Task 09 owns structured data and the form; Task 10
  adds the conversational interface over the same authoritative draft.
- Completion/editability decisions in DEC-06 recorded.

## Required reading

Read `AGENTS.md`; RF-13 and CA-13.1–CA-13.3; EXT-RF-AI-01 and
EXT-CA-AI-01.3/01.5/01.8; RN-05, RN-11, RN-32; RNF01, RNF04; DEC-06 and
DEC-19; RF-15/CA-15.1 only for the downstream validity contract;
`docs/requirements.md` sections 6, 8, 9.2, and 11.

## Scope

Implement shared server-side completeness validation, an atomic completed-state
transition with timestamp, frontend validation/confirmation states for both
approved entry experiences, and a stable application-level way for later AI
generation to determine whether a valid completed onboarding exists. The
backend derives client ownership from authenticated identity where the client
is logged in; the conversation and form cannot bypass the same validation.

## Out of scope

- AI calls or training generation (Task 13).
- Post-completion consultation (RF-14) or edit behavior beyond what DEC-06 explicitly approves.
- Adding onboarding fields not approved in Task 09 or treating chat text as the
  authoritative completed state.

## Acceptance criteria

- CA-13.1: missing required fields prevent completion and identify validation problems.
- CA-13.2: successful completion stores both state and date/time atomically.
- CA-13.3: downstream training logic can reliably identify an available valid onboarding without direct UI assumptions.

## Tests

Add completeness-domain tests, persistence/API integration tests for atomic transition and timestamp, authorization tests, and UI completion-state tests. Include incomplete and already-completed cases according to DEC-06. Run and report relevant tests.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/11-onboarding-completion.md`, then only the requirements and
extension sections/IDs listed under Required reading. Inspect the existing
repository before modifying files. Implement only this task across the shared
structured form/conversation state. Stop and ask if an unresolved DEC item
requires a material human decision. Run relevant tests, review the Git diff,
and provide the completion report required by `AGENTS.md` and this task. Do not
commit or push.
