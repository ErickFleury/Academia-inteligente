# Task 24 — Nonfinancial Administrative Dashboard

## Objective

Implement the decision-complete, nonfinancial portion of the administrative
dashboard by composing existing client, confirmed-attendance, and anonymous
occupancy information. This task must not introduce billing, payment, plan,
subscription, revenue, profit, or employee-management behavior.

## Requirements covered

- RF-28: CA-28.1 and CA-28.3, plus only the already-implemented nonfinancial
  modules applicable to CA-28.2.
- RF-29: CA-29.1.
- CA-28.2 financial and employee examples are not completion claims for this
  task because their source modules are excluded or not implemented.
- CA-29.2 is explicitly excluded because it is financial and conditional.

## Related rules and constraints

- RN-04/RN-05: dashboard APIs require backend-enforced administrative
  authorization and must not disclose client-owned protected records.
- RN-23/RN-27/RN-32/RN-33: use minimum aggregate data, preserve audit and
  temporal integrity, and do not rewrite the attendance ledger.
- RNF01–RNF04: keep aggregate queries bounded, UI states understandable,
  responsive, accessible, and module boundaries explicit.
- DEC-10 remains authoritative for current anonymous occupancy and source
  freshness. The dashboard must consume that aggregate projection rather than
  calculate a competing occupancy value.
- DEC-11 keeps individual passage history private and client-linked. The
  dashboard may aggregate confirmed entry events but must not expose passage
  identities or external client references.
- DEC-13 remains unresolved for financial indicators. This task avoids that
  decision entirely and must not add financial placeholders.
- EXT-RF-LANG-01 applies to all user-visible and accessible UI copy.

## Prerequisites and dependencies

- Tasks 03, 04, 06, 08, and 22 are implemented.
- Use the existing Account/Client active-state definition and the existing
  confirmed-passage and occupancy services. Do not create parallel sources of
  truth.
- Inspect the current `/admin` client-management route before choosing the
  smallest navigation/layout change that preserves access to existing admin
  functions.

## Required reading

Read `AGENTS.md`, then this task, then only the following canonical material:

- `docs/requirements.md`: RF-28/CA-28.1–CA-28.3,
  RF-29/CA-29.1–CA-29.2, RF-23–RF-25, RN-04, RN-05, RN-23, RN-27, RN-32,
  RN-33, RNF01–RNF04, DEC-10, DEC-11, DEC-13, DEC-16, DEC-17, DEC-19, and
  EXT-RF-LANG-01;
- the Task 22 completion report and current occupancy/access implementation;
- `docs/frontend-design.md` for the administrative shell, shared states,
  responsive layout, accessibility, and Portuguese presentation.

## Exact implementation scope

Create an administrator-only dashboard that displays these existing indicators:

1. number of active clients, using the canonical account/client active-state
   behavior already implemented;
2. attendance history over recent calendar weeks as aggregate counts of
   confirmed client **entry** passage events, clearly labelled as confirmed
   entries rather than unique clients or duration of attendance;
3. current anonymous client occupancy, including the existing current/stale
   status and update time from Task 22.

The attendance series must be deterministic, chronologically ordered, bounded
to a documented recent-week window, and built from persisted confirmed passage
events. It must not count heartbeats, corrections, recognition attempts,
release requests, unknown references, exits, staff, or camera observations as
entries. Follow established timestamp/time-zone conventions; stop for a human
decision if the repository does not provide enough information to group a
boundary event safely.

Keep indicator failures isolated: an authorized user may still see independent
successful indicators when one aggregate source fails, with a controlled
Portuguese error state for the failed indicator. Authentication or
authorization failure must fail closed for the entire dashboard.

## Backend scope

- Add the minimum admin-authorized aggregate service/API needed by the UI.
- Reuse client and occupancy/access domain queries; do not copy their business
  rules into the controller.
- Return aggregates only. Do not serialize client IDs, names, e-mails,
  `client_reference`, individual passage rows, biometric data, or raw
  integration payloads.
- Avoid N+1 queries and unbounded event reads. Use database aggregation for the
  weekly attendance series.
- Preserve Task 22 source-health behavior exactly. Dashboard reads must not
  mutate occupancy or attendance state.

## Frontend scope

- Reuse Task 08 `AdminShell`, theme, page headers, cards, loading/empty/error
  feedback, and existing navigation patterns.
- Preserve discoverable access to existing client, progress-post, and equipment
  administration screens.
- Present counts and dates in `pt-BR`. Use wording such as “clientes ativos”,
  “entradas confirmadas” and “clientes na academia”; never imply named presence
  or camera-derived certainty.
- Check 360×800 phone, 768×1024 tablet, and 1366×768 desktop layouts. Cards and
  the weekly history must remain readable without horizontal page scrolling.

## Persistence and migration scope

No new authoritative dashboard table, snapshot, or counter is expected. Derive
the indicators from existing persisted modules. Do not create a migration
unless inspection proves a narrowly scoped read-performance index is necessary;
if so, justify it in the completion report and do not change domain semantics.

## Authorization and privacy

- Enforce the admin role at every new backend endpoint.
- A hidden frontend route is not authorization.
- Do not expose the dashboard to clients, instructors, attendants, employees,
  or anonymous users through this task.
- Keep occupancy aggregate-only and attendance non-identifying.

## Integration boundaries

- Current occupancy comes from the Task 22 authoritative projection.
- Attendance comes from confirmed passage events, not biometric recognition,
  turnstile release, heartbeats, or camera data.
- Failure of an external source must not authorize access or fabricate a fresh
  value.

## Explicitly out of scope

- Billing, fees, invoices, payment status, payment providers, plans,
  subscriptions, pricing, checkout, revenue, profit, or financial placeholders.
- Employee counts or employee management before RF-07/RF-08 are implemented.
- Named-presence lists, client attendance drill-down, individual passage
  history, exports, camera tracking, or biometric data.
- Changes to DEC-10 occupancy semantics or Task 22 ingestion.
- Resolving DEC-13 or claiming CA-29.2.

## Acceptance criteria

- Direct API tests prove only an administrator can obtain the aggregates.
- Active-client count follows the existing canonical state and excludes
  deactivated clients.
- Weekly attendance counts only persisted confirmed client entry events and is
  stable across repeated reads/restarts.
- Occupancy value/status matches the Task 22 projection, including stale-state
  presentation.
- One indicator failure produces a controlled per-indicator state without
  leaking another context or bypassing authorization.
- No response contains individual attendance identity or sensitive integration
  data.
- The admin UI is understandable and usable at the three required viewports.

## Expected tests and validation

Add or update focused backend service/API tests for aggregation boundaries,
week ordering, active-state semantics, source reuse, authorization, privacy,
and partial indicator failure. Add frontend tests for successful, empty,
loading, stale, per-indicator error, and unauthorized states.

Run the repository-standard targeted backend and frontend commands discovered
from the existing project configuration, then at minimum:

```bash
git diff --check
git status --short
```

Review the full diff and confirm no payment, financial, named-presence,
biometric, camera-tracking, or unrelated feature was introduced.

## Documentation and completion requirements

After implementation, update only relevant task/status documentation to record
the nonfinancial partial completion of RF-28/RF-29. Do not mark financial or
employee examples complete. Report files changed, tests/results, important
decisions, and unresolved issues as required by `AGENTS.md`.

Stop and ask if implementation reveals a material undefined decision, including
ambiguous attendance aggregation or time-zone behavior that cannot be resolved
from established repository conventions. Do not commit or push.

## Ready-to-run implementation prompt

Read `AGENTS.md`, then
`docs/tasks/24-nonfinancial-administrative-dashboard.md`, then only the
requirements and decisions listed under Required reading. Inspect the existing
repository and Task 22 implementation before editing. Implement only the
nonfinancial administrator dashboard described by this task. Preserve anonymous
occupancy, keep attendance aggregate-only, and do not create any payment,
billing, plan, profit, employee, biometric, or camera-tracking behavior. Follow
`docs/frontend-design.md`, reuse Task 08 shared admin layout/components, and
check phone, tablet, and desktop. Stop and ask if a materially new human
decision is required. Run relevant backend/frontend tests, review the Git diff,
and provide the required completion report. Do not commit or push.
