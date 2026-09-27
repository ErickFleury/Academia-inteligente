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

- A newly provisioned client-only Account receives only the `client` realm role.
  Attaching Client to an already approved active instructor Account adds
  `client` without removing its employee/instructor roles. Client creation must
  never originate or elevate an employee/admin role, and backend authorization
  must continue to reject client-only access to administrative APIs.
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

### Employee/person provisioning amendment

**Status:** approved for RF-07/RF-08 and instructor work — 2026-09-26

Client and employee identities reuse one Account-linked personal record for
first name, multiword surname, globally unique mathematically validated CPF,
Brazilian phone, and Brazilian address. Client has no CNPJ; Employee may have
an optional mathematically validated CNPJ and currently supports only the
`instructor` specialization. The address consists of CEP, street, number,
optional complement, neighborhood, city, and UF. ViaCEP is a replaceable
server-side convenience adapter only: returned fields may be prefilled but are
always editable, and failure never blocks manual address entry.

This field set follows the Correios technical address structure (street type/
name, number, complement, neighborhood, CEP, locality, and UF). ViaCEP was
selected because its documented free JSON service returns the corresponding
CEP, `logradouro`, `bairro`, `localidade`, and `uf` fields and explicitly
defines invalid and not-found behavior. Its warning against bulk validation is
respected: the application performs individual form assistance, not database
harvesting. Supporting references: <https://www.correios.com.br/enviar/precisa-de-ajuda/guia-de-enderecamento/guia-de-enderecamento>
and <https://viacep.com.br/>.

An administrator may register, view, update, and deactivate employees and may
update every initial client or employee field. Name/e-mail and role changes are
durably reconciled with Keycloak. Employee creation uses the same secure
first-access and no-local-password boundary as client provisioning. Matching
normalized e-mail and CPF may attach both Client and Employee to one Account;
conflicting combinations are rejected. The Keycloak identity receives the
union of its active approved domain roles. Deactivating one domain profile
removes only that role, while backend authorization also checks local
role-specific active state so a stale token cannot retain permission.

## DEC-05 — Account activity and physical-access eligibility

**Status:** approved — 2026-09-20

`account_active` alone determines whether an identity may authenticate to the
application. An inactive account must not authenticate normally.

**Multi-role amendment — 2026-09-26:** Client and Employee have independent
role-active state. For an Account linked to both, deactivating one domain role
does not end login while the other remains active; Keycloak and backend policy
remove only the deactivated role. `account_active` remains the overall login
gate and becomes false when no linked application role remains active. This is
separate from physical-access eligibility.

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
`OLLAMA_TIMEOUT_SECONDS` (default 120), with JSON-Schema-constrained local HTTP
output mapped and validated through the same application response contract. The
local request disables optional model thinking and the onboarding/training
assistant prompts require concise, necessary-only responses; this keeps local
interactive use bounded without changing the structured validation boundary.
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
availability, or disclosure of private data. DEC-10 resolves only anonymous
occupancy's authoritative source. Profile-presence visibility is governed
separately by `EXT-DEC-PRES-01` and does not change DEC-10.

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

## EXT-DEC-SOC-02 — Social client profiles and post interactions

**Status:** approved for Task 26 — 2026-09-25

Task 26 expands the individual client profile into a bounded social profile and
supersedes only the follower, like, and comment exclusions previously stated by
EXT-DEC-SOC-01. Existing progress-update ownership, private/shared visibility,
post moderation, sensitive-data exclusions, and account-erasure rules remain in
force.

A social profile is visible to active authenticated clients by default. The
owner always has access to their own profile and is the only person who can see
or change the profile-visibility switch. Disabling visibility immediately
hides the cross-client profile, its follower/following lists, and its profile
post collection from other clients. It does not change individual post
visibility: an explicitly shared post remains eligible for the existing shared
progress feed, while a private post remains author-only. Existing follow
relationships are retained while a profile is hidden and become visible again
if the owner re-enables the profile. Anonymous/guest profile access is not
approved.

The canonical client identity remains its internal UUID; neither a name nor a
nickname is an identifier. The profile shows the client's existing display
name and may additionally show an optional, owner-editable, non-unique nickname.
The nickname is presentation-only, is plain text, limited to 40 characters,
and does not alter login, authorization, account linkage, post ownership, or
historical relationships.
An optional plain-text biography is owner-editable and limited to 160
characters.

The owner may upload, replace, or remove their profile picture by activating
the picture control. Task 26 accepts JPEG, PNG, or WebP up to 5 MiB, validates
the actual media, normalizes it to a bounded image while removing metadata, and
stores the resulting bytes in a dedicated client-owned PostgreSQL record. The
frontend never sends a filesystem path as profile identity. Replacement or
owner removal permanently deletes the previous bytes; account erasure deletes
all profile-image data. Other clients and administrators cannot edit the image.

Following is a unilateral relationship between two active clients. Self-follow
and duplicate relationships are forbidden. A client may follow or unfollow an
otherwise visible profile; no approval request is required. A visible profile
may expose its follower and following counts and lists to authenticated clients.
Private follow requests, blocks, recommendations, notifications, and friend
semantics are future work and are not introduced by Task 26.

The profile lists the owner's retained posts newest-first. The owner can see
their private and shared posts and any moderation state; another authenticated
viewer sees only shared, non-hidden posts on a visible profile. Deleted posts
are not presented. Opening a permitted post displays its current like count and
comments. Any active authenticated client with access to a shared, non-hidden
post may like/unlike it, including its author, with at most one like per client,
and may add a plain-text comment up to the existing 2,000-character post-content
ceiling. Comment authors may delete their own comments. Post authors do not
gain authority to delete another client's comment merely
because it appears on their post. Private or hidden posts accept no cross-client
interaction. Post deletion removes attached likes and comments while retaining
only the already-approved contentless post tombstone.

Administrators may moderate shared comments and the social biography/profile
picture, but cannot edit client content or enable/disable profile visibility.
Hide and restore actions require a reason; deletion accepts an optional reason.
Moderation audit data contains only the minimum actor, target, action, timestamp,
and reason and never duplicates image bytes or user-authored content. Owner and
administrator deletions remove content from client views. Full account erasure
removes the social profile, image bytes, follow edges, likes, comments, posts,
tombstones, and related audit data so the erased client cannot be reidentified.

Other-client profile responses expose only approved social fields: display
name, optional nickname, optional biography, permitted profile image, follower
and following information, permitted posts, and the existing current-presence
boolean only when EXT-DEC-PRES-01 independently allows it. E-mail, internal IDs,
health, training, attendance history, biometrics, payment, credentials, and
administrative data are excluded. The profile presence preference remains a
separate default-off consent and is not implied by the default-on social
profile.

Task 26 may introduce stable service/API boundaries that a later feed can
consume, but it does not implement a feed, recommendations, direct messages,
notifications, rankings, leaderboards, public profiles, or another social
framework. A future feed must receive its own requirement and task.

## EXT-DEC-SOC-03 — Authenticated chronological feed and social media

**Status:** approved for Task 27 — 2026-09-26

Task 27 is the later requirement and task anticipated by EXT-DEC-SOC-02. It
supersedes only that decision's feed deferral and Task 26's chronological
comment presentation. ProgressUpdate remains the sole post aggregate;
EXT-DEC-SOC-01 private/shared ownership and tombstones, EXT-DEC-SOC-02 profile,
like/comment, moderation, privacy, and erasure foundations, and
EXT-DEC-PRES-01 presence consent remain authoritative unless amended below.

“Public post” means the existing `shared` state and is visible only to active
authenticated clients. It never means anonymous or guest access. New posts
remain private by default and require explicit sharing. The `/progresso` feed
contains shared, non-deleted, moderation-visible posts ordered newest-first by
`created_at` and UUID as a deterministic tie-breaker. The API uses an opaque
cursor and bounded pages. There is no ranking, recommendation, trending,
follow-based selection, discovery/search, advertisement, or other algorithm.

The composer creates a post owned by the authenticated client; browser-supplied
author IDs are ignored. It is the same ProgressUpdate shown in the author's
permitted profile history, not a feed-only copy. Post/comment text is trimmed
plain text up to 2,000 characters. A post or comment is valid when it contains
text, media, or both, so image-only posts and image-only comments are allowed.
Posts accept at most four ordered images and comments at most one. Each input
image is JPEG, PNG, or WebP up to 5 MiB, decoded by content, required to be
static and valid,
orientation-normalized, stripped of metadata, bounded within 1024×1024 while
preserving aspect ratio, safely re-encoded, and stored as bytes in a dedicated
PostgreSQL record. Media is served by authorized APIs; it is never base64 JSON,
an external URL, or a host filesystem path.

Post and comment authors may edit their own text and replace or remove their
attachments. Superseded bytes are deleted in the same transaction. A content
or attachment change records `edited_at`, and client views display “editado”
without exposing an edit-history body. The same ownership rule applies to
direct API calls. A shared post with any retained, non-deleted comment cannot
be made private. Likes do not prevent the transition: they remain persisted
but unavailable to other clients while the post is private, interactions are
disabled, and the relationships become visible again if the author reshares
the post.

Profile visibility and post visibility remain independent. A shared post from
a private social profile remains in the feed. Clicking its author opens a
private-profile shell containing only the presentation username—nickname when
present, otherwise the existing client name—and the permitted profile picture
or fallback avatar. Biography, follow graph, presence, and profile post history
remain unavailable. Feed and comment author projections use only opaque social
profile IDs and approved name/avatar presentation; they expose no Account or
Client UUID, e-mail, subject, health, training, attendance, biometric, payment,
credential, or administrative data.

Feed cards always expose the accurate like and visible-comment counts without
hover. Post detail shows visible comments newest-first and has one accessible
composer for optional text and at most one image. There are no replies or reply
relationships. Administrators may hide/restore an entire shared post or shared
comment with a required reason and may delete the whole aggregate with an
optional reason, including all of its media. They cannot edit user content.
Post deletion removes its image bytes, likes, comments, and comment images and
retains only the approved contentless post tombstone and minimum audit
metadata. Comment deletion removes its text and image from client views.
Moderation/audit records never copy content or image bytes.

Full account erasure deletes authored posts/tombstones and media, authored
comments/media, likes given or received through erased posts, comments/likes
attached to erased posts, related social audit records, and the previously
approved social/account aggregates. Cursor pagination and UI caching cannot
retain erased or newly hidden content after a subsequent authorized read.

The initial full composer appears at the top of “Progresso.” When it leaves the
viewport, one compact fixed action appears without duplicating focusable
composer controls; activating it returns to and focuses the composer. This is
presentation behavior, not a second draft or publication surface. Task 27 adds
no replies, notifications, messages, blocks, public guest profiles, sensitive
automatic publication, camera behavior, or payment functionality.

## EXT-DEC-SOC-04 — Account privacy and approved follow requests

**Status:** approved implementation decision — 2026-09-26

This amends EXT-DEC-SOC-01 through EXT-DEC-SOC-03 only for account privacy.
Post audience is derived from the account rather than chosen per post. Public
accounts publish to active authenticated clients; private accounts expose active
non-hidden posts only to their owner and accepted followers. Toggling account
privacy atomically reclassifies every active authored post. A private account
may receive one pending request per non-follower; the owner alone can view and
accept/reject it. The requester receives no notification, graph, or private
content before acceptance. The owner may see a compact pending-request indicator
beside follower information. Follow requests are deleted on decision, unfollow,
post deletion where applicable, and complete account erasure. This does not
approve public/guest profiles, recommendations, messaging, blocks, or any
presence-consent change.

## EXT-DEC-PRES-01 — Profile presence visibility

**Status:** resolved for Task 23 — 2026-09-25

This is an optional, default-off client preference (`share_current_presence =
false`) controlling only whether the client's individual profile may show a
current-presence tag. It is not a named-presence directory, feed, list, or
occupancy-screen feature. Consent is explicit and cannot be inferred from an
account, terms, biometric enrollment, gym entry, anonymous occupancy, or use of
other features. Staff cannot enable it for a client.

The preference never changes confirmed-passage recording, private access-event
history/auditing, corrections, source freshness, occupancy reconstruction, or
the client-only aggregate required by DEC-10. All applicable clients remain in
anonymous occupancy regardless of their preference. The occupancy tab stays
aggregate-only: no names, avatars, profile links, or other identifying presence
data are permitted.

When viewing an individual client profile, show a green Portuguese current-status
tag such as “Na academia” only when the client enabled the preference, the
latest confirmed client passage is an entry with no later exit, the entry is no
more than 12 hours old, and the authoritative access source is current under
DEC-11. A confirmed exit or stale/unavailable source immediately suppresses the
tag for subsequent reads. Recognition, camera data, release commands,
authorization, anonymous totals, AI inference, login, or profile activity can
never establish it. Re-enabling resumes the same derived rule without rewriting
history or requiring a new entry.

The persisted client-owned preference records enabled/disabled state, consent
and last-updated timestamps, and an optional consent/policy version. It is
separate from the passage ledger and follows the client/account lifecycle.
Minimal consent-change audit metadata may retain client, prior/new value,
timestamp, and consent version; it must not retain raw passage history or any
biometric, health, payment, training, or credential data. No separate
profile-presence visibility history is stored.

Opt-out takes effect immediately for subsequent reads, hides the tag for every
viewer including staff, and never erases or changes operational passage data.
No role receives a profile-presence override and no privileged or client-facing
directory of currently present people is approved. The feature exposes only the
boolean current status through the individual profile tag; it adds no profile
fields, entry time, duration, visit history, checkpoint, internal ID, or other
private detail. This decision is an identity-visibility layer only and does not
modify or reinterpret DEC-10.

## EXT-DEC-EQP-01 — Equipment catalog grouping and inventory representation

**Status:** approved for Task 21 — 2026-09-25

Task 21 uses a two-level equipment domain. `EquipmentModel` is the canonical
logical equipment type/model/variant shown as one catalog entry, identified by
an internal UUID rather than its display name. `EquipmentUnit` represents one
physical machine and belongs to exactly one `EquipmentModel`. Renaming a model
does not change its identity or historical relationships.

Functionally distinct variants are separate models: for example, Leg Press
45°, Leg Press Horizontal, and Leg Press Vertical are different
`EquipmentModel` records. Multiple equivalent physical machines of one variant
are separate `EquipmentUnit` records under that one model.

The authoritative active quantity is derived, never independently stored:
`COUNT(active EquipmentUnit rows for an active EquipmentModel)`. A model and a
unit have their own active/inactive lifecycle states. Deactivation preserves
the record and its historical relationships; it removes an inactive unit from
the derived count and hides an inactive model from the active catalog. Task 21
does not introduce serial-number, maintenance, telemetry, reservation, or
real-time occupancy/use semantics.

“Active” means present in the managed gym inventory/catalog. It never means
free, immediately available, unoccupied, unused, or reservable. User-facing
and API wording must say “active units”/“total active units”, never
“available” or “free units”. A future Task 17 equipment-aware proposal may use
an active model with one or more active units only as evidence that the gym has
that equipment; it must not infer real-time availability.

## EXT-DEC-INST-01 — Instructor professional area

**Status:** approved for Tasks 28–37 — 2026-09-26

The instructor feature depends on RF-07/RF-08 and the Account-linked person
model recorded under DEC-04. A responsible instructor is a stable local
Employee identity, not an unverified browser identifier or mutable token name.
Current presentation uses first name plus surname; immutable approved-version
history retains the attribution necessary to survive later rename or
deactivation.

The dedicated instructor SPA opens at Feed and provides, in order, Feed,
Planos pendentes, Meus planos, Todos os planos, Clientes, Equipamentos, and
Perfil. Perfil is only a bounded future-feature state. The feed reuses the
existing social query/presentation and includes moderation-visible posts from
public client profiles only. Instructors have no client social identity and no
posting, liking, commenting, following, or other social mutation authority.

There is exactly one instructor-editable training draft per client across
initial AI creation, manual authoring, current-plan editing, and accepted
adaptation. Retained adaptation source/history is not a second editable draft.
All drafts requiring review appear in Planos pendentes. Saving edits never
activates; explicit instructor approval atomically makes the draft current,
supersedes the prior current version, records responsible Employee and approval
time, and rejects stale competing writes. Editing a current plan with an
existing draft requires explicit confirmation before that draft is discarded.

Instructor client search covers active clients only and has onboarding,
training, and responsible-instructor filters. Training states are Todos, Sem
plano, Pendente de aprovação, and Plano ativo; the redundant “Somente
rascunho” state is not used. Instructors may complete unfinished onboarding and
edit completed onboarding in place for training work, with ordinary validation
and non-sensitive audit attribution.

Equipment inventory-active state remains governed by EXT-DEC-EQP-01. A new
independent unit state is `operational` or `out_of_order`. Instructors may only
change that operational state. A model is usable for newly authored/generated
training content only with at least one unit that is both active and
operational. Historical/current plans are not rewritten, and operational never
means free or available now.

## DEC-02 — Occupancy requirement identifier normalization

**Status:** resolved — 2026-09-25

The historical `X` suffix on the anonymous-occupancy requirements has no
separate meaning. The canonical identifiers are `RF-24` (calculate current
occupancy) and `RF-25` (display current occupancy). The former labels
`RF-24X`/`RF-25X` are retired and do not indicate conditional, cancelled, or
different requirements.

## DEC-10 — Anonymous occupancy source of truth

**Status:** resolved for Task 22 occupancy architecture — 2026-09-25

The authoritative anonymous occupancy source is the persisted ledger of
confirmed physical-passage events for clients only. The current count covers one
logical gym occupancy zone associated with the controlled entry/exit system; it
does not mean every person in the building and excludes employees, attendants,
instructors, administrators, and other staff.

Recognition, authorization, gate/door release, and confirmed physical passage
are distinct. Only a confirmed client passage changes occupancy: an entry adds
one and an exit removes one. Recognition, authorization, or release without
confirmed passage must not change the count.

Camera-based counting is deferred and is not approved for Task 22. If approved
later, it is an auxiliary observation source only: access/passage events remain
authoritative, observations cannot overwrite or blend with the official count,
and a discrepancy may be recorded/reported only to authorized staff. A future
camera observation must declare its covered zone and may be compared only with
compatible coverage. Partial areas cannot be summed into whole-gym occupancy
without a later approved complete, non-overlapping coverage design.

The future camera freshness threshold is 60 seconds. A failed or stale camera
observation is unavailable/not current and never replaces the access-event
count. If a future observation disagrees with the ledger, the ledger count
remains official and the difference is an explicit discrepancy; no synthetic,
averaged, or camera-corrected public value is permitted.

## DEC-09 — Biometric quality and handling

**Status:** resolved for biometric recognition and enrollment — 2026-09-25

The required 95% precision is a measured quality metric of the configured
facial-recognition system on an appropriate representative validation dataset:
`TP / (TP + FP) >= 95%`. It is not a requirement that every individual provider
match score be at least `0.95`. Each selected provider/model instead uses a
configurable, calibrated match threshold that supports the required measured
precision; it must not be hardcoded as universal domain logic.

A result below that configured threshold is not recognized, must not cause a
turnstile-release request, and must never be replaced by acceptance of the
closest candidate. One additional capture/recognition attempt may be offered;
after that failure, this biometric flow ends. External or manual alternatives
remain outside this decision.

Biometric information is logically separate from ordinary account/profile data
and ordinary APIs must not expose biometric payloads. Where a provider manages
templates, the application stores only the minimum needed reference: client,
external biometric subject/reference, enrollment state, lifecycle timestamps,
and non-sensitive audit metadata. It must not duplicate templates in the
primary relational store unless an explicitly documented provider requirement
makes that technically necessary.

A raw enrollment photo is temporary material, removed after successful
enrollment when technically possible. Persistent imagery required by a selected
provider must be explicitly documented. Replacement is safe and ordered:
successfully enroll the replacement, activate its reference, then revoke the
previous reference. A failed replacement must leave the existing usable
enrollment intact. Active material remains only while biometric access is
enabled and required; replaced/revoked or disabled references must no longer be
usable. Deletion, including applicable account deletion, removes provider
biometric material according to the approved lifecycle and provider capability.

Audit records may include the client, authorized actor, reference identifier,
action, result, timestamps, and replacement/revocation relationship. They must
never include raw facial images, templates, feature vectors, or sensitive
recognition payloads. Provider selection remains open, but every selected
provider must satisfy this policy and the DEC-11 integration boundary.

**Personal-use implementation recommendation (not a provider decision):** begin
with a locally self-hosted CompreFace pilot behind the DEC-11 adapter boundary.
Its Docker-deployable REST service and service API keys make it suitable for a
small local deployment without sending biometric material to a cloud provider.
This is neither an approved production provider nor evidence that the required
precision has been met. Before any automatic release is enabled, validate the
configured camera, lighting, and threshold against representative local
conditions and demonstrate the required measured precision. The pilot must also
use the approved external/manual fallback rather than weakening a threshold. A
managed provider with liveness detection may be evaluated later, but requires a
separate assessment of biometric-data processing, retention, and deployment
obligations.

## DEC-11 — Physical-access integration boundaries

**Status:** resolved for the approved occupancy and facial-recognition/release
boundaries — 2026-09-25

This decision does not approve biometric capture/recognition implementation or
other physical-access behavior. It approves an external machine-to-machine
confirmed-passage event contract for occupancy. Each event must carry a
provider-unique `event_id`, `occurred_at`, `checkpoint_id`, `direction`
(`entry` or `exit`), `event_type=passage_confirmed`, and an opaque
`client_reference`, using equivalent repository naming where appropriate. It
requires no biometric image, facial template, or raw recognition data.

`client_reference` is a sufficiently unique opaque external access/biometric
subject reference used only for server-side resolution to a local `Client`.
It is not an e-mail, name, image, template, raw biometric data, or the
application's internal Client UUID. The external producer never needs that UUID.
Before accepting a normal confirmed client-passage event, the backend resolves
the reference to a valid local Client and the private passage ledger persists
that Client relationship as its authoritative domain association. The external
reference may be retained as traceability metadata but is not a Client's primary
domain identifier.

An unknown or invalid reference is a controlled integration failure: do not
create a normal client-passage record, alter occupancy, guess a client, or
create a Client. Record only the non-sensitive operational metadata needed for
diagnosis. Events for non-client identities likewise do not alter client
occupancy. This satisfies RF-23 CA-23.4 without changing the public boundary:
the public occupancy response never exposes the reference, Client UUID, names,
e-mails, individual events, biometric identifiers, or recognition information.

The external producer authenticates with a dedicated server-configured
integration credential/API secret sent through an authorization mechanism or
header. It is separate from end-user credentials, is never hardcoded or sent to
the frontend, and OAuth2 client credentials/mTLS are not required at this
stage.

`event_id` is source-unique and idempotent. Retrying the same matching event
cannot change occupancy again. A reused identifier with conflicting contents is
an integration inconsistency/error, not a new passage. The persisted ledger
must enforce this identity. A reuse with a different `client_reference`,
direction, checkpoint, timestamp, or event semantics is conflicting rather than
a new passage. Failed recognition, successful recognition without passage,
denied/granted authorization without passage, and gate release without passage
do not affect occupancy.

Effective occupancy never becomes negative. An exit at zero is retained as an
auditable event/inconsistency while the effective public count remains zero.
Manual correction is limited to administrators and attendants. It appends an
auditable correction event with actor, timestamp, signed adjustment, and reason;
it never overwrites the passage ledger. The authoritative count is
reconstructable from persisted confirmed-passage and correction events. A cache
or snapshot may optimize reads but cannot be the sole authoritative state.

The anonymous public response exposes only aggregate occupancy, freshness/status,
and update time—never identities, passage history, biometric/recognition data,
camera images, or raw events. If the authoritative access source is stale or
unavailable, preserve its last known count but label it stale/unavailable rather
than current; do not substitute camera-derived occupancy.

The confirmed-passage producer sends an authenticated `source_heartbeat` with
`checkpoint_id` and timestamp every 60 seconds. The aggregate occupancy view is
`current` while the latest authoritative heartbeat is no more than 120 seconds
old and is `stale` after that; no absence of passage events alone is treated as
a source failure. The last reconstructed count remains visible when stale.

For the separate facial-recognition flow, a dedicated camera captures/scans a
client at a designated turnstile; a provider-neutral recognition integration
evaluates the result under DEC-09, maps a successful biometric reference to its
client, and sends one release request to the external turnstile system. The
application owns recognition integration, result evaluation, client mapping,
release-request submission, and non-sensitive audit metadata. The external
turnstile system owns electrical/mechanical actuation, physical movement, and
physical passage. A release request never proves passage.

The normalized recognition boundary carries only necessary metadata: a
recognition/event identifier, timestamp, checkpoint/camera identifier where
applicable, biometric subject/reference, recognized/not-recognized result, and
provider score only when required for threshold evaluation. It must not carry
raw facial imagery through ordinary application events. Provider credentials
use provider-appropriate server-side authentication and are never hardcoded or
exposed to the frontend. Asynchronous provider events require a source-unique
event ID; duplicate delivery cannot create more recognition attempts or release
requests. Synchronous calls likewise use an application-assigned unique logical
recognition-request ID so retries can be correlated safely.

Recognition failure or a below-threshold result sends no release request. A
successful recognition may create one logical release request with a unique
release-request ID; retries retain that identifier so an external controller
does not interpret them as distinct access attempts. Release integration uses a
dedicated server-side machine credential/API secret; OAuth2 client credentials
and mutual TLS are not currently required. No manual biometric override or
manual turnstile-release bypass is part of this application flow.

If recognition-provider integration fails, recognition is not assumed and no
release is requested. If release integration fails after recognition, record a
controlled integration failure without claiming passage. Logs and ordinary
client/admin APIs must never expose images, templates, feature data, or raw
provider payloads; non-sensitive IDs, checkpoint, timestamp, result,
release-request ID, and integration outcome are permitted operational metadata.

This facial-recognition/release policy does not change DEC-10: recognition,
successful recognition, release request, and turnstile release are not
occupancy changes. Only DEC-10's confirmed physical-passage events govern the
anonymous occupancy ledger. A later confirmed passage may carry the opaque
access/biometric subject reference, which the backend resolves to the private
Client-linked ledger event without placing biometric material in the passage
payload.

## EXT-DEC-FACE-01 — Local facial-access pilot

**Status:** approved by the user through the requirements interview and explicit
implementation instruction. Canonical policy: EXT-RF-FACE-01 in requirements.md.

The owner approved local no-cost CompreFace, mandatory shared-person enrollment
for client/staff registration, administrator-only operation, button webcam capture,
no liveness or agreement flow, simulated release and explicitly confirmed passage,
active-client-only entry but recognized exit despite inactivity, reasoned state
corrections, and the existing occupancy display without an extra simulation label.
Staff enrollment is reserved for future tracking; none is implemented here.
Test identities may be erased once replacement registration is usable; bootstrap
admin/service access and unrelated configuration must survive. No real gate call,
paid dependency, other participant, or population-accuracy claim is authorized.

The later pilot exception takes precedence over the older biometric deferral and
full membership prerequisite only within this explicit scope. CompreFace's exact
free-use artifacts and operational preflight remain an implementation gate.
See facial-access-specification.md for the complete interview decisions, contracts
and task order. No changes to unrelated health, training or financial policy.
