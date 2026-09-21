# Architectural decisions

## DEC-03 — Technology and architecture decisions

**Status:** approved — 2026-09-20

The MVP uses a modular-monolith architecture. Authentication is provided by
Keycloak through OIDC.

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
