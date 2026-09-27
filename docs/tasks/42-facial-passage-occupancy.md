# Task 42 — Confirmed passages and occupancy

**Feature task:** FACE-IMPL-05. **Status:** complete.

## Requirements and changes

EXT-RF-FACE-01; RF-20/22/23/24/25; FACE-CA-03/08/09/10/12/13/15.
The approved pilot entry/exit exception, existing occupancy freshness rules,
separate profile-presence consent and RNF01/04/05/06 apply.

- `biometrics/passages.py` confirms an owned, authorized, unexpired attempt after
  rechecking current enrollment, client eligibility and state revision. It writes
  one deterministic passage, consumes the attempt and updates state atomically.
  UUID command replay and database locks prevent duplicate concurrent changes.
- Reasoned administrator corrections append person-linked occupancy adjustments
  and audit, invalidate pending attempts and update the same state transaction.
  No-op and repeated corrections cannot drift the count or invent release events.
- Migration 28 adds internal simulated provenance, state revisions and correction
  linkage. Existing aggregate occupancy responses keep their public shape.
  Startup and state reads reconstruct projections from confirmed ledger history.
  Person erasure removes linked passages and corrections together.
- Named presence retains its separate opt-in and freshness rules and respects
  later state corrections. Snapshot timestamp normalization also handles mixed
  SQLite/Python timezone representations used by regression tests.
- The admin-only pilot heartbeat checks both the local provider API and recognition
  worker before refreshing source health. Stale health preserves the last count.

## Verification

- **335 backend tests passed**, including PostgreSQL tests, with the suite's
  localhost CORS fixture configuration. The focused passage/occupancy/presence
  suite passed 44 tests before the full run.
- Coverage includes no count change from recognition alone, idempotent entry/exit,
  inactive-client exit, stale/revoked/deactivated authorization, competing attempt
  confirmations and corrections, reconstruction, privacy, consent, cleanup and
  provider failure. Migration upgrade/downgrade passed on isolated PostgreSQL.
- Scoped Ruff checks and Git whitespace/scope review passed. Migration 28 applied
  to the local Docker database; backend restarted with the new implementation.
- No dependency added. No real face captured or external turnstile call made.

The administrator workspace and heartbeat scheduling in its open panel follow in
Task 43. Owner-camera verification remains Task 44; representative accuracy and
liveness remain unverified.
