# Tasks 45–51: instructor review/custody delivery — 2026-10-24

## Delivered owner scope

The owner authorized every active Instructor to perform the review/custody
functions and explicitly requested an in-app workflow. Canonical
EXT-CA-AI-02.23–25 now records that scope. The existing instructor shell exposes
**Revisão de evidências**, `/instrutor/evidencias`. See the
[workflow guide](../training-evidence-instructor-workflow.md).

The workspace presents 24 source records, 37 nonexecutable proposed rules, the
current prescription bundle, and public protocols of registered evaluations.
Instructors can submit attributable methodological/professional/adjudication
judgments, declare independence, certainty, competence/conflicts and deadlines,
and explicitly supersede their own judgment while preserving its original
assessment. Distinct people must perform the two independent functions.
The backend enforces authenticated active local Instructor linkage, current
artifact hashes, complete executable bundles before approval, scoped request
idempotency and concurrent single-successor/current-person constraints.

Custody registers a frozen synthetic protocol, artifact references, explicit
threshold/repetition/resource budget, private cases/reference judgments and
the custodian's actual attestations. Public protocol review never selects the
private case column. Only the authenticated custodian may retrieve cases, and
the payload hash is checked before response. Session changes clear private UI
state before paint. No model call, corpus upload, automatic policy publication,
cohort enablement or release is triggered by these actions.

Runtime policy/dictionary/accounting approval references must resolve to current
app judgments for the substantive bundle hash. Forged, expired or superseded
approvals cannot be restored by editing packaged JSON; contract deadlines cannot
extend human approval deadlines. The digest excludes only approval bookkeeping
to avoid circular signatures. Pilot reset refuses when review/custody records
exist instead of erasing professional history or private evaluation material.

## Files changed in this continuation

- Backend: `evidence_review.py`, `evidence_review_models.py`,
  `evidence_review_schema.py`, `evidence_review_router.py`, migration
  `20261024_36_evidence_review_custody.py`, router/model registration in
  `app/main.py`/`alembic/env.py`, runtime review verification and pilot-reset guard.
- Frontend: `evidence-review.ts`, `instructor-evidence-review-page.tsx`, route
  registration and instructor navigation; focused page/shell regressions.
- Writer schedule fix: `prescription_development.py`,
  `prescription_writer_schema.py`, `prescription_runtime.py`, `integrations/ai.py`
  and schedule/schema tests. Context is derived from authoritative confirmed
  schedule facts; no confirmation means session scope with a null schedule.
  Complete-plan paths reject missing confirmation before invoking the writer.
- Documentation: canonical owner extension, frontend design, Tasks 47/50,
  implementation/status pointers, workflow guide and retained probe manifests.
  Earlier uncommitted work was preserved; no commit or push occurred.

## Execution and verification

- Full backend with isolated PostgreSQL opt-in and fake external providers:
  **1,087 passed in 206.05 seconds**. Includes three concurrency tests, immutable
  supersession, cross-custodian denial, runtime current-review references,
  deadlines, storage-outage privacy, source registry, reset and reversible
  migration with retained sentinel data.
- Full frontend: **312 passed / 45 files in 220.24 seconds**. Includes seven
  focused workspace regressions. Initial execution overlapped corpus initialization
  and encountered timeouts; it was stopped and repeated after indexing finished.
  Form tests batch independent field edits while preserving actual input events,
  request assertions and the unchanged five-second test timeout.
- Frontend `npm run lint` and production `npm run build`: passed. Existing
  Vite large-bundle advisory remains. Full backend Ruff checks and changed-file
  formatting checks passed. No project dependency was added.
- Migration 36 applied to both isolated PostgreSQL and the ordinary local app
  through its normal fail-closed startup. Backend health returned `ok`, and
  the frontend served the new route with HTTP 200. These HTTP checks do not
  establish authenticated browser UX acceptance.
- [Read-only runtime manifest](45-51-runtime-review-delivery.json): main database
  has **66 public BGE-M3 vectors, all 1,024 dimensions**, migration 36 and the
  expected catalog hash. No private evaluation payload was read.
- Computer-use inventory has no available browser/app; explicit in-app browser
  creation failed. Manual keyboard, viewport and intended-user checks remain
  unperformed. Automated DOM checks do not replace them.

## Retained actual model failures

The earlier actual single-call writer rejection remains in the
[original result](51-prescription-local-writer-development-result.json).
After the confirmed-schedule context fix, two separately prespecified exposed
synthetic development probes made one actual local Qwen3 4B call each, zero
retries and zero saved/published candidates:

| Scenario | Actual result | Duration |
| --- | --- | --- |
| [Session plan](51-prescription-writer-schedule-session-plan.json) / [result](51-prescription-writer-schedule-session-result.json) | Typed candidate rejected: `unapproved_prescriptive_note` | 20.897 s |
| [Confirmed week plan](51-prescription-writer-schedule-confirmed-week-plan.json) / [result](51-prescription-writer-schedule-confirmed-week-result.json) | Controlled provider failure: `malformed_structured_output` | 17.374 s |

Both positive expectations failed; subsequent mutation controls were not
executed because no positive candidate was accepted. The public reports retain
failure metadata without publishing rejected prescription prose/doses. They use
exposed synthetic fixtures, not real approved policies or independent held-out
cases. No independent quality/rate/clinical conclusion follows from them.

## Remaining acceptance gates

Task 46's selected-passage ingestion is verified in the main and isolated
databases. It embeds original selected passages, not summaries and not entire
downloaded articles. Technical generation/review wiring for Tasks 48–50 is
implemented, and the newly authorized review/custody workflow is available.

Tasks 45/47/51 still need actual human appraisals/decisions, completed and approved
computable policy/exercise/accounting/execution artifacts, professionally reviewed
feasibility, independently prepared sealed cases/protocol approval, budgeted
actual-policy/corpus/writer/lifecycle evaluation, and scoped professional/release
sign-offs. Task 50 also needs real browser/intended-user checks. The actual local
writer has not demonstrated a supported positive in these development probes.
Assigning the Instructor role and building forms do not perform those actions.
No real instructor judgment or independent seal was fabricated or submitted.

`TRAINING_PRESCRIPTION_GATE_ENABLED=false` remains in the local deployment;
zero real approved cohorts are claimed. Tasks 45–51 cannot yet be reported as
fully accepted under their canonical criteria.
