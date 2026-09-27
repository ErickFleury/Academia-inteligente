# Task 43 — Administrator facial-access workspace

**Feature task:** FACE-IMPL-06. **Status:** complete.

## Requirements and changes

EXT-RF-FACE-01, RF-20–25 and FACE-CA-03/04/07/08/09/10/11/13/14/15 apply.
The page follows `docs/frontend-design.md`, RNF02/03 and existing backend
administrator authorization; no attendant or staff-access workflow was added.

- `/admin/acesso-facial` opens from the administrative dashboard and uses the
  existing AdminShell, MUI theme, status notices and webcam dialog. The test panel
  shows provider health, anonymous occupancy and pending provider cleanup.
- Entry/exit selection, deliberate capture and separate thirty-second passage
  confirmation show the identified client's name and simulated release. Direction
  changes cancel the prior attempt. Uncertain requests expose result polling
  without automatically resending an image; deliberate retry remains bounded.
- Corrections select a client, show current presence, require a reason and send
  the displayed revision. Conflicts refresh state and retain the reason. UUID
  retries preserve idempotency. No correction fabricates a recognition result.
- Bounded newest-first history combines safe audit events and person corrections,
  supports client/direction/result filters and cursor pagination, and shows names,
  localized times and correction reasons without images, scores or provider IDs.
- Provider status and history endpoints are admin-only. The open panel refreshes
  heartbeat every sixty seconds only after provider readiness checks; closing it
  stops scheduling. Camera capture stays explicit. The page explains deferred
  liveness protection; the existing occupancy page gains no simulation label.

## Verification

- **342 backend tests passed**, including real PostgreSQL cursor tie-ordering,
  filter/privacy checks, malformed cursors, endpoint limits and authorization.
- **137 frontend tests passed** across 28 files. New tests cover separate passage
  confirmation, uncertain capture/confirmation recovery, two-capture budget,
  direction cancellation, expiry, reason/revision corrections, stale-state
  recovery, history filters, heartbeat lifecycle and protected routing.
- TypeScript/production build passed. The existing >500 kB bundle advisory remains.
  Scoped Ruff and Git whitespace/scope checks passed.
- Firefox checked initial, authorized and confirmed states at 360×800, 768×1024
  and 1366×768: no horizontal page overflow, one main/h1, labeled controls and
  buttons at least 44 px tall. Keyboard confirmation worked. Synthetic camera
  stream and API fixtures were used; temporary fixture source files were removed.
- No dependency added, real face captured, test identity deleted or external
  turnstile call made in this task.

Actual owner enrollment and webcam matching remain Task 44. Browser fixture
results do not establish real recognition accuracy or liveness.
