# Task 20 — Controlled Progress Sharing

## Objective

Implement the minimal approved private/shared progress-update feature for
authenticated clients without expanding it into a general social network.

## Requirements covered

- EXT-RF-SOC-01: EXT-CA-SOC-01.1–EXT-CA-SOC-01.6.

## Related rules and constraints

- RN-04/RN-05: backend authorization, client ownership, and explicit shared
  visibility apply to every API.
- RN-11/RN-23/RN-28/RN-33: sensitive data, logs, exports, and historical
  integrity remain protected.
- RNF02–RNF04: understandable privacy controls, mobile usability, modular policy.
- EXT-DEC-SOC-01 is **blocking** before persistence/API design.

## Prerequisites

- Tasks 03, 06, and 08 complete; Task 19 is recommended so the original MVP journey
  is verified first.
- EXT-DEC-SOC-01 recorded. Stop rather than selecting an audience, moderation,
  deletion, or retention model by inference.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; `docs/product-extensions.md` EXT-RF-SOC-01;
`docs/requirements.md` sections 2, 3.1, 4.1, 7.1.1, 8.4, 9.2, and 11; RF-04,
RF-05; RN-04, RN-05, RN-11, RN-23, RN-28, RN-33; RNF02–RNF04; DEC-17,
DEC-19, and EXT-DEC-SOC-01.

## Scope

Implement client-owned progress-update persistence, private/shared visibility,
backend visibility/ownership policies, author create/update/delete behavior as
approved, and a responsive client interface. Resolve the author from the
authenticated Keycloak subject, never from a browser-asserted client ID. Keep
post content explicit and isolated from sensitive domain aggregates.

Reuse Task 08 ClientShell and shared feed/card/feedback patterns. Clearly show author, date/time, content, and the author's own visibility state without encouraging disclosure of protected health or other private data. Check phone, tablet, and desktop; do not copy a social network's visual identity.

## Out of scope

Followers, friends, direct messages, comments, likes, rankings, leaderboards,
automatic health/training/payment/attendance publication, or unapproved
moderation/administrative access.

## Acceptance criteria

- EXT-CA-SOC-01.1–EXT-CA-SOC-01.6 are verified through UI and direct APIs.
- Cross-client mutation/deletion and private-post retrieval attempts are denied.
- No protected aggregate is serialized into a progress update automatically.

## Tests

Add domain/policy, persistence/API, cross-client negative, privacy/logging, and
responsive frontend tests for private/shared/author flows. Run only controlled
local tests; no external social service is introduced.

## Completion requirements

Verify all extension criteria, review the Git diff, and report files changed,
tests/results, decisions, and unresolved issues. Do not commit or push.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/20-controlled-progress-sharing.md`, then only the requirements and
extension IDs listed under Required reading. Inspect the repository before
editing. Implement only the minimal controlled progress-sharing extension. Follow
`docs/frontend-design.md` and reuse Task 08 shared layout/components; check phone,
tablet, and desktop. Stop
and ask if EXT-DEC-SOC-01 or another unresolved item requires a material human
decision. Run relevant backend/frontend tests, review the Git diff, and provide
the required completion report. Do not commit or push.
