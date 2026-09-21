# Task 21 — Opt-in Visible Presence

## Objective

Implement a privacy-preserving named current-presence view for authenticated
clients only after explicit consent, persistence, source, and retention rules
are approved.

## Requirements covered

- EXT-RF-PRES-01: EXT-CA-PRES-01.1–EXT-CA-PRES-01.6.

## Related rules and constraints

- RN-04/RN-05: authenticated backend authorization and client isolation.
- RN-10/RN-11/RN-23/RN-34: biometric, health, logs, and reports remain private.
- RF-24X/RF-25X anonymous occupancy must remain independent.
- DEC-10 and EXT-DEC-PRES-01 are both **blocking**.

## Prerequisites

- Tasks 06 and 20 complete.
- DEC-10 and EXT-DEC-PRES-01 recorded. Stop before migrations, consent UI, or
  presence queries if either remains unresolved.

## Required reading

Read `AGENTS.md`; `docs/product-extensions.md` EXT-RF-PRES-01;
`docs/requirements.md` sections 2, 3.1, 4.1, 7.1.1, 8.4, 9.2, and 11; RF-23–RF-25X;
RN-04, RN-05, RN-10, RN-11, RN-23, RN-34, RN-37; DEC-10, DEC-18, DEC-19,
EXT-DEC-PRES-01.

## Scope

Implement the approved default-off preference lifecycle, minimal opted-in
profile projection, presence query, revocation/freshness behavior, and responsive
authenticated-client UI. Resolve the viewer and subject identities through local
account/client links. Preserve anonymous count independently.

## Out of scope

Inferring consent, exposing non-opted-in identities, public presence, health,
biometric, payment, credential, or administrative fields, social-network
features, or changing the occupancy implementation approved for Task 20.

## Acceptance criteria

- EXT-CA-PRES-01.1–EXT-CA-PRES-01.6 are verified.
- Direct API tests prove non-opted-in and revoked clients do not appear.
- Named-view failures do not remove the anonymous occupancy count.

## Tests

Add consent lifecycle, projection, presence/freshness, cross-client/privacy,
revocation, authorization, fallback, and responsive frontend tests. Ensure
biometric/camera details never appear in responses or logs.

## Completion requirements

Verify all extension criteria, review the Git diff, and report files changed,
tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/21-opt-in-visible-presence.md`, then only the requirements and
extension IDs listed under Required reading. Inspect the repository before
editing. Implement only opt-in named presence while keeping anonymous occupancy
independent. Stop and ask if DEC-10, EXT-DEC-PRES-01, or another unresolved item
requires a material human decision. Run relevant backend/frontend tests, review
the Git diff, and provide the required completion report. Do not commit or push.
