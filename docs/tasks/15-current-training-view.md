# Task 15 — Current Training View

## Objective

Provide a mobile-first client view of the authenticated client's current training sheet, including a clear empty state.

## Requirements covered

- RF-16: CA-16.1–CA-16.3.
- RF-17 CA-17.3 is integration-verified here; Task 13 owns persistence behavior.

## Related rules and constraints

- RN-05: clients can view only their own training context.
- RN-18: historical data must not be rewritten while displaying the current version.
- RNF01–RNF03: prompt loading/error feedback and usable smartphone, tablet, and desktop layouts.
- Resolved lifecycle decisions inherited from Tasks 13–14 determine which version is “current”; this task must not reinterpret them.
- DEC-16 is **non-blocking** for implementation but required later for formal performance/device measurement.

## Prerequisites

- Tasks 06, 08, 13, and 14 complete. The current-sheet flow requires an
  authenticated client whose `account.keycloak_subject` was populated by Task
  06; a database-only client is not a usable login identity.
- A stable current-version query contract exists.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; RF-16 and CA-16.1–CA-16.3; RF-17/CA-17.3; RN-05, RN-18; RNF01–RNF03; DEC-16; `docs/requirements.md` sections 2.2, 7.1.1, 8, 9.2, and 11.

## Scope

Implement the authorized backend query and responsive frontend page for the
client's current sheet. Represent its exercises and relevant approved
instructions in a mobile-usable training format, with loading, controlled error,
and no-sheet states. Query by authenticated identity rather than trusting a
client identifier supplied by the browser.

Reuse Task 08 ClientShell, loading/error/empty states, and typography. On phones, organize the workout as session → exercise → sets/repetitions/time/load/rest → instruction/context; avoid a separate card for every small value and ordinary horizontal scrolling.

## Out of scope

- Editing, version creation, chat, adaptation, history browsing, or onboarding display.
- Choosing a new training schema or exposing another client's/admin-wide sheets.
- Formal RNF benchmarks before DEC-16 is resolved.

## Acceptance criteria

- CA-16.1: a client with a current sheet can view that exact version.
- CA-16.2: a client without a sheet sees an appropriate empty state.
- CA-16.3: UI and direct API attempts cannot retrieve another client's sheet.
- Reload confirms CA-17.3 through existing persistence.

## Tests

Add API authorization/isolation tests, current/empty/error query tests, frontend rendering tests, and responsive checks at the project-approved viewports when available. Run relevant suites and report results.

## Completion requirements

- Verify every assigned CA and the RF-17 integration check.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then `docs/tasks/15-current-training-view.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this authenticated client-facing task, deriving the client from the Keycloak subject and optimizing the current-plan/exercise view for mobile. Follow `docs/frontend-design.md` and reuse Task 08 shared shell/components; check phone, tablet, and desktop. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
