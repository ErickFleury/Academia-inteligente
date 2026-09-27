# Administrative dashboard redesign

## Scope and reversal

User-approved frontend redesign preserving the existing dashboard, registration,
search, editing, account-status, provisioning, invitation, facial-enrollment and
client-erasure functions. No backend, API, data-model, authentication, Keycloak
or dependency changes. New elements visualize existing data only.

Branch: `redesign/admin-dashboard-ui`.
Baseline: `1e50c0d` on `redesign/client-instructor-ui`.
The earlier pushed baseline remains on `master` at `079ca6c`.

To review the prior admin interface while retaining the client/instructor
redesign, switch back to `redesign/client-instructor-ui` after saving any later
uncommitted work. The admin commits can also be reverted newest first; no
migration rollback is needed. Do not reset shared/pushed history.

## Requirements and checkpoints

Read and preserve RF-01–05, RF-07–09, RF-28–29, RF-32,
EXT-RF-FACE-01, EXT-RF-SOC-01 (moderation navigation), EXT-RF-LANG-01,
related RN-01–05/10/11/23/26/28/33/34 and RNF02–04. Existing acceptance
criteria and decision gates remain authoritative; no financial or new staff-role
functionality is inferred from the dashboard requirement.

1. Shared administrative sidebar, overview/clients/instructors sections and
   attendance presentation. Uses the client/instructor theme and icons.
2. Focused person-registration/edit dialogs, clearer directory rows and grouped
   fields, preserving biometric and account actions and their validations.
3. Responsive/keyboard checks, full frontend regression suite and production build.

## Design choices

Existing admin destinations move from dashboard header buttons into the shared
responsive sidebar. Indicators remain individually loaded and individually
retryable. Weekly bars use the already-returned counts and retain readable week
labels and exact values; the bars are decorative and do not imply unique clients,
occupancy or a new metric. Zero values are not shown as positive-height bars.
Management tabs remain mounted when hidden so queries/local drafts are retained.

Registration and editing now use a shared accessible dialog with a scrollable
body and persistent action footer. Phones use the full screen. Identity/contact,
address and account controls are grouped; directory rows separate names, email
addresses and status. Account provisioning, onboarding invitation and confirmed
client erasure retain their original service calls and permission rules.

Closing a registration dialog retains ordinary field drafts for the current
page, but clears the staged facial proof and unmounts the camera component.
Reopening requires facial readiness verification again; the interface explains
this. Closing is blocked during saves and postal-code lookup. Feedback appears
inside the active dialog, within its focus boundary. Existing facial enrollment
requirements and retry/duplicate-command protections remain in force.

Checkpoint 2 validation: 19 targeted management/workspace tests passed, including
registration, edit, provisioning, facial gating, directory searches and draft
retention. Existing shell/dashboard tests also passed during implementation.

## Verification and delivery

- `4d9eca6`: shared admin navigation, section tabs and dashboard presentation.
- `100267d`: focused client/instructor management dialogs and regression tests.
- Final documentation checkpoint records the completed validation below.

Changed implementation files: `app.tsx`, `admin-workspace.tsx`,
`admin-dashboard-page.tsx`, `client-management.tsx`, `employee-management.tsx`,
`components/application-shell.tsx`, `components/management-dialog.tsx`, and the
scope comment in `components/workspace-presentation.tsx`. Tests cover the shell,
workspace and both management components. Documentation changes are this report
and `docs/frontend-design.md`.

The full frontend suite exercised all **163 tests in 31 files**: 161 passed and
two OIDC URL assertions initially failed because Docker inherited local HTTPS
development URLs. Rerunning the complete app/auth files with the documented
localhost API/OIDC overrides passed all **44 tests**, resolving those two
failures without changing authentication code or assertions. All 163 distinct
tests therefore passed across the full run and targeted environment-corrected
rerun. The explicit rerun command was:

```sh
docker compose run --rm --no-deps \
  -e VITE_API_BASE_URL=http://localhost:8000 \
  -e VITE_OIDC_ISSUER=http://localhost:8080/realms/academia \
  -e VITE_OIDC_CLIENT_ID=academia-web \
  -e VITE_OIDC_REDIRECT_URI=http://localhost:5173/ \
  frontend npm test -- src/app.test.tsx src/auth.test.ts
```

TypeScript validation and production build passed after temporary browser
fixtures were removed (`docker compose run --rm --no-deps frontend npm run build`).
Output: 793.20 kB, gzip 227.86 kB. The existing non-blocking large-chunk warning
remains. `git diff --check` passed; no unrelated files, dependencies, backend
changes or migrations were introduced.

Isolated Firefox checks covered **41 page/layout states** at 360×800, 768×1024
and 1366×768. Coverage includes overview, both directories, create/edit dialogs,
account controls, mobile navigation, equipment/details, facial access and
moderation. Checks found no horizontal overflow, unnamed visible controls or
buttons below the established 44 px height. Dialog actions remained in the
viewport; Escape restored focus to registration/menu triggers. Representative
phone/desktop screenshots were visually inspected. Synthetic browser responses
were used; no real accounts, biometric captures or external service calls were
created. These are scoped UI checks, not a claim of complete accessibility or
live end-to-end biometric certification.

Ephemeral local evidence: `/tmp/admin-redesign-ui-results.json` and
`/tmp/admin-redesign-*.png`. Temporary repository fixtures were removed.
There are no unresolved redesign issues. Nothing was pushed.
