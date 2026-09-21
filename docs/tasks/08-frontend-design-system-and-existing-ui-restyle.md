# Task 08 — Frontend Design System and Existing UI Restyle

## Objective

Establish the approved visual system in React/MUI and restyle the frontend
delivered by Tasks 01–07 before building further client-facing screens.

## Requirements covered

Presentation integration only for existing RF-01–RF-05 and RF-09 UI. This task
does not claim new RF/CA behavior or retroactively change completed task scope.
RNF02/RNF03 usability and responsiveness are the principal quality criteria.

## Related rules and constraints

- `docs/frontend-design.md` is the approved visual/UI source of truth.
- RN-02/RN-04/RN-05 and DEC-04/DEC-05/DEC-17: preserve authentication,
  authorization, account state, and client isolation while changing presentation.
- RNF01/RNF02/RNF03/RNF04: visible progress, clear forms/navigation, phone
  usability, and reusable components.
- DEC-03 fixes React/TypeScript/Vite/MUI; no additional UI framework or major
  dependency is approved. DEC-16 is needed only for formal RNF measurements.

## Prerequisites

- Tasks 01–07 completed under their historical scopes.
- Read the approved `docs/frontend-design.md` and inspect the actual frontend
  before choosing shared components or refactoring any screen.

## Required reading

Read `AGENTS.md`; `docs/frontend-design.md`; `docs/requirements.md`
RF-01–RF-05 and RF-09 with their CA, RNF01–RNF04, RN-02/RN-04/RN-05,
sections 2.1–2.2 and 9.2; `docs/decisions.md` DEC-03–DEC-05 and DEC-17;
completed Tasks 01–07 only for existing frontend behavior and test contracts.

## Scope

- Build a reusable global MUI theme: typography, semantic colors and contrast,
  backgrounds/surfaces, spacing, radii, borders, elevation, and focus treatment.
  Define shared page/section headers, responsive containers, navigation,
  buttons, forms (including text fields, selects, checkboxes, radios, switches),
  chips/badges, cards, dialogs, alerts, snackbars/toasts, skeleton/loading,
  empty, and error patterns. Use existing MUI capabilities first.
- Establish distinct but related ClientShell and AdminShell foundations. Apply
  them to current routes where appropriate without inventing unimplemented
  client features or administrative data.
- Restyle the current app sign-in entry, callback/session states, authenticated
  landing/shell, authorization denial, admin client registration, search/list,
  detail, profile editing, activation/deactivation, identity provisioning and
  retry, onboarding invitation, navigation, forms, actions, loading, errors,
  success feedback, and empty states. Include existing dialog/notification
  behavior where present; define shared patterns for future use.
- Keep content and actions clear at representative phone, tablet, and desktop
  widths. Dense admin views may use a lighter content surface or tighter
  spacing while retaining the same visual language.
- Preserve current client/server contracts, OIDC behavior, role boundaries,
  Keycloak first access, provisioning states, invitation behavior, and all
  tests of Tasks 01–07. Only fix an exposed functional bug when it is small,
  directly caused or revealed by the presentation refactor, and separately
  verified; otherwise report it to its owning task.

## Out of scope

- Backend, database, API contract, Keycloak realm/theme, or business-flow
  changes; new client features, RFs, AI, onboarding content, and production
  imagery.
- Copying Strive Gym Club code, assets, text, branding, or exact page layout.
- Adding another UI framework or introducing unapproved dependencies.
- Treating the initial restyle as the final production polish (Task 18).

## Acceptance criteria

- One reusable theme and shared UI foundation governs existing public,
  authenticated/client, and administrative screens; repeated visual patterns
  are not implemented independently in each page.
- All existing Tasks 01–07 frontend flows remain usable and retain their
  authorization and API behavior, including pending/failed provisioning and
  invitation feedback.
- Phone, tablet, and desktop checks show usable navigation, forms, lists,
  loading/error/empty states, and touch targets without ordinary client
  horizontal scrolling.
- Semantic structure, labels, keyboard navigation, focus visibility, contrast,
  and non-color status cues remain accessible.
- No reference-site asset or content is copied, and missing imagery never
  prevents a core action.

## Tests

Run existing frontend tests, typecheck/lint, and build. Add or adjust focused
tests only where shared UI behavior or changed presentation selectors need
coverage. Inspect the main flows at representative phone/tablet/desktop sizes
and record accessibility findings. Do not require live external services for
automated tests.

## Completion requirements

Record shared components/tokens introduced, screens restyled, responsive and
accessibility checks, unchanged behavior, test results, and any remaining
visual/functional issues. Review the Git diff for unrelated changes. Do not
commit or push.

## Ready-to-use Terra/Medium Codex prompt

Use Terra with Medium reasoning. Read `AGENTS.md`, then
`docs/tasks/08-frontend-design-system-and-existing-ui-restyle.md`, then the
Required reading listed there. Inspect the existing frontend and shared MUI
setup before editing. Build the shared design system and restyle only the
frontend from Tasks 01–07, preserving behavior/API contracts and following
`docs/frontend-design.md`. Run relevant frontend tests, typecheck/build,
responsive/accessibility checks, review the diff, and report results. Do not
commit or push.
