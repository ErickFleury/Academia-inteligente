# Task 19 — MVP End-to-End Verification

## Objective

Verify the complete MVP critical path, cross-module security boundaries, external-failure behavior, and applicable non-functional criteria without adding new product scope.

## Requirements covered

- Verification only for RF-01–RF-05, RF-09–RF-13, RF-15–RF-19, and the
  approved MVP extension EXT-RF-AI-01.
- Re-run every CA assigned in Tasks 02–17; implementation ownership remains with those tasks. Include Task 06's RF-01/RF-04/RF-05 integration checks without changing original ownership. Task 08 and Task 18 are visual implementation/polish prerequisites, not owners of RF acceptance criteria.

## Related rules and constraints

- Recheck the RN mappings in `docs/implementation-plan.md`, especially RN-02, RN-04, RN-05, RN-11–RN-19, RN-23, and RN-29–RN-33.
- RNF01–RNF06 and CA-RNF01.1–CA-RNF06.3 apply across the integrated system.
- DEC-16 is **blocking for formal RNF acceptance** because load, timeout, viewport, usability, and availability measurement conditions are undefined.
- All earlier blocking decisions must already be resolved; do not repair missing decisions through test assumptions.

## Prerequisites

- Tasks 02–18 complete; Task 01 baseline remains healthy.
- DEC-16 recorded for formal RNF sign-off. If absent, run objective checks that are possible and report the unverified RNF criteria rather than claiming them.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; `docs/requirements.md` sections 2.2, 3, 3.1, 4, 4.1, 8,
9 (especially DEC-16), and 11; `docs/product-extensions.md` EXT-RF-AI-01;
review every MVP RF/CA, extension CA, and completed task report for Tasks 02–17.

## Scope

Add and run end-to-end/contract checks for the critical journey: admin authentication/authorization, local client creation with Keycloak provisioning, client-only role assignment and first-access password setup, invitation, secure-link/form and conversational onboarding, shared structured data capture/completion, safe initial generation, current-sheet display, isolated chat, approved adaptation, and persistence after reauthentication. Validate provisioning compensation, inactive-account rejection, client denial of administrative APIs, identity-derived client ownership, unauthorized/cross-client paths, and e-mail/AI failure containment. Document traceability from each MVP and extension CA to its passing test or remaining issue.

Confirm Task 08 shared UI patterns and Task 18 polish did not regress existing functionality, accessibility, or phone/tablet/desktop usability. This verification does not introduce a new visual language.

## Out of scope

- New features, redesigns, broad refactors, production deployment, and all non-MVP RFs.
- Silently weakening criteria to make tests pass.
- Large fixes spanning task boundaries; report them to the owning task unless a small in-scope integration correction is clearly sufficient.

## Acceptance criteria

- Every MVP CA and EXT-CA-AI-01.1–EXT-CA-AI-01.8 has a recorded pass or explicit unresolved failure; none is omitted.
- Critical-path tests pass under the approved local runtime.
- Direct API authorization and cross-client isolation are exercised, not inferred from UI tests.
- E-mail/AI outages are controlled and do not corrupt unrelated or approved state.
- Each CA-RNF01.1–CA-RNF06.3 is measured as defined by DEC-16 or explicitly reported unverified.

## Tests

Run the full relevant unit, integration, API-contract, frontend, and end-to-end suites. Use controlled e-mail/AI substitutes, not live external services. Run approved performance, responsive, usability, and failure-recovery checks. Report commands, results, skipped checks, and evidence mapping.

## Completion requirements

- Verify all MVP CA and applicable RNF criteria or report precise gaps.
- Inspect the Git diff for unrelated changes.
- Report files changed, tests executed/results, important decisions, and unresolved issues.
- Do not commit or push unless explicitly requested.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then `docs/tasks/19-mvp-end-to-end-verification.md`, then only the requirements and extension sections/IDs listed under Required reading. Inspect the existing repository and completed task reports before modifying files. Implement only this verification task, including conversational onboarding, identity-derived client ownership, and Task 08/18 design consistency against `docs/frontend-design.md` on phone/tablet/desktop. Stop and ask if an unresolved DEC item requires a material human decision. Run the relevant tests, review the Git diff, and provide the completion report required by `AGENTS.md` and this task. Do not commit or push.
