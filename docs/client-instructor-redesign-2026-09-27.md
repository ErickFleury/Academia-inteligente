# Client and instructor visual redesign

## Scope and baseline

User-approved presentation-only redesign of all existing client and instructor
surfaces. Keep destinations, actions, state transitions, permissions, data and
API contracts. No backend, dependency, authentication or Keycloak changes.

Baseline: `079ca6c28073fb6fcf511205364adef64b1dc59a` on `master`, pushed by the owner.
Work branch: `redesign/client-instructor-ui`.

Requirements preserved: RF-11–RF-19, RF-25, RF-33; EXT-RF-AI-01,
EXT-RF-SOC-01–03, EXT-RF-PRES-01, EXT-RF-EQP-01, EXT-RF-INST-01–05,
EXT-RF-LANG-01. Acceptance criteria remain unchanged. Applicable rules include
RN-04/05/11–20/23/28–33 and RNF02–04. The canonical specification and
`frontend-design.md` were read before editing.

## Checkpoints

1. Shared client/instructor presentation and navigation.
2. Client training, assistant, onboarding, feed, profile and post detail.
3. Instructor client workspace, plan review/collections and read-only social views.
4. Responsive, keyboard and full frontend regression verification.

Each checkpoint is committed separately. The recently redesigned equipment
pages retain their contents and receive the shared shell treatment.

## Reverting

Before merging this branch, switching back to `master` restores the pushed
checkpoint (after saving any later uncommitted work). No database rollback is
needed. Individual commits can be reverted with `git revert <commit>`; revert
later commits first when they touch the same presentation code. If this branch
is merged/pushed, use new revert commits rather than rewriting shared history.
The final verification section records the exact commit range and results.

## Implementation evidence

- Foundation checkpoint: `d2c1815`; 16 navigation/area-switch tests and TypeScript
  passed. The menu order, responsive drawer and authorization-dependent switch
  remain intact.
- Client content checkpoint: 21 targeted client/social regression tests and
  TypeScript passed. Changes are limited to markup, styles and accessible
  presentation; existing request handlers and persistence contracts are retained.
