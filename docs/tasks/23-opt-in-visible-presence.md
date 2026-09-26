# Task 23 — Opt-in Visible Presence

**Status:** implemented — 2026-09-25

## Objective

Implement a privacy-preserving current-presence tag on an individual client
profile after explicit consent, persistence, source, and retention rules are
approved.

## Requirements covered

- EXT-RF-PRES-01: EXT-CA-PRES-01.1–EXT-CA-PRES-01.6.

## Related rules and constraints

- RN-04/RN-05: authenticated backend authorization and client isolation.
- RN-10/RN-11/RN-23/RN-34: biometric, health, logs, and reports remain private.
- RF-24/RF-25 anonymous occupancy must remain independent.
- Task 22 and EXT-DEC-PRES-01 are complete; preserve their boundaries.

## Prerequisites

- Tasks 06, 08, and 22 complete.
- EXT-DEC-PRES-01 recorded: use only default-off, profile-only derived presence.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; `docs/product-extensions.md` EXT-RF-PRES-01;
`docs/requirements.md` sections 2, 3.1, 4.1, 7.1.1, 8.4, 9.2, and 11; RF-23–RF-25;
RN-04, RN-05, RN-10, RN-11, RN-23, RN-34, RN-37; DEC-10, DEC-18, DEC-19,
EXT-DEC-PRES-01.

## Scope

Implement the approved default-off preference lifecycle, profile-only current
status tag, derived passage/freshness behavior, revocation, and responsive
authenticated-client UI. Resolve the viewer and subject identities through local
account/client links. Preserve anonymous count independently; do not create a
directory or list of present clients.

Reuse Task 08 ClientShell and Task 22 count display. Keep the occupancy view
anonymous; show the opt-in state and revocation control clearly on the client's
own profile, without suggesting everyone present is visible. Check phone,
tablet, and desktop.

## Out of scope

Inferring consent, exposing non-opted-in identities, public presence, health,
biometric, payment, credential, or administrative fields, social-network
features, or changing the occupancy implementation approved for Task 22.

## Acceptance criteria

- EXT-CA-PRES-01.1–EXT-CA-PRES-01.6 are verified.
- Direct API tests prove non-opted-in and revoked clients have no tag.
- Profile-presence failures do not remove the anonymous occupancy count.

## Tests

Add consent lifecycle, projection, presence/freshness, cross-client/privacy,
revocation, authorization, fallback, and responsive frontend tests. Ensure
biometric/camera details never appear in responses or logs.

## Completion requirements

Verify all extension criteria, review the Git diff, and report files changed,
tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/23-opt-in-visible-presence.md`, then only the requirements and
extension IDs listed under Required reading. Inspect the repository before
editing. Implement only opt-in profile presence while keeping anonymous occupancy
independent. Stop and ask if another unresolved item
requires a material human decision. Run relevant backend/frontend tests, review
the Git diff, and provide the required completion report. Follow
`docs/frontend-design.md` and reuse Task 08 shared layout/components; check phone,
tablet, and desktop. Do not commit or push.
