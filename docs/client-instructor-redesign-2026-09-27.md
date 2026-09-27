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
- Instructor content checkpoint: 24 targeted tests passed, covering exact client
  filters, onboarding validation, draft editing/saving, approval, stale state,
  immutable history, equipment references and read-only social access.
  TypeScript passed. The instructor Perfil placeholder remains a placeholder.

## Final verification

Implementation checkpoints:

- `d2c1815`: shared sidebar, icons, scoped theme and page presentation.
- `2e5dbcd`: client page contents and shared social cards.
- `df15d0a`: instructor client/plan workspaces and read-only social layouts.
- The final checkpoint containing this report tightens the phone profile header
  and records verification. At delivery, the complete redesign range is
  `079ca6c..HEAD` on `redesign/client-instructor-ui`.

Commands run through the existing Docker frontend service:

- `npm test` with test API/OIDC localhost environment overrides: **159 passed,
  30 files**. Includes administrative regression coverage for the shared
  component boundaries. Existing tests were retained without relaxed assertions.
- `npm run lint`: TypeScript passed at each implementation checkpoint.
- `npm run build`: final TypeScript and production build passed after preview
  fixtures were removed; output 787.54 kB, gzip 226.72 kB. The pre-existing
  non-blocking chunk-size warning remains.
- `git diff --check`: passed.

Isolated Firefox checks used synthetic in-browser responses (no live record,
account or AI mutations). At 360×800, 768×1024 and 1366×768, 77 page/state checks
covered current/draft training, training chat, onboarding conversation/form,
feed, own/other profile, post detail, instructor client search/selection,
pending-plan preview/edit, own/all-plan collections/history, read-only feed/post,
both equipment surfaces and the instructor profile placeholder. All passed
horizontal overflow, visible-control naming and 44 px button checks. A further
19 checks verified the final compact phone profile and active sidebar/menu
states with dual-role switching visible. Keyboard Enter opens the mobile panel;
Escape closes it and restores focus to its trigger. Screenshots were visually
inspected for representative phone/tablet/desktop states. These are scoped UI
checks, not a new claim of complete WCAG or formal owner-journey certification.

Local ephemeral evidence: `/tmp/redesign-ui-results.json`,
`/tmp/redesign-final-ui-results.json` and `/tmp/redesign-*.png`.
The temporary HTML/TSX preview entry points were removed before the final build.

## Changed-file map and remaining scope

- `frontend/src/components/application-shell.tsx`, `workspace-presentation.tsx`,
  `ui.tsx` and `instructor-shell.tsx`: navigation and shared visual foundations.
- Client page TSX files for training, chat, onboarding, feed, profile and post
  detail, plus `post-card.tsx`: content grouping and consistent controls.
- Instructor client, pending-plan, collection, feed and post-detail TSX files,
  `components/training-plan-content.tsx` and `training-draft-fields.tsx`:
  operational reading/editing layouts.
- `docs/frontend-design.md` and this report: design and reversal guidance.

The instructor profile remains the existing future-feature state; equipment
contents retain the prior redesign. All existing destinations and actions remain.
No backend/API/database/authentication/dependency changes or new features were
introduced. No database rollback is required. No product decision remains open
for this presentation scope. Owner preference review of the visual direction
remains possible from the isolated branch; `master` is untouched.
