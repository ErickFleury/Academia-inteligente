# Task 11 — Initial AI Training Generation

## Objective

Generate a safe, structured, client-scoped initial training proposal from a valid completed onboarding and pass it through the approved review/version lifecycle.

## Requirements covered

- RF-15: CA-15.1–CA-15.5.
- RF-17 CA-17.1 is integration-verified here; Task 10 owns its implementation.

## Related rules and constraints

- RN-12–RN-19: professional review/editing, serious-health blocking, restriction precedence, no silent approval, historical preservation, and manual fallback.
- RN-23/RN-29: safe logs and absolute cross-client context isolation.
- RN-30: output must not be presented as medical diagnosis.
- RN-31: responsible professional remains identifiable where the approved flow requires one.
- RNF01, RNF05, RNF06: processing indication, controlled provider failure, and a replaceable AI adapter.
- DEC-04, DEC-07, DEC-08, DEC-15, and DEC-18 are **blocking** for reviewer access, severity/approval flow, provider contract, manual/review scope, and health-data handling.

## Prerequisites

- Tasks 09 and 10 complete.
- Blocking decisions DEC-04, DEC-07, DEC-08, DEC-15, and DEC-18 recorded.

## Required reading

Read `AGENTS.md`; RF-15 and CA-15.1–CA-15.5; RF-17/CA-17.1; RN-12–RN-19, RN-23, RN-29–RN-31; RNF01, RNF05, RNF06; DEC-04, DEC-07, DEC-08, DEC-15, DEC-18; sections 6.2, 8.2, and 10.

## Scope

Implement the provider-independent AI generation contract, client-scoped context assembly from the completed onboarding, response validation into the approved training structure, severity-block handling, provider error mapping, and handoff to the Task 10 lifecycle. Include approved review/activation steps only as defined by DEC-07/DEC-15.

## Out of scope

- Chat (Task 13), dynamic adaptation (Task 14), provider selection, medical diagnosis, or invented severity rules.
- Broad exercise management, completed-workout tracking, or unapproved automatic activation.
- Live-provider dependence in automated tests.

## Acceptance criteria

- CA-15.1: no proposal/version is generated without a completed valid onboarding.
- CA-15.2: a valid successful adapter response becomes a structured, persistible proposal/sheet through the approved flow.
- CA-15.3: generated content is associated only with the intended client.
- CA-15.4: health cases meeting the approved serious-risk criteria create no training plan.
- CA-15.5: generation demonstrably uses that client's onboarding data.
- Integration confirms CA-17.1 without duplicating version logic.

## Tests

Use fake adapters for success, malformed response, timeout, and unavailable-provider cases. Add context-isolation, missing/incomplete onboarding, serious-risk, restriction-precedence, schema validation, authorization, and lifecycle integration tests. Run relevant tests and report results.

## Completion requirements

- Verify every assigned CA and the RF-17 integration check.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/11-initial-ai-training-generation.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
