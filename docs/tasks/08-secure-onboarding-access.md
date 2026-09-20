# Task 08 — Secure Onboarding Access

## Objective

Validate invitation tokens and open only the onboarding associated with the intended client.

## Requirements covered

- RF-10: CA-10.1–CA-10.3.

## Related rules and constraints

- RN-05: a client may access only their own context.
- RN-23: raw tokens and health-related context must not leak into logs.
- RN-32: token expiry and use timestamps follow the shared time convention.
- RNF01–RNF03: validation feedback and the entry page remain prompt, understandable, and responsive.
- DEC-06 is **blocking** for validity period, reuse/consumption rules, and editability window.

## Prerequisites

- Task 07 complete; Task 06 identity provisioning is inherited through it.
- Invitation-token decisions in DEC-06 recorded.

## Required reading

Read `AGENTS.md`; RF-10 and CA-10.1–CA-10.3; RN-05, RN-23, RN-32; RNF01–RNF03; DEC-06; sections 4.1 and 10.

## Scope

Implement token validation and client/onboarding scoping at the backend plus the minimum frontend entry states for valid, invalid, and expired links. Apply the approved use/reuse semantics and avoid exposing whether unrelated clients exist.

## Out of scope

- Physical or health form fields (Task 09) and completion (Task 10).
- General authentication/password recovery.
- Inventing token lifetimes or post-completion edit behavior.

## Acceptance criteria

- CA-10.1: a valid token opens the corresponding onboarding entry state.
- CA-10.2: invalid and expired tokens are rejected with a controlled response.
- CA-10.3: a token cannot retrieve or mutate another client's onboarding.

## Tests

Add token validation unit tests and API/UI integration cases for valid, malformed, expired, reused (as defined), and cross-client attempts. Avoid real e-mail services. Run the relevant tests and report results.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/08-secure-onboarding-access.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
