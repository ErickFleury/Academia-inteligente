# Task 18 — MVP Frontend Visual Polish

## Objective

Polish the integrated MVP frontend after its major screens exist, using the
Task 08 design system consistently before final end-to-end verification.

## Requirements covered

Presentation and usability verification for implemented MVP UI: RF-01–RF-05,
RF-09–RF-13, RF-15–RF-19, and EXT-RF-AI-01. This task introduces no new
product behavior and does not replace acceptance testing in Task 19.

## Related rules and constraints

- `docs/frontend-design.md` and Task 08 govern shared UI patterns.
- RNF01–RNF04 cover visible progress, usability, responsiveness, and
  maintainability; DEC-16 still governs formal measurement thresholds.
- RN-05/RN-11/RN-23/RN-29 and applicable decisions continue to protect
  client/health context and authorize operations.

## Prerequisites

- Tasks 08–17 complete for the MVP screens being polished; Task 19 follows.
- All relevant product/decision gates were resolved by the feature owners.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; `docs/requirements.md`
sections 2–4, 8, 9.2, and 11; `docs/product-extensions.md` EXT-RF-AI-01;
RNF01–RNF04 and applicable MVP RF/CA; Task 08 and completed UI task reports
for Tasks 09–17; DEC-16 for formal acceptance limits.

## Scope

- Audit implemented entry, admin, onboarding, training, AI chat, adaptation,
  loading, empty, error, and feedback states against the shared theme/shells.
- Resolve inconsistent type hierarchy, spacing, controls, transitions,
  unnecessary visual duplication, and copy using existing shared components.
- Check phone, tablet, and desktop edge cases; keyboard/focus, semantic
  headings, labels, contrast, and non-color status communication.
- Preserve task-owned behavior and API contracts. Report larger functional
  defects to their owning task rather than changing unrelated business logic.

## Out of scope

- New product features, backend/Keycloak changes, new UI framework, marketing
  site reproduction, or rewriting Task 08 foundations without demonstrated
  inconsistency.

## Acceptance criteria

- Major MVP screens share the established visual language with suitable client
  and admin density, and no obvious duplicate primitives remain.
- Representative phone/tablet/desktop flows, including onboarding, training,
  and chat, remain readable and operable; no ordinary client horizontal scroll.
- Loading transitions, empty states, errors, copy, focus, labels, and contrast
  are consistent and accessible without changing business outcomes.
- Existing feature tests remain green or any unresolved issue is reported
  precisely for Task 19/its owning feature.

## Tests

Run the relevant frontend tests, typecheck/lint, build, and targeted responsive
and keyboard/accessibility checks. Adjust tests only for actual shared UI
behavior or presentation restructuring. Record remaining formal RNF items
pending DEC-16 rather than claiming a pass.

## Completion requirements

Report areas checked/polished, files changed, test and viewport results,
important design decisions, and unresolved issues. Review the Git diff for
unrelated changes. Do not commit or push.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/18-mvp-frontend-visual-polish.md`, then its Required reading.
Inspect the implemented MVP frontend and Task 08 shared UI. Polish visual,
responsive, loading/empty/error, copy, and accessibility consistency without
changing business behavior; follow `docs/frontend-design.md`. Run relevant
frontend checks, review the diff, and report results. Do not commit or push.
