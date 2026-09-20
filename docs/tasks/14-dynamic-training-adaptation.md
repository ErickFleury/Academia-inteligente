# Task 14 — Dynamic Training Adaptation

## Objective

Turn relevant chat reports into an AI-generated adaptation proposal and, only through the approved flow, a new current training version.

## Requirements covered

- RF-19: CA-19.1–CA-19.4.
- RF-17 CA-17.2/CA-17.3 are integration-verified; Task 10 owns versioning behavior.

## Related rules and constraints

- RN-12–RN-15: professional review/modification and client restrictions govern adaptation validity.
- RN-16/RN-17: never silently overwrite an approved sheet; use a proposal/new version.
- RN-18: preserve prior versions and executed history.
- RN-29/RN-30: isolate context and avoid diagnosis language.
- RN-31: preserve the responsible professional.
- RNF04–RNF06: keep adaptation logic modular and provider failures contained.
- DEC-04, DEC-07, DEC-08, and DEC-15 are **blocking** for approvers, states/transitions, contracts, and professional/manual workflows.

## Prerequisites

- Tasks 10 and 13 complete.
- Blocking decisions DEC-04, DEC-07, DEC-08, and DEC-15 recorded.

## Required reading

Read `AGENTS.md`; RF-19 and CA-19.1–CA-19.4; RF-17/CA-17.2–CA-17.3; RN-12–RN-18, RN-29–RN-31; RNF04–RNF06; DEC-04, DEC-07, DEC-08, DEC-15; sections 8.2 and 10.

## Scope

Implement change-request detection/triggering as defined by the approved contract, context-safe adaptation generation, structured proposal validation, review/approval transitions, and activation through Task 10's version service. Preserve unrelated sheet content and expose only the UI needed for the approved actors/states.

## Out of scope

- Silent direct mutation, invented approvers/states, provider selection, exercise-catalog management, or retroactive modification of completed training.
- Reimplementing version persistence or general chat behavior.
- Medical diagnosis or adaptation beyond the reported context.

## Acceptance criteria

- CA-19.1: a controlled scenario reporting interference from a prior problem yields a context-related adaptation proposal.
- CA-19.2: only a change approved through the defined flow becomes a later current version.
- CA-19.3: unrelated portions of the sheet remain intact.
- CA-19.4: the changed current sheet persists after reauthentication.
- Integration re-verifies CA-17.2/CA-17.3 through Task 10 services.

## Tests

Use fake AI responses. Add contextual adaptation, unrelated-content preservation, cross-client isolation, rejection/no-op, approval authorization, provider failure, immutable-history, new-current-version, and reauthentication persistence tests. Run relevant suites and report results.

## Completion requirements

- Verify every assigned CA and RF-17 integration checks.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Codex prompt

Read `AGENTS.md`, then `docs/tasks/14-dynamic-training-adaptation.md`, then only the requirements sections/IDs listed under Required reading. Inspect the existing repository before modifying files. Implement only this task. Stop and ask if an unresolved DEC item requires a material human decision. Run relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
