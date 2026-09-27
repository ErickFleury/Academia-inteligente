# Task 33 — Instructor Client Workspace and Manual Draft

## Status

Implemented (2026-09-27). Depends on Tasks 31 and 32.

Verification: nine focused backend tests, PostgreSQL accent-search and concurrent
first-draft creation coverage (plus three collection race regressions), eleven
workspace/shared-editor/collection UI tests, and the frontend build pass. Ruff
and Git whitespace checks pass. Synthetic Firefox checks verified the workspace
and manual form at 360×800, 768×1024, and 1366×768 without horizontal overflow.
Migration 20260927_23 applied successfully.

Name normalization uses PostgreSQL built-ins, without an extension or dependency.
Search projections remain set-based and cursor-bounded. Both manual API entry
points use the same locked eligibility check and retain creator Employee linkage;
approval remains a separate action. The manual form shares the existing draft
fields. Onboarding actions remain explicitly reserved for Task 34.

## Objective

Implement the Clientes search/workspace for training state and allow an
instructor to create the first manual plan draft through the existing sole-draft
and approval lifecycle.

## Requirements covered

- EXT-RF-INST-04: EXT-CA-INST-04.1–EXT-CA-INST-04.3 and training-workspace
  portions of EXT-CA-INST-04.6.
- EXT-RF-INST-03: EXT-CA-INST-03.6–EXT-CA-INST-03.7.
- RF-02 only as an instructor-specific minimized search projection; it does not
  grant administrative client access.
- RF-17/CA-17.4, RN-14, RN-19, RN-31, and EXT-RF-LANG-01.

## Required reading

Read `AGENTS.md`, this task, and only: `docs/requirements.md` RF-02,
RF-15–RF-17, EXT-RF-INST-02–EXT-RF-INST-04, RN-04, RN-05, RN-11,
RN-14, RN-19, RN-23, RN-31–RN-33, RNF01–RNF04, DEC-07, DEC-15,
DEC-17, EXT-DEC-INST-01, sections 2.1, 7.1.1, 7.3, and 9.2;
`docs/instructor-role-specification.md` sections 9, 10, 14, and 16.5;
Tasks 28–32 and current client/onboarding/training models and tests;
`docs/frontend-design.md` instructor-compatible AdminShell density, training,
filters, forms, responsiveness, and accessibility.

## Exact implementation scope

- Add a bounded instructor-only search projection over active Clients. Search
  by partial name, case-insensitively and accent-insensitively, with normalized
  whitespace and deterministic alphabetical name/ID ordering. Do not search or
  return e-mail, CPF, phone, address, CNPJ, or account activation controls.
- Add combinable filters exactly for onboarding (Todos, Concluído, Não
  concluído), training (Todos, Sem plano, Pendente de aprovação, Plano ativo),
  and responsibility (Todos, Sem instrutor, Eu, Instrutor específico). Do not
  add “Somente rascunho” or an account-active filter. Draft/current existence
  predicates remain independently truthful, so a client with both may match
  the corresponding filter selected in separate queries.
- Results show client name, onboarding state, training state, current
  responsible instructor when any, and whether the sole draft/current plan
  exists. Use bounded pagination and set-based projections without N+1 reads.
- Add a minimized instructor client workspace that links directly to the
  existing sole draft, current plan, and history when present. Reserve clear
  locations for Task 34 onboarding actions but do not expose sensitive
  onboarding values in list results.
- When the client has no current plan and no draft, allow an instructor to
  create a complete manual plan draft with the existing plan/item schema.
  Attribute origin/creator to the active local Employee. Creation leaves it as
  `proposal`; it appears in Planos pendentes and requires a separate Task 31
  approval action. If eligibility changed concurrently, return a conflict and
  create nothing.
- If a current plan exists, direct the instructor to Task 32 editing. If a draft
  exists, open it; do not create or replace another draft.

## Boundaries

- Do not implement onboarding reads/writes yet, administrative registration,
  active-state changes, client assignment, AI calls, automatic approval, or a
  new exercise catalog.
- Do not expose personal contact/identity data or use browser-supplied identity
  as authorization.

## Acceptance criteria and tests

Test partial/case/accent-insensitive name matching and ordering; every filter
alone and in combination; active-client-only behavior; minimized fields;
pagination/no N+1; workspace draft/current/history links; eligible manual draft;
separate approval; current/draft conflict; concurrent creation race;
instructor-only APIs; and responsive accessible search, filter, result, empty,
error, and manual-form states.

Run targeted backend/frontend tests, `git diff --check`, and
`git status --short`; review for administrative/sensitive data leakage or a
second draft path.

## Completion requirements

Update only relevant status documentation after verification. Report files,
tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/33-instructor-client-workspace-and-manual-draft.md`, then only its
Required reading. Inspect Tasks 28–32 and current client/training queries before
editing. Implement only the minimized active-client search/filter/workspace and
first manual draft creation. Use the one canonical draft and separate explicit
approval; do not implement onboarding mutations or administrative client data.
Run targeted tests, review the diff, and provide the required completion report.
Do not commit or push.
