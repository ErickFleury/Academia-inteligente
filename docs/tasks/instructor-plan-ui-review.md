# Instructor Training Plan UI Review

Completed on 2026-09-27 following the user's explicit scope selection:
Planos pendentes, Meus planos, and Todos os planos.

## Review and implementation

Previously, the selected plan/editor appeared after the full list of large
cards. Pending drafts opened directly as a long form, and approved history was
mixed into the exercise reading area. This made reviewing and switching plans
unnecessarily difficult, especially on phones.

The three destinations now share a compact list and focused plan-reading
layout. Larger desktops show both areas; phone/tablet views show the list or
selected plan, with a visible return action and restored keyboard focus.
Exercises group sets, repetitions, rest, load guidance, and recorded equipment.
Pending plans open in preview; a separate tab enables editing. Preview retains
unsaved edits, and approval saves those displayed edits before approving their
new revision. Closing, reloading, or selecting another plan within the workspace
requires confirmation before discarding unsaved edits. Successful approval
returns keyboard focus to the pending-list heading.

Approved plans separate exercise content and approval history into tabs, retain
historical instructor/date attribution, and label historical content read-only.
The all-plan collection keeps name search prominent, groups optional filters,
and provides an explicit reset. Counts describe loaded records, not a guessed
database total.

## Scope and decisions

This is a frontend follow-up to EXT-RF-INST-02/03, their approval/history and
single-draft boundaries, EXT-RF-LANG-01, and RNF02/RNF03. Existing backend
contracts, scope filters, bounded pagination, revision checks, approval rules,
and exact existing-draft replacement confirmation remain authoritative.
No dependency, database migration, seed-data change, or new API was introduced.
The shared theme and instructor navigation are retained; only these plan pages
opt into the shell's wider content area. All application-controlled copy is
pt-BR. The earlier Task 37 manual-checklist/soak follow-up is unaffected.

## Files changed

- `frontend/src/instructor-pending-plans-page.tsx`: list/preview/edit workspace,
  unsaved-edit guard, loading request ordering, approval focus restoration.
- `frontend/src/instructor-plan-collections-page.tsx`: collection/filter layout,
  focused detail/history, read-only historical navigation, focus restoration.
- `frontend/src/components/training-plan-content.tsx`: reusable readable exercise
  content for pending, current, and historical plans.
- `frontend/src/instructor-shell.tsx`: optional wider content size for plan pages.
- Both instructor plan page test files: updated interactions plus regression
  coverage for reading, filter reset, focus, unsaved edits, and preview approval.
- `docs/frontend-design.md`: documented the shared instructor plan pattern.
- This report: review findings, scope, verification, and limitations.

## Verification

- Full frontend suite: **119 passed, zero failures** using
  `docker compose run --rm --no-deps -e VITE_API_BASE_URL=http://localhost:8000 -e VITE_OIDC_ISSUER=http://localhost:8080/realms/academia -e VITE_OIDC_REDIRECT_URI=http://localhost:5173/ frontend npm test -- --reporter=json --outputFile=/app/.plan-ui-tests.json`.
  Temporary JSON output was inspected and removed.
- `docker compose run --rm --no-deps frontend npm run lint`: passed.
- `docker compose run --rm --no-deps frontend npm run build`: passed. The existing
  non-fatal advisory for a bundle exceeding 500 kB remains.
- Firefox checks with synthetic API fixtures: **36 state/viewport combinations**
  across 360×800, 768×1024, and 1366×768. Covered lists, filters, details, history,
  historical reading, and pending editing. No horizontal page overflow,
  unlabeled visible controls, or audited button below 43 CSS pixels (theme target
  44). Each page retained one main landmark and h1. Real keyboard arrow/Space
  activation of tabs, heading focus, visible back navigation, return focus, and
  absence of historical editing passed. Representative screenshots were inspected.
- `git diff --check`: passed; changed-file scope reviewed. Browser fixture pages
  and test output were removed before committing.

The browser audit is scoped and does not claim comprehensive WCAG or
screen-reader certification. Backend tests were not rerun because this change
contains no backend behavior or contract changes. No blocking issue remains for
this UI follow-up.

## Follow-up: explicit client names

At the user's request, all three instructor plan pages now separate the plan
name from an explicit “Cliente: {nome}” label on list cards and detail headers.
Approval-history entries also show the attached client. Names use the existing
API `client_name` field; no backend or data changes were needed.

Changed both instructor plan pages, their corresponding test files, the frontend
design guide, and this report. Focused regression tests verify the client label
on pending, personal, and all-plan collections, details, and history.

Verification for this follow-up:

- Both affected frontend test files: **13 passed**.
- Frontend lint and production build: passed; the existing non-fatal bundle-size
  advisory remains.
- Firefox synthetic-fixture audit: **36 state/viewport checks passed** across
  phone, tablet, and desktop sizes, including explicit client-label assertions.
  Representative list and detail screenshots were inspected.
- Temporary browser fixtures removed; Git diff whitespace and scope reviewed.

No unresolved issue was introduced by this follow-up.
