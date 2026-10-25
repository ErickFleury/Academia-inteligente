# Tasks 45–51 operational integration follow-up

**Latest automated verification — 2026-10-24:** 1,087 backend tests and 312
frontend tests pass; production build passes. The earlier failed-run snapshots
below are historical. See the [instructor-workflow delivery](45-51-instructor-review-delivery.md)
and latest technical-closure sections.
Professional acceptance, independent evaluation and release remain incomplete.

Owner follow-up, 2026-10-23: enrich the licensed vector corpus; re-execute
previously incomplete specifications; connect operational backend validation,
onboarding, retrieval and writing providers; integrate authenticated client and
instructor screens; execute real-model end-to-end/interface verification and
obtain the specified human review/release decisions.

`requirements.md` remains canonical. The development sequencing exception remains
in force; it does not grant professional approval, waive the independent seal or
authorize enabling unreviewed cohorts for real students.

## Audit of prior prompts and incomplete specifications

| Prior request | Existing evidence | Actual unfinished work / acceptance boundary |
| --- | --- | --- |
| Task 45 discovery and methodology | Prespecified protocol, source review, owner role decision and research registry | Named qualified independent appraisers, actual judgments/certainty/adjudication and accountable release owners remain absent |
| Task 46 acquisition/indexing | Original S4 recovery proof; final 66-vector expansion, unchanged second run and nine topic retrieval probes verified on 2026-10-24 | Professional appraisal and reviewed clinical/dimension coverage remain absent; technical topic hits cannot establish them |
| Task 47 prescription contracts | Policy schemas, domain spec and 37 concrete research/decision records across eleven goal families | Independently review/adopt/adapt rules, dictionary, input authority and accounting; acquire actual reusable passages; execute reviewed feasibility and seal independent evaluation |
| Task 48 shared prescription gate | Operational context/provider adapters, shared typed validation/accounting/projection; migration 35 executed and tested up/down on PostgreSQL | Actual deployment-provider verification remains pending; no reviewed cohort is enabled |
| Task 49 orchestration | Operational generation/chat/adaptation, replay/revision validation, client acceptance, resubmission/approval and manual lineage connected | Independent reviewed input/policy contracts, remaining clarification authority and real-provider verification; no invented request facts or clinical defaults |
| Task 50 review UI | Real authenticated client/instructor calls replace preview callbacks in production views | Browser/keyboard/responsive verification and intended-user review remain pending; current session exposes no browser surface |
| Task 51 verification/release | Broad fake-provider CI and original technical BGE probe | Actual deployment writer end-to-end positive/rejection cases, budgets, sealed independent assessment, reviewed UI and named scoped release sign-offs |

Previous reports explicitly call these partial/incomplete; they are not treated
as finished because tests of a synthetic development harness passed. Fictional
fixture policies remain mechanics tests. The researched rule registry is not an
approved operational policy and will not be promoted by inventing hashes or people.

## Corpus expansion scope and operational notes

Nine additional CC-BY-4.0 article subsets have been acquired through the official
Europe PMC full-text XML API, with fixed article IDs, original snapshots, exact
selection hashes, attribution and technical review. The final proposed catalog
contains 24 bibliographic records and 66 passages (47 new). Scientific approval
is pending. No third-party image, supplementary dataset or underlying DEPP
protocol database was imported. Adapted asthma Table 3 is excluded.

An initial 40-passage layout passed 65 offline/PostgreSQL knowledge tests but real
Ollama embedding rejected inputs exceeding its physical token-batch default.
The transaction rolled back. An experimental physical-batch adjustment was
reverted; the final layout keeps the existing adapter/model configuration and
uses shorter, complete paragraph selections. One oversized stretching result
selection was omitted with its reason in the recipe. See the
[expansion report](46-training-evidence-expansion-report.md) and its published
acquisition, indexing and retrieval manifests. The 2026-10-24 follow-up verified
all 66 final-layout vectors, 47 new embeddings in three calls and zero unchanged
second-run calls. Nine known-topic technical queries retrieved their target
source within six passages; prescription dimension coverage remains unassessed.

Docker subsequently stopped responding to container operations while its version
endpoint remained responsive. The service later recovered without volume deletion,
permitting the isolated operational proof above. No prescription validation or
professional approval is inferred from infrastructure recovery.

## Operational implementation completed in this follow-up

- `prescription_runtime.py` obtains completed own-student onboarding, approved
  policy/execution/accounting/dictionary artifacts, confirmed minimized inputs,
  live retrieval and source review state. Unapproved packaged policies reject
  before a writer call; catalog metadata cannot override database revocation.
- Existing generation supports initial/targeted requests and complete rebuilds.
  Chat changes use the same typed gate; transport replay revalidates saved content
  without regenerating from changed retry text. Actionable chat is rendered from
  the saved projection, rather than unrestricted model prose. Non-prescriptive
  chat uses backend flow guidance during this disabled rollout.
- The mandatory automatic exercise review remains in place, including its bounded
  correction. It cannot replace the evidence gate. Sources/inputs are resolved
  again after the reviewer returns; late revocation discards the candidate.
- RF-19 retains its separate proposal and explicit acceptance. The whole resulting
  sheet and totals are validated at generation and acceptance; acceptance creates
  a qualified instructor draft without changing the immutable current plan.
- Resubmission and instructor approval revalidate exact revisions. Manual edits
  clear AI qualification, retain lineage and work without calling external AI.
  Explicit manual assumption requires an active local instructor and an audit reason.
- Migration `20261023_35` adds validation, input-confirmation and adaptation-validation
  persistence without backfilling historical qualification or inventing approvals.
- Client/instructor review endpoints enforce backend ownership and active roles;
  only the instructor gets rule/source decision traces, without private raw chat
  or complete input snapshots. The real React screens use bearer-authenticated
  calls with revision/snapshot hashes and controlled pt-BR failure messages.
- The existing HTTP AI adapter receives the typed schema. A dedicated strict
  transport schema uses fixed decision-dimension properties and discriminated
  alternatives compatible with the provider's structured-output contract; local
  domain validation remains mandatory. See
  [official schema constraints](https://developers.openai.com/api/docs/guides/structured-outputs).
- `TRAINING_PRESCRIPTION_GATE_ENABLED` remains `false` in Compose and the example
  environment. Ordinary deployed flows are not switched to an unapproved cohort.

## Verification and limits

Native Python 3.13 tests exercise the actual ORM/domain and ASGI endpoints with
explicitly synthetic policy/provider fixtures. Positive generation/adaptation,
immutable current content, rejection rollback, source revocation during model
review, retry revalidation, client isolation and instructor-only traces are covered.
The migration was initially executed up/down against isolated SQLite. The
2026-10-24 test adds real PostgreSQL up/down in a disposable schema, verifies
retained parent rows, empty new tables, foreign keys and indexes. An actual
`alembic upgrade head` also completed on the isolated evidence database.

The broad native backend run returned **983 passed, 57 skipped, 7 failed and
2 setup errors**. The seven failures were reproduced in identity/biometric suites
with missing native database/OIDC setup; setup errors used very long parameter IDs
under Windows temporary paths. These results are not reported as a green suite.
Focused final results are recorded in the subsequent verification update.

The frontend production build passed. The initial broad native test run returned
**291 passed and 13 failed**: twelve exceeded the existing five-second timeout,
and logout used an absent/invalid native issuer configuration. A serial rerun with
an explicit local test issuer is being checked; no timeouts or assertions were
weakened. The initial connected/shared review component run passed 16 tests.

No browser surface was returned by the browser inventory; the native computer-use
pipe was unavailable. Consequently no screenshot, keyboard, responsive or intended-
user verification is claimed. Docker's internal init API still timed out after
process restart and termination of only its own WSL distribution; volumes were
preserved and no other distribution was shut down.

The original infrastructure-bound gaps in expansion indexing and PostgreSQL
migration are now resolved by the operational manifests and migration regression.
Actual deployment writer runs, professionally approved rules/input authority/accounting/dictionary,
retrieval feasibility, sealed independent evaluation and named release signatures
remain pending. In particular the current confirmation API can reconfirm available
authorized facts; it does not fabricate missing request observations or approve a
new medical collection workflow. These are explicit acceptance gaps, not fixture
approvals or completed release claims.

## Verification follow-up — 2026-10-24

Scope remains EXT-RF-AI-02 and the RF-15/16/17/18/19 integration dependencies.
No additional cohort, source license, model, dependency or professional approval
was introduced. `TRAINING_PRESCRIPTION_GATE_ENABLED` remains false.

The first broad Docker backend run overlapped real ingestion and hit the existing
database-wide bootstrap advisory lock despite UUID-isolated test schemas. It
returned 1,039 passed and 12 failed; it is not a clean suite result. Tests were
subsequently rerun after ingestion finished. A native frontend run spanning a
long environment interruption was stopped and is not used as timing evidence.
No timeout or assertion was relaxed.

The sequential full backend run returned **1,051 passed and 2 failed**. One failure
exposed the pilot-reset allowlist's incompatibility with knowledge and prescription
tables. The other is `test_history_api_limits_and_admin_only`: after removing its
identity override it sends the helper's bearer token to the unavailable configured
Keycloak and receives controlled HTTP 503 rather than the asserted 401. This
unrelated authentication-test dependency was left unchanged; the full suite is
not reported as green.

The reset dependency is now corrected and verified with synthetic data only.
Its explicit allowlist includes the three prescription tables and separately
classifies the two shared knowledge tables. Dependency-ordered deletes replace
TRUNCATE so client-private evidence can be erased while public source metadata
and vector values remain exactly preserved. Tests verify equipment/bootstrap
preservation, new input-confirmation cleanup, idempotency and refusal of an
unknown table before deletion. The existing local/pilot/owner guards and default
read-only inventory remain in place; no application reset was executed.

Migration plus reset regressions: **5 passed**. The final affected backend suite
returned **609 passed in 95.58 seconds**, including opt-in PostgreSQL tests:

```text
docker compose -p academia-evidence run --rm --no-deps -e TEST_POSTGRES=1 backend sh -c 'python -m pytest tests/test_knowledge*.py tests/test_prescription*.py tests/test_training*.py tests/test_facial_pilot_reset.py -q --tb=short'
```

These tests use fake external providers and synthetic policies; the actual BGE-M3
indexing/retrieval runs are separately documented above. Ruff lint and formatting
checks passed for the affected modules/tests; the formatter also added a missing
blank line in `prescription_development.py`. The frontend production build passed
in Docker (existing warning: bundle exceeds 500 kB).

The complete Docker frontend run used the configured local test issuer and one
worker: **302 passed, 2 failed in 245.73 seconds** across 44 files. Both failures
were the unchanged 5-second timeout in the client/employee registration tests;
the connected prescription review and all training-view tests passed. No browser,
keyboard, responsive or intended-user review is implied by DOM tests.
An isolated rerun of those two registration files returned **17 passed, 1 failed
in 28.27 seconds**: employee registration passed, while complete client
registration still exceeded five seconds. It remains an unresolved frontend
verification issue; no timeout was increased and neither registration module was
modified in this continuation.

```text
docker compose -p academia-evidence run --rm --no-deps -e VITE_OIDC_ISSUER=http://localhost:8080/realms/academia frontend npm test -- --maxWorkers=1
docker compose -p academia-evidence run --rm --no-deps -e VITE_OIDC_ISSUER=http://localhost:8080/realms/academia frontend npm test -- --maxWorkers=1 src/client-management.test.tsx src/employee-management.test.tsx
docker compose -p academia-evidence run --rm --no-deps frontend npm run build
```

Changes in this continuation: `backend/scripts/reset_facial_pilot.py`,
`backend/tests/test_facial_pilot_reset.py`,
`backend/tests/test_prescription_migration.py`, the formatting-only development
module adjustment, this status report, the implementation plan, the verification
report's current-status pointer, and the expansion report with its indexing/
retrieval manifests and reproducible probe script.
Earlier uncommitted implementation work was retained. No commit/push occurred.

## Latest technical closure — 2026-10-24

The previously remaining authentication/test-timeout failures are resolved:

- `test_biometric_history.py` now explicitly supplies an invalid-session fake
  identity provider. Its HTTP 401 assertion no longer contacts configured live
  Keycloak; production identity behavior and assertions remain unchanged.
- Client/instructor registration tests locate associated labels within their
  active dialog, avoiding repeated document-wide accessible-role searches for
  every field. Both complete workflows still fill all required values, verify
  facial readiness, submit and assert the outgoing payload. No test timeout,
  requirement or assertion was removed or increased. The focused run passes
  all 18 tests; client registration took 2.765 seconds and instructor registration
  1.353 seconds in that run.
- Task 50 review isolation now clears prior private state synchronously when
  credentials, role, version or revision changes. A numeric request generation
  resets child input/action state without placing bearer tokens in React keys.
  A new regression observes the committed DOM from a parent layout effect:
  it reproduced the previous session's draft and private manual note before
  passive-effect cleanup, then passes after the fix. The new session's manual
  reason is empty even when its response uses the same draft identifier.

Final full runs (Docker, one frontend worker, unchanged five-second test timeout,
explicit local test issuer, PostgreSQL opt-in, fake external providers):

| Check | Result |
| --- | --- |
| Full backend `python -m pytest -q --tb=short` | **1,053 passed in 117.72 seconds** |
| Full frontend `npm test -- --maxWorkers=1` | **305 passed / 44 files in 214.90 seconds** |
| Shared/connected prescription review tests | **17 passed**, including the new privacy regression |
| Identity/history regression group | **21 passed** |
| `npm run build` (TypeScript + Vite) | Passed; existing bundle-size warning remains |
| Ruff checks/format for changed Python test | Passed |
| Git whitespace/diff review | Passed |

The code in this continuation changes five files:
`backend/tests/test_biometric_history.py`,
`frontend/src/client-management.test.tsx`,
`frontend/src/employee-management.test.tsx`,
`frontend/src/components/connected-prescription-review.tsx`, and its regression
test. Task 48/49/50 status paragraphs now point to implemented operational wiring
while retaining all incomplete acceptance gates. No dependency, model, release
policy or canonical requirement changed; no commit/push was made.

Browser verification was attempted again: the computer-use inventory returned
no apps/browsers and explicit in-app browser creation returned
`Browser is not available: iab`. Consequently no browser screenshot, real keyboard,
viewport or intended-user acceptance is claimed. DOM tests do not fill this gap.

The actual Compose deployment setting remains
`TRAINING_PRESCRIPTION_GATE_ENABLED=false`. Its writer is local Ollama
`qwen3:4b`; no paid-provider call is needed for a separately labeled, exposed
synthetic development probe. Such a probe is not Task 51's independent sealed
actual-corpus evaluation and cannot approve a real cohort.

### Actual local writer development probe

The existing Ollama service was started with its retained model volume. A
[single-call plan](51-prescription-local-writer-development-plan.json) was written
before inference: one call, zero retries, existing 360-second timeout, no database
configuration and no candidate publication. The
[reproducible script](51-prescription-local-writer-probe.py) uses the existing
public, explicitly synthetic fixture and the real deployed adapter/parser and
typed core validator. It neither imports synthetic approvals into runtime
artifacts nor exercises production persistence, retrieval or automatic review.

The [actual result](51-prescription-local-writer-development-result.json) records:

- Ollama `0.34.1`, configured `qwen3:4b`, digest
  `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
- Exactly one real request, `num_ctx=16384`, `think=false`, `stream=false`,
  preserving the adapter's existing behavior and model configuration.
- **44.243 seconds**; parsing into the typed contract succeeded, but core
  validation rejected with `missing_input / schedule_not_confirmed`.
- **The prespecified positive technical expectation was not met.** The rejected
  candidate required an unconfirmed schedule; the validator did not invent
  confirmation or publish a usable fallback. Zero candidates were saved or
  published, and neither raw candidate prose nor its dosing was retained in the
  public report. No correction/retry was added after observing this result.

This is an exposed development failure with controlled rejection, not an
independent evaluation, a demonstrated supported positive, a clinical judgment
or an estimate of false-rejection rates. Full real-policy/corpus/lifecycle
positive and negative runs, professional judgments, independent sealing and
scoped sign-offs remain absent. The deployment gate remains false.

Additional files for this probe are the reproducible script and the two linked
JSON manifests. They are separate from offline CI; lint/format checks passed.

## Owner-authorized instructor workspace and final verification

The owner's subsequent decisions authorize all active Instructors and explicitly
include an in-app review/custody workflow. It is now implemented and running at
`http://localhost:5173/instrutor/evidencias`, under **Revisão de evidências**.
The [delivery report](45-51-instructor-review-delivery.md) lists changed files,
identity/hash/deadline/concurrency protections, private evaluation custody,
public protocol review, actual model failures and remaining acceptance gates.
The [workflow guide](../training-evidence-instructor-workflow.md) explains the
actual instructor actions. Registration does not publish policies or run models.

Final complete suites after these changes:

| Check | Result |
| --- | --- |
| Backend, isolated PostgreSQL opt-in, fake external providers | **1,087 passed in 206.05 s** |
| Frontend, one worker, existing five-second timeout | **312 passed / 45 files in 220.24 s** |
| `npm run lint`, `npm run build` | Passed; existing bundle-size advisory |
| Backend Ruff lint and changed-file format checks | Passed |
| Migration 36 | Applied to isolated and main PostgreSQL through normal startup |
| Main backend health / frontend route | `ok` / HTTP 200 |
| Main public vector corpus | 66 BGE-M3 vectors, all 1,024 dimensions |
| Git whitespace/diff review | Passed; existing CRLF advisories only |

The first frontend attempt overlapped corpus indexing, timed out and was stopped;
the final complete run above followed initialization and passed. The initial
static-check attempt invoked an absent ESLint command; the actual configured
`npm run lint` (TypeScript) subsequently passed. No package or lockfile changed.
The ordinary startup indexed the newly selected passages without bypassing
`backend-init`; [read-only runtime metadata](45-51-runtime-review-delivery.json)
confirms the catalog hash and schema version without reading sealed payloads.

The two later actual local writer probes remain failures: session output rejected
for an unapproved prescriptive note; confirmed-week output failed structured
parsing. Both had one call, zero retries and zero saved/published candidates;
their frozen plans/results are linked in the delivery report. No independent
sealed evaluation or supported real-policy positive is claimed. Actual human
reviews, complete approved contracts, independent evaluation, browser/intended-user
acceptance and release sign-offs remain outstanding. The deployment gate is
still false. No commit/push occurred.
