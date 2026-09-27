# Task 36 — Equipment-Aware Training Usability

## Status

Implemented (2026-09-27). Depends on Tasks 31, 33, and 35.

Verification: targeted lifecycle/generation/adaptation/chat/review/equipment,
current-plan API, collection/authoring, and fake-adapter suites pass. Fifteen
shared-editor/workspace/current-view frontend tests pass. Four PostgreSQL tests
cover the existing item migration/round trip and approval racing an outage,
unit deactivation, or model deactivation; the three review race regressions also
pass. Production build, scoped Ruff, and Git whitespace checks pass. Synthetic
Firefox checks cover 360×800, 768×1024, and 1366×768, including editor focus
clearance below the mobile header and no horizontal overflow.

Task 31 already supplied the nullable canonical item columns in migration 22;
no duplicate migration or new dependency was needed. One equipment-domain query
now supplies bounded UUID/name context and paginated instructor choices. Ordered
model locks synchronize all inventory writers with validation immediately before
training persistence/approval. Only exact unchanged approved items, including
their original multiplicity, qualify for historical preservation. Saved new
draft items and retained adaptation candidates receive no blanket exemption.
The shared AI draft-edit schema/context was updated as a necessary dependency.
Current/history snapshots remain read-only. No unresolved Task 36 issues.

## Objective

Make the approved active-and-operational equipment boundary authoritative for
new machine-dependent plan content across initial AI generation, adaptation,
manual authoring, draft editing, and approval, while retaining current and
historical plans unchanged.

## Requirements covered

- EXT-RF-INST-05: EXT-CA-INST-05.4–EXT-CA-INST-05.6.
- RF-15, RF-17, and RF-19 integration only for equipment references/usability.
- EXT-RF-EQP-01 and Task 25 as consumed catalog boundaries.
- RN-12–RN-20, RN-31–RN-33, DEC-07, DEC-08, DEC-15, and DEC-18.

## Required reading

Read `AGENTS.md`, this task, and only: `docs/requirements.md` RF-15, RF-17,
RF-19, RF-32, RF-33, EXT-RF-EQP-01, EXT-RF-INST-02,
EXT-RF-INST-03, EXT-RF-INST-05, RN-04, RN-05, RN-12–RN-20,
RN-29–RN-33, RNF01, RNF04–RNF06, DEC-07, DEC-08, DEC-15,
DEC-18, EXT-DEC-EQP-01, EXT-DEC-INST-01; Tasks 14, 17, 25, 31, 33,
and 35 plus current generation/adaptation/lifecycle provider contracts and
tests; `docs/frontend-design.md` training/review/forms guidance.

## Exact implementation scope

- Extend canonical TrainingPlanItem input/persistence with nullable
  `equipment_model_id` and human-readable equipment requirement/snapshot,
  following Task 25's validated EquipmentModel identity pattern. Existing rows
  remain valid as equipment-free/legacy content. Model rename/deactivation or
  operational changes never rewrite retained item history.
- Treat a genuinely equipment-free item as nullable. New or user-modified
  machine-dependent content with a non-empty equipment requirement must carry a
  canonical model reference currently returned by Task 35's active-and-
  operational usable-model query. Validate server-side immediately before
  persistence/approval; frontend/provider claims are not authority.
- Initial AI generation receives only bounded usable model UUID/name pairs and
  returns the nullable canonical reference for machine-dependent items. Reject
  malformed, missing, unknown, inactive, zero-active-unit, or all-out-of-order
  references atomically, with no draft/current mutation. Use fake providers.
- Change Task 25 adaptation context and validation from merely active units to
  active-and-operational units for newly proposed candidates. Preserve the
  existing exception for unchanged carried-forward historical items so an
  outage/deactivation does not rewrite or silently drop unrelated current
  content.
- Manual creation and instructor draft editing use the same usable-model
  service and selectors. Revalidate new/changed machine-dependent items at save
  and explicit approval to catch state changes after the page loaded. An
  unusable choice produces controlled pt-BR feedback and leaves the current
  plan untouched.
- Show retained unavailable model snapshots read-only in current/history and
  copied unchanged items. Do not label them available/free or automatically
  substitute another machine. New choices list only usable models.
- Keep adapter context minimal: model UUID/name only, no unit IDs/labels,
  operational details, inventory metadata, or live-use claims.

## Boundaries

- Do not add exercise catalog CRUD, automatic substitutions, maintenance,
  reservations, occupancy, telemetry, camera data, or real-time availability.
- Do not invalidate, rewrite, or remove existing current/history solely because
  equipment later becomes inactive or out of order.
- Do not allow AI to approve or activate.

## Acceptance criteria and tests

Test plan-item migration/round trip; equipment-free items; initial-generation
usable context; adaptation usable context; manual/editor selectors; server-side
save/approval revalidation; operational-to-out-of-order race; unknown/inactive/
zero-unit/all-out-of-order rejection with atomicity; unchanged retained item
preservation; rename snapshot/canonical link; later state change without
history mutation; minimized provider context; no-live-availability wording;
and regressions for single draft, concurrency, and explicit instructor approval.

Run targeted equipment/training backend/frontend tests,
`git diff --check`, and `git status --short`; inspect for historical rewrites or
duplicated catalog logic.

## Completion requirements

Update only relevant status documentation after verification. Report files,
tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/36-equipment-aware-training-usability.md`, then only its Required
reading. Inspect Tasks 25/31/33/35 and every training item/provider contract
before editing. Implement only canonical equipment references on plan items and
active-and-operational usability for new/changed initial, adaptation, manual,
edit, and approval content. Preserve unchanged current/history and never imply
live availability. Use fake providers, run targeted regression tests, review
the diff, and provide the required completion report. Do not commit or push.
