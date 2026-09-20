# Task 01 — Project Foundation

## Objective

Create the agreed, runnable project skeleton and shared quality baseline needed by every MVP slice, without implementing business functionality.

## Requirements covered

No RF or functional CA is owned by this enabling task. It prepares the architecture needed to implement the explicit MVP.

## Related rules and constraints

- RNF04: preserve clear module boundaries, focused responsibilities, and a testable structure.
- RNF05/RNF06: external e-mail and AI services must sit behind replaceable adapters and must not take unrelated capabilities down.
- TEC-01–TEC-10 and requirements sections 6–7 define the allowed architecture envelope.
- DEC-03 is **blocking**: authentication approach, NestJS/Python responsibilities, runtime topology, e-mail direction, and tool versions must be recorded first.
- DEC-17 is **non-blocking** because this task creates no domain schema or migrations; those must wait for the relevant later task.
- DEC-16 is **non-blocking**: measurement thresholds can be finalized later, but test seams and observability should remain possible.

## Prerequisites

- No previous task file.
- Approved resolution for the blocking parts of DEC-03.
- If those decisions are not recorded, stop before selecting frameworks beyond those explicitly fixed by the specification.

## Required reading

Read `AGENTS.md`; requirements sections 1, 4, 6, 7, 8, 9 (DEC-03, DEC-16, DEC-17), and 10.

## Scope

Establish the agreed top-level applications, local runtime composition, configuration examples, formatting/lint/test commands, health checks, OpenAPI baseline, and empty module boundaries for identity, clients, onboarding, training, and integrations. Add no domain behavior, schema, or migrations. Use only tools and versions approved through DEC-03.

## Out of scope

- Every RF and business workflow.
- Choosing auth, e-mail, AI provider, ORM, test framework, or NestJS/Python division without an approved decision.
- Production hosting, biometrics, firewall rules, and non-MVP modules.

## Acceptance criteria

- No functional CA is claimed.
- The agreed services start using documented commands, configuration contains no secrets, and baseline lint/build/test checks run.
- The skeleton demonstrates separated internal modules and adapter boundaries without placeholder business endpoints.

## Tests

Add minimal smoke/configuration checks appropriate to the selected stack. Run the documented build, lint, test, and local service health checks; report exact results and anything requiring external infrastructure.

## Completion requirements

- Verify all foundation checks above.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests/checks executed and results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/01-project-foundation.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. If a blocking DEC item is unresolved or requires a material human decision, stop and ask. Run the relevant checks, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
