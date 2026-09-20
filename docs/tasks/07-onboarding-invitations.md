# Task 07 — Onboarding Invitations

## Objective

Send and track client-bound onboarding invitations through the approved e-mail integration.

## Requirements covered

- RF-09: CA-09.1–CA-09.3.

## Related rules and constraints

- RN-23: tokens and sensitive client details must not appear unnecessarily in logs.
- RN-32: invitation and failure timestamps use the project-wide time convention.
- RNF01, RNF05, RNF06: show processing, isolate the e-mail provider behind an adapter, and return controlled failures.
- DEC-03 is **blocking** for SMTP/API selection and deployment implications. CA-06.4 belongs to non-MVP RF-06 and must not be silently imported, but its relationship to the shared e-mail infrastructure must be documented by the decision.
- DEC-06 is **blocking** for token lifetime, use/reuse policy, and link behavior.

## Prerequisites

- Tasks 03, 04, and 06 complete. A database client must not be assumed to have
  a usable Keycloak identity unless Task 06 provisioning succeeded or its
  explicit reconciliation path completed.
- E-mail direction in DEC-03 and invitation-token policy in DEC-06 recorded.

## Required reading

Read `AGENTS.md`; RF-09 and CA-09.1–CA-09.3; RN-23, RN-32; RNF01, RNF05, RNF06; TEC-09; DEC-03 and DEC-06; RF-06/CA-06.4 only for the shared-infrastructure boundary; sections 6.2 and 10.

## Scope

Implement an e-mail adapter contract, invitation creation/dispatch, a client-bound link, authorized trigger UI/API, and persisted delivery outcome. Make provider failures distinguishable from successful completion. Automated tests must replace the provider with a controlled fake.

This onboarding invitation is separate from Task 06's Keycloak first-access
required-action message. Do not treat one message, token, or delivery result as
proof that the other flow completed.

## Out of scope

- Rendering/accepting onboarding content (Tasks 08–10).
- Password recovery (RF-06), provider selection, or production e-mail account setup.
- Claiming delivery when only enqueueing/sending has failed.

## Acceptance criteria

- CA-09.1: triggering an invitation sends a message to the linked client e-mail through the adapter.
- CA-09.2: the message link identifies the intended client's onboarding without exposing unsafe identity data.
- CA-09.3: provider failure is recorded as failure, never completion.

## Tests

Add unit tests for invitation/token creation and provider outcome mapping, API authorization/integration tests, and UI state tests. Include successful and failed fake-provider scenarios. Run relevant tests and report results.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/07-onboarding-invitations.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
