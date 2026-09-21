# Task 21 — Equipment Catalog and Quantities

## Objective

Implement original equipment management/consultation plus total active quantity
by approved logical type/model, without implying live equipment availability.

## Requirements covered

- RF-32: CA-32.1–CA-32.5.
- RF-33: CA-33.1–CA-33.5.
- EXT-RF-EQP-01: EXT-CA-EQP-01.1–EXT-CA-EQP-01.4.

## Related rules and constraints

- RN-04: management is backend-authorized.
- RN-33: deactivation preserves required history.
- RNF01–RNF04: performant, understandable, responsive, modular catalog.
- EXT-DEC-EQP-01 is **blocking** before migrations.

## Prerequisites

- Tasks 03, 06, and 08 complete; Task 19 is recommended before post-MVP work.
- EXT-DEC-EQP-01 recorded with the unit/aggregate/grouping model. Stop rather
  than infer real-time use or a grouping key.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; RF-32/RF-33 and CA-32.1–CA-33.5;
`docs/product-extensions.md` EXT-RF-EQP-01; `docs/requirements.md` sections 3.1,
4, 7.1.1, 8.4, and 11; RN-04, RN-20 only where exercise linkage is approved,
RN-33; RNF01–RNF04; DEC-17, DEC-19, EXT-DEC-EQP-01.

## Scope

Implement authorized equipment create/read/update/deactivate behavior, optional
image and approved descriptive information, active client/visitor catalog, and
active total per approved type/model. Label counts as total active units. Keep
administrative APIs protected and client/visitor responses free of internal
administrative data.

Reuse Task 08 shared components. Client/visitor catalog may use approved local imagery with clear name/type, concise metadata, total units, and detail hierarchy; absence of an image must not break use. Keep admin management denser than client browsing. Check phone, tablet, and desktop.

## Out of scope

Real-time free/occupied status, reservations, sensors, WebSockets, exercise CRUD,
or a new storage/infrastructure technology.

## Acceptance criteria

- CA-32.1–CA-33.5 and EXT-CA-EQP-01.1–EXT-CA-EQP-01.4 are verified.
- A catalog item such as “Leg Press — Total units: 4” cannot be interpreted by
  API/UI wording as “4 currently free.”
- Unauthorized management and inactive-item public visibility are denied.

## Tests

Add model/count, CRUD/deactivation/history, authorization, active catalog,
image/optional-data, and responsive UI tests. Include count updates and explicit
no-live-availability contract assertions.

## Completion requirements

Verify all original and extension criteria, review the Git diff, and report
files changed, tests/results, decisions, and unresolved issues. Do not commit or
push.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/21-equipment-catalog-and-quantities.md`, then only the requirements
and extension IDs listed under Required reading. Inspect the repository before
editing. Implement only RF-32, RF-33, and EXT-RF-EQP-01. Follow
`docs/frontend-design.md` and reuse Task 08 shared layout/components; check phone,
tablet, and desktop. Stop and ask if
EXT-DEC-EQP-01 or another unresolved item requires a material human decision.
Run relevant backend/frontend tests, review the Git diff, and provide the
required completion report. Do not commit or push.
