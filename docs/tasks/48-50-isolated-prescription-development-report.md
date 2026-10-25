# Tasks 47–50 isolated development report

2026-10-23. **Development implementation only; no operational feature release.**
Scope follows the [owner-approved sequencing exception](../training-prescription-development-amendment.md)
to EXT-CA-AI-02.18/19. Real professional approvals, reviewed corpus feasibility,
independent sealed evaluation and release signatures remain pending.

## Implemented scope

| Area | Development implementation |
| --- | --- |
| Task 47 accounting | Explicit working/warm-up/unknown sets; separate direct/indirect muscle counts; no default fractional coefficient; session and actual seven-day occurrences; unknown/per-side quantities never become inferred zero or multipliers. Operational method stays pending with no mappings. |
| Task 48 contract | Discriminated repetitions/duration and intensity units/scales; measured-baseline provenance; progression/stopping/regression instruction keys; recognized exercise/variation keys and consolidated session items; confirmed input and policy/evidence hashes. |
| Task 48 checks | Owner, source authority, confirmation/conflicts/validity, exact goal/experience, seven dimensions, current license/source/locator/content/artifact hashes, six-passage bound, item/session/week/muscle parameters and confirmed schedule. Unused policy alternatives do not force irrelevant citations. |
| Task 49 orchestration | One isolated service for initial/targeted/rebuild/chat-edit/correction/prescriptive-prose operations and explicitly confirmed full-plan adaptation. Preflight precedes the writer; relevant evidence is filtered before its callback; context is resolved again before writes. Rejections contain no workout. |
| Task 49 persistence | Existing lifecycle/client locks; proposal and trace commit together. Replays/cache/submission/approval revalidate content and support. Trace binds exact persisted revision, policy/dictionary/accounting, displayed instructions and writer configuration. |
| Task 49 inputs | Owned completed-onboarding builder uses shared completion validation and requested fields only; missing age is not invented. Separate request confirmation binds the minimized effective snapshot and schedule without modifying onboarding. Conflicts require resolution. |
| Task 49 manual | Active instructor-only assumption on saved exact revision with reason and retained AI lineage. Manual edits clear qualification/citations; manual assumption/edit/approval do not call AI/retrieval. Unvalidated legacy bases reject the AI path. |
| Task 50 UI | pt-BR loading/empty/four rejection categories, backend-projected tables/instructions/sources, instructor-only traces, input confirmation, retained previous draft, manual responsibility and stale-action feedback. No discarded table/submission/override. |

Protected development records contain only relevant own-client snapshots and
references, not raw private chat. Client projections omit input snapshots and
privileged trace internals. Synthetic positive cases include medication/complaint
disclosures; a blanket rejection is not the test oracle. No clinical ranges or
reviewer identities were invented for operational artifacts.

## Isolation and remaining operational work

`IsolatedPrescriptionService` refuses ordinary PostgreSQL schemas and non-memory
SQLite. PostgreSQL tests use private `test_prescription_<uuid>` schemas; clients
must be allowlisted and have `prescription-dev-*` subjects. Normal FastAPI routes
do not import/register it. Its validation/confirmation tables are created only by
isolated fixtures; no production migration was introduced.

The reusable frontend component is not imported by normal routes. Its separate
Vite preview contains public fictitious fixtures and acknowledgement callbacks,
with no API client, real account, storage or activation. The preview entry/fixtures
are excluded from the normal production bundle. Existing operational training/AI
services and client/instructor pages remain unchanged.

Before operational enablement: complete real policy/dictionary/input/accounting
review and permission gaps; reviewed six-passage feasibility; authenticated API
and actual writer/retrieval-adapter wiring; production migrations; preservation
of existing automatic completeness/variation/review checks; full retained RF-19
adaptation workflow integration; independent actual-deployment evaluation and
scoped release approval. The harness covers already-confirmed adaptation writes,
not replacement of that retained queue. Legacy/manual free-text bases without a
complete typed record remain conservatively rejected rather than silently parsed.
These are not fully completed operational Tasks 47–50.

## Reproduce

From the repository root, using the existing Compose environment:

```powershell
docker compose -p academia-evidence up -d postgres
docker compose -p academia-evidence run --rm --no-deps -e TEST_POSTGRES=1 backend sh -c 'python -m pytest tests/test_knowledge*.py tests/test_prescription*.py tests/test_training*.py -q'
docker compose -p academia-evidence run --rm --no-deps -e VITE_OIDC_ISSUER=http://localhost:8080/realms/academia -e VITE_OIDC_CLIENT_ID=academia-web -e VITE_OIDC_REDIRECT_URI=http://localhost:5173/ frontend npm test -- --maxWorkers=1
docker compose -p academia-evidence run --rm --no-deps frontend sh -c 'npm run lint && npm run build'
```

PostgreSQL tests cover concurrent same-request creation, one saved draft/trace,
atomic rollback and ordinary-schema denial. Tests use fake external providers;
teardown removes only their own UUID schemas, not application data or volumes.

From `frontend/`, start the standalone preview:

```powershell
npm exec vite -- --host 127.0.0.1 --port 5177 --strictPort
```

Open `http://127.0.0.1:5177/prescription-development.html`. Its banner explicitly
identifies fictitious development data. It demonstrates client/instructor,
rejection/outage, saved-draft and confirmation states without a production effect.

## Validation and limits

The final expanded backend run passed **580 tests in 75.89 seconds**, including
real PostgreSQL persistence/concurrency and the existing training/knowledge
regressions. The earlier run passed 571 before the final additional cases.
The complete frontend passed **301 tests / 43 files** in the
canonical Node Docker environment; the final focused component run passed **13**.
Ruff checks passed; all nine targeted Python files passed formatting. TypeScript
and Vite production build passed in the repository's Docker environment.
No test limits were lowered.

Earlier Windows runs are not concealed: the first had one missing test-issuer
failure and seven timeouts; specifying the issuer and one worker fixed the issuer
case but left three timeouts in existing client/employee-management tests. Those
files and authentication behavior were not changed. The same full suite passed
in Node 24.21.0 Docker with the existing five-second test limits. Windows timing
variability is not claimed resolved. Vite retains its large-main-chunk warning;
no unrelated code splitting/refactor was performed.

Browser automation inventory returned no enabled apps/browsers. Phone/tablet/
desktop screenshots, visual overflow and real keyboard review are **unverified**;
accessible labels/roles, confirmation changes and role/action visibility have DOM
test evidence only.

Task 51's independently sealed actual-deployment evaluation was **not run**.
Professional/methodological judgments, untouched held-out custody, actual approved
prescription policies, run budgets and scoped signatures remain absent. Task 46
real BGE-M3 indexing is prior separate evidence, not prescription evaluation.
No real cohort was enabled; no model/provider or clinical approval was implied.

## Files

- Training module: `prescription_accounting.py`, `prescription-accounting.json`,
  `prescription_contract.py`, `prescription_validation.py`, `prescription_development.py`.
- Backend tests: `prescription_fixtures.py`, `test_prescription_accounting.py`,
  `test_prescription_validation.py`, `test_prescription_development.py`,
  `test_prescription_development_postgres.py`.
- Frontend: `training-prescription.ts`, reusable `training-prescription-review.tsx`
  and tests, development fixtures/preview and `prescription-development.html`.
- Docs: approved sequencing amendment, canonical .18/.19, Task 47–51 status/
  reference updates and this report. The prespecified Task 45 protocol bytes stay unchanged.

Existing unrelated changes were preserved. No new dependency, paid service,
architecture, retention rule, commit or push.
