# Task 34 — Instructor Onboarding Management

## Status

Planned. Depends on Tasks 12, 29, 30, and 33.

## Objective

Allow an instructor to continue and complete unfinished client onboarding or
edit authoritative completed onboarding in place, using the existing schema and
validation with need-to-know authorization and non-sensitive attribution.

## Requirements covered

- EXT-RF-INST-04: EXT-CA-INST-04.4–EXT-CA-INST-04.7.
- RF-11–RF-13 only as the existing schema, validation, ownership, completion,
  and downstream-validity behavior reused for instructor work.
- RN-11, RN-23, RN-29–RN-31, DEC-06, DEC-18, and EXT-RF-LANG-01.

## Required reading

Read `AGENTS.md`, this task, and only: `docs/requirements.md` RF-11–RF-15,
EXT-RF-INST-04, RN-04, RN-05, RN-11, RN-13, RN-23, RN-29–RN-31,
RN-33, RNF02–RNF04, DEC-06, DEC-18, EXT-DEC-INST-01, sections 2.1,
7.1.1, 7.3, and 9.2; `docs/instructor-role-specification.md` sections 10,
11, 14, and 16.5–16.6; Tasks 10–12, 29, 30, and 33 plus current onboarding
models/services/forms/audit/tests; `docs/frontend-design.md` onboarding,
sensitive forms, feedback, responsiveness, and accessibility.

## Exact implementation scope

- Add instructor-only client-targeted onboarding read/update/complete services
  and APIs. Resolve an active local Employee plus `instructor` role and the
  target active Client server-side. Admin alone, attendant, base employee,
  client, inactive instructor, and anonymous callers receive no access.
- Reuse the authoritative physical/training and health onboarding structures,
  field limits, conditional requirements, normalization, validation, and
  completion service. Do not copy validation into the router or frontend.
- For an unfinished draft, load and continue the same aggregate. Partial saves
  remain drafts. Explicit completion succeeds only when the normal RF-13
  validation passes and records completion consistently; it must not create a
  second onboarding aggregate.
- For completed onboarding, allow the instructor to update every existing
  approved onboarding field in place. The complete state and original
  completion timestamp remain intact; normal validation must hold after the
  update. Do not add revision history, reopen the client editing flow, or
  silently trigger AI/plan generation.
- Record minimized audit/operational evidence for instructor read-sensitive,
  save, completion, and completed-update actions using actor Employee ID,
  target onboarding/client ID, action, timestamp, outcome, and changed field
  names only. Never copy values, medication/condition text, full payloads,
  tokens, CPF/contact data, or exception bodies into logs/audit.
- Reuse/adapt the existing onboarding form inside InstructorShell and connect
  contextual actions from Task 33. All labels, validation, confirmation,
  loading, success, error, and accessible names are pt-BR. Do not show an
  unnecessary client-facing “edited by instructor” message.

## Boundaries

- Do not expose onboarding in search results, grant general health browsing,
  change the schema, add diagnosis/risk inference, create onboarding history,
  call AI, or create/approve a plan automatically.
- Do not weaken the client's own completed-onboarding edit prohibition.

## Acceptance criteria and tests

Test correct-client draft continuation, partial save, completion validation,
completed in-place edit and persistence, unchanged completion timestamp/state,
all approved fields, downstream completed-onboarding read consistency,
instructor local-active authorization, denial of every other role, target
isolation, non-sensitive audit contents and failure outcomes, no sensitive
logging, and responsive accessible form states.

Run targeted onboarding backend/frontend tests, `git diff --check`, and
`git status --short`; inspect the diff for copied health values or broadened
staff access.

## Completion requirements

Update only relevant status documentation after verification. Report files,
tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/34-instructor-onboarding-management.md`, then only its Required
reading. Inspect and reuse the existing onboarding service, validation, form,
and audit patterns before editing. Implement only instructor-targeted draft
continuation/completion and valid completed in-place editing from the client
workspace, with strict need-to-know authorization and value-free attribution.
Do not add onboarding history, AI calls, or automatic plan changes. Run targeted
tests, review the diff, and provide the required completion report. Do not
commit or push.
