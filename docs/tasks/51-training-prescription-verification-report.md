# Tasks 46–51 verification status — 2026-10-23

**Current development follow-up:** the owner approved isolated Tasks 48–50
implementation before review/sealing while retaining every operational release
gate. See the [approved amendment](../training-prescription-development-amendment.md)
and [implemented development scope/tests](48-50-isolated-prescription-development-report.md).
The original snapshot below predates that decision; its statements that Tasks
48–50 were not implemented describe that earlier point. No independent clinical/
prescription release is implied by the newer software tests.

**2026-10-24 continuation:** the
[operational integration follow-up](45-51-operational-integration-follow-up.md)
now records real expanded-corpus indexing, nine scoped technical retrieval
probes, PostgreSQL migration execution/regression, reset compatibility and the
latest automated verification. The historical acceptance table below is retained
as its original snapshot, not a current claim that operational wiring is absent.
Professional approvals, independent sealing/evaluation and release remain open.

**Owner-authorized instructor workflow:** EXT-CA-AI-02.23–25 adds actual
judgment/custody registration at `/instrutor/evidencias`. See the
[delivery report](45-51-instructor-review-delivery.md) and
[operator workflow](../training-evidence-instructor-workflow.md). Its synthetic
software tests do not constitute human appraisal or independent evaluation.

## Earlier verification snapshot, before the development exception

**Not an independent prescription verification or release approval.** Task 46
technical ingestion is implemented; Task 47 has draft records/helpers and an
exploratory retrieval probe. Tasks 48–50 are not implemented because Task 47's
explicit preimplementation design/seal prerequisites remain unsatisfied. Task 51
mandatory actual-writer evaluation has not run. Existing runtime AI behavior has
not acquired the new mandatory abstention/qualification gate through this work.

## Evidence and versions

- Source protocol: Task 45 1.2; source review 1.1; appraisals/certainty unassessed.
- Corpus: 15 sources/19 passages, catalog SHA-256
  `c6f0448559ae7e53168e21c7f4415e1b9001a585e66b01628e1930c975b9fb54`.
- [Acquisition](46-training-evidence-acquisition.json),
  [actual indexing](46-training-evidence-indexing.json), and
  [development retrieval](46-training-evidence-development-retrieval.json) manifests.
- BGE-M3 digest: `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`;
  1024-dimensional PostgreSQL vectors. Fresh run: 19 texts/two calls; unchanged
  second run: zero embedding calls. No writing model was invoked/evaluated.
- Policy/dictionary artifact: `2026-10-23-draft-1`, pending only; zero actual
  approved rules, dictionary entries, cohort releases or validator versions.
- [Policy review package](../training-prescription-policy-review.md) and
  [recovery runbook](../training-evidence-recovery.md) supply review inputs and
  exact non-destructive recovery commands.

The user confirmed that no prior approvals, reviewers or seal exist and assigned
all initial responsibilities to the instructor profile. This functional owner
assignment is recorded; actual identity, competence/conflicts/availability and
independence remain unverified. It does not establish the canonical two-human
review/custody requirements. No named approval or exception was fabricated.

## Acceptance mapping (EXT-CA-AI-02)

| Criterion | Current evidence and remaining boundary |
| --- | --- |
| .1 | Task 45 initial goal/experience/restriction matrix; draft pending slice in 47. No professionally supported cohort. |
| .2 | S4 article rights, provenance, capture, technical review, locators and extraction hashes verified; other candidates remain metadata-only. Named technical continuity owner still pending. |
| .3 | Actual S4 download, 19 committed `vector(1024)` rows, zero unchanged re-embeddings; real PostgreSQL migration/search and rollback tests. |
| .4 | Draft schemas/EtD review queue; all real appraisal/policy approvals pending. |
| .5 | Existing six-passage retrieval retained; exploratory S4 retrieval succeeds. No coverage-aware production selection/validation implemented. |
| .6 | Draft unit/bounds/input-dependency record checks; candidate item/session/week/muscle validation remains Task 48. |
| .7 | Documents distinguish bibliographic support from prescription qualification; backend prescription result gate remains unimplemented. |
| .8 | Mandatory discard, four stable outcome categories and no prose bypass remain Task 49; corpus ingestion alone does not change generation. |
| .9 | Shared prescriptive entry-point integration/replay/retry enforcement not implemented. Existing RAG regressions pass. |
| .10 | Existing lifecycle tests pass; new atomic rejection behavior requires Tasks 48–49 and is not claimed. |
| .11 | No frontend change. Qualified/abstention/trace/input/manual-assumption UX remains Task 50. |
| .12 | No independent reviewed suite, cohort denominators or trace appraisal; no prescription effectiveness/reliability result. |
| .13 | Existing historical snapshots unchanged; revision-bound prescription trace and reuse/review invalidation remain Tasks 48–49. |
| .14 | Task 45 protocol/registers and draft EtD schema exist; independent tool/domain judgments and outcome certainty are still unassessed. |
| .15 | Mandatory actual-deployment writer/corpus/policy/validator repeated-run evaluation not executed; run budget/thresholds unsealed. |
| .16 | Draft dictionary/bounds/accounting references; dictionary empty and unapproved. Typed candidate/progression/projection and deterministic totals remain 48–50. |
| .17 | Input inventory/readiness proposal exists; authority/validity approval and minimized confirmed snapshot are absent. No new medical facts collected. |
| .18 | Real six-passage technical probe, zero reviewed development cases, dimension coverage not assessed; approved feasibility exit unmet. |
| .19 | Task 45 early design exists; independent cases/answers, thresholds, repeat counts, custody and seal absent. No held-out material created/read. Production gate implementation deferred. |
| .20 | Existing lifecycle preserved; explicit manual assumption, AI lineage and qualification transitions remain 48–50. |
| .21 | Recovery tooling/runbook plus isolated PostgreSQL outage/rollback/recovery/fallback/fresh-state tests; startup failure propagates. No degraded-startup promise or production live-writer outage evaluation. |
| .22 | Instructor functional owner recorded. Named competent independent reviewers/custodian, scoped approvals and final release decision absent. |

## Checks executed

Using isolated Compose project `academia-evidence`, repository Docker dependencies
and UUID-scoped PostgreSQL test schemas:

```powershell
docker compose -p academia-evidence run --rm --no-deps -e TEST_POSTGRES=1 backend sh -c 'python -m pytest tests/test_knowledge*.py tests/test_prescription_policy.py tests/test_training*.py -q'
```

Result: **488 passed in 52.39 seconds**, including real-PostgreSQL tests and fake
external providers. Subsequent targeted acquisition/recovery hardening checks are
**45 passed in 5.05 seconds** for acquisition, recovery, policy and startup tests
after cache-path/atomic-write and fallback-passage hardening. Ruff checks passed
and all nine new/modified targeted files passed the format check.
Ruff checked modified/new Python modules;
local JSON/hash/link/whitespace checks and Git diff review were performed. No
frontend tests/lint/build or browser viewports were run because no frontend code
changed. Fake-provider fixtures are development tests, never held-out approval.

Operational acquisition/indexing/search ran separately, with exact versions and
timings in the public manifests. The actual-deployment writer suite, professional
evaluation, independent judgments and release sign-offs are **unexecuted**.
There is no honest supported-acceptance/false-rejection denominator to report;
these outcomes are unmeasured, not zero. No configuration is certified by the
488 passing software tests.

## Remaining decision and implementation order

The instructor owner must supply qualified independent methodological/professional
assessments (or obtain an explicit human change to the canonical independence
requirement), complete the bounded real policy/dictionary/input decisions, review
development-case dimension feasibility, and arrange independent sealing before
Task 48. A single reviewer designation does not meet the current design gate.
Then implement 48, integrate 49, build 50, and execute 51's sealed actual-deployment
evaluation and scoped sign-offs. No retention, architecture, paid-service,
provider/model or clinical-threshold decision was made implicitly.

No commit/push or source archive/model weights entered Git. Existing unrelated
changes in requirements and Task 45 documents were preserved; only the relevant
Task 46–51 status section of the existing implementation-plan changes was updated.
The isolated project can be stopped without removing volumes; raw capture and
database evidence remain available locally. No live client was read, submitted
or activated by this work.

## Changed file inventory

| Area | Files |
| --- | --- |
| Cache/image exclusions | `.gitignore`, `backend/.dockerignore` |
| Knowledge implementation | `backend/app/modules/knowledge/acquisition.py`, `acquisition-s4.json`, `ingestion.py`, `recovery.py`, `bootstrap.py`, `catalog.json` |
| Draft policy/development helpers | `backend/app/modules/training/prescription_policy.py`, `prescription-policies.json`, `prescription_feasibility.py` |
| New tests | `backend/tests/test_knowledge_acquisition.py`, `test_knowledge_recovery.py`, `test_prescription_policy.py` |
| Updated catalog/startup regressions | `backend/tests/test_knowledge.py`, `test_knowledge_startup.py`, `test_knowledge_migrations_postgres.py` |
| Documentation | Task 46–51 status files; relevant `docs/implementation-plan.md` statuses; this report; Task 46 ingestion report and three public manifests; `docs/training-evidence-recovery.md`; `docs/training-prescription-policy-review.md` |

No canonical requirement, frontend, provider configuration, production training
service or existing client/history record was modified by this implementation.
