# Task 05 — Client Profile and Status

## Objective

Allow authorized users to update basic client data and change the approved client lifecycle state while preserving history.

## Requirements covered

- RF-03: CA-03.1–CA-03.4.

## Related rules and constraints

- RN-02: inactive users cannot authenticate normally.
- RN-33: inactivation must preserve required historical relationships.
- RNF04: state rules belong in domain/application logic, not only the UI.
- DEC-05 is **blocking**: define active, enabled, biometric-ready, paid, and enrolled states and how CA-03.4 applies within an MVP that excludes RF-22.
- DEC-17 is **blocking before migrations** for lifecycle fields and historical relations.

## Prerequisites

- Task 04 complete.
- DEC-05 and the relevant client model portion of DEC-17 recorded.
- If CA-03.4 cannot be met without adding RF-22, stop and request an explicit scope decision; do not implement biometrics implicitly.

## Required reading

Read `AGENTS.md`; RF-03 and CA-03.1–CA-03.4; RN-02, RN-33; RNF04; DEC-05 and DEC-17; RF-22 only to understand the excluded biometric dependency; sections 8.2 and 10.

## Scope

Implement validated basic-profile updates and lifecycle transitions defined by DEC-05. Persist changes, integrate inactive status with authentication, and preserve linked history. Enforce backend authorization and expose the approved administrative UI.

## Out of scope

- Biometric enrollment or photo storage (RF-22).
- Payment/membership enablement (RF-31), physical-access decisions, or permanent deletion.
- Any guessed workaround for CA-03.4.

## Acceptance criteria

- CA-03.1: valid edits persist across page reloads.
- CA-03.2: a deactivated client is no longer treated as an enabled user under the approved state model.
- CA-03.3: deactivation preserves history.
- CA-03.4: enabled clients satisfy the approved biometric-photo rule; if DEC-05 leaves this unresolved, the task is blocked and must not claim completion.

## Tests

Add transition/domain tests, API persistence/authorization tests, authentication regression coverage for deactivated users, historical-integrity tests, and focused UI tests. Run all affected suites and report results.

## Completion requirements

- Verify every assigned CA, explicitly including or reporting the block on CA-03.4.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Subsequent approved dependency

This task remains complete for the approved reduced RF-03 scope, with CA-03.4
still pending. Task 06 must verify `account_active` against a provisioned client
identity while preserving DEC-05's separation from physical-entry eligibility;
it does not add biometric behavior here.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/05-client-profile-and-status.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision, especially DEC-05/CA-03.4. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
