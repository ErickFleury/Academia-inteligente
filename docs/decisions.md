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
