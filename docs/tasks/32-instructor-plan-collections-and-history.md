# Task 32 — Instructor Plan Collections and History

## Status

Planned. Depends on Task 31.

## Objective

Implement Meus planos, Todos os planos, current-plan detail/history, and the
safe approved-plan-to-draft editing workflow without mutating active or
historical versions.

## Requirements covered

- EXT-RF-INST-03: EXT-CA-INST-03.1–EXT-CA-INST-03.5 and
  EXT-CA-INST-03.7. First-plan manual creation remains Task 33.
- RF-16/RF-17 integration for current selection and immutable history.
- EXT-RF-LANG-01.

## Required reading

Read `AGENTS.md`, this task, and only: `docs/requirements.md` RF-16, RF-17,
EXT-RF-INST-02, EXT-RF-INST-03, RN-04, RN-05, RN-14, RN-16–RN-19,
RN-31–RN-33, RNF01–RNF04, DEC-07, DEC-15, EXT-DEC-INST-01, sections
7.1.1 and 7.3; `docs/instructor-role-specification.md` sections 5–8 and
16.3–16.4; Task 31 and current lifecycle/current-plan implementations/tests;
`docs/frontend-design.md` training, filters, responsive lists, dialogs, and
shared states.

## Exact implementation scope

- Add bounded instructor-authorized current-plan query services/APIs. Meus
  planos returns only current plans whose responsible Employee is the caller.
  Todos os planos returns every current plan and includes client presentation
  name, responsible instructor presentation name, latest approval date, and
  status.
- Todos os planos supports combinable trimmed client-name search,
  responsible-instructor filtering, and inclusive approval date/date-range
  filtering using `America/Sao_Paulo` calendar dates, as approved in the
  canonical requirements. Include the entire selected day/end date, excluding
  the following local midnight. Define deterministic ordering and stable
  bounded pagination; avoid N+1 queries.
- Add detail APIs/UI shared by both lists. Show the immutable current content
  and the client's approved/superseded history in deterministic newest-first
  order with historical responsible attribution and approval date. Historical
  versions have no edit controls and reject mutation directly.
- `Editar` on a current plan creates a complete new sole draft copied from the
  current version; it does not change current content or responsibility. The
  new draft proceeds through Task 31 save/approval.
- If any sole draft exists for that client, the initial edit request returns a
  conflict describing that fact without replacement. The UI presents an
  accessible consequential-action dialog. Only a second explicit confirmed
  request may discard that exact still-current draft and clone the still-current
  approved version. Cancellation changes nothing. Use expected identifiers/
  revisions so concurrent draft/current changes make confirmation stale rather
  than deleting newer work.
- Integrate both pages into the Task 30 InstructorShell with pt-BR loading,
  empty, error, filter, no-result, and stale-conflict states.

## Boundaries

- Do not create a first plan from these list pages, implement client search or
  onboarding, modify a current/history version in place, or add assignment of
  clients to instructors.
- Do not expose health, contact, Account/Client/Employee IDs, drafts from other
  contexts beyond the approved conflict/pending detail, or unbounded history.

## Acceptance criteria and tests

Test Meus planos responsibility scope; Todos os planos completeness, combined
filters, `America/Sao_Paulo` date boundaries (including UTC/local-day differences),
pagination/order, and no N+1 behavior; current and
history detail; immutable history direct denial; clean clone; existing-draft
conflict; cancel; explicit exact-draft replacement; stale confirmation races;
authorization; and responsive accessible lists/filter/dialog states at the
three representative viewports.

Run targeted backend/frontend tests, `git diff --check`, and
`git status --short`; review for in-place mutation or silent draft loss.

## Completion requirements

Update only relevant status documentation after verification. Report files,
tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/32-instructor-plan-collections-and-history.md`, then only its
Required reading. Inspect Task 31 and existing plan queries before editing.
Implement only Meus planos, Todos os planos with approved combined filters,
bounded current/history detail, and concurrency-safe current-to-draft editing
with explicit exact-draft discard confirmation. Never mutate current/history
in place or silently remove a draft. Run targeted tests, review the diff, and
provide the required completion report. Do not commit or push.
