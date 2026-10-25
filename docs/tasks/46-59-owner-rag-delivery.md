# Tasks 46–59: owner-authorized RAG delivery

Implementation date: 2026-10-25. Canonical scope is `docs/requirements.md`,
including the owner's operational RAG amendment. The owner explicitly instructed:
“Não há nem haverá avaliador ou casos independentes. Implemente o que for necessário
para que funcione o RAG.” Independent evaluation/custody is therefore optional
for `owner_rag`, rather than an operational prerequisite. No professional opinion,
human review signature, sealed case or clinical certainty was fabricated.

## Delivered operating scope

The existing initial proposal, targeted/rebuild generation, chat edit, adaptation,
client submission and instructor approval workflows consume eligible consultation
passages and the applicable owner-accepted research rules. Drafts identify owner
authorization and the absence of professional/independent evaluation. Ordinary
instructor approval remains necessary before activation.

This assisted mode does not claim compiled prescription qualification. The separate
typed-policy validator remains available and tested; its real clinical policy
package is still pending. An empty compiled dictionary or absent independent seal
does not block assisted RAG. No qualified-prescription badge is granted on that basis.

| Task | Current implemented scope | Verification boundary |
| --- | --- | --- |
| 46 | Licensed acquisition, atomic indexing, idempotence, recovery and existing corpus integration | 66 PostgreSQL vectors; 19 indexed sources; original acquisition/indexing manifests retained |
| 47 | Exact owner authorization, 37-rule/11-family inventory, source/rule fingerprints and a bounded technical exercise dictionary | Source/rule acceptance is not a clinical appraisal; no compiled clinical policy is published |
| 48 | Shared source/permission/freshness/scope checks, typed validation, exact calculations and revision-bound evidence | Assisted consultation and compiled qualification are explicitly distinct |
| 49 | Owner RAG wired into generation, chat, adaptations, reuse, submission and approval; atomic rejection and manual editing | Current plans/history are preserved; source/input/content changes block dependent reuse |
| 50 | Existing client/instructor shells, truthful source notices, request inputs, typed modality display/editing and private-session cleanup | Automated UI checks and build pass; manual browser/keyboard/viewport review is unexecuted because no browser surface is available |
| 51 | Technical regression verification, actual local RAG/provider diagnostic, outage control, read-only readiness audit and release authorization record | No independent evaluation is claimed or required for this owner-authorized mode |

Tasks 52–58 implement approval/compiler readiness, exercise/modal contracts,
backend arithmetic, narrowed schemas, exclusive/open bounds, scoped context and
one bounded correction. Task 59 adds the exposed regression evidence and preserves
the earlier experiments. Full compiled-policy scientific qualification remains
an optional, separate unfinished scope; it is not a prerequisite silently reinstated
for assisted drafting.

## Runtime design and decisions

- `owner-rag-authorization.json` records the actual instruction, canonical source/
  rule registry hash, writer configuration and technical exercise-dictionary hash.
  Changed/revoked/unlisted approvals or an unapproved model configuration reject.
- `owner-rag-exercises.json` contains twelve technical free-exercise identities,
  Portuguese labels, explicit aliases and muscle groups. It contains no doses,
  clinical population approval or professional review record. The writer chooses
  stable IDs; the backend renders names and checks numeric repetition ranges.
- Only applicable primary rules/accounting are sent to the writer. Alternative
  protocols are not silently combined. Complete retrieved passages are retained;
  whole lower-ranked passages may be omitted to fit a 35,000-character base-context
  budget, within the unchanged maximum of six. Passage text is not truncated.
- With no explicitly requested schedule, the schema offers session A only. Source
  frequency does not invent days. Targeted requests use the applicable dictionary.
- Consultation records bind exact content, onboarding keys/hash, source/rule hashes,
  dictionary and writer configuration. Reuse, submission and approval recheck those
  dependencies and live source eligibility. Instructor edits clear AI grounding.
- Unknown absolute kg loads are rejected rather than derived from demographics.
  Backend Decimal calculations cover the five recorded arithmetic defects. Typed
  contracts preserve continuous activity, holds/sides, tasks and group rest relations.
- The same `qwen3:4b` model is retained. Structured reasoning is disabled only for
  the new assisted mode after an excessively slow exposed run. The existing adapter
  timeout and 16k context setting are retained. Compiled/legacy reasoning behavior
  is unchanged.
- Each logical attempt shares writer/review/focus budgets of 4/4/2 HTTP calls,
  maximum ten total, one content correction and the configured operation deadline.
  Ordinary logs contain counts/durations/reasons, not prompts or medical content.

## Actual model and corpus checks

The frozen `owner-rag-runtime-20261025T131003Z` experiment used actual PostgreSQL/
BGE-M3 retrieval and the configured local writer/automatic reviewer. Public-corpus
queries were read-only. Synthetic accounts, onboarding and proposals existed only
in disposable in-memory SQLite; no real client record was read or activated.

Model: `qwen3:4b`, digest
`359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.

| Case | Result | Actual model HTTP calls | Elapsed |
| --- | --- | --- | --- |
| Initial strength proposal | Reviewable proposal saved in isolated state, not activated | Writer 1; automatic review 1; focus 0 | 43.808 s |
| Retrieval outage | `technical_unavailability / retrieval_unavailable`; zero proposals | 0 | 0.050 s |

Six passages reached the successful writer/reviewer, with measured contexts of
21,219/22,066 characters. The successful proposal contained bodyweight squat,
push-up and dumbbell row, each 2 × 8–12 with 180-second rest. This is a software
diagnostic output, not a professionally verified individual training recommendation
or a full-body/clinical coverage claim. The frozen plan's expected outcome was a
reviewable initial proposal without activation, not a clinical efficacy result.

Implementation fingerprints remained unchanged during that run. Original plans,
results and raw structured answers are preserved separately from later software
checks. Earlier slow/failed attempts remain recorded, including unavailable
intermediate outputs from the intentionally stopped reasoning-enabled run.

The original two full-sheet attempts, 74-case experiment and ten isolated
diagnostics were not rescored. The new `prescription-fragments-2` rubric separates
`fragment_valid` from `required_action`, retains all 37 rules/74 cases and grades
representation, quantity and action separately. Explanations and clinical accuracy
remain explicitly ungraded by these fragment tests.

## Automated verification

The full backend suite before the final dictionary transport refinement returned
**1,175 passed**, including opt-in PostgreSQL tests. The new owner-RAG suite after
that refinement returns **14 passed**, including malformed repetitions, invented
movements/days, one correction, source revocation, missing citations, external-load
provenance, chat replay and complete adaptation persistence. Final full-suite
results are recorded in the completion follow-up below.

The affected six-file frontend run returned **58 passed**; the added credential-
switch/late-response privacy checks and remediation component run returned
**21 passed**. TypeScript and production build pass. Earlier broad frontend runs
had existing five-second test timeouts and an absent native OIDC issuer; their
failures are retained rather than described as a green suite. No timeout or
assertion was weakened. Browser inventory returned no apps or browsers, so no
manual visual/keyboard/viewport verification is claimed.

Migration `20261024_37` was applied to local PostgreSQL. It preserves dose metadata
and explicitly inapplicable quantities without rewriting prior rows. SQLite and
PostgreSQL regressions verify preservation and refusal of lossy downgrade. Local
backend health and final deployment configuration are checked in the completion
follow-up. No volume reset, real-client evaluation, commit or push was performed.

## Changed files

| Area | Files |
| --- | --- |
| Owner RAG | `backend/app/modules/training/owner_rag.py`, `owner_rag_schema.py`, `owner-rag-authorization.json`, `owner-rag-exercises.json` |
| Existing workflow integration | `generation_service.py`, `chat_service.py`, `adaptation_service.py`, `prescription_runtime.py`, `selection.py`, `completeness.py`, `presentation.py`, `router.py`, `schema.py`, `models.py`, `backend/app/integrations/ai.py`, `backend/app/main.py` |
| Compiled contract/remediation | `prescription_policy.py`, `prescription_accounting.py`, `prescription_contract.py`, `prescription_authorization.py`, `owner-prescription-authorizations.json`, `prescription_math.py`, `prescription_modes.py`, `prescription_mode_validation.py`, `prescription_validation.py`, `prescription_development.py`, `prescription_writer_schema.py`, `prescription_budget.py`, `prescription_selection.py`, `prescription_adaptation.py`, `prescription_inputs.py`, `prescription_router.py` |
| Evaluation/reporting helpers | `prescription_evaluation.py`, `backend/scripts/compile_prescription_bundle.py`, `prescription_fragment_rubric_v2.py`, `probe_prescription_remediation.py`, `probe_owner_rag_runtime.py`, `verify_prescription_readiness.py` |
| Persistence | `backend/alembic/versions/20261024_37_prescription_modalities.py` |
| Frontend | `current-training-page.tsx`, `training-dose.ts`, `training-prescription.ts`, `training-plan.ts`, `training-adaptation.ts`, `instructor-pending-plans-page.tsx`, `training-draft-fields.tsx`, `evidence-review.ts`, `instructor-evidence-review-page.tsx`; shared training table/content/review, modality-fields and request-input components |
| Tests | `backend/tests/test_owner_rag.py`, `test_prescription_remediation.py`, `test_prescription_remediation_persistence.py`, `test_prescription_fragment_v2.py`, `test_prescription_evaluation.py`, `conftest.py`; affected frontend tests including credential isolation and source readiness |
| Configuration/docs | `docker-compose.yml`, `.env.example`, canonical owner amendment in `docs/requirements.md`, relevant implementation-plan/task status pointers and this report |

Earlier uncommitted work elsewhere in the repository was preserved. This inventory
describes this implementation's scope; it does not attribute every pre-existing
dirty file to this delivery.


## Completion follow-up: 2026-10-25

The final full backend run returned **1,180 passed in 146.56 seconds**, including
PostgreSQL tests (`docker compose exec -T -e TEST_POSTGRES=1 backend python -m
pytest -q`). Ruff and formatting checks passed. The final frontend production
build (`npm.cmd run build`, TypeScript followed by Vite) passed; Vite retains its
large-chunk advisory. The affected six-file UI run returned **60 passed** after
the credential-isolation checks were added. No test assertion or timeout was
weakened. The optional evidence-review forms now use fixed three-row native
textareas within the existing MUI fields to avoid repeated autosize measurements.

The backend was recreated with `docker compose up -d --no-deps backend` and its
health endpoint returned `status: ok`. Runtime mode is `owner_rag`, the recorded
authorization is valid, independent evaluation is not required, and PostgreSQL
is at migration `20261024_37`. This activates assisted drafting, while instructor
approval still governs plan activation. No existing client plan was rewritten.

The [public-corpus readiness snapshot](46-51-readiness-20261025T132747Z.json)
records 66 vectors, 37 accepted research rules, zero compiled clinical policies,
zero custody seals and authorization for the assisted scope. The
[37-rule/11-family inventory](52-59-remediation-readiness-20261025.json) separately
reports unfinished compiled-policy inputs; these do not block owner RAG.
The actual successful model run is preserved in
[its result](52-59-owner-rag-runtime-20261025T131003Z-result.json) and
[its frozen plan](52-59-owner-rag-runtime-20261025T131003Z-plan.json).

Tasks 46?49 are implemented for the amended owner-assisted scope. Task 50's
implementation is delivered, but its complete acceptance remains pending manual
browser, keyboard and viewport checks. No browser surface was available in this
session. Full clinical policy qualification and independent efficacy evaluation
are not claimed. There was no commit or push; unrelated pre-existing changes
were preserved.

The final broad frontend run did **not** finish fully green: Vitest's persisted
file-level results record **44 of 47 files passing**, with failures in
`app.test.tsx`, `client-management.test.tsx` and
`approved-training-session.test.tsx`. Individual failure diagnostics were not
captured in this snapshot, so no cause is asserted here. See the
[preserved file results](50-frontend-final-broad-file-results-20261025.json).
These failures remain unresolved and are not counted as successful checks.

The final isolated source-workspace run returned **10 passed in 14.03 seconds**
(`npm.cmd test -- src/instructor-evidence-review-page.test.tsx --maxWorkers=1
--reporter=verbose`), including attributable judgments, truthful owner acceptance,
readiness distinctions, custody privacy, credential switching and controlled
expired-authorization feedback.

Follow-up diagnostics identified a test-shell OIDC redirect mismatch
(`/auth/callback` versus the suite's expected `/`) and five-second UI timeouts.
The initial three-file diagnostic returned 34 passing and four failing tests,
including two redirect assertions and two timeouts; one test was interrupted by
an approximately 861-second execution stall. No application redirect configuration
or test limit was changed to accommodate the diagnostic. The corrected test-shell
redirect is `VITE_OIDC_REDIRECT_URI=http://localhost:5173/`.

The corrected three-file follow-up returned **36 passed, 2 failed in 61.25
seconds**. All application/OIDC tests passed; the remaining failures were the
five-second limits in the CPF-validation and A/B/C approval tests (8.218 and
5.094 seconds). The latter passed in 3.790 seconds in the immediately preceding
diagnostic, so its checks are not represented as consistently green. These
performance/time-limit failures remain unresolved. This delivery does not claim
a completely passing broad frontend suite or full Task 50 acceptance.


## Subsequent owner-requested matrix: 2026-10-25

The owner requested a fresh approval check and actual generated-sheet outputs.
All 24 source/37 rule versions remain owner-approved. Two exposed five-case
rounds produced three accepted sheets from six ordinary generation attempts,
with four zero-call/no-save negative controls. Strength succeeded twice,
hypertrophy once, and muscular endurance failed both rounds. The approved-load
and duplicate-exercise guards rejected invalid candidates. These observations
limit the earlier single-case success: retrieval/context/citation binding work,
but consistent generation across goals is not established. No professional or
independent qualification is claimed. See the [complete matrix and generated
sheets](51-owner-rag-matrix-20261025.md); raw answers and both frozen plans are
preserved there. No model instructions or production gates were changed between
these rounds.


## Subsequent qualitative-load correction: 2026-10-25

The owner-requested hypertrophy load specification is now implemented. The new
closed qualitative load contract, shared pre-review validator and bounded repair
passed 1,206 backend tests and five of five frozen actual-provider hypertrophy
generations. The historical load failures above remain preserved. The prior
endurance-rule adherence issue is separate and remains unclaimed. See the
[implementation delivery and all five outputs](51-hypertrophy-load-remediation-delivery-20261025.md).
