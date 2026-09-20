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
