# Task 35 — Equipment Operational State

## Status

Implemented (2026-09-27). Depends on Tasks 21, 29, and 30.

Verification: eleven equipment backend tests, two PostgreSQL migration/concurrency
tests, and four frontend tests pass. Production build, Ruff, and Git whitespace
checks pass. Synthetic Firefox checks cover 360×800, 768×1024, and 1366×768
without horizontal overflow. Migration 20260927_25 applied successfully.

Operational state is independent of inventory activation and quantity. Instructor
APIs expose bounded model/unit reads and a revision-checked state mutation only;
existing inventory administration authorization remains unchanged. The reusable
usable-model query is ready for Task 36. No live-use semantics or new dependencies
were introduced. No unresolved Task 35 issues.

## Objective

Add the independent operational/out-of-order state for physical equipment units
and the instructor Equipamentos page, while preserving inventory-active counts
and forbidding general inventory administration.

## Requirements covered

- EXT-RF-INST-05: EXT-CA-INST-05.1–EXT-CA-INST-05.3 and authorization/no-live-
  availability portions of EXT-CA-INST-05.6.
- RF-32/RF-33 and EXT-RF-EQP-01 only as existing inventory/catalog behavior
  that must remain unchanged.
- EXT-RF-LANG-01.

## Required reading

Read `AGENTS.md`, this task, and only: `docs/requirements.md` RF-32, RF-33,
EXT-RF-EQP-01, EXT-RF-INST-05, RN-04, RN-05, RN-20, RN-33,
RNF01–RNF04, EXT-DEC-EQP-01, EXT-DEC-INST-01, sections 2.1, 7.1.1,
and 7.3; `docs/instructor-role-specification.md` sections 12, 14, and 16.7;
Tasks 21, 29, and 30 plus current equipment migrations/services/APIs/admin and
catalog UIs/tests; `docs/frontend-design.md` shared shell, equipment, responsive,
status, and accessibility guidance.

## Exact implementation scope

- Add a required EquipmentUnit operational state constrained to `operational`
  or `out_of_order`, independent of its existing inventory `active` flag. Set
  existing/development units to `operational` through the migration; do not
  reinterpret or rename `active`.
- Keep RF-32/EXT-RF-EQP-01 `active_quantity` exactly as the count of inventory-
  active units for an active model, regardless of operational state. Public/
  client catalog behavior and wording remain total active inventory, never
  free/available-now inventory.
- Add focused equipment service queries for active models with their units and
  for models having at least one unit that is both active and operational.
  The latter is a reusable training-usability boundary for Task 36, not a new
  mutable aggregate/counter.
- Add instructor-only bounded read APIs and a mutation that changes only one
  unit's operational state. Resolve active local Employee plus Keycloak role.
  Validate exact allowed values and handle concurrent/not-found/inactive-unit
  cases consistently.
- Build the InstructorShell Equipamentos page showing active models, unit label,
  inventory state as needed for context, and clear “Operacional”/“Fora de
  serviço” state. Allow only “Marcar fora de serviço” and “Voltar a operacional.”
  Include accessible confirmation/feedback appropriate to the established UI.
- Direct instructor calls to model/unit create, metadata update, activation/
  deactivation, label change, image change, or deletion remain forbidden. Do
  not broaden admin endpoints; administrator inventory behavior remains
  independently authorized.

## Boundaries

- Do not modify AI/training schemas or filters yet; Task 36 consumes the service.
- Do not add maintenance tickets, notes, reason/history, telemetry, sensors,
  reservations, occupancy, real-time use, or “available/free” wording.
- Do not change derived active quantity based on operational state.

## Acceptance criteria and tests

Test migration/default/constraint, state independence from active, active count
unchanged, usable-model service query, instructor read/toggle, every forbidden
inventory mutation, inactive/local-unlinked role denial, admin/client/anonymous
denial, concurrent/not-found handling, exact Portuguese state wording, and
responsive accessible list/loading/empty/error/success states.

Run targeted equipment backend/frontend tests, `git diff --check`, and
`git status --short`; review for live-availability semantics or expanded CRUD.

## Completion requirements

Update only relevant status documentation after verification. Report files,
tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/35-equipment-operational-state.md`, then only its Required reading.
Inspect Task 21 inventory semantics and Task 30 InstructorShell before editing.
Implement only the separate unit operational state, reusable usable-model query,
instructor read/toggle APIs, and Equipamentos page. Preserve active quantity
and deny all instructor inventory CRUD. Do not add training integration or
live-availability behavior. Run targeted tests, review the diff, and provide the
required completion report. Do not commit or push.
