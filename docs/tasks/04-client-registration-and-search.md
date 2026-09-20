# Task 04 — Client Registration and Search

## Objective

Deliver the administrator-facing slice for creating clients and listing/searching them by name or e-mail.

## Requirements covered

- RF-01: CA-01.1–CA-01.3.
- RF-02: CA-02.1–CA-02.3.

## Related rules and constraints

- RN-01: enforce the approved unique identity rule.
- RN-04/RN-05: only authorized users may access third-party client data.
- RN-23/RN-32: safe logs and consistent timestamps.
- RNF01–RNF04: prompt, usable, responsive, modular forms and lists.
- DEC-04 is **blocking** for which administrative profiles may operate this slice.
- DEC-17 is **blocking before client migrations** for client/account identifiers and relationships.
- DEC-05 is **non-blocking** if this task avoids activation/habilitation transitions; do not assume their semantics.

## Prerequisites

- Tasks 01, 02, and 03 complete.
- Client-slice decisions from DEC-04 and DEC-17 recorded.

## Required reading

Read `AGENTS.md`; RF-01/RF-02 and CA-01.1–CA-02.3; RN-01, RN-04, RN-05, RN-23, RN-32; RNF01–RNF04; DEC-04, DEC-05, DEC-17; sections 7.1 and 10.

## Scope

Implement client persistence, validated creation, unique active-account e-mail handling, administrative list/detail access, and name/e-mail search through the agreed backend API and responsive frontend. Make creation atomic so validation failures leave no partial client/account record.

## Out of scope

- Updating or changing client state (Task 05).
- Biometric photo, onboarding invitation, employee management, payment, or membership.
- Defining active versus enabled behavior from DEC-05.

## Acceptance criteria

- CA-01.1: valid required fields create a client with a unique identifier.
- CA-01.2: an e-mail already linked to another active account is rejected.
- CA-01.3: invalid fields return clear validation and persist nothing partial.
- CA-02.1/CA-02.2: authorized administrators can list and search by name/e-mail.
- CA-02.3: unauthorized users cannot retrieve third-party client data through UI or API.

## Tests

Add domain/validation tests, persistence/API integration tests for atomicity and uniqueness, authorization tests, and focused UI tests for forms/search/responsive states. Run the relevant suites and report results.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/04-client-registration-and-search.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
