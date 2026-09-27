# Task 39 — Protected facial enrollment and cleanup

**Feature task:** FACE-IMPL-02. **Status:** complete.

## Requirements and scope

EXT-RF-FACE-01; RF-22; supporting RF-01/03/07/08, RF-04/05;
FACE-CA-03/05/11/13 and the enrollment foundation of FACE-CA-01/02/04.
Applicable RN-01/04/05/07/10/23/26/27/32/34 and RNF01/04/05/06.
Registration integration, person erasure, browser capture and access recognition
remain the following tasks; this checkpoint does not mark their acceptance passed.

## Implementation

- New `backend/app/modules/biometrics/` owns configuration, a provider-neutral
  adapter, bounded in-memory JPEG/PNG capture, enrollment lifecycle, APIs and
  cleanup. No dependency added. Standard-library MIME parsing handles exactly
  one image and one command UUID after admin authorization.
- Migration `20260927_26` adds enrollment, owned staging, command recovery,
  append-only audit, durable cleanup and a metadata lock. No application table
  contains images, templates, embeddings, raw provider responses or scores.
- Administrator sessions bind normalized identity, intended role and revision.
  Staged faces cannot authorize. Every external write has a previously committed
  cleanup intent; failed, abandoned and interrupted captures remain recoverable.
- Replacement stages first, changes the enrollment atomically, and queues old
  material for deletion. Revocation disables the local reference immediately.
  Shared-person attachment participates in the caller's transaction without
  committing it. Existing client access-reference mappings change atomically.
- A short database lock and a persisted capture lease serialize enrollment
  starts, including across processes. Late responses cannot overwrite a newer
  capture. Cleanup waits for in-flight capture expiry and checks that a subject
  is not active before deletion. It runs on startup and on a one-minute schedule;
  failed deletion uses bounded backoff and exposes pending status.
- Configuration accepts only disabled/pilot and the approved local provider URL.
  Recognition inspects all detected faces and requests two candidate identities;
  single-face quality, ambiguity and cross-person enrollment conflicts fail closed.
  The provider uses bounded requests, rejects redirects, and exposes safe codes.
- `backend/app/main.py` registers the admin router, safe error mapping and
  failure-isolated cleanup lifecycle; Alembic imports the new model metadata.

## Evidence

- Full backend suite with isolated PostgreSQL tests: **286 passed**.
  Command: `docker compose run --rm --no-deps -e TEST_POSTGRES=1
  -e CORS_ALLOWED_ORIGINS=http://localhost:5173 backend pytest -q`.
  The initial run inherited the deployment's LAN-only CORS origin and failed
  the existing localhost CORS fixture; using its expected test environment
  resolved it without changing runtime policy.
- Focused tests cover invalid images, bounded multipart transport, metadata
  stripping, no/multiple/low-quality faces, conflicting identities, admin-only
  APIs, command replay/ownership, safe replacement/revocation, failed deletion,
  restart recovery, stale and late captures, shared reuse and adapter contracts.
- PostgreSQL tests verify migration upgrade/downgrade, duplicate concurrent
  session creation, competing revocations, capture exclusion and preservation
  of staged cleanup after local attachment rollback. They use synthetic adapter
  doubles in disposable schemas, not live recognition or user data.
- Migration applied successfully to the local Docker database.
- Local CompreFace adapter readiness and blank-image rejection passed. No real
  face enrolled. Provider credentials remained server-side and unprinted.
- Scoped Ruff checks and Git whitespace/scope review passed.

## Remaining work

No functional decision is pending for this checkpoint. `FACIAL_ACCESS_MODE`
remains disabled in the deployment until the integrated workflows are ready.
Mandatory registration, edit controls and full person erasure belong to Task 40.
No test account was deleted. Owner webcam/calibration evidence remains Task 44;
population precision and liveness remain unverified.
