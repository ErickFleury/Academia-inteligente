# Architectural decisions

## DEC-03 — Technology and architecture decisions

**Status:** approved — 2026-09-20

The MVP uses a modular-monolith architecture. Authentication is provided by
Keycloak through OIDC.

### Keycloak login-theme amendment — 2026-09-22

Keycloak uses the repository-managed `academia` login theme for the
user-facing authentication experience. The theme is mounted into the Keycloak
container by Docker Compose and selected by the managed `academia` realm, so a
clean local deployment does not require an admin-console theme selection. It
follows `docs/frontend-design.md`, including Portuguese copy, responsive
behavior, accessible focus/error states, and the application's visual tokens.
It extends the supported Keycloak `keycloak.v2` login theme through resources
and CSS rather than replacing authentication templates unnecessarily.

This is presentation/deployment integration only: Keycloak continues to own
credentials, required actions, errors, sessions, and OIDC behavior. It does
not alter roles, provisioning, account activity, PKCE, redirect URIs, or token
handling.

| Area | Approved decision |
| --- | --- |
| Main architecture | Modular monolith |
| MVP backend | Python only; NestJS has no MVP responsibility and must not be scaffolded or introduced |
| Future NestJS use | Requires an explicit decision in a future task |
| Python runtime | 3.13.15 |
| Backend framework | FastAPI 0.141.1 |
| Backend container image | `python:3.13.15-slim-trixie` |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Frontend | React + TypeScript + Vite |
| UI | MUI |
| Authentication | Keycloak using OIDC |
| E-mail | SMTP behind an integration layer |
| Development e-mail | Mailpit in Docker |
| Infrastructure | Docker Compose |
| Deployment target | Linux host running Docker Compose |
| Firewall | Host-level UFW; do not expose internal services, including PostgreSQL, directly to the Internet |
| Frontend tests | Vitest + React Testing Library |
| Backend tests | pytest with FastAPI `TestClient`; do not use Jest or Supertest for the Python backend |
| Hosting provider | Undecided |

### ORM and database access amendment

The MVP remains Python/FastAPI only. Prisma is replaced by SQLAlchemy 2.x.
Alembic is the migration tool and psycopg 3 is the PostgreSQL driver. Database
access is synchronous unless a later task explicitly approves asynchronous
behavior.

### Task 01 version baseline

| Tool or image | Selected version |
| --- | --- |
| Node.js | 24.21.0 LTS |
| React and React DOM | 19.3.0 |
| TypeScript | 5.9.3 |
| Vite | 8.3.0 |
| PostgreSQL image | `postgres:18.6-bookworm` |
| Keycloak image | `quay.io/keycloak/keycloak:26.6.3` |
| Mailpit image | `axllent/mailpit:v1.30.7` |
| SQLAlchemy | 2.0.54 |
| Alembic | 1.20.0 |
| psycopg | 3.3.6 |
| pytest | 9.1.1 |
| Ruff | 0.16.8 |
| MUI | 9.0.0 |
| Vitest | 4.1.11 |
| React Testing Library | 16.3.0 |
| Docker Compose | v2.26.1 or compatible v2 tooling |

The Node LTS baseline favors a currently supported runtime. Stable releases and
official images are used where available; container images are pinned to exact
tags, while the JavaScript lockfile pins exact package versions. Prisma, Jest,
and Supertest are intentionally absent because the approved MVP backend is
Python/FastAPI. Major-version changes require explicit approval in a later task.

## DEC-04 — Roles and account provisioning

**Status:** approved — 2026-09-20

**Session-renewal amendment — 2026-09-22:** An authenticated browser session
uses OIDC refresh-token rotation to renew access tokens while the user remains
active. Five consecutive minutes without authenticated browser activity ends
the local session; no automatic refresh occurs after that boundary. Access and
refresh tokens remain only in browser `sessionStorage`, are cleared on timeout,
refresh failure, or sign-out, and are never persisted in PostgreSQL, URLs, or
application logs. Keycloak's realm and client idle-session limits match the
five-minute inactivity policy. This does not change `account_active`, role
authorization, or physical-access eligibility.

Keycloak realm roles are `client`, `employee`, `attendant`, `instructor`, and
`admin`. Attendant and instructor are specialised employee roles.

- There is no public employee or administrator registration.
- The initial application administrator is provisioned by the Keycloak realm
  bootstrap using environment-provided credentials; credentials are never
  hardcoded or committed.
- Client accounts will be provisioned by the client-registration flow. Employee
  accounts will be provisioned by the later administrative employee-management
  flow.
- Attendants may manage biometric enrolment when that module exists, but may not
  access client medical or health information.
- Instructors may access health information only when it is functionally needed
  for training-plan work. Administrator status does not by itself grant
  unrestricted medical-information access.

### Client identity-provisioning amendment

**Status:** approved — 2026-09-20

Administrative client creation must provision a corresponding Keycloak user.
The Keycloak e-mail must equal the normalized local `account.email`, and the
resulting OIDC `sub` must be stored in `account.keycloak_subject`; application
and client UUIDs remain independent from that external identifier under
DEC-17. Later authorized e-mail changes must preserve the same subject linkage
and keep the Keycloak e-mail synchronized with the local authoritative value.

- A newly provisioned client receives only the `client` realm role. Client
  creation must never grant `admin` or another employee role, and backend
  authorization must continue to reject client access to administrative APIs.
- The administrator does not choose a permanent client password. Keycloak owns
  all credentials and must send the client through its secure first-access
  required-action flow to define a password. PostgreSQL stores no password,
  temporary credential, reset token, or equivalent authentication secret.
- Public self-registration remains disabled. Provisioning is initiated only by
  an authorized administrative operation.
- `account.account_active` remains the application-login authority described by
  DEC-05. Physical gym-entry eligibility remains a separate concern.
- Local client registration succeeds once the Account/Client pair and its
  durable reconciliation record are persisted. It must explicitly report
  identity provisioning as pending, not claim that the client can log in. The
  Keycloak reconciliation is scheduled independently for each client, so a
  pending identity never blocks another administrative registration. Identity
  provisioning succeeds only once the Keycloak user, exact role assignment,
  local account/client, and persisted subject linkage are consistent.
  External/local partial failures require explicit compensation or durable
  reconciliation, controlled errors, and idempotent retry behavior; an orphan
  identity or unlinked usable account must not be silently accepted.
- Existing local accounts with a null `keycloak_subject` are not assumed to
  have usable identities. They require explicit provisioning/reconciliation.

### Task 06 implementation record

Cross-system creation and e-mail synchronization use durable local
reconciliation state. Creation first persists the local Account/Client pair and
returns a visible pending-provisioning state; a background reconciliation
attempt is scheduled per client, with an authorized retry path if it fails.
Keycloak creation, role mapping, and required-action delivery are retried
idempotently using a reconciliation identifier stored as a Keycloak user
attribute; a client-role token without a linked local account is rejected by
the application. The reproducible local first-access procedure is documented
in `README.md`.

## DEC-05 — Account activity and physical-access eligibility

**Status:** approved — 2026-09-20

`account_active` alone determines whether an identity may authenticate to the
application. An inactive account must not authenticate normally.

`gym_access_enabled` is a separate physical-entry state. An active client can
log in even without biometrics, a valid/current enrolment, payment/access
eligibility, or physical-entry permission, so they can complete onboarding,
manage account-related flows, or make payments. Physical-entry authorization
will be evaluated separately when the applicable biometric, enrolment, payment,
modality, and access-count modules are implemented.

### RF-03 MVP clarification

**Status:** approved — 2026-09-20

For Task 05, authorized administrators may update basic client profile data and
the application `account_active` state. An inactive account must be rejected by
application authentication, while its client and historical relationships are
preserved. `account_active` remains independent from physical-entry eligibility.

CA-03.4 is explicitly pending: it requires the RF-22 biometric photo flow and
must not be treated as satisfied or approximated until that dependency is
explicitly implemented and approved.

## DEC-06 — Onboarding invitation token policy

**Status:** partially approved — 2026-09-20

This approval resolves only the onboarding invitation-token portion needed by
RF-09 and Tasks 07 and 09. The onboarding schema, required fields, editability, and
other DEC-06 matters remain unresolved.

- An `onboarding_invitation` token is cryptographically random, bound to exactly
  one client, and expires 24 hours after issuance.
- It is single-use. It is consumed only after a valid intentional redemption,
  never by passive URL validation/GET, so mail scanners and prefetchers do not
  invalidate it.
- Issuing a new invitation invalidates every prior unused invitation token for
  that client. Only the newest valid token is redeemable.
- Expired, used, invalid, or wrong-client tokens receive a controlled response
  without revealing unnecessary account/client information. They are not renewed
  automatically; an authorized flow may issue a replacement invitation.
- The application persists only a secure token hash/verification representation,
  never the raw token. Raw tokens must not appear in application logs.
- The invitation is not a permanent authentication mechanism. After a successful
  redemption, later own-onboarding access uses the normal authenticated-client
  context when available; the link is not reused for later edits.

### Onboarding schema amendment

**Status:** approved — 2026-09-21

Structured onboarding fields are authoritative. Conversational onboarding may
later populate the same fields but may not replace validation or persistence.
The approved minimum schema is:

| Field | Type and validation | Draft/completion rule |
| --- | --- | --- |
| `training_goal` | Trimmed text, required for completion, 1–500 characters. | May be absent in a partial draft. |
| `training_experience` | Required enum: `none`, `beginner`, `intermediate`, or `advanced`. | May be absent in a partial draft. |
| `height_cm` | Integer in centimeters, greater than 0 and at most 300. | May be absent in a partial draft. |
| `weight_kg` | Decimal kilograms, greater than 0 and at most 500, with at most 2 decimal places. | May be absent in a partial draft. |
| `has_limitations_or_complaints` | Required boolean for completion. | Its detail is required only when true. |
| `limitations_or_complaints` | Trimmed text, at most 2,000 characters. | Required and non-empty when the corresponding boolean is true; otherwise null. |
| `uses_medications` | Required boolean for completion. | Its detail is required only when true. |
| `medications` | Trimmed text, at most 2,000 characters. | Required and non-empty when the corresponding boolean is true; otherwise null. |
| `has_health_conditions` | Required boolean for completion. | Its detail is required only when true. |
| `health_conditions` | Trimmed text, at most 2,000 characters. | Required and non-empty when the corresponding boolean is true; otherwise null. |

The physical ranges are technical sanity checks, not medical judgments. The
free-text health fields are client-reported information: the application does
not diagnose, infer dosage advice, or create a medical-diagnosis vocabulary.
BMI is not persisted; any future BMI use derives it from approved source data.

An onboarding starts in `draft`. The authenticated owning client may save
partial draft progress when supplied values individually satisfy their
type/range rules; reopening the draft returns persisted values. Draft saves
update the current draft without creating a history version for each save.

Completion requires all four training/physical values, explicit values for all
three booleans, and every conditional detail required by a true boolean. Task
10 provides the validation boundary; Task 12 performs the explicit atomic
`draft` to `completed` transition and records `completed_at` only after that
same validation succeeds.
After completion, client edits are disabled and completed information is not
silently overwritten; a future approved revision/replacement flow is required.

## DEC-07 and DEC-15 — Training version lifecycle, review, and manual authoring

**Status:** resolved for Task 13 — 2026-09-22

Each training-plan version has exactly one lifecycle state: `proposal`,
`approved`, `current`, or `superseded`. AI and an instructor may create a
proposal. Both may edit proposal content, but every write uses concurrency-safe
revision checking so one actor cannot silently overwrite another actor's work.

Only an identity with the `instructor` role may formally approve and activate a
version. AI may never approve or activate a plan. Approval records
`approved_by` and `approved_at`; all versions record `created_by`, `created_at`,
and whether their original source was `ai` or `instructor`. Task 13 temporarily
uses the authenticated Keycloak instructor identity directly; it does not
create a full local instructor profile.

An instructor may create a complete manual proposal without AI. A minimum plan
version contains plan name, objective, and ordered exercise items with exercise
name, sets, repetitions, load/load guidance, and rest. The manual and AI flows
are respectively:

`instructor proposal → instructor edit → instructor approve → instructor activate → current`

`AI proposal → AI/instructor edit → instructor approve → instructor activate → current`.

At most one version per plan may be `current`. Activating an approved version
atomically supersedes the previous current version. Content in `approved`,
`current`, and `superseded` versions is immutable. A later change creates a new
proposal version, preserving all earlier versions and their items unchanged.
Completed-workout history is not rewritten by version changes. Task 13 records
the lifecycle/audit metadata; full instructor profile, exercise catalog, AI
generation, and completed-workout workflows remain future tasks.

**Task 14 amendment — 2026-09-22:** AI training generation is not automatically
blocked by a health-risk classification. Relevant client-reported health,
medication, limitation, and complaint data must influence the structured
proposal, but may not prevent its creation. The safety control is mandatory
instructor review: AI creates only a `proposal` and can never approve or
activate it. This is the approved current interpretation of CA-15.4 and RN-13.

**Task 15 amendment — 2026-09-22:** a client may have at most one `current`
training plan across all of their plans. Activating an approved version makes
any previously current plan for that same client `superseded`, preserving its
version and item history. This adds a client-wide current-plan invariant without
changing the established version states or instructor-only activation rule.

**Task 17 amendment — 2026-09-23:** AI-generated training adaptations are
retained structured proposals, distinct from raw training chat and from a
training-plan version. An adaptation is generated only after the client has
explicitly confirmed that they want a proposal; ordinary Task 16 chat remains
conversational and read-only. A proposal may add, remove, replace, or adjust
one or more plan items. A single item change is sufficient and unaffected items
must be preserved.

The client may accept a proposal for professional review or reject it. Client
acceptance moves it to `pending_instructor_review`; it never activates a plan.
An instructor may edit every structured operation, approve, or reject it. Only
instructor approval creates a new immutable current version atomically,
superseding the prior current version. The AI and client may never approve or
activate a plan. Repeated decisions do not create duplicate versions; a
proposal based on a non-current version is marked `superseded` rather than
merged automatically. Proposals and their audit metadata are retained with
training history, independently of raw-chat retention.

For Task 17, AI may identify a recognized real-world exercise not already
stored by the application. It must be a reviewable candidate, distinguishable
from an existing exercise, and may include descriptive equipment requirements.
It must not silently create a catalog entity or invent fictional exercises.
Task 21 remains the future authoritative equipment catalog boundary; until it
exists, instructor review is the normalization boundary.

## DEC-18 — Health-data storage, access, and audit evidence

**Status:** partially approved — 2026-09-21

This approval applies only to health/onboarding data. Biometric storage,
replacement, retention, and access remain unresolved until RF-22 or a separate
biometric task.

- Store onboarding health data in PostgreSQL in a dedicated onboarding-health
  structure or an equivalently clearly separated persistence model, linked by
  internal application identifiers. Do not store it in Keycloak, authentication
  tokens, URLs, or ordinary Account/Client profile fields.
- A client may read and edit only their own editable draft. An attendant has no
  health-data access. Admin role alone does not grant health-data access, and
  ordinary administrative client APIs/UI must not expose health fields.
  Instructors may access relevant data only when a later, explicitly approved
  training-plan/review function requires it; Task 10 creates no instructor
  health screen or API.
- Future AI integrations receive only minimum approved context for the resolved
  client; data from one client never enters another client's context.
- Never log medications, health-condition text, limitations/complaints, full
  onboarding payloads containing health data, or raw invitation tokens.
  Operational/audit evidence may record actor ID, client/onboarding ID, action,
  timestamp, success/failure, and changed field names—never sensitive values.
- Account/client deactivation does not delete onboarding or health history.
  Completed data remains while client history remains; the MVP has no automatic
  time-based deletion. Account deletion/anonymization needs a separate approved
  workflow and no legal retention duration is inferred.
- Draft values may be replaced by the owning client while editable. Completed
  data must not be overwritten silently; post-completion changes require a
  future revision/replacement flow. Preserve non-sensitive audit metadata for
  allowed operations without duplicating health payloads.

### AI-conversation amendment

**Status:** approved for Task 11 — 2026-09-21

Raw conversational-onboarding messages and their bounded summary are sensitive,
client-owned PostgreSQL data. They are visible only to the owning client; they
are not available to instructors, attendants, ordinary administrators, or
other clients. Raw messages and the summary expire after five days. Structured
onboarding values validated from the conversation remain under their own
onboarding lifecycle and are not deleted with raw chat content. A project-
compatible purge entry point must delete expired raw conversation state without
requiring new scheduling infrastructure.

AI context is minimized to the current user message, a bounded summary, at
most six recent messages by default (configuration-controlled), and only the
structured onboarding values actually necessary for the current exchange. No
cross-client context is permitted. Prompts, raw messages/responses, health
values, and provider credentials are never logged; operational metadata may
record internal IDs, provider/model, duration, outcome, error category, retry
count, and time.

Provider failures must leave the authoritative onboarding draft unchanged. A
valid provider result, schema validation, persistence of accepted updates, and
conversation response are one safe operation; invalid/malformed/refused output
or a timeout is retried once and then returns a controlled failure without
persisting proposed updates. The provider timeout is ten seconds per attempt.
The frontend creates a UUID for each logical user message and reuses it for a
retry; the backend uses client/conversation plus that identifier as an
idempotency key, so a successful duplicate never calls the provider, writes
messages, or applies updates twice.

Biometric DEC-18 questions remain unresolved.

## DEC-08 — AI provider, contract, and bounded context

**Status:** resolved for Task 11 — 2026-09-21

The initial provider is the OpenAI API and initial configurable model is
`gpt-5.6-luna`. Provider and model are environment-configured; API keys remain
server-side secrets. Onboarding domain code depends on a provider-neutral
application interface, with the OpenAI Responses API and Structured Outputs
contained in its adapter. No provider SDK response type, model ID, API key, or
provider-specific behavior crosses that boundary.

Normal provider-neutral interview turns contain client-facing Portuguese
`assistant_message` and advisory `interview_status`; they do not mutate the
structured draft. When the interviewer reports readiness, a separate
schema-constrained final-extraction operation returns only approved onboarding
fields. The backend validates that extraction against DEC-06 atomically,
calculates readiness, and treats structured onboarding as the
only authoritative state. AI output cannot diagnose, give medication guidance,
invent fields/facts, bypass validation, or override backend readiness.

The OpenAI adapter uses the supported Responses API with schema-constrained
Structured Outputs rather than free-form JSON instructions. Refusal, incomplete
or unparseable output, retryable provider failure, and timeout are controlled
provider failures subject to the single retry policy recorded under DEC-18.

**Development adapter amendment — 2026-09-21:** Ollama is an approved second
implementation of the same provider-neutral onboarding interface for local,
zero-API-cost development and testing. It uses configurable
`OLLAMA_BASE_URL`, `OLLAMA_MODEL` (default `qwen3:8b`), and
`OLLAMA_TIMEOUT_SECONDS` (default 30), with JSON-Schema-constrained local HTTP
output mapped and validated through the same application response contract.
This does not replace OpenAI or change its ten-second production timeout.
For reproducible local use, Ollama may run as an optional internal Docker
Compose profile with a persistent model volume; it is not exposed on a host
port and is not a production infrastructure requirement.

**Task 14 amendment — 2026-09-22:** initial training generation reuses the
same compatible, environment-configured provider/model selection behind a
provider-neutral contract. It receives only the requesting client's completed
authoritative structured onboarding and returns a schema-constrained plan
proposal. The backend validates the Task 13 plan model before persistence;
provider output never approves or activates a version.

**Initial-draft follow-up — 2026-09-23:** after completed onboarding, the
client may explicitly request an initial AI-generated training draft from the
personal training area. A client may have at most one active `proposal`,
regardless of origin. AI or an instructor may create it only when none exists;
a repeat AI request reuses the existing draft rather than calling the provider
or creating another one.

**Task 16 training-chat amendment — 2026-09-22:** the client-facing training
assistant is a separate, persisted, client-owned conversation. Its response
contract is conversational Brazilian Portuguese and does not produce field
updates, plan patches, or adaptation proposals. It may carry a non-binding
signal that an adaptation may be useful, pending the later Task 17 client
confirmation. It may receive
only the authenticated client's current approved plan, its exercises and
permitted metadata, relevant completed-onboarding facts when functionally
needed, a bounded summary, and bounded recent messages. It must never mutate,
approve, activate, or otherwise change a training-plan version; dynamic changes
remain exclusively in Task 17's proposal/review workflow.

Raw training-chat messages and its supporting summary are retained for 30 days
and are then eligible for the same simple opportunistic cleanup pattern used by
onboarding chat. Raw training chat is visible only to its owning client, never
to another client, attendant, ordinary administrator, or instructor. The
frontend creates a UUID for each logical message and retries with the same UUID;
client/conversation plus that UUID is the server-side idempotency key. Existing
provider-neutral adapters implement the same contract for OpenAI and Ollama.
OpenAI keeps the ten-second-per-attempt, one-retry policy; Ollama retains its
separate configurable local-development timeout. Raw messages, prompts,
provider responses, health details, and credentials must not be logged.

**Single-draft refinement follow-up — 2026-09-23:** when exactly one active
draft exists, the owning client's training chat may update that draft only
after the client clearly asks for a change. The AI may edit the sole draft
regardless of whether AI or an instructor created it. The adapter returns a
full structured draft; the backend validates it through the Task 13 plan schema
and revises it with optimistic concurrency. It cannot update an approved,
current, or superseded version or any other client's draft. This narrowly
scoped proposal refinement does not approve, activate, or change a current
plan, and instructor review remains mandatory.

**Task 17 adaptation amendment — 2026-09-23:** adaptation generation uses the
same provider-neutral OpenAI/Ollama boundary, structured-output validation,
minimized own-client context, one-retry failure policy, and provider timeout
rules. Its contract contains only a structured proposal explanation and
operations; it cannot mutate a plan directly. Context contains the
authenticated client's base current version, source own chat message, bounded
recent own chat/summary, and only health context relevant to the requested
change. The frontend creates a UUID for each logical adaptation request; the
backend keys idempotency by client, base version, and that UUID. Provider or
validation failure persists no proposal, plan version, or current-pointer
change.

**AI-initiated suggestion amendment — 2026-09-23:** Task 16 chat may identify
from the authenticated client's own conversation that a training change could
be useful. It may then present a non-binding, persisted suggestion and reason
in Portuguese. The client does not need to manually initiate an adaptation.
However, the client must still explicitly confirm the suggested draft before
structured Task 17 generation begins, and must separately accept that resulting
proposal before instructor review. The suggestion cannot modify a plan, create
a version, or bypass any Task 17 human-review boundary.

## DEC-16 — Personal-use non-functional measurement protocol

**Status:** approved for Task 19 — 2026-09-23

The system is intended for personal use, so formal MVP verification does not
assume commercial traffic, redundant infrastructure, or a production uptime
SLA. The approved reference dataset is approximately 50 synthetic clients with
representative related history. Normal load is one active user, with a burst
check of three simultaneous requests.

Representative common internal operations are executed ten times; at least
nine executions must complete within the existing two-second requirement.
External operations show visible processing feedback within 200 milliseconds
and complete with a valid result or controlled error under their approved
adapter timeout/retry policy. OpenAI keeps its ten-second timeout per attempt
and one retry; Ollama keeps its separately configurable local timeout.

Critical journeys are checked at 360×800 smartphone, 768×1024 tablet, and
1366×768 computer viewports. They must remain usable, and the smartphone view
must not require horizontal scrolling. The intended user performs the
documented client, instructor, and administrator journeys from a checklist
without source-code consultation or step-by-step assistance. A blocked journey
fails; confusing but completable steps are findings. Keyboard access, visible
focus, readable contrast, accessible labels, and the absence of critical
automated accessibility violations are required.

Availability means availability while the personal host, network, and required
infrastructure are running. Verification uses an eight-hour local soak with a
core health check each minute and no unexplained core outage. Planned
maintenance and host/network downtime are excluded. A normal stack restart must
restore core functions within five minutes without data loss or manual database
repair. High availability and redundant infrastructure are not required.

Simulated AI and e-mail failures must remain controlled, preserve authoritative
data, and leave independent internal operations available. The affected test
suite must pass, significant changes require regression coverage, business
rules remain in service/domain modules, and fake compatible adapters must prove
provider details do not leak into domain or public API contracts. Task 19 must
record its environment, commands, results, and criterion-level evidence. Any
future multi-user or broader deployment requires a new measurement decision.

## DEC-17 — Application identity and client-account relationship

**Status:** approved — 2026-09-20

Application identifiers are independent from Keycloak identifiers. `account.id`
and `client.id` are application-generated UUID primary keys; a Keycloak OIDC
subject is never used as a domain identifier.

- `account.keycloak_subject` is the unique external OIDC `sub` reference and
  remains nullable until the corresponding Keycloak identity is provisioned.
- `account.email` is normalized and globally unique, including for inactive
  accounts. It is the authoritative e-mail field and is not duplicated in
  `client`.
- `account.account_active` controls whether an account may authenticate. This
  decision does not define later activation or physical-access transitions.
- `client.account_id` is a unique foreign key to `account.id`, forming a
  one-to-one relationship. Client-specific data belongs to `client`.
- Passwords and other credentials remain exclusively in Keycloak. The local
  account model is reusable for later client, employee, and administrator
  identities.

## DEC-19 — Client-facing product direction and approved extensions

**Status:** approved — 2026-09-20

The product evolves as a client-facing gym platform while retaining its
administrative capabilities and original requirements. The following additions
are approved and specified under stable extension IDs in
`docs/product-extensions.md`:

- `EXT-RF-AI-01`: conversational AI onboarding over authoritative structured
  onboarding data, coexisting with the secure-link/form flow;
- `EXT-RF-SOC-01`: limited, controlled progress sharing;
- `EXT-RF-EQP-01`: active equipment quantity by approved logical type/model;
- `EXT-RF-PRES-01`: optional named presence with explicit client opt-in.

This decision does not renumber or reinterpret an original RF. Client-owned
APIs must resolve the local client from the authenticated Keycloak subject and
must not trust an arbitrary browser-supplied client ID as proof of ownership.
Client-facing training-plan and AI-chat behavior remains governed by RF-16,
RF-18, RF-19, RN-05, RN-16–RN-18, and RN-29–RN-31.
The current-plan area is mobile-usable and shows the authenticated client's
exercises and approved instructions. AI chat may use only functionally necessary
permitted context from that client's onboarding, current plan, plan
history/context, and already-implemented client-visible exercise/equipment data.

The new extensions do not approve a general social network, real-time equipment
availability, or disclosure of private data. `DEC-10` remains unresolved, and
named presence cannot be implemented until its separate privacy/persistence
decision (`EXT-DEC-PRES-01`) is approved.

## EXT-DEC-SOC-01 — Controlled progress-sharing audience and moderation

**Status:** approved for Task 20 — 2026-09-23

The feature is intentionally a small, client-owned progress feed rather than a
social network. An update is private by default. Its author may explicitly set
it to shared, which makes it visible to all active authenticated clients. There
are no explicit recipients, groups, followers, or guest viewers. Private
updates remain author-only; an administrator cannot access one solely because
of the administrative role.

Administrators may moderate shared updates only. They can hide or restore an
update and must provide a reason. A hidden update disappears from other-client
feeds, but its author sees the moderation state and reason. Administrators
cannot edit a client's content or create an update for a client. The author
alone can edit or delete their own update.

Author deletion immediately removes the content from all views and retains only
a contentless tombstone plus minimum audit metadata. Hidden updates retain their
content and moderation state for possible restoration. Active updates persist
until author deletion or a future approved account-deletion/anonymization
workflow; no retention duration is inferred. Audit records contain actor ID,
update ID, action, timestamp, and moderation reason where applicable, never
content or automatically derived sensitive domain data. The interface warns
authors not to publish health, payment, credential, attendance, biometric, or
presence data. This decision does not approve reporting, comments, likes,
direct messages, rankings, or leaderboards.

**Deletion amendment — 2026-09-23:** administrators may delete shared progress
updates with an optional reason, leaving a contentless tombstone. They may also
irreversibly erase a client: delete the Keycloak identity and all attached local
records with no retained audit record, for anonymity. Erasure overrides normal
history preservation only for this explicitly requested privacy workflow.
