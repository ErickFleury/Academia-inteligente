# Task 03 — Authorization

## Objective

Enforce the approved MVP permissions in both interface navigation and backend APIs.

## Requirements covered

- RF-05: CA-05.1, CA-05.2, and CA-05.3.

## Related rules and constraints

- RN-04/RN-05: authorize every protected operation and isolate each client's data.
- RN-11: health data is restricted to roles with a defined functional need.
- RN-23/RN-29: avoid sensitive logging and cross-client AI context.
- RNF04: centralize permission logic rather than duplicating it across controllers/components.
- DEC-04 is **blocking**: the role/permission matrix, employee subprofiles, professional equivalence, and provisioning must be approved.
- DEC-18 is **non-blocking for the authorization mechanism**, but its health-data permissions must be resolved before Task 10.

## Prerequisites

- Task 02 complete.
- Approved DEC-04 role and permission matrix.

## Required reading

Read `AGENTS.md`; RF-05 and CA-05.1–CA-05.3; RN-04, RN-05, RN-11, RN-23, RN-29; RNF04; DEC-04 and DEC-18; sections 2, 4.1, and 10.

## Scope

Implement reusable backend guards/policies and corresponding frontend visibility/navigation for the approved MVP roles. Deny direct API access independently of frontend controls. Provide test identities/fixtures only through the approved provisioning method.

## Out of scope

- Inventing permissions for unresolved employee subprofiles.
- Employee management (RF-07/RF-08), audit/export flows, or any domain operation from later tasks.
- Treating hidden UI controls as sufficient authorization.

## Acceptance criteria

- CA-05.1: a client cannot access administrative capabilities.
- CA-05.2: an administrator can access the approved MVP administrative operations.
- CA-05.3: direct calls to forbidden APIs are rejected even when the UI is bypassed.

## Tests

Add policy/guard unit tests and API integration tests covering allow/deny cases for each approved MVP role, plus frontend visibility tests where applicable. Run them and report exact results.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Subsequent approved dependency

This task remains complete under its original scope. Task 06 must assign a
newly provisioned identity only the `client` role and re-run CA-05.1/CA-05.3
against administrative APIs; that integration evidence is not retroactively
claimed here.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/03-authorization.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
