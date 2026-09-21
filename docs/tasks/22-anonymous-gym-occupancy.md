# Task 22 — Anonymous Gym Occupancy

## Objective

Implement the approved anonymous current-occupancy calculation and mobile client
display only after the relationship between access events and auxiliary camera
counts is decided.

## Requirements covered

- RF-23: CA-23.1–CA-23.4 where access events are part of the approved source.
- RF-24X: CA-24.1–CA-24.4.
- RF-25X: CA-25.1–CA-25.3.
- RN-37 is a related auxiliary-camera rule, not silently treated as equivalent
  to RF-24X.

## Related rules and constraints

- RN-04/RN-05/RN-23/RN-32: authorized event ingestion, client-safe responses,
  safe logging, and timestamps.
- RN-33: access history is not destructively rewritten.
- DEC-10 is **blocking** for occupancy source/meaning/display behavior.
- DEC-11 is **blocking** where RF-20/external events feed RF-23.

## Prerequisites

- Tasks 03, 06, and 08 complete; physical access/event prerequisites selected by the
  approved DEC-10/DEC-11 design are implemented.
- DEC-10 and applicable DEC-11 parts recorded. Stop if either source-of-truth or
  event contract remains materially unresolved.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; RF-20–RF-25X and their CA for boundaries; RN-04–RN-10,
RN-23, RN-32, RN-33, RN-35–RN-37; RNF01, RNF03–RNF06;
`docs/requirements.md` sections 3, 4.1, 7.1.1, 8.4, 9.2, and 11; DEC-02,
DEC-09–DEC-12, DEC-19.

## Scope

Implement only the approved idempotent attendance/occupancy inputs, non-negative
current anonymous count, failure/freshness behavior, authorized API, and mobile
client display. Keep aggregate occupancy independent from named presence.

Reuse Task 08 ClientShell and data-display/feedback patterns. Make the current count immediately readable with concise status/context, not a marketing card. Preserve a clear count-only boundary and check phone, tablet, and desktop.

## Out of scope

Named clients currently present (Task 23), opt-in preferences, inferred camera
identity, biometric algorithms, live equipment usage, or any unapproved
resolution of DEC-10.

## Acceptance criteria

- Applicable CA-23.1–CA-25.3 are verified under the approved source model.
- Duplicate input never double-counts and displayed count is never negative.
- The client view reveals a count only, no identity or sensitive detail.
- Auxiliary camera failure/source disagreement follows DEC-10 explicitly.

## Tests

Add domain/idempotency/concurrency, persistence/API, authorization/privacy,
source-failure/freshness, and mobile UI tests. Use test doubles for external
camera/access integrations.

## Completion requirements

Verify each assigned CA or report the precise approved exception, review the Git
diff, and report files changed, tests/results, decisions, and unresolved issues.
Do not commit or push.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/22-anonymous-gym-occupancy.md`, then only the requirements/decisions
listed under Required reading. Inspect the repository before editing. Implement
only anonymous occupancy. Follow `docs/frontend-design.md` and reuse Task 08
shared layout/components; check phone, tablet, and desktop. Stop and ask if DEC-10, applicable DEC-11 behavior, or
another unresolved item requires a material human decision. Run relevant tests,
review the Git diff, and provide the required completion report. Do not commit
or push.
