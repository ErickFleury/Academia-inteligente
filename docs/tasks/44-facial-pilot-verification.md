# Task 44 — Local reset and owner verification

**Feature task:** FACE-IMPL-07. **Status:** in progress; owner webcam checks pending.

## Scope and completed evidence

EXT-RF-FACE-01 and FACE-CA-01–16; RF-01/03/07/08, RF-20–25 and the approved
owner-only pilot exceptions apply. The six implementation checkpoints are
complete. This final checkpoint cannot be completed from synthetic tests alone.

On 2026-09-27 the authorized local reset removed nine disposable Keycloak users
and nine application Accounts: eight Client records and three Employee records
(two shared-role identities), plus their onboarding, plans, social data,
reconciliation work and access-state history. No real enrollment existed.

- Post-reset inventory: zero test users, Accounts, PersonProfiles, Clients,
  Employees, enrollment subjects, access references, passages, corrections,
  plans and related person data. The bootstrap administrator remains in Keycloak
  without needing a local Account or face. Provisioning service authentication
  remains usable. Keycloak management/realm/client/role configuration was not changed.
- Equipment/catalog preservation checked; this deployment had zero models/units.
  PostgreSQL tests also verified preservation with populated equipment and a
  bootstrap-linked local Account. No Docker volumes were removed.
- Actual bootstrap login through Keycloak and the protected Acesso facial page
  passed both before and after reset. Provider readiness and zero occupancy were
  visible. The temporary browser session was cleared afterward.
- Post-reset local provider preflight passed subject API, empty-subject lifecycle
  and blank-image rejection in **0.102 s total**. This is service plumbing timing,
  **not genuine-face recognition latency**. No face enrolled by the agent.
- Task 43 regression evidence: **342 backend / 137 frontend tests passed** and
  TypeScript production build passed. Reset-specific tests add **2 passing checks**,
  including real PostgreSQL preservation/idempotency. Scoped Ruff passed.

## Installed recognition configuration

CompreFace 1.2.0 runs in local Docker with the pinned CPU FaceNet model
`20180402-114759`; model SHA-256:
`bf2c12f31880aaa865fa5a9c168dcbd619f7a40b1633f6446d416fac2421ab99`.
Detection threshold **0.90**, match threshold **0.80**, ambiguity margin **0.10**,
provider request timeout **10 s**. These remain uncalibrated starting values.
Provider images stay in its isolated local volume. No liveness protection or
external turnstile call exists. Provenance/free-use evidence: [Task 38](38-facial-provider-foundation.md).

The future release integration locator remains `TURNSTILE_RELEASE_REQUESTED` in
`backend/app/modules/biometrics/release.py`, through
`TurnstileReleaseAdapter.request_release`. Current mode is always simulated.

## Owner-only checklist — pending

Use the existing administrator login at the local frontend. In the current LAN
deployment the administrative panel is `https://192.168.15.64:5173/admin`; the
facial workspace is `/admin/acesso-facial`. Use HTTPS or localhost for webcam
permission. No new password or credential is included in this document.

1. In **Clientes**, fill your own registration data. Confirm submission is blocked
   before facial readiness. Use **Verificar cadastro facial**, allow the webcam,
   press **Capturar rosto**, and finish registration only after success. Record
   any camera/provider failure and verify entered form data survives it.
2. In the instructor/staff registration form, use the same CPF and e-mail. Verify
   shared enrollment is reused without another scan, while registration and
   provisioning complete. Staff-only denial is already covered by controlled
   automated fixtures; do not enroll another person for this check.
3. Open **Acesso facial**, choose **Entrada**, and recognize your face. Verify your
   name and **Simulação: liberação solicitada** appear while occupancy remains 0.
   Confirm passage within 30 seconds: occupancy becomes 1. A repeat entry must
   explain that you are already inside and leave occupancy unchanged.
4. Alternate confirmed entry and exit until recording ten fresh deliberate
   captures of your own face. Record each recognition success/rejection and
   approximate click-to-result duration below; describe camera, lighting and pose.
   Do not classify a correct inside/outside policy denial as a recognition failure.
5. Leave one authorization unconfirmed for over 30 seconds. Confirm no passage
   or count change occurs and a new scan is required. Close the webcam dialog
   and verify the camera indicator turns off.
6. While inside, deactivate your **Client** role from its edit form. Verify a
   recognized exit still works; an entry while inactive is denied. Reactivate it
   afterward. Ordinary account login and face authorization are separate checks.
7. Use **Corrigir presença** with a reason to move yourself inside, then outside.
   Verify the count and named history change together. Choosing the existing
   state must leave the count unchanged. Do not enable profile presence just for
   this test: named presence remains separately opt-in.
8. Test replacement in your person edit form. An unsuccessful capture must retain
   the previous enrollment; a successful replacement must permit recognition.
   Revoke it, verify immediate denial and eventual provider cleanup, then enroll
   again if you want to keep using the pilot. Ordinary login must still work.
9. Confirm an entry, restart the backend using the command below, refresh the
   page and verify occupancy remains 1. Confirm an exit to return to 0. Closing
   the panel stops heartbeat; after more than 120 seconds without another source,
   the existing occupancy display must become stale while preserving the count.
10. Verify filtered recent events, correction reasons and the normal occupancy
    display. Report anything unexpected before this task is marked complete.

| Owner evidence | Result |
| --- | --- |
| Browser, webcam, lighting and pose | Pending |
| Client enrollment and shared staff reuse | Pending |
| Fresh captures 1–10: recognized/rejected and approximate seconds each | Pending |
| Separate release/confirmation, repeat entry and expiry | Pending |
| Inactive exit and denied inactive entry | Pending |
| Corrections and unchanged-state correction | Pending |
| Replacement, revocation and cleanup | Pending |
| Restart, stale heartbeat and preserved count | Pending |

## Startup and recovery

The current `.env` already enables `FACIAL_ACCESS_MODE=pilot` and holds the local
provider credentials. Keep it ignored by Git. Preserve the deployment's existing
LAN HTTPS Compose override when starting services. With the same Compose settings:

```sh
docker compose --profile biometrics up -d compreface-fe
docker compose run --rm --no-deps backend alembic upgrade head
docker compose up -d backend frontend
docker compose run --rm --no-deps backend python scripts/biometric_preflight.py
```

For the owner's restart check, use `docker compose restart backend`; this must
preserve enrollment/history/count. Provider cleanup resumes on startup and each
minute. Keep the panel open for its healthy-source heartbeat. If unavailable,
use **Verificar serviço** and **Consultar resultado**; never infer passage from a
timeout or automatically resend a capture. A new capture remains deliberate.

To suspend face operations, set `FACIAL_ACCESS_MODE=disabled` and recreate the
backend. Ordinary login remains available. Mandatory face registration is not
bypassed. Stop provider services without deleting their volumes when needed;
do not restore revoked faces or reset the database as routine recovery.

`backend/scripts/reset_facial_pilot.py` defaults to inventory. It is limited to
the local Docker endpoints and requires the configured `APP_ADMIN_USERNAME` in
its process environment. Explicit `--apply` is destructive and is only for the
already authorized, pre-enrollment test reset performed above. Stop backend
writes before applying; an interrupted apply must be reconciled before restart.
The script refuses to erase newly enrolled faces and checks its table allowlist
before deleting external identities. Do not run it again for this checklist.

## Remaining completion gates

Owner evidence above is still required. No genuine-face success rate, latency,
calibration or camera compatibility has been measured yet. The single-owner test
cannot establish representative precision >=95%, false acceptance across people,
liveness, complete real-gym eligibility, or physical turnstile readiness. Those
remain separate gates before any additional-person or real-hardware deployment.
Keep this task open until the agreed owner checks are complete. The user explicitly
requested a checkpoint commit of the completed setup before the project inspection;
that commit does not mark the outstanding owner verification as complete.
