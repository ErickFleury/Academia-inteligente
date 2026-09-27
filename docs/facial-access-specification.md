# Facial Access Pilot — Implementation Specification

**Status:** requirements interview consolidated; implementation has not started.
**Scope:** a controlled local pilot involving only the project owner.
**Authority:** `docs/requirements.md` remains the canonical implementation
specification. This document records the user's approved feature decisions and
an implementation design. Apply the explicit canonical amendments in section 2
before implementing affected behavior. It is not a commercial-deployment approval.

## 1. Approved outcome and scope

The owner uses a computer webcam to enroll a face and test client identification.
After recognition and authorization, the application records and displays a
**simulated turnstile unlock request**. It makes no external turnstile call.
The operator separately confirms simulated physical passage; only that action
changes the existing gym occupancy count.

### 1.1 Decisions made in the interview

| ID | Approved decision |
| --- | --- |
| FACE-01 | Local webcam pilot; document a readily discoverable future unlock integration point; persist/display a simulated release event with no external call. |
| FACE-02 | Use the owner's computer and webcam. Dedicated gates, passage sensors, and additional cameras are not required. |
| FACE-03 | Only clients use the access test and count. Staff use a separate door. Enroll staff now for future internal camera tracking, but implement no staff access, attendance, or tracking in this delivery. |
| FACE-04 | Select Entrada or Saída, click to scan, then explicitly confirm simulated passage. Recognition/release alone does not change occupancy. |
| FACE-05 | Both client and staff registration require successful valid facial enrollment before completion. Reuse an existing valid enrollment when adding the second role to the same person. |
| FACE-06 | Local Docker CompreFace, conditional on free software/model use. Necessary enrollment images may remain in its separate local store. No cloud recognition or paid service/model. |
| FACE-07 | One enrollment per shared person, reused by Client and Employee roles. The access scan identifies the person without requesting name/e-mail. |
| FACE-08 | Button-triggered live webcam scans only; no file upload or continuous recognition. Liveness/photo/video spoof detection is deferred, with the limitation documented. |
| FACE-09 | Pilot entry requires a recognized face and an active Client. Membership, payment, modality, and access-allowance checks are deferred explicitly for this pilot. |
| FACE-10 | Recognized clients may exit even when deactivated. Real emergency-door operation belongs to the external hardware system. |
| FACE-11 | After failed recognition or a mistaken test passage, an administrator may correct the client's inside/outside state with a required reason. This creates an audited correction, not a fictional match or unlock. |
| FACE-12 | Reject entry when already inside and exit when already outside; explain the conflict and leave the count unchanged. |
| FACE-13 | No offline authorization or hardware control is requested. Controlled failure and explicit retry preserve the separation between recognition, release, and passage. |
| FACE-14 | Administrators operate enrollment and the pilot now. Attendant workflows are deferred. Instructors cannot manage faces. Future intended enrollment permissions are admin/attendant. |
| FACE-15 | Enrollment in client/staff registration and edit forms; one admin page named Acesso facial containing the test panel, recent events, and corrections. |
| FACE-16 | No agreement/consent workflow or checkbox in this controlled pilot: only the owner participates. This does not establish a policy for enrolling others or future employee tracking. |
| FACE-17 | Keep enrollment material until replacement, explicit revocation, or person deletion. Keep event history until test reset/person deletion. Discard recognition-attempt images after processing. Deactivation blocks entry but retains recognition for exit. |
| FACE-18 | Simulated passages update the existing occupancy page. Do not add a simulation label to that page. The test panel and internal event provenance still identify simulation. |
| FACE-19 | Existing logins are test data; the user authorizes deleting them and their associated data from Keycloak and the application database. No reset has been executed in this documentation task. |
| FACE-20 | Produce this implementation specification first. Implement later in dependency order, with one checkpoint commit per fully completed task. |

### 1.2 Exclusions

No actual turnstile HTTP call, relay control, real passage sensor, staff access,
staff attendance, internal tracking, visitor/minor enrollment, multi-gym/multi-zone
count, continuous CCTV processing, paid provider, cloud biometric processing,
liveness protection, membership/billing implementation, new client attendance
screen, biometric export, or public recognition endpoint is included.

The only real biometric subject in this pilot is the owner. Automated tests use
synthetic fixtures and adapter doubles. Adding other people or deploying physical
access requires a new review of purpose, enrollment policy, security, hardware,
recognition validation, and the deferred business rules.

## 2. Requirement traceability and canonical amendments

### 2.1 Applicable existing requirements

- RF-01–RF-03: client registration/editing and deferred CA-03.4 biometric readiness.
- RF-07/RF-08: employee registration/editing and shared person identity.
- RF-04/RF-05: authenticated operations and backend role enforcement.
- RF-20: authenticated integration contracts, validation, and idempotency;
  physical turnstile mechanics remain external.
- RF-21: known identity, inactive-client entry denial, and recognition quality.
- RF-22: enrollment validation, protected biometric management, safe replacement.
- RF-23–RF-25: client-linked passage history, non-duplicating count, mobile display.
- RN-01/RN-03–RN-10/RN-23/RN-26–RN-28/RN-32–RN-36: identity, authorization,
  separation of recognition/eligibility, failures, privacy, notices/audit,
  timestamps, history, and entry eligibility.
- RNF01–RNF06: performance, usability, responsiveness, maintainability,
  availability/failure isolation, and provider-independent integrations.
- DEC-04/05/09/10/11/12/17/18; EXT-DEC-INST-01 shared identity;
  EXT-DEC-PRES-01 independently consented profile presence.
- `docs/frontend-design.md`: established MUI theme, shared components, admin
  shell, responsive/accessibility behavior, and application text in pt-BR.

### 2.2 Amendments required before feature code

These changes are explicitly supported by the interview. Do not reinterpret
other requirements as implicitly amended.

| Canonical area | Required amendment |
| --- | --- |
| RF-01/03/07/08 and RF-22 | Mandatory valid enrollment for new Client/Employee registration; shared-person reuse; existing login remains independent of biometric readiness. Bootstrap administration is not client/staff registration and needs no scan. |
| DEC-04 / authorization | Explicit, limited admin permission to enroll, replace, revoke, inspect enrollment status, operate tests, view operational events, and correct state. No general biometric payload access. Attendant workflows remain future work. |
| RN-35/RN-36 / DEC-12 | Local simulated entry exception: recognized face + active Client; full membership/payment/modalities/access limits remain unresolved for real access. |
| DEC-09 lifecycle | Provider-owned local enrollment images approved; transient application captures; one person across roles; deactivation retains enrollment for exit. |
| DEC-10/DEC-11 / RF-23–RF-25 | Explicit administrator-confirmed simulated source may feed the existing local count, with internal provenance and no new occupancy-page label. Strict per-client transitions and reasoned person-linked corrections apply to this pilot source. |
| DEC-11 | Simulated release adapter only, plus corrections that never act as a manual turnstile-release bypass. Preserve the future idempotent external adapter boundary. |
| RF-21 quality / DEC-09 | A one-person functional pilot cannot establish population precision. Keep the >=95% measured precision requirement unverified until a representative validation set exists; do not mark it passed based on this pilot or enable real hardware. |
| Verification/roadmap | Add feature tasks and acceptance mapping without reopening unrelated completed tasks or claiming a live hardware integration. |

Promote these approved policies to `docs/requirements.md`, record supporting
history in `docs/decisions.md`, and link this document in the implementation plan.
If inspection reveals another conflict, stop that affected task for a decision.

## 3. Existing implementation and reuse boundaries

Inspected code:

- `backend/app/modules/clients/models.py`: Account, Account-linked PersonProfile
  (primary key `account_id`), Client, Employee, and identity reconciliation.
- `backend/app/modules/clients/service.py` and
  `backend/app/modules/employees/service.py`: registration, shared identities,
  independent role activity, durable Keycloak provisioning; client erasure.
- `backend/app/modules/occupancy/{models,service,router}.py`: hashed external
  client-reference mapping, source-idempotent passage ledger, corrections,
  heartbeats, and reconstructable non-negative count.
- `frontend/src/client-management.tsx`, `employee-management.tsx`,
  `occupancy-page.tsx`, and `components/application-shell.tsx`.

Keep the existing stack: React/TypeScript/Vite, FastAPI/Python modular monolith,
PostgreSQL, Keycloak, Docker Compose. Add a focused `biometrics` backend module
and a provider adapter; do not embed recognition libraries throughout domain
services or add another application backend. CompreFace is an isolated external
local service and may have its own internal stack/database.

Reuse existing occupancy routes and projections. Add protected pilot endpoints
rather than giving a browser the existing machine integration secret. Existing
external ingestion accepts confirmed events independently of recognition; do not
silently apply pilot authorization to externally confirmed physical passages.
No external event producer is configured for this controlled pilot. Mixing a
future real producer with simulated state requires a separate cutover plan.

## 4. Provider and local deployment

### 4.1 Selection and evidence

CompreFace provides Docker deployment, recognition/enrollment REST APIs, and CPU
support. Its application is published under Apache-2.0. The selected software
and model must incur no license fee or subscription. Source:
[official project](https://github.com/exadel-inc/CompreFace) and
[license](https://github.com/exadel-inc/CompreFace/blob/master/LICENSE).

The inspected host is x86_64 with an Intel Core i9-9900K, AVX, and approximately
32 GiB RAM. This fits the documented CPU architecture requirement, but is not a
performance measurement. Source:
[installation](https://github.com/exadel-inc/CompreFace/blob/master/docs/Installation-options.md).

Use the standard CPU deployment initially. The official release page examined
for this specification lists 1.2.0 as latest. Pin verified images by version and
resolved digest. Its default core build selects FaceNet; record the actual model
artifact/version/hash and its applicable terms before installation. Do not infer
model rights from the application's license, swap in an unapproved paid model,
or silently choose a different provider. Sources:
[releases](https://github.com/exadel-inc/CompreFace/releases),
[1.2.0 core build](https://github.com/exadel-inc/CompreFace/blob/v1.2.0/embedding-calculator/Dockerfile),
[FaceNet software license](https://github.com/davidsandberg/facenet/blob/master/LICENSE.md).

Frigate was considered, but its camera-stream/person-detection workflow exceeds
this button-triggered pilot. This is a scope-fit judgment, not a comparative
accuracy claim. No future tracking-provider choice is made here.
[Frigate documentation](https://docs.frigate.video/configuration/face_recognition/).

### 4.2 Configuration and preflight

- Add an explicit Compose profile for biometrics, isolated provider persistence,
  healthchecks, and `FACIAL_ACCESS_MODE=disabled|pilot`; there is no live mode.
- Keep provider API access internal to Docker. If a management UI is needed for
  provisioning, bind it to loopback and a non-conflicting port. Never publish
  the provider on the LAN or embed its API key in React.
- Backend configuration: provider URL/key, detection threshold, match threshold,
  ambiguity margin, model version, bounded timeout, capture limits, and pilot
  mode. Commit examples/placeholders only. Use the existing HTTP client when
  possible; a new SDK dependency is unnecessary for ordinary REST calls.
- Disable CompreFace's optional anonymous statistics during setup; verify no
  recognition/enrollment calls require outbound networking. Image/model downloads
  during installation are distinct from biometric processing. Source:
  [statistics policy](https://github.com/exadel-inc/CompreFace/blob/master/docs/Gathering-anonymous-statistics.md).
- The browser obtains webcam permission through its normal permission prompt
  using the existing HTTPS origin or a supported localhost origin. No custom
  agreement screen/checkbox is added. Stop camera tracks when the view closes.
- Do not expose demographic/age/gender plugins, provider image-download URLs,
  templates, embeddings, or raw provider responses in application APIs.
- Preflight must verify free-use terms, pinned artifacts, startup, camera capture,
  enrollment/deletion, telemetry setting, resource use, and recognition latency.
  Stop provider setup if the approved cost/local-only constraints cannot be met.

Technical defaults below are bounded implementation choices, not claims about
measured performance: one scan in flight per session, 10-second provider request
timeout, no automatic recognition retry, 15-minute staging expiry, 30-second
passage-confirmation validity, JPEG/PNG captures up to 5 MiB and 4096×4096 pixels.
Validate decoded format/size, strip metadata, and reject malformed images before
provider calls. Surface processing and timeout feedback immediately.

Recognition thresholds must be explicit calibrated configuration, never a
hardcoded universal 0.95. Record initial values and model in preflight evidence.
Request enough candidate results to reject ambiguity; do not hide additional
faces by limiting detection to the largest face. Zero/multiple faces, multiple
plausible identities, or a below-threshold result cannot authorize access.

## 5. Enrollment and registration transaction

### 5.1 New person

1. Administrator fills the existing client/staff form. All current identity,
   CPF/e-mail, address, specialized-role, and validation rules remain applicable.
2. Administrator opens the webcam preview and clicks Capturar rosto. Capture is
   explicit; no file upload and no automatic/background recognition.
3. Backend validates the form's identity and image, then creates a bounded
   enrollment session owned by that administrator and bound to intended person
   identity and requested registration role. No Client/Employee is created yet.
4. Persist a staging operation and unpredictable provider subject before the
   provider call. Enroll exactly one accepted face example under that subject.
   Staged subjects are never eligible for access, even if returned by recognition.
5. Return enrollment readiness and an opaque session ID; do not return an image,
   template, provider key, or reusable provider URL. Administrator may retry
   failed capture without losing ordinary form values.
6. Final form submission includes the enrollment session. Under one database
   transaction, revalidate identity and session ownership/expiry/readiness,
   create or link Account/PersonProfile and the requested role, attach the ready
   enrollment, consume the session, and queue existing Keycloak reconciliation.
7. Report completed local registration only with valid enrollment attached.
   Keycloak provisioning may retain its existing distinct pending state. Failed
   provisioning is retried through existing reconciliation, without another scan.

Invalid registration must not leave a partially registered person. An external
provider side effect can outlive a rolled-back database transaction: retain a
minimal durable cleanup job and revoke abandoned staged subjects. Do not claim
cross-system atomicity. Refresh/retry with the same operation ID cannot create
another person or enrollment. An ambiguous provider timeout is reconciled by
staged subject ID; it is never treated as successful enrollment.

### 5.2 Existing person and shared roles

Matching CPF and normalized e-mail identify the shared Account/PersonProfile
under existing rules. Reuse that person's valid enrollment when adding the
second role; the backend verifies reuse, not a client-supplied boolean.
If enrollment is missing/revoked, require a successful scan before role creation.

Edit forms show enrollment status and administrator capture/replace/revoke
controls. They do not expose stored face images. Ordinary personal-data edits
remain possible without rescanning. Facial similarity alone never merges two
accounts or overrides CPF/e-mail identity; ambiguous cross-person matches are
rejected for review. The same person must use the existing shared identity.

### 5.3 Replacement, revocation, and deletion

- Replacement enrolls a new staged subject first, atomically switches the current
  reference after success, then revokes/deletes the former subject through a
  durable cleanup job. Failure preserves the previous usable enrollment.
- Only the current enabled version can authorize an attempt. Old references and
  in-flight attempts tied to superseded/revoked enrollment cannot be confirmed.
- Revocation immediately disables backend use and invalidates pending attempts;
  delete provider material with retryable reconciliation. Camera failure or
  revocation cannot silently disable ordinary application login.
- Deactivation is different from revocation: deny entry but retain facial data
  so an already-inside client can be recognized for exit.
- Removing one role preserves enrollment while the shared person still has the
  other role. Removing the entire person deletes all provider material and local
  biometric references, events, state, and staged data attributable to them.
- Extend existing erasure rather than creating a competing partial erasure path.
  Remove deleted-client passages and person-linked corrections together so the
  reconstructed pilot count remains consistent. No identifying tombstone is
  retained after full erasure; remove cleanup references once deletion succeeds.
- Show pending provider cleanup to admins without raw provider responses. An
  interrupted deletion must resume after restart rather than silently succeeding.

## 6. Access test, release trigger, and passage

### 6.1 Operator flow and authorization

Only an authenticated active administrator may use Acesso facial. The scanned
person does not sign in to the kiosk/panel; browser authorization belongs to the
operator. Show direction controls Entrada/Saída, webcam preview, Reconhecer rosto,
result, and a separate Confirmar passagem button when allowed.

| Condition | Result |
| --- | --- |
| Unknown, ambiguous, no face, multiple faces, below threshold, revoked/staged subject, provider failure | No release request and no passage. Explain the failure; offer at most one additional capture in this logical attempt. |
| Staff-only person | No client access release/count change; staff access is outside the pilot. |
| Entry: active Client, valid enrollment, currently outside | Create one simulated release request; allow passage confirmation. |
| Entry: inactive Client or already inside | Deny, explain, and preserve count. Employee activity does not override Client inactivity. |
| Exit: recognized Client with valid enrollment, currently inside | Create simulated release request regardless of Client/Account login-active status; allow confirmation. |
| Exit: currently outside | Reject inconsistent transition; preserve count. |

Use `Client.active` for pilot entry eligibility; do not infer it from Employee
activity or Keycloak roles. Ordinary account-login checks apply to the admin
operator, not to a recognized client's eligibility to leave.

Start a new logical attempt only by explicit user action. Store direction on
attempt creation; changing direction cancels the pending attempt. A retry after
failed recognition belongs to that attempt and is bounded to two captures total.
A successful scan does not start a loop or repeatedly emit requests.

### 6.2 TURNSTILE_RELEASE_REQUESTED — integration locator

**Stable search marker:** `TURNSTILE_RELEASE_REQUESTED`.
**Planned module:** `backend/app/modules/biometrics/release.py`.
**Planned boundary:** `TurnstileReleaseAdapter.request_release(request)`.
These are implementation targets, not claims that the files/functions exist.

The authorization service reaches this boundary only after a successful match
and positive policy decision. The pilot adapter persists/returns a simulated
acknowledgement and makes no external network call. Show
“Simulação: liberação solicitada” in the test panel. The administrator-facing
result may include the client's name; the adapter payload must not.

Minimum provider-neutral release contract:

| Field | Meaning |
| --- | --- |
| `release_request_id` | Application-generated UUID; unique logical release; reused on retry. |
| `recognition_attempt_id` | Correlates the recognized/authorized attempt. |
| `occurred_at` | Server UTC timestamp with explicit offset in JSON. |
| `checkpoint_id` | Pilot checkpoint identifier, `pilot-webcam`. |
| `direction` | `entry` or `exit`, fixed for this attempt. |
| `subject_reference` | Opaque current biometric/access reference; no name, e-mail, CPF, Client UUID, image, or template. |
| `mode` | `simulated` in this delivery. |

Enforce one release per logical attempt with a database unique constraint. Retry
or polling returns the existing result. A future hardware adapter must keep
idempotency and separate credentials, but is not implemented now. Record the
exact final symbol, schema, configuration and test paths in this section when
implemented so the later external integration is easy to locate.

### 6.3 Confirmed passage and concurrency

Confirmar passagem explicitly simulates one physical passage within 30 seconds
of the successful result. A stale/canceled/superseded attempt requires a new scan.
Backend rechecks enrollment, direction, inside/outside state, and entry activity;
for exit it still ignores client deactivation. Never rely solely on UI disabling.

Lock per-client state, validate its expected revision, insert one source-marked
passage, update state and consume the attempt in the same database transaction.
Use a unique passage event ID derived from the logical attempt and preserve it on
retry. Two tabs racing to confirm cannot apply two transitions; exact retries
return the prior successful result. A stale different attempt returns a conflict.
Serialise count-affecting changes as needed to keep ledger/count consistent.

Confirmed entry moves outside → inside (+1); confirmed exit moves inside → outside
(-1). A new client begins outside after the clean pilot reset. Never decrement
below zero, create an exit merely because a result says recognized, or infer
passage from an adapter acknowledgement. Abandoned scans/releases add nothing.

### 6.4 Administrator correction

On the same page, select a client, desired state Dentro/Fora, and a required
non-blank reason (up to 1,000 characters). Show existing state before submission.
Backend locks state, checks revision, and records actor, client, timestamp,
previous/target state, and reason. Append the corresponding signed occupancy
correction and update state atomically. No-op submissions leave count unchanged;
retries are idempotent. Corrections invalidate that client's pending attempts.

Do not overwrite passage history, claim recognition, or create a release request.
This is the pilot fallback for failed recognition, revoked enrollment, missed
passage, or an operator mistake. Real emergency egress remains outside software.

## 7. Data model, APIs, and retention

### 7.1 Minimum persisted records

| Record | Required relationships and invariants |
| --- | --- |
| BiometricEnrollment | Unique current enrollment per shared person (`PersonProfile.account_id`); opaque subject, generation/revision, enabled/revoked state, provider/model identifier, lifecycle timestamps. No image/template bytes in application DB. |
| EnrollmentSession | UUID, admin actor, identity binding, intended operation/role, staged provider subject, state, expiry, consumed result; reusable only by that actor for that person/operation. |
| BiometricCleanupJob | Provider subject and pending delete/reconcile state, bounded retry metadata; no raw capture. Survives local registration rollback. |
| RecognitionAttempt | UUID, admin actor, checkpoint, direction, capture count, result code, nullable person/client and enrollment revision, server times, expiry, state revision, terminal/confirmed state. |
| ReleaseRequest | Unique recognition-attempt relationship and request ID, opaque subject/checkpoint/direction, simulated outcome and timestamp. |
| ClientAccessState | Unique Client, inside/outside, monotonically increasing revision, last state-changing event. Reconstructable from passages/person corrections; not the sole source of truth. |
| Existing passage/correction ledger | Preserve existing fields/contracts; add pilot source/provenance and nullable person-correction metadata where needed, with unique command IDs. |
| Biometric audit | Actor, affected person, operation, outcome code, time and safe correlation IDs; append-only during normal use, erased under the approved person-deletion/reset lifecycle. |

The existing ClientAccessReference permits one active mapping per Client. Reuse
or migrate it to point at the current enrollment reference digest, update it
atomically on replacement, and retain historical passage digests unchanged.
Staff-only enrollment has no client occupancy mapping. Shared-role linking adds
that mapping when a Client is created. Do not use provider references as local
person primary keys.

### 7.2 Protected API contract

Use a consistent `/biometrics` router with admin authorization on every endpoint;
final path spelling may follow repository conventions without changing behavior.
All mutation commands carry a UUID idempotency key. A replay with conflicting
operation identity/direction/target returns 409; never repurpose an old command.

| Method/path | Input and result |
| --- | --- |
| `POST /enrollment-sessions` | Registration identity/role or existing person operation; returns owned staging session and expiry. |
| `POST /enrollment-sessions/{id}/capture` | Bounded multipart webcam image and command ID; returns ready/rejected/pending status, never image bytes. |
| `GET /enrollment-sessions/{id}` | Owned staging/cleanup status for recovery from interrupted requests. |
| Existing client/employee create endpoints | Add enrollment session ID or backend-verified shared-enrollment reuse; atomically consume/attach at registration. |
| `GET /people/{id}/enrollment` | Minimal status/revision for admin forms. |
| `POST /people/{id}/enrollment/replacement` | Commit a ready owned replacement session with expected revision. |
| `POST /people/{id}/enrollment/revocation` | Explicit revocation, expected revision, and operation ID; returns local-disabled/provider-cleanup state. |
| `POST /access-attempts` | Direction and command ID; returns attempt ID. |
| `POST /access-attempts/{id}/capture` | Image plus capture command ID; records recognition, policy result and any simulated release. |
| `POST /access-attempts/{id}/passage` | Command ID; validates and confirms the simulated passage once. |
| `POST /state-corrections` | Client ID, target state, expected revision, reason, command ID. |
| `GET /events` | Bounded newest-first cursor history; filter by client, result and direction; default 20, maximum 100. |
| `POST /pilot-heartbeat` | Authenticated panel heartbeat; backend checks pilot/provider readiness before updating source freshness. |

Keep typed domain/result codes with pt-BR frontend messages. HTTP 401/403 enforce
identity/permission; 404 hides unavailable records; 409 represents stale state
or conflicting command; 422 covers invalid input/capture; 503 covers unavailable
provider; timeout produces a controlled external-service failure. A normal
unknown/denied recognition is an explicit result, not a server crash.

Persist idempotency results before reporting success. Do not auto-replay an image
capture after an uncertain timeout. Poll the operation or reconcile its provider
subject; any new capture is deliberate and separately identified. Bind attempts
and sessions to their operator; do not accept an arbitrary browser-supplied
recognized person, score, enabled flag, provider subject, or authorization result.

### 7.3 Retention and isolation

CompreFace's standard API retains enrollment examples and supports image/subject
deletion. This storage is explicitly approved. Its API also exposes image
retrieval: application routes must not proxy that feature. Source:
[REST contract](https://github.com/exadel-inc/CompreFace/blob/master/docs/Rest-API-description.md).

Enrollment examples stay only in isolated local provider storage until replaced,
revoked, or the person is erased. Discard browser/backend capture buffers once
processed or canceled; do not retain attempt pictures, video, or exported images.
Cleanup of expired/abandoned sessions runs at least once per minute and on startup;
failed provider cleanup remains visible/retryable and the subject remains denied.

Keep minimal operational event/audit history until test reset or person deletion.
Do not copy facial material, raw responses, access secrets, or scores/images into
ordinary logs, shared reports, training AI context, social profiles, or exports.
No new backup/export workflow is introduced. If local volumes are manually backed
up, those copies require the same lifecycle and must not restore revoked subjects
as enabled; this pilot provides no claim of deletion from unmanaged copies.

No consent/agreement workflow, checkbox, or participation notice is implemented
for the owner's controlled self-test. Normal browser camera permission and useful
camera/error guidance remain. Document lack of liveness in the admin test page
and feature documentation; do not add a simulation label to the occupancy page.

## 8. Occupancy, history, and failure behavior

Use the existing aggregate-only occupancy API and page, including its normal
current/stale feedback. Persist source provenance internally; add no simulation
badge or text to that page per the user's instruction. Do not expose names or
passage history there. The admin test history may show names, direction, time,
result, correction reason and safe request IDs, but no images/templates.

While Acesso facial is open and its backend/provider are healthy, send the
existing logical source heartbeat every 60 seconds for `pilot-webcam`. The
existing 120-second freshness boundary applies. Closing the panel or losing the
provider eventually makes the source stale; the last count stays visible.
Do not send a fabricated healthy heartbeat merely because the page is open.

Count/state survive refresh and restart. Do not reset at midnight, on logout, or
when a client is deactivated. Administrator corrections fix mistakes; the
explicit full test reset is an operational setup procedure, not an automatic
scheduled action. Existing profile-presence preference remains independent;
recognition alone never makes a person socially visible. Verify that per-client
corrections do not leave a contradicted presence tag based on an older passage.

| Failure | Required outcome |
| --- | --- |
| Webcam unavailable/permission denied/invalid capture | Clear retry guidance; registration stays incomplete; no fake enrollment. |
| Provider unavailable/timeout | Controlled error; no match/release/passage; retain existing usable enrollment on failed replacement. |
| Unknown or ambiguous match | No nearest-candidate acceptance; one additional capture, then end attempt. |
| Database failure before commit | No successful response; exact retry/reconciliation resolves persisted outcome without duplicate state changes. |
| Crash after provider enrollment but before attachment | Durable staged subject reconciled or deleted; no orphan accepted as an enabled person. |
| Revocation/deactivation/replacement while a scan is pending | Revalidate at confirmation; deny stale enrollment or new entry after deactivation; permit valid recognized exit. |
| Double click/concurrent confirmations or corrections | One atomic state transition; exact retry is idempotent; other stale commands conflict. |
| Restart | Rebuild/check state from ledger, resume cleanup, preserve history/count; do not replay expired release attempts. |

## 9. UI and permissions

Add Acesso facial to the existing admin navigation, with one page containing:

1. Webcam test panel and Entrada/Saída selection, explicit capture, result,
   simulated release acknowledgement, and separate passage confirmation.
2. Recent events with bounded pagination and basic client/direction/result filters.
3. Client state correction controls with required reason and clear confirmation.
4. Provider unavailable/cleanup pending status and a short liveness limitation.

Add a reusable capture component to client/staff forms: camera preview, capture,
retry, readiness/error, replacement and revocation. Show shared enrollment reuse
when adding a second role. Keep current form data after recoverable scan errors.
Do not expose provider configuration or embeddings as product controls.

Use existing MUI theme/AdminShell from `components/application-shell.tsx` and
existing routing conventions. pt-BR labels, keyboard/focus management, clear live
status feedback, associated form errors, and phone/tablet/desktop layouts are
required. Camera support failure has a useful state rather than an empty panel.

| Actor | Permission in this delivery |
| --- | --- |
| Admin | Enrollment/status/replacement/revocation, registration, test panel, recent events, person-state corrections. |
| Instructor/Employee | No biometric-management or access-panel permission, even if their own face is enrolled. |
| Client | Existing aggregate occupancy and existing permitted app functions only. |
| Attendant | New feature workflow deferred; existing unrelated permissions remain unchanged. |
| Anonymous | No capture, enrollment, recognition, history or correction. Preserve existing aggregate API policy. |

Audit critical enrollment/configuration changes and show their outcomes in the
admin recent-event/status view; no email, Slack, or new notification system is
introduced. Users cannot arbitrarily edit/delete audit rows. Approved complete
person erasure and test reset remain distinct operations.

## 10. Authorized test-account reset

Do this only in the identified local test deployment during implementation setup,
after code/database checks and before real self-enrollment. The user's existing
authorization covers deleting test logins from Keycloak and the application DB;
no account was deleted while writing this specification.

Inventory only IDs/counts needed to establish the target; do not print secrets or
export personal records. Remove test identities and all linked test-person data,
including shared client/staff records, provisioning jobs, plans, onboarding,
social data, passage/correction history and any biometric material. Reconcile
across Keycloak/provider/database instead of treating one successful deletion as
proof of complete reset. Clear pending account jobs that could recreate users.

Preserve/recreate the environment-configured bootstrap application administrator
and Keycloak administration/service identities so the owner can register again.
Keep realm/client/role configuration, migrations, application configuration and
unrelated gym/equipment catalog. Do not indiscriminately remove Docker volumes.
The bootstrap admin is not required to enroll before administering the system.
Verify admin login, zero test-person identities/orphan data, zero occupancy and
no stale client access references. Reset credentials never go into Git or docs.

## 11. Acceptance criteria and verification

| ID | Required evidence |
| --- | --- |
| FACE-CA-01 | Both registration APIs/UI reject missing/invalid enrollment; successful scan enables registration; failed enrollment creates no partial Client/Employee and abandoned provider material is cleaned. |
| FACE-CA-02 | Same-person second-role creation reuses enrollment; conflicting CPF/e-mail remains rejected; staff-only scans cannot enter/count as clients. |
| FACE-CA-03 | Only admin may operate new endpoints; direct client/instructor/anonymous calls fail; cross-operator sessions/attempts cannot be consumed. |
| FACE-CA-04 | Capture is live, button-triggered, bounded and single-face; no background recognition; camera tracks stop when closing. |
| FACE-CA-05 | Failed replacement preserves old enrollment; successful replacement disables old reference; revocation immediately denies use and cleanup resumes after restart. |
| FACE-CA-06 | Entry requires a valid recognized active Client outside; exit accepts recognized inside Client despite deactivation; unknown/ambiguous/low-score results never authorize. |
| FACE-CA-07 | Successful authorization produces one persisted/displayed simulated release; no actual turnstile call; stable trigger locator and adapter contract are documented. |
| FACE-CA-08 | Scan/release without confirmation leaves count unchanged; one timely confirmation transitions state/count exactly once; stale, repeated and concurrent transitions do not double-count. |
| FACE-CA-09 | Reasoned admin correction updates client state and count atomically with audit; no forged match/release; repeated/no-op corrections do not drift. |
| FACE-CA-10 | Existing occupancy page shows the updated count with normal stale handling and no new simulation label; no identities leak to aggregate views. |
| FACE-CA-11 | Local-only provider behavior, no paid dependency, no browser API key, no ordinary image/template endpoint, no sensitive logging or AI context; attempt captures transient. |
| FACE-CA-12 | Shared-role removal preserves needed enrollment; full person erasure removes associated local/provider data and leaves coherent count; reset verified in both Keycloak and database. |
| FACE-CA-13 | Provider/camera/database failure and restarts follow section 8; bounded retries and cleanup; unrelated app functions remain usable. |
| FACE-CA-14 | Admin forms/page work at 360×800, 768×1024 and 1366×768 with keyboard focus, understandable feedback and no horizontal page overflow. |
| FACE-CA-15 | No agreement workflow, staff tracking/attendance, attendant provisioning, continuous recognition, real release, or membership billing introduced. |
| FACE-CA-16 | Record actual model/threshold, latency and self-test evidence without claiming measured population precision or liveness. Real-hardware quality gate remains unverified. |

Automated tests must not contact real CompreFace, Keycloak, a camera, or hardware.
Use adapter doubles for enrollment/recognition/release and real PostgreSQL tests
for transaction, uniqueness, erasure and concurrency behavior. Regression scope
includes registration, employees, shared identity/provisioning, erasure,
occupancy, profile presence, and frontend forms/shells.

Suggested existing checks (adjust new test filenames to final modules):

```sh
docker compose run --rm --no-deps -e TEST_POSTGRES=1 backend pytest -q
docker compose run --rm --no-deps backend ruff check .
docker compose run --rm --no-deps frontend npm test
docker compose run --rm --no-deps frontend npm run lint
docker compose run --rm --no-deps frontend npm run build
git diff --check
```

Run focused tests per task; run the broader suites when registration/shared
identity and occupancy integration land. Do not repeatedly rerun passing suites
without a new change or unresolved issue.

Manual owner-only verification: enroll through each registration journey (reuse
the shared identity for the second role), capture ten fresh genuine attempts
under documented lighting/pose, record successes/rejections and latency, and
exercise entry/release/no-passage/confirmation/repeated-entry/deactivation/exit/
correction/replacement/revocation/restart. Verify unknown-reference and negative
outcomes with controlled fixtures; never present fixtures as live accuracy data.
Target common app operations within the existing two-second RNF01 boundary;
report scan latency separately against the bounded provider timeout.

A single owner's face cannot validate false-acceptance rates across people or
representative `TP/(TP+FP) >= 95%`. That original acceptance criterion remains
unverified. Its eventual protocol must specify representative genuine/impostor
samples, model/camera/lighting/threshold, precision, false acceptance/rejection
and latency. This pilot's successful functional completion does not satisfy it.

## 12. Dependency-ordered implementation tasks

Each row is a focused checkpoint, completed/tested/reviewed before its commit.
Task identifiers here are feature-local; assign global roadmap numbers when
updating the implementation plan.

| Task | Deliverable and completion boundary |
| --- | --- |
| FACE-IMPL-01 | Canonical amendments from section 2, provider/model free-use evidence, pinned Compose profile and local adapter preflight; no real face enrolled and no hardware calls. Stop if approved provider constraints cannot be satisfied. |
| FACE-IMPL-02 | Biometric data model/migration, staging, provider adapter, safe replacement/revocation and cleanup; unit/API/PostgreSQL tests pass. |
| FACE-IMPL-03 | Mandatory enrollment integrated atomically into both registration flows and shared-role reuse; admin capture/edit components, Keycloak/erasure integration and regression tests pass. |
| FACE-IMPL-04 | Recognition attempts and separate entry/exit authorization; simulated release adapter, idempotency, result codes and precise trigger documentation; no count change yet. |
| FACE-IMPL-05 | Confirmed-passage state machine, person corrections, count reconstruction, heartbeat and presence consistency; concurrency/restart/privacy tests pass. |
| FACE-IMPL-06 | One Acesso facial admin page with test panel/history/corrections; responsive/accessibility checks and integrated frontend/backend regressions pass. |
| FACE-IMPL-07 | Authorized local test-account reset and owner-only enrollment/flow validation; document evidence, actual model/configuration, unresolved technical limitations, startup/recovery instructions. No claim of representative accuracy or physical deployment readiness. |

Do not delete existing test accounts until the new registration flow is usable.
Do not commit biometric data, credentials, captures, provider databases, or test
exports. Record reset outcomes as counts/status only. A failed task stays open;
a partially functioning enrollment/release flow is not a completed checkpoint.

Rollback/recovery: disable the pilot endpoints through configuration, leave OIDC
and unrelated modules operating, stop the provider profile without deleting its
volume, and retain database schema/history while resolving the fault. Disabling
the feature must not bypass mandatory enrollment for new registrations. Do not
restore revoked subjects or silently downgrade to old code that accepts new
un-enrolled registrations. Destructive rollback/data restoration requires a
specific reviewed procedure; schema downgrades are tested on disposable data.

## 13. Completion and remaining gates

The product questions for this controlled, owner-only pilot are resolved above.
No implementation, installation, facial capture or account reset was performed
by this documentation task. Only this new specification file was changed.

Before affected code: canonical amendments are mandatory. Before provider use:
pin/verify the exact free-use model and service artifacts and calibration settings.
Before any real hardware or additional-person rollout: resolve full eligibility,
privacy/participation policy, liveness/security, hardware protocols, and measured
recognition quality. Those are explicit future gates, not hidden pilot features.

At each implementation checkpoint report files changed, tests/evidence, important
decisions and unresolved issues, then commit as requested. Stop and ask when a
new functional decision or canonical conflict appears. Do not mark RF-20's
external integration, RF-21's population precision, or real physical-access
operation complete on the strength of simulated events.
