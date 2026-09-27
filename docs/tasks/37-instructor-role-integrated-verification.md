# Task 37 — Instructor Role Integrated Verification

## Status

Done by explicit user direction on 2026-09-27. Technical verification passed:
248 backend tests (including PostgreSQL), 115 frontend tests, lint/build, and
scoped browser/performance/restart checks. The user will perform the intended-user
checklist. Checklist results and the eight-hour availability soak remain
unverified follow-up evidence, not passing acceptance results. See the
[evidence and completion report](37-instructor-role-integrated-verification-report.md).

## Objective

Verify the complete instructor role and RF-07/RF-08 dependency as one coherent,
secure, responsive journey; repair only defects that prevent the already
approved acceptance criteria from being met.

## Requirements covered

- RF-01/CA-01.4–CA-01.5 and RF-03/CA-03.5–CA-03.6 integration.
- RF-07: CA-07.1–CA-07.6; RF-08: CA-08.1–CA-08.5.
- EXT-RF-INST-01 through EXT-RF-INST-05, all acceptance criteria.
- RF-11–RF-19, RF-32/RF-33, EXT-RF-SOC-02/03, and EXT-RF-EQP-01 only
  for regression/integration at the boundaries changed by Tasks 28–36.
- RNF01–RNF06 and EXT-RF-LANG-01 for the affected journeys.

## Required reading

Read `AGENTS.md`, this task, `docs/instructor-role-specification.md`, and only
the requirement/decision sections referenced above in `docs/requirements.md`;
Tasks 28–36 and their completion notes/current implementations/tests;
`docs/frontend-design.md` shared shells, forms, training, feed, responsive,
language, and accessibility guidance. Do not reopen unrelated requirements.

## Verification scope

Exercise and automate, where practical, these end-to-end journeys:

1. Admin creates and provisions a new instructor with complete person/contact/
   address data, ViaCEP success and manual fallback, then updates all initial
   fields and deactivates/reactivates the employee.
2. Admin links instructor and client roles to the same matching Account and
   verifies independent role activity, exact Keycloak synchronization, and
   backend denial despite stale tokens.
   Verify both directions of the sidebar/mobile area switch without a new login,
   correct client onboarding/default entry, unchanged permissions, and absence
   of the switch when either active role is missing.
3. Instructor login opens Feed, uses the exact navigation, reads only public-
   profile posts/detail, cannot use social mutations, and sees only the bounded
   Perfil future state.
4. Initial AI, manual, accepted adaptation, and current-plan edit paths converge
   on one draft. Two instructors race to save/approve; only the first valid
   state-changing action succeeds. Approval atomically changes current/history,
   responsibility, and client-visible approval metadata.
5. Meus planos/Todos os planos filters, history, existing-draft confirmation,
   client search/filter/workspace, and first manual draft behave exactly as
   specified without exposing contact/health data in lists.
6. Instructor continues/completes draft onboarding and edits completed
   onboarding with normal validation and value-free attribution; all other
   staff roles remain denied.
7. Instructor changes only equipment operational state. Active quantity stays
   inventory-based; new/changed training choices use active operational units;
   later outages do not rewrite current/history.

## Required security/privacy checks

- Direct API tests cover anonymous, client, admin-only, attendant, base
  employee, inactive instructor, unlinked instructor-role token, wrong target,
  and active instructor cases for every new endpoint family.
- Responses/logs/audits do not leak credentials, tokens, CPF/CNPJ, address,
  health values, internal identity IDs, private social data, or another
  client's protected context outside explicitly authorized admin detail.
- Keycloak/ViaCEP/AI failures are controlled and create no partial authority or
  corrupted domain state. Tests use fakes, never live services.

## UI/RNF validation

Verify 360×800, 768×1024, and 1366×768; keyboard-only navigation; visible
focus; semantic headings/landmarks; labels and errors; dialogs; loading/empty/
error/success/stale states; touch targets; no ordinary horizontal scrolling;
and complete pt-BR application copy. Measure only repository-approved personal-
use performance boundaries where changed query paths require it.

## Boundaries

Do not add features, redesign approved workflows, resolve unrelated decisions,
or perform broad refactoring. A defect fix must map to an assigned acceptance
criterion and receive a focused regression test. Stop for a human decision if
verification exposes a specification conflict rather than guessing.

## Completion and commands

Run the relevant backend and frontend suites, lint/type/build checks used by
the repository, then `git diff --check` and `git status --short`. Review the
full diff. Update canonical implementation-status rows and Task 28–37 statuses
only for behavior actually verified. Produce an evidence matrix mapping every
assigned CA to a test/manual result, plus files changed, commands/results,
decisions, and unresolved issues. Do not commit or push.

## Ready-to-run implementation prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/37-instructor-role-integrated-verification.md`, then the listed
requirements, Tasks 28–36, and current implementations/tests. Verify the full
RF-07/RF-08 and instructor journey exactly as scoped. Add or repair only what a
listed acceptance criterion requires; do not invent features or refactor
unrelated modules. Use fake external services, test direct authorization and
privacy, check all three viewports/accessibility/pt-BR states, run the relevant
suites and diff checks, update status only with evidence, and provide the
required evidence/completion report. Do not commit or push.
