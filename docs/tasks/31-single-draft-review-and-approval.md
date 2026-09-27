# Task 31 — Single-Draft Review and Approval

## Status

Implemented (2026-09-27). Single-draft review, atomic approval/current transition,
stable Employee attribution, and client presentation are covered by targeted
backend/frontend regressions and isolated PostgreSQL concurrency tests.
Depends on Tasks 29 and 30 and the existing Tasks 13–17/25.

## Objective

Make every instructor-reviewable plan change use the one canonical client draft,
implement Planos pendentes, and make explicit instructor approval atomically
activate that draft with stable responsible-instructor attribution.

## Requirements covered

- EXT-RF-INST-02: EXT-CA-INST-02.1–EXT-CA-INST-02.8.
- RF-15–RF-19 integration only where their proposal/review paths must converge
  on the sole draft.
- RF-16 for responsible instructor and approval date in the client current view.
- RF-17/CA-17.2–CA-17.4 and RN-12–RN-19/RN-29–RN-33.

## Required reading

Read `AGENTS.md`, this task, and only: `docs/requirements.md` RF-15–RF-19,
EXT-RF-INST-02, sections 2.1, 7.1.1, 7.3, and 9.2, RN-04, RN-05,
RN-12–RN-19, RN-29–RN-33, RNF01–RNF04, DEC-07, DEC-15, DEC-17,
EXT-DEC-INST-01; `docs/instructor-role-specification.md` sections 4–6 and
16.1–16.4; Tasks 13–17, 25, 29, and 30 plus current training lifecycle,
generation, adaptation, instructor review, and client current-plan tests;
`docs/frontend-design.md` training/review/shared-state guidance.

## Exact implementation scope

- Preserve the database-enforced maximum of one `TrainingPlanVersion` in
  `proposal` for each client and make it the only editable instructor-review
  draft across initial AI, manual instructor, current-plan edit, and accepted
  adaptation sources.
- On client acceptance of an adaptation, materialize/link the validated complete
  proposed plan through that sole draft boundary. Retain the adaptation source
  and operations as history, but remove its separate instructor-edit/approval
  authority. If a different draft already exists, return a controlled conflict
  and preserve both the current plan and existing draft; never overwrite or
  create a second editable draft.
- Add instructor-authorized bounded pending-list/detail APIs and replace the
  existing isolated adaptation-review presentation with Planos pendentes. Each
  row/detail includes client presentation name, draft timestamps and revision,
  origin, and current responsible instructor when a current plan exists.
- Support direct `Aprovar`, and `Editar e aprovar`: full draft fields/items are
  editable with `expected_revision`; an intermediate save remains `proposal`
  and never changes the current plan. The explicit approval action validates
  the complete draft and, in one transaction, supersedes the prior current
  version, makes the draft current, records approval time and the approving
  local Employee, and updates plan-current invariants.
- Replace raw Keycloak-sub-only responsibility for new approvals with a stable
  Employee relationship and immutable historical name attribution sufficient
  to survive employee rename/deactivation. Do not rewrite earlier version
  attribution when responsibility changes.
- Extend the client current-plan API/UI to show “Instrutor responsável” and the
  localized approval date. Do not expose employee e-mail, CPF, address, Account
  ID, or internal Employee ID.
- Lock/revision-check every state-changing path. The first successful save or
  approval wins; stale later calls return 409 and pt-BR reload/review feedback.

## Boundaries

- Do not implement Meus planos, Todos os planos, client search/workspace,
  onboarding, or approved-plan cloning in this task.
- Do not add a second draft status/table, silently merge adaptations, mutate
  historical/current content in place, or allow AI/client/admin approval.
- Preserve equipment-reference validation and unrelated-content behavior from
  Tasks 17/25.

## Acceptance criteria and tests

Test every draft source against the single-draft invariant; accepted adaptation
materialization/linkage; existing-draft conflict; complete pending list;
instructor-only detail/save/approve; save-without-activation; direct and edited
atomic approval; rollback on failure; current supersession/history; stable
responsibility after rename/deactivation; client presentation; two-instructor
stale save/approval races; cross-client/privacy denial; and regression of
generation/adaptation/current-plan flows.

Run targeted training backend/frontend suites, `git diff --check`, and
`git status --short`; inspect the full diff for a remaining parallel approval
path or non-atomic transition.

## Completion requirements

Update only relevant status documentation after verification. Report files,
tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/31-single-draft-review-and-approval.md`, then only its Required
reading. Inspect all existing training draft/adaptation/review paths before
editing. Implement only the one cross-source TrainingPlanVersion draft,
Planos pendentes, concurrency-safe edit/save, atomic explicit approval/current
transition, stable Employee responsibility, and client-visible instructor/date.
Preserve adaptation history and equipment validation but remove any parallel
instructor approval authority. Run targeted regression tests, review the diff,
and provide the required completion report. Do not commit or push.
