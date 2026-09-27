# Task 41 — Recognition policy and simulated release

**Feature task:** FACE-IMPL-04. **Status:** complete.

## Requirements and changes

EXT-RF-FACE-01; RF-04/05, RF-20/21/22; FACE-CA-03/06/07/11/13/15.
RN-04/05/06/07/08/10/23/26/27/32/34 and the approved pilot RN-35/36 exception;
RNF01/04/05/06 apply. Passage/count writes remain Task 42.

- `biometrics/access.py` separates face identification from client eligibility.
  It rejects unknown/staged/revoked references, no/multiple/low-quality faces,
  below-threshold and ambiguous results. Staff-only identities never receive
  client release. Entry checks Client activity and outside state; recognized
  inside clients can exit despite Client or ordinary login deactivation.
- Owned attempts fix direction and allow at most two deliberate captures.
  A new attempt cancels the operator's older pending attempt. Explicit cancel,
  safe polling, persisted command replay, interrupted-capture recovery and
  thirty-second authorized-result validity prevent automatic retry/release loops.
  Replacement/revocation cancels already identified pending attempts; a face
  changed during provider processing is revalidated before authorization.
- `biometrics/release.py` contains the stable `TURNSTILE_RELEASE_REQUESTED`
  marker, `TurnstileReleaseRequest`, `TurnstileReleaseAdapter.request_release`
  and `SimulatedTurnstileReleaseAdapter`. Its payload contains only correlation
  UUIDs, UTC time, checkpoint, direction, opaque subject and simulated mode.
  It has no HTTP client, hardware dependency, or identifying person payload.
- Migration 27 adds attempts and release records, audit/command correlations,
  and the client state projection required to evaluate inside/outside eligibility.
  The projection initializes from confirmed history; recognition changes no
  passage ledger, occupancy count, or inside/outside state. The unique attempt
  relationship prevents duplicate release records; a DB constraint rejects
  non-simulated mode. Person/client erasure includes these new relationships.
- All new API routes enforce admin authorization and attempt ownership.
  API responses contain safe result codes and authorized operational identity,
  never raw scores/images/provider payloads. The UI/test panel follows in Task 43.

## Verification

- **64 related tests passed**, including isolated PostgreSQL checks: recognition
  matrix, client/account deactivation and exit, staff-only rejection, capture
  budget, provider failure, command ownership, duplicate release prevention,
  direction cancellation, in-flight revocation, recovery, enrollment lifecycle,
  erasure and unchanged occupancy behavior.
- Real PostgreSQL verifies concurrent replay processes one capture/releases once,
  migration upgrade/downgrade and the simulated-only database constraint.
- Scoped Ruff and Git whitespace/scope review passed.
- Migration applied to the local Docker database. No real face captured, test
  identity removed, or external turnstile call made. No dependency added.

No unresolved functional decision remains. Actual passage confirmation, state
corrections and occupancy/presence projection are the next task; authorization
alone deliberately leaves the existing count unchanged. The owner pilot still
does not verify representative >=95% precision or liveness.
