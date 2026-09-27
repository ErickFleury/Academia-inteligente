# Task 37 — Instructor Role Integrated Verification Report

## Status and scope

Technical verification passed on 2026-09-27. **Task 37 is done by explicit user
direction:** “mark task 37 as done and i will do the checklist now.” The user
will perform the intended-user checklist. Its results and the eight-hour
availability soak required by `docs/requirements.md` section 4.0.1 (DEC-16)
remain unverified follow-up evidence. User-directed task closure does not mark
these acceptance checks as passed or replace them with automated test results.

This report covers RF-01/CA-01.4–01.5, RF-03/CA-03.5–03.6, RF-07/RF-08,
EXT-RF-INST-01–05, and their assigned integration, language, and RNF boundaries.
It does not approve unrelated RFs, change authorization policy, or satisfy the
deferred biometric CA-03.4. The canonical requirements remain unchanged.

Completed implementation checkpoints:

| Task | Commit | Result |
| --- | --- | --- |
| Existing implementation through 31 | `2790392` | Preserved the initial working tree before new implementation. |
| 32 | `882518b` | Current collections, filters, immutable history, confirmed draft replacement. |
| 33 | `fd7d483` | Active-client workspace and first manual draft. |
| 34 | `b93a811` | Instructor onboarding continuation, completion, and in-place correction. |
| 35 | `dfc49d6` | Separate equipment operational state. |
| 36 | `aa6eb44` | Equipment-aware authoring, AI context, validation, and historical preservation. |

The user's explicit per-task checkpoint instruction supersedes the task
prompt's older “Do not commit” instruction. The user explicitly authorized
closing Task 37 before the remaining formal evidence is available; its completed
checkpoint retains those limitations in this report.

## Environment and commands

Local Linux development host; repository Docker Compose services; repository
Python 3.13/FastAPI/PostgreSQL and Node/Vite versions; installed Firefox ESR.
Tests use synthetic records and fake Keycloak, CEP, e-mail, and AI adapters.
PostgreSQL tests create isolated schemas and remove them afterwards. No live
provider was used to establish functional test results; no dependency was added.

| Check | Command | Result |
| --- | --- | --- |
| Complete backend, including PostgreSQL integration and concurrency | `docker compose run --rm --no-deps -e TEST_POSTGRES=1 -e CORS_ALLOWED_ORIGINS=http://localhost:5173 backend pytest -q` | 248 passed, no skips, 23.85 s. |
| Complete frontend | `docker compose run --rm --no-deps -e VITE_API_BASE_URL=http://localhost:8000 -e VITE_OIDC_ISSUER=http://localhost:8080/realms/academia -e VITE_OIDC_REDIRECT_URI=http://localhost:5173/ frontend npm test -- --reporter=json --outputFile=/app/.task37-frontend.json` | 115 passed, no failures. Temporary JSON output removed after inspection. |
| Python lint | `docker compose run --rm --no-deps backend ruff check . --output-format concise` | Passed. |
| Frontend lint | `docker compose run --rm --no-deps frontend npm run lint` | Passed. |
| TypeScript and production bundle | `docker compose run --rm --no-deps frontend npm run build` | Passed; existing non-fatal bundle-size advisory remains. |
| Diff whitespace | `git diff --check` | Passed. |
| Scope review | `git status --short`, full tracked diff and new-file review | Changes grouped below; temporary browser fixtures removed. |

The PostgreSQL suite includes actual concurrent transactions for review,
draft replacement, first manual draft, equipment state, and approval versus
inventory changes. It also exercises the equipment-reference and operational-
state migration round trips. SQLite-only success is not used as evidence for
those races or PostgreSQL constraints.

## Functional acceptance evidence

Paths below are relative to `backend/tests/` unless prefixed with `frontend/`.
“Pass” means the listed automated/scoped browser evidence passed; it does not
claim intended-user usability completion. Related criteria are grouped only
when the evidence exercises each of them.

| Acceptance criteria | Evidence and observed result |
| --- | --- |
| CA-01.4 | **Pass:** `test_clients.py` creates normalized authoritative person data, validates CPF/phone/address, and rejects invalid input; `frontend/src/client-management.test.tsx` covers the full form and CEP fallback. No client CNPJ field. |
| CA-01.5 | **Pass:** `test_shared_accounts.py` links a Client to an existing instructor Account, rejects conflicting identity, and retains the employee role. |
| CA-03.5 | **Pass:** `test_clients.py`, `test_shared_accounts.py`, and client-management UI tests cover persisted shared-field updates, validation rollback, and retry feedback. |
| CA-03.6 | **Pass:** `test_shared_accounts.py` covers durable pending reconciliation, provider failure, independent activity, stale tokens, and recovery from either administrative endpoint. |
| CA-07.1, CA-07.2 | **Pass:** `test_employee_api.py::test_admin_create_search_view_and_clear_optional_fields` and employee UI registration test create and retrieve the identified employee with complete required data. |
| CA-07.3 | **Pass:** employee API identity-conflict and update-conflict tests reject incompatible duplicates without partial accounts. |
| CA-07.4 | **Pass:** employee API validation and specialization-escalation tests, CNPJ tests in `test_employees.py`, and employee UI complete-person form test. Only instructor is assignable. |
| CA-07.5 | **Pass:** `test_employees.py` and `test_shared_accounts.py` cover first-access delivery, retries, no repeated first-access for an existing identity, unknown-subject rejection, and durable recovery. Credentials remain owned by the identity adapter. |
| CA-07.6 | **Pass:** `test_employees.py::test_instructor_can_share_an_active_client_account_and_reconcile_roles`; reverse linkage and failed-provider recovery in shared-account tests. |
| CA-08.1 | **Pass:** employee API create/search/view test and UI list/detail/error tests. |
| CA-08.2, CA-08.4 | **Pass:** employee API persists edits and clears optional fields; invalid edits preserve saved data; shared-account tests verify shared personal identity updates. Browser form audit confirms all initial fields remain editable. |
| CA-08.3, CA-08.5 | **Pass:** shared-account independent deactivation/reconciliation and stale mixed-role tests; instructor API families deny an inactive local Employee despite a role-bearing token. |
| EXT-CA-INST-01.1 | **Pass:** local linked active Employee plus token role required by `test_instructor_integration.py` and shared-account stale-role tests. |
| EXT-CA-INST-01.2 | **Pass:** `frontend/src/instructor-shell.test.tsx`, `app.test.tsx`, and `components/area-switch.test.tsx`: exact seven destinations, default Feed, sign-out, mobile drawer, same-session role switching, onboarding/default entry, and no switch without both roles. Browser keyboard drawer checks pass. |
| EXT-CA-INST-01.3 | **Pass:** `test_progress_updates.py` public/private/moderation tests and pagination regression, repeated on real PostgreSQL by `test_instructor_performance_postgres.py`. Private posts are excluded before pagination. |
| EXT-CA-INST-01.4 | **Pass:** social read-only authorization tests, post/comment image parent-privacy tests, and `frontend/src/instructor-feed-page.test.tsx`. Shared cards show permitted media/counts; instructor has no compose/like/edit/follow actions. |
| EXT-CA-INST-01.5 | **Pass:** bounded Perfil route in `frontend/src/app.test.tsx` and shell test; shell performs no social-profile creation request. |
| EXT-CA-INST-01.6 | **Pass:** direct negative-identity matrix in `test_instructor_integration.py`, including media endpoints. |
| EXT-CA-INST-02.1 | **Pass:** lifecycle, generation, adaptation, chat, and review tests converge initial AI/manual/accepted adaptation/current edits on the sole client draft. |
| EXT-CA-INST-02.2 | **Pass:** `test_training_review.py::test_pending_api_minimization_pagination_detail_and_atomic_approval` and pending-page UI tests. |
| EXT-CA-INST-02.3 | **Pass:** save/revision guards in review tests and pending-page UI tests; saving never selects a current version. |
| EXT-CA-INST-02.4 | **Pass:** direct/edit-then-approve lifecycle tests, transaction rollback test, and real PostgreSQL concurrent review tests. |
| EXT-CA-INST-02.5 | **Pass:** `test_training_current_api.py` and `frontend/src/current-training-page.test.tsx` verify responsible instructor and approval date. |
| EXT-CA-INST-02.6 | **Pass:** review and collections tests retain historical approval attribution and immutable approved content. |
| EXT-CA-INST-02.7 | **Pass:** `test_training_review_postgres.py` two real transactions; review tests reject stale source responses and version/revision mismatches. |
| EXT-CA-INST-02.8 | **Pass:** review privacy/minimization tests, current-sheet own-client isolation, and full instructor negative-identity matrix. |
| EXT-CA-INST-03.1 | **Pass:** `test_training_collections.py` mine scope uses approved-version responsibility, including retained attribution. |
| EXT-CA-INST-03.2 | **Pass:** same suite verifies all scope, combined name/responsible/date filters, inclusive São Paulo dates, minimal projection, bounded pagination, and set-based queries. |
| EXT-CA-INST-03.3 | **Pass:** current/history detail and immutable content tests plus `frontend/src/instructor-plan-collections-page.test.tsx`. |
| EXT-CA-INST-03.4 | **Pass:** clone tests preserve the current version and create a separate sole unapproved draft. |
| EXT-CA-INST-03.5 | **Pass:** exact-revision confirmation, cancel/conflict, superseded unapproved draft, rollback, and real PostgreSQL confirmation races; UI dialog tests. |
| EXT-CA-INST-03.6 | **Pass:** `test_instructor_clients.py` first-manual-draft test checks both entry points, no current/draft prerequisite, and separate approval; workspace UI tests. |
| EXT-CA-INST-03.7 | **Pass:** collection authorization tests, full identity matrix, and PostgreSQL replacement/first-draft races. |
| EXT-CA-INST-04.1 | **Pass:** instructor-client search tests cover active clients, normalized accent/case/whitespace matching, ordering, and PostgreSQL accent behavior. |
| EXT-CA-INST-04.2 | **Pass:** client list tests cover exact combinable state filters and derive draft/current status without duplicate state. |
| EXT-CA-INST-04.3 | **Pass:** minimized projection/query-count tests and `frontend/src/instructor-clients-page.test.tsx` contextual actions. No contact or health fields in client search lists. |
| EXT-CA-INST-04.4 | **Pass:** `test_instructor_onboarding.py` and `frontend/src/instructor-onboarding.test.tsx` continue, save, validate, and intentionally complete unfinished onboarding. |
| EXT-CA-INST-04.5 | **Pass:** same tests update all approved fields in place after completion, preserve the original completion timestamp, and retain client read-only behavior. |
| EXT-CA-INST-04.6 | **Pass:** missing/inactive client, inactive/unlinked instructor, other staff, anonymous, and private raw-chat denial tests. |
| EXT-CA-INST-04.7 | **Pass:** onboarding tests verify Employee attribution without submitted health values in audit records. |
| EXT-CA-INST-05.1 | **Pass:** operational-state service/API tests and real PostgreSQL migration test populate legacy units and enforce allowed states. |
| EXT-CA-INST-05.2 | **Pass:** `test_equipment_operational.py` and equipment-page UI tests allow read/toggle only; inventory mutations remain denied. |
| EXT-CA-INST-05.3 | **Pass:** operational-state and existing `test_equipment.py` tests preserve independent inventory activity and derived active quantity. |
| EXT-CA-INST-05.4 | **Pass:** equipment-usability tests require an active model with an active operational unit for new/changed items, selectors, AI context, save, and approval. PostgreSQL tests serialize inventory writers with approval validation. |
| EXT-CA-INST-05.5 | **Pass:** exact unchanged approved-item tests preserve current/history after outages; edits, duplicates, and saved-but-never-approved items do not inherit this exception. Migration tests preserve legacy content. |
| EXT-CA-INST-05.6 | **Pass:** API exposes operational state without occupancy/reservation meaning; unauthorized toggles and stale revisions fail closed. |
| RF-11–RF-19 integration | **Pass:** complete onboarding, conversation, generation, current, lifecycle, review, chat, and adaptation suites. Provider failures, client rejection, stale baselines, and instructor review preserve authoritative current plans and private context. |
| RF-32/RF-33, EXT-RF-EQP-01 integration | **Pass:** existing catalog/inventory suite plus operational/usability suites; inventory count remains distinct from usable-model eligibility. |
| EXT-RF-SOC-02/03 integration | **Pass within changed boundaries:** existing progress/social tests and shared-card client UI regression tests retain privacy/moderation/media behavior and client interactions. No claim of unrelated social feature verification. |

## Security and privacy evidence

`test_instructor_integration.py` exercises 23 read/write endpoint shapes for each
of anonymous, client-only, admin-only, attendant, base Employee, inactive
instructor, and unlinked instructor-token identities. Every call returns a
controlled 401/403; rejected mutations preserve the draft revision and equipment
state. Active instructor wrong-target reads return 404. Administrative client/
employee access and client-private onboarding/chat endpoints remain denied.
Positive cases are exercised by the feature suites listed above.

List projections, onboarding audit content, AI context minimization, and
cross-client/private-post isolation have explicit assertions in their feature
tests. No real passwords, access tokens, first-access credentials, or health
values were added to fixtures, reports, or logs. Synthetic image responses are
served through the same authenticated parent-policy checks. This is scoped
verification, not a claim of an independent security audit.

## Browser, language, and RNF evidence

An ephemeral Vite fixture renders the actual shared/admin/instructor components
with deterministic synthetic responses. Firefox is driven through its existing
Marionette interface; no browser automation dependency was added. The phone
case uses an exact 360×800 frame because Firefox's outer-window minimum is
wider. Tablet and desktop content viewports are exactly 768×1024 and 1366×768.

Task 32–36 browser checks covered collection/history/editor, client workspace,
onboarding, equipment, and equipment selection. Task 37 rechecked administrative
client and instructor forms, instructor feed, and post detail at all three
sizes. Its 12 combinations had one main landmark and one h1, no unlabeled
visible controls, no audited button below 43 CSS pixels (theme minimum 44), no
ordinary horizontal overflow, and loaded media with accessible text. Mobile
Tab/Enter opens navigation; Escape closes it and restores trigger focus. The
dual-role switch remains outside the seven-item menu. Representative phone and
desktop screenshots were visually inspected for clipping, overlap, and contrast.

Processing feedback was measured with a synthetic 600 ms provider delay at all
three sizes for both administrative forms. The clicked button is disabled and
changes to Portuguese processing text within the visible viewport; all six
observations were 54–67 ms, below 200 ms. Temporary fixture pages, screenshots, and raw
browser output are not application assets and are not committed.

| Criterion | Evidence/status |
| --- | --- |
| EXT-CA-LANG-01.1 | **Pass in affected scope:** application forms, feedback, navigation, controls, accessible labels, and read-only instructor pages use pt-BR; UI tests assert representative copy. |
| EXT-CA-LANG-01.2 | **Pass at changed adapter boundaries:** generation/adaptation/chat tests use fake providers and preserve the Portuguese output contract; no live AI-language audit claimed. |
| EXT-CA-LANG-01.3 | **Pass in affected scope:** shared date rendering uses pt-BR; collection filters test São Paulo calendar boundaries. No new currency presentation. |
| EXT-CA-LANG-01.4 | **Retained existing configuration:** repository-managed Portuguese Keycloak theme remains selected. Hosted first-access/login screens were not newly browser-audited in Task 37; no fresh live journey claim. |
| EXT-CA-LANG-01.5 | **Pass in affected scope:** the three-size component/browser audit found no unexplained English application controls. |
| CA-RNF01.1 | **Pass for changed internal query/write paths:** real PostgreSQL ten-run samples and three-request burst below. Browser rendering verified separately; these are not WAN latency measurements. |
| CA-RNF01.2 | **Pass for changed administrative actions:** visible button processing feedback below 200 ms, duplicate writes blocked; existing CEP/AI loading states retained and tested. |
| CA-RNF01.3 | **Pass:** fake identity/CEP/AI failures return controlled errors; durable retry and manual address entry remain usable. Adapter timeout policies unchanged. |
| CA-RNF02.1 | **Technical evidence passed:** exact navigation, role routing, labels, keyboard, and contextual-action tests. Intended-user assessment remains pending. |
| CA-RNF02.2 | **Pass:** required labels, validation, preserved invalid inputs, save/provision states, and explicit stale-draft confirmation covered by UI tests. |
| CA-RNF02.3 | **Pending:** intended user must execute the checklist below without source code or step-by-step help. |
| CA-RNF03.1, CA-RNF03.2, CA-RNF03.3 | **Pass for audited screens:** exact three-size checks, mobile navigation/controls, and no horizontal content overflow. |
| CA-RNF04.1, CA-RNF04.2 | **Pass:** domain validation stays in services; shared cards/media and existing forms/shells avoid parallel visual implementations. No new technology or dependency. |
| CA-RNF04.3 | **Pass:** full affected suites, actual PostgreSQL races, focused fixes, lint, type-check, and bundle build. |
| CA-RNF05.1 | **Pending soak:** no eight-hour availability claim. Restart recovery passed as detailed below. |
| CA-RNF05.2, CA-RNF05.3 | **Pass for simulated failure isolation:** shared-account and AI/onboarding suites retain durable state and independent internal operations on provider failure. |
| CA-RNF06.1, CA-RNF06.2, CA-RNF06.3 | **Pass:** fake compatible identity, CEP, mail, and AI adapters exercise the existing integration interfaces; provider errors remain controlled, without domain dependence on provider response internals. |

The automated browser checks reported no violations of their defined
label/landmark/target/overflow checks. They are a limited audit, not an axe scan,
screen-reader certification, or a claim of complete WCAG conformance.

### Performance samples

`test_instructor_performance_postgres.py` seeds 50 synthetic clients with
representative onboarding and conversation records, draft/current/history
states, public/private posts, and equipment. Each operation below completed
**10 of 10** executions within 2 seconds (DEC-16 requires at least 9).
In-process ASGI calls use real PostgreSQL; network and browser latency are not
included. Measurements are a bounded personal-use sample.

| Operation | Maximum elapsed (ms) |
| --- | ---: |
| Instructor feed | 62.14 |
| Client search | 20.71 |
| Current collections | 91.11 |
| Pending review | 83.57 |
| Responsible-instructor options | 9.27 |
| Onboarding read | 11.00 |
| Equipment read | 5.23 |
| Usable equipment selector | 5.13 |
| Draft save | 13.22 |
| Onboarding save | 13.62 |
| Equipment toggle | 9.22 |

The three simultaneous requests completed in 42.85 ms total. A separate test
repeats public-profile filtering and cursor pagination on PostgreSQL.

### Restart recovery

A controlled `docker compose restart` was followed by health/service checks.
Backend health and data comparison passed at 45 seconds. Keycloak realm
discovery and the frontend both returned HTTP 200 when checked at 88 seconds,
within the five-minute limit. Core Compose services were running; backend,
PostgreSQL, and Mailpit health checks passed. Development frontend TLS uses its
existing self-signed certificate; the local probe bypassed certificate
verification only for that read.

Before/after SHA-256 hashes of ordered complete rows matched for Account,
Client, PersonProfile, Employee, Onboarding, TrainingPlan, TrainingPlanVersion,
TrainingPlanItem, EquipmentModel, and EquipmentUnit. Only hashes were exposed
in output. No database repair or application-data edits were required. This
restart result does not establish eight-hour availability.

## Defects repaired and files changed

- **Instructor feed/media** (`backend/app/modules/social/{service,models}.py`,
  `employees/instructor_social_router.py`, `backend/tests/test_progress_updates.py`):
  apply public-profile filtering before page limits, normalize cursor timestamps,
  preserve ORM boolean-default behavior in SQLite, and authorize comment-image
  reads against the visible parent post and comment. No social mutation granted.
- **Shared feed presentation** (`frontend/src/post-card.tsx`, `post-media.tsx`,
  `progress-page.tsx`, `instructor-feed-page.tsx`, `instructor-post-detail-page.tsx`,
  `instructor-social.ts`, `social.ts`, and instructor feed tests): reuse cards/media,
  render read-only counts and images, end failed loading, and provide retry.
- **Administrative processing** (`frontend/src/{employee,client}-management.tsx`
  and tests): immediate Portuguese progress, disabled mutation buttons, and a
  synchronous duplicate-write guard while provisioning/saving is pending.
- **Shared accessibility presentation** (`frontend/src/components/application-shell.tsx`,
  `theme.ts`): opaque sticky mobile header and minimum icon-button touch targets.
- **Integrated verification** (`backend/tests/test_instructor_integration.py`,
  `test_instructor_performance_postgres.py`): direct authorization matrix,
  PostgreSQL performance samples, and public-feed regression.
- **Test isolation** (employee/shared-account/review/collections/onboarding/equipment
  test fixture imports, occupancy tests, and frontend onboarding-conversation/
  profile-presence/occupancy tests): remove accidental global fixture plugins and
  provide the proper linked actor/fake API boundary. `frontend/vitest.config.ts`
  bounds workers to two to avoid full-suite CPU contention; timeouts and assertions
  were not relaxed.
- **Required lint cleanup** (migrations 08, 09, 10, 15, 17, 18, 19;
  `backend/app/modules/progress/{router,service}.py`; `social/router.py`): formatting,
  import ordering, and unused-import removal only. AST comparison excluding imports confirmed
  equivalent executable structure for these ten files. No historical schema
  behavior changed.
- **Documentation** (`docs/requirements.md`, Task 28/29/30/37 status notes, this
  report): distinguish implemented functionality from remaining formal evidence.

## Remaining intended-user checklist

Record tester, date, role, outcome (pass/blocked), and confusing steps. Use only
synthetic accounts. The intended user should complete these outcomes without
consulting code or receiving step-by-step assistance:

- Administrator: register and provision an instructor; edit all initial fields;
  use CEP lookup and manual fallback; attach a matching client role; deactivate
  and reactivate each role independently and observe the resulting access.
- Client: enter the correct onboarding/current-plan flow; complete onboarding;
  view the approved plan with responsible instructor/date; switch areas when
  both roles are active and return without a new login.
- Instructor: read a public feed post and media; locate a pending plan, edit/save,
  then approve; find mine/all plans with combined filters; inspect history;
  cancel then confirm existing-draft replacement; locate a client and create a
  first manual draft; continue/correct onboarding; toggle equipment state and
  observe usable training choices without rewriting historical plans.

Also coordinate an uninterrupted eight-hour local host window. During that
window, record core health once per minute, classify any planned host/network
exclusions, and investigate any unexplained core outage. No such soak has been
started or reported as passing in this task.

Record checklist and soak results here when available. Resolve any observed
defects as follow-up work, run checks relevant to those changes, and commit each
completed follow-up. Task 37 is already closed by user direction; no passing
result is inferred for either outstanding check. No functionality decision is
otherwise unresolved.
