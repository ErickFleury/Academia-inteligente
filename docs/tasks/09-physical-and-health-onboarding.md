# Task 09 — Physical and Health Onboarding

## Objective

Capture and persist the approved physical and health onboarding fields with strict client isolation and role-based access.

## Requirements covered

- RF-11: CA-11.1–CA-11.3.
- RF-12: CA-12.1–CA-12.3.

## Related rules and constraints

- RN-05/RN-11: client isolation and need-to-know health access apply in UI and API.
- RN-23: medical details must not appear unnecessarily in logs.
- RN-29: persisted data must remain safely attributable for later client-scoped AI context.
- RNF02–RNF04: clear validation, responsive forms, and modular health/profile handling.
- DEC-04, DEC-06, DEC-17, and DEC-18 are **blocking** for access roles, exact fields/types/units/required status, model relationships, retention, and logging policy.

## Prerequisites

- Tasks 03 and 08 complete; Task 06 identity provisioning is inherited through
  the onboarding chain.
- Relevant resolutions for DEC-04, DEC-06, DEC-17, and DEC-18 recorded.

## Required reading

Read `AGENTS.md`; RF-11/RF-12 and CA-11.1–CA-12.3; EXT-RF-AI-01 only for the stable structured-data handoff to Task 10; RN-05, RN-11, RN-23, RN-29; RNF02–RNF04; DEC-04, DEC-06, DEC-17, DEC-18, DEC-19; `docs/requirements.md` sections 3.1, 4.1, 7.1, 9.2, and 11.

## Scope

Implement the approved onboarding schema, backend validation/persistence, draft retrieval while editable, and a responsive form with distinct physical, complaints, medications, and history/conditions areas. Enforce token/client binding and approved staff access at every endpoint.

Expose the same server-side field schema and validation as a reusable
application boundary for Task 10. Structured fields remain authoritative; this
task does not implement AI conversation behavior.

## Out of scope

- Choosing missing fields, units, validation ranges, or retention rules.
- Conversational onboarding (Task 10), completion (Task 11), post-completion
  self-review (RF-14), AI severity assessment, or training generation.
- Broad medical records or diagnosis functionality.

## Acceptance criteria

- CA-11.1: every approved physical field can be saved and retrieved.
- CA-11.2: approved required physical fields are validated clearly.
- CA-11.3: reopening an editable form restores the saved draft accurately.
- CA-12.1: clearly separated complaints, medications, and relevant history/condition inputs exist.
- CA-12.2: submitted health data belongs only to the intended client.
- CA-12.3: unauthorized UI and direct API access are denied.

## Tests

Add schema/validation unit tests, persistence and authorization integration tests, cross-client negative tests, logging-safety checks where practical, and focused responsive form tests. Run relevant suites and report results.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then `docs/tasks/09-physical-and-health-onboarding.md`, then only the requirements and extension sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task and provide the reusable authoritative structured schema/validation boundary needed by Task 10. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
