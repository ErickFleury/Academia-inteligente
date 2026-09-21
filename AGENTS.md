# Repository Guidelines

## Project

This repository contains the Academia Inteligente system.

The primary consolidated implementation specification is located at:

`docs/requirements.md`

Traceability sources remain authoritative for their respective purpose:

- `requirements.md`: preserved historical/source specification;
- `docs/decisions.md`: chronological approved decisions;
- `docs/product-extensions.md`: approved additions beyond the original source.

If these documents appear to conflict, first check whether
`docs/decisions.md` explicitly resolves the conflict. Use the recorded decision
when it does; otherwise stop the affected task and request a human decision.

Before implementing a requirement, read its RF or extension requirement,
acceptance criteria, related business rules, applicable non-functional
requirements, and decision gates in `docs/requirements.md`.

Treat the acceptance criteria as the definition of completion.

## Architecture

Use the architecture defined in `docs/requirements.md`.

Current stack:

- Frontend: React + TypeScript + Vite
- Backend: Python 3.13 / FastAPI modular monolith; NestJS has no current MVP responsibility
- Database: PostgreSQL
- API: REST + JSON + OpenAPI
- Authentication: Keycloak/OIDC with local Account identity linkage
- Infrastructure: Docker Compose
- AI: provider-independent adapter/integration layer

Exact approved versions and infrastructure choices are recorded in DEC-03 and
summarized in `docs/requirements.md`. Do not reintroduce historical technology
alternatives as active architecture.

Do not introduce major technologies or architectural changes without approval.

## Project Structure

Expected top-level structure:

- `frontend/`
- `backend/`
- `services/` when Python services are required
- `docs/`
- `docker-compose.yml`

Follow framework conventions inside each application.

Do not create unnecessary top-level directories.

## Implementation Workflow

For each task:

1. Identify the original RFs and product-extension IDs explicitly requested in
   the prompt.
2. Read those requirements, their acceptance criteria, related business rules,
   and applicable non-functional requirements in `docs/requirements.md`.
3. Inspect the existing implementation before editing.
4. Identify dependencies between the requested RFs and existing modules.
5. Modify only what is necessary to implement the requested RFs.
6. Run tests related to the requested RFs.
7. Review the resulting Git diff.

Do not implement RFs that were not explicitly requested unless they are
strictly required as a dependency. If an unrequested RF appears necessary,
report it before expanding the scope.

Do not implement unrelated requirements.
Do not perform unrelated refactoring.
Do not add dependencies without justification and approval.

If the specification is ambiguous or conflicts with the existing architecture,
ask before making a major assumption.

## Coding Guidelines

Follow the configured formatter and linter.

For TypeScript:

- variables/functions: `camelCase`
- classes/types/components/DTOs: `PascalCase`
- files/directories: `kebab-case` unless framework conventions differ

Keep modules focused and avoid duplicated business logic.

Controllers should handle transport concerns.
Business rules should remain in services/domain logic.

## Security

Authorization must always be enforced by the backend, not only the frontend.

Never commit secrets, credentials, API keys, tokens, or production data.

Treat authentication, biometric, medical, financial, and personal data as
sensitive.

Do not expose sensitive data unnecessarily in logs.

Data belonging to one client must never be exposed to another client,
including through AI context.

## External Services and AI

Keep external services behind integration/adapter layers.

Tests must not depend directly on live external services.

AI failures must be handled as controlled external-service failures.

Do not silently modify previously approved training plans.

## Testing

Add or update tests for changed behavior.

Run tests directly related to the current task.
Run broader tests when shared infrastructure is affected.

Do not lower established test or coverage requirements.

## Git

Keep commits focused on one logical change.

Do not commit or push unless explicitly requested.

Before finishing a task, verify that unrelated files were not modified.

## Completion

At the end of each implementation task, report:

- files changed
- tests executed
- important decisions
- unresolved issues
