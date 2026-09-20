# Task 10 — Training Version Lifecycle

## Objective

Establish the approved training-sheet lifecycle, immutable version history, current-version selection, and professional responsibility metadata before connecting AI workflows.

## Requirements covered

- RF-17: CA-17.1–CA-17.3. This task owns versioning behavior; Tasks 11 and 14 integrate with it without reimplementing it.

## Related rules and constraints

- RN-12/RN-14: instructor review and full modification must follow the approved flow.
- RN-16/RN-17: AI cannot silently alter an approved sheet; proposed changes create a proposal/new version.
- RN-18: updates cannot retroactively alter completed training history.
- RN-19: the model must not prevent the approved manual path when AI is unavailable.
- RN-31–RN-33: preserve professional responsibility, timestamps, and historical relationships.
- DEC-04, DEC-07, DEC-15, and DEC-17 are **blocking** for professional identity, lifecycle states, manual/review scope, and model relationships.
- DEC-08 is **non-blocking** because the lifecycle must remain provider-independent.

## Prerequisites

- Tasks 03 and 09 complete.
- Relevant resolutions for DEC-04, DEC-07, DEC-15, and DEC-17 recorded.

## Required reading

Read `AGENTS.md`; RF-17 and CA-17.1–CA-17.3; RN-12, RN-14, RN-16–RN-19, RN-31–RN-33; RNF04; DEC-04, DEC-07, DEC-15, DEC-17; sections 7.1, 8.2, and 10.

## Scope

Implement training-sheet/version persistence and application services for initial version creation, subsequent version creation, current-version changes, immutable history, and responsible-professional attribution as approved. Provide test seams for AI/manual callers; expose only endpoints/UI explicitly required by the approved review lifecycle.

## Out of scope

- Calling AI (Tasks 11, 13, 14), current client display (Task 12), exercise catalog CRUD, or completed-workout tracking.
- Inventing approval states, manual authoring UI, or professional permissions.
- Mutating an existing historical version in place.

## Acceptance criteria

- CA-17.1: initial creation produces version one through the lifecycle service.
- CA-17.2: an approved/effectivated change creates a later version and makes it current.
- CA-17.3: the current version and history persist across reload/restart.
- RN-18/RN-31 behavior is demonstrable with historical fixtures and responsibility metadata.

## Tests

Add domain tests for transitions/invariants, persistence tests for ordering/current uniqueness/immutability, authorization tests for approved actors, and concurrency/transaction tests where current-version races are possible. Run relevant tests and report results.

## Completion requirements

- Verify every assigned CA.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/10-training-version-lifecycle.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
