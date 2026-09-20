# Task 02 — Authentication

## Objective

Implement the authentication vertical slice for active MVP users and enforce unauthenticated behavior on protected routes.

## Requirements covered

- RF-04: CA-04.1, CA-04.2, and CA-04.3.

## Related rules and constraints

- RN-02: inactive users cannot authenticate normally.
- RN-04: protected operations must use authenticated identity.
- RN-23: credentials, tokens, and sensitive details must not leak to logs.
- RN-32: session-related timestamps use one consistent convention.
- RNF01, RNF04, RNF05: responsive, modular authentication that does not make independent behavior depend on external outages.
- DEC-03, DEC-04, and DEC-05 are **blocking**: auth mechanism, initial account provisioning/roles, and the meaning of active versus enabled must be resolved.

## Prerequisites

- Task 01 complete.
- Blocking decisions DEC-03, DEC-04, and the authentication-relevant part of DEC-05 recorded.

## Required reading

Read `AGENTS.md`; RF-04 and CA-04.1–CA-04.3; RN-02, RN-04, RN-23, RN-32; RNF01, RNF04, RNF05; DEC-03–DEC-05; sections 6.2 and 10.

## Scope

Implement the selected authentication mechanism across backend and the minimum frontend session flow. Validate credentials, represent authenticated identity, reject invalid credentials, protect designated API/UI routes, and handle inactive accounts according to the approved state model. Add no role-specific business permission beyond what authentication needs.

## Out of scope

- Authorization policy implementation (Task 03).
- Client CRUD, employee CRUD, password recovery (RF-06), and biometric/membership access.
- Selecting Keycloak versus integrated auth in this task.

## Acceptance criteria

- CA-04.1: valid credentials for an active user start a usable authenticated session.
- CA-04.2: invalid credentials create no session and return a controlled failure.
- CA-04.3: protected UI/API routes without a valid session return an unauthenticated state.
- RN-02 is verified for inactive accounts.

## Tests

Add unit/integration tests for valid, invalid, expired/absent session, inactive-user, and protected-route cases. Do not require a live third-party identity service in automated tests. Run relevant frontend/backend tests and report results.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/02-authentication.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
