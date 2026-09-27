# Task 40 — Mandatory facial registration and shared identity

**Feature task:** FACE-IMPL-03. **Status:** complete.

## Requirements

EXT-RF-FACE-01; RF-01/03/07/08, RF-04/05 and RF-22;
FACE-CA-01/02/03/04/05 and enrollment/erasure portions of FACE-CA-11/12/13/14.
RN-01/03/04/05/10/23/26/27/32/33/34 and RNF01–RNF06 apply.
The real owner scan, reset, access test, occupancy and final integrated review
remain in their later checkpoints.

## Changes

- Both registration APIs now require a command UUID and either a ready owned
  enrollment session or backend-verified existing shared-person enrollment.
  `biometrics/registration.py` owns the transaction spanning Account, PersonProfile,
  role, enrollment attachment, command result and Keycloak reconciliation intent.
  Invalid/expired/wrong-owner enrollment rolls everything local back; its
  previously durable provider cleanup intent remains. Exact retry returns the
  existing role; conflicting command reuse fails. Disabling the feature does
  not bypass mandatory enrollment. Existing low-level role persistence supports
  participating in this transaction without an intermediate commit.
- Admin client/employee responses include the shared `person_id` needed by the
  protected enrollment controls. Readiness lookup uses POST so CPF/e-mail do not
  enter URL/access logs. Ordinary edits and Keycloak provisioning remain separate.
- Both existing frontend forms reuse `FacialEnrollment` and `WebcamCapture`.
  They preserve ordinary inputs, verify shared reuse, stage explicit webcam
  captures, recover an uncertain result, and support replacement/revocation.
  Submission remains disabled until readiness is verified; identity changes and
  expiry invalidate the proof. Commands retain their UUID on an unchanged retry.
- The accessible MUI camera dialog has explicit capture, immediate processing,
  permission/failure feedback, one in-flight capture, no upload input, and track
  shutdown when closed/unmounted, including late permission responses. Images
  remain transient and are never placed in persistent browser storage.
- Existing client erasure now includes biometric metadata/audit/staging. A
  surviving instructor retains the shared enrollment. Full erasure detaches
  only minimal opaque cleanup jobs, which disappear after provider deletion;
  no identifying tombstone remains. In-flight staged material is deleted only
  after its bounded operation window. Existing Keycloak erasure is retained.
- Approved frontend design guidance documents the reusable enrollment pattern.
  Tests use explicit synthetic enrollment arrangements; no live face is used.

## Verification

- Full backend suite, including disposable PostgreSQL schemas: **296 passed**.
- Full frontend suite: **127 passed**. Existing URL assertions require localhost
  test environment overrides rather than the deployment's LAN HTTPS values:

  ```sh
  docker compose run --rm --no-deps -e TEST_POSTGRES=1 -e CORS_ALLOWED_ORIGINS=http://localhost:5173 backend pytest -q
  docker compose run --rm --no-deps -e VITE_API_BASE_URL=http://localhost:8000 -e VITE_OIDC_ISSUER=http://localhost:8080/realms/academia -e VITE_OIDC_REDIRECT_URI=http://localhost:5173/ frontend npm test
  ```

- PostgreSQL verifies concurrent registration retry creates one role/enrollment
  and full erasure respects foreign keys while preserving pending cleanup.
- Focused UI tests verify explicit capture, duplicate prevention, permission
  failure, late camera cleanup, shared reuse, identity invalidation and revocation.
- Frontend build and scoped backend lint passed. Vite retains its existing
  advisory about the application bundle exceeding 500 kB.
- Firefox component checks in the real admin shell at 360×800, 768×1024 and
  1366×768: no horizontal page overflow, controls labeled, adequate button
  heights, single main/heading, and keyboard-focusable revocation. Both role
  variants and initial/ready states checked with synthetic data. Temporary
  browser fixtures removed. This is not real webcam/recognition evidence.
- Local Docker backend recreated with `FACIAL_ACCESS_MODE=pilot` in ignored
  environment configuration. Backend health, local provider connectivity and
  anonymous enrollment rejection passed; credentials were not printed.
- Git whitespace/scope review passed. No dependency added, real face enrolled,
  test person erased, hardware call, or new consent workflow introduced.

No unresolved functional decision remains for this checkpoint. The authorized
account reset and owner camera/recognition validation are still Task 44.
