# Owner-approved evidence and generation checks — 2026-10-24

Scope: the owner's explicit request to accept all consultation sources and proposed
rules and test training-sheet generation (RF-15 / EXT-RF-AI-02). After being informed
that independent professional opinions were absent, the owner selected
“Alterar o requisito para decisão do proprietário”. The canonical owner approval
amendment records this governance change; no professional opinion is invented.

## Approval recorded

The versioned [owner registry](../../backend/app/modules/training/owner-evidence-approval.json)
accepts **24 source artifacts and 37 proposed-rule artifacts** by exact hash.
The authenticated instructor artifact API and `/instrutor/evidencias` expose this
owner basis separately from human judgments, scientific certainty and independent
review completion. No instructor identity, competence, attestation or signature
was fabricated, and no judgment/custody rows were inserted into the live database.
Changed, unlisted, revoked, corrupt or missing approvals cannot authorize a version.

Research sources referenced inside rule artifacts are also bound through those
artifacts' reference metadata. Approval is acceptance for consultation/research,
not a new copyright permission. The existing corpus remains **19 sources with
66 passages**, with three excluded and two pending sources retaining their
technical statuses. No licenses, passages, source review deadlines, numeric
findings or proposed numeric ranges were changed. The six-passage retrieval
limit and configured local model were preserved.

## Automated verification

All checks use fake external adapters in CI, including real PostgreSQL tests in
temporary schemas. Live model calls are a separate, explicitly bounded probe.

```powershell
docker compose run --rm -T --no-deps -e TEST_POSTGRES=1 backend python -m pytest tests/test_owner_approval.py tests/test_prescription_policy.py tests/test_prescription_accounting.py tests/test_prescription_validation.py tests/test_prescription_runtime.py tests/test_prescription_operational_flows.py tests/test_prescription_development.py tests/test_prescription_development_postgres.py tests/test_prescription_writer_schema.py tests/test_evidence_review.py tests/test_evidence_review_postgres.py -q
docker compose exec -T frontend npm test -- src/instructor-evidence-review-page.test.tsx
docker compose exec -T frontend npm run build
```

- Backend: **160 passed**, including nine owner-approval tests and actual
  PostgreSQL concurrency/rollback checks, in 32.95 seconds on the final run.
- Instructor evidence page: **9 passed**, including explicit owner basis without
  claiming professional review or creating a judgment.
- TypeScript/production build passed. Vite retains the bundle-size advisory.
- Ruff lint and format checks passed for the five touched/new Python files.
- `git diff --check` passed. The restarted backend answered `/health` with `ok`
  and recognized all 61 current owner approvals.

Tests verify exact-version binding, revocation, missing/corrupt/invalid-UTF-8
registries, future decisions, prohibition of fabricated professional-review
claims, API serialization, unknown goal rejection and approval coverage. Existing
typed-validation, isolation, immutability and failure-preservation tests still pass.

## Local generation experiment

The [probe](../../backend/scripts/probe_owner_approved_generation.py) freezes its
plan before model execution. Two fully synthetic, implementer-visible cases ask
for one full-body session using free exercises, for hypertrophy and strength.
Each receives the applicable owner-approved research profile/rules and up to six
eligible passages retrieved through the real BGE-M3/PostgreSQL knowledge service.
The database transaction is read-only, uses a random synthetic scope and queries
no student/account tables. No actual student context is sent to the model.

Provider: local Ollama, `qwen3:4b`, digest
`359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`.
Budget: at most four model calls total, one generation and one automatic
assessment per case, 360-second timeout per call and no retries. The deployed
adapter's reasoning/context settings are unchanged. Model output must pass schema,
recognized exercise names, duplication, citation, session and automatic-review
checks. Only outputs that pass these checks appear as development samples.

Execution:

```powershell
docker compose run --rm -T --no-deps -e PYTHONPATH=/app backend python scripts/probe_owner_approved_generation.py
```

The [frozen plan](51-owner-approved-generation-plan.json) and
[full results/development sample](51-owner-approved-generation-result.json)
preserve both attempts, including the rejection:

| Synthetic case | Observed result | Generation + assessment elapsed |
| --- | --- | --- |
| Hypertrophy, beginner, one full-body free-exercise session | Generation and automatic checks passed; five exercises, three valid citations from retrieved Iversen passages | 361.169 seconds |
| Strength, intermediate, one full-body free-exercise session | Automatic assessment rejected session A with `ambiguous_exercise`; rejected content was not exported as a sample | 280.760 seconds |

Actual budget consumption: **four model calls**, two per case, with no retries.
One of two development cases passed the listed automatic checks; one was rejected.
This is not a population acceptance/rejection rate or an assessment of scientific
correctness. No failed case was regenerated until it passed. These long observed
latencies are a practical limitation of this local configuration; no performance
compliance claim is made.

The development sample is explicitly unqualified. For example, an accepted
legacy-shaped sheet has no complete per-item dose/progression-to-policy trace;
valid citations and a positive automatic assessment do not supply that trace.

## Remaining technical boundaries

This experiment tests generation using the approved research inputs. It does
**not** establish complete numeric-rule compliance, clinical effectiveness,
independent evaluation or qualified operational release. The context explicitly
identifies the absence of a professional opinion and keeps scientific certainty
unassessed. An automatic model assessment is not an independent human opinion.

The actual executable bundle remains incomplete: exact goal mappings and coherent
applicability branches, decisions across all seven dimensions, the exercise
dictionary, execution/input-authority contracts, accounting and consistent
version links still need implementation. Owner acceptance cannot fill those
fields by changing a status flag. The existing typed runtime must continue to
reject this incomplete bundle; its rollout setting was not changed. In particular,
this work does not claim that the ordinary client flow now uses completed typed
policies or that research-rule prose is deterministically enforced as dose bounds.
The normal application generation path was not redirected through this probe.

No existing student proposal/current plan was edited, submitted or activated.
No independent sealed cases were opened, no evaluation seal or release sign-off
was created, and there was no commit or push. The source/rule governance decision
is complete; technical qualification and evaluation remain separate open work.

## Files changed in this request

- `docs/requirements.md`: owner alternative and aligned decision-gate wording.
- `docs/training-evidence-instructor-workflow.md`: owner-basis operator guidance.
- `backend/app/modules/training/owner_approval.py`: registry validation and
  approved goal-family research context.
- `backend/app/modules/training/owner-evidence-approval.json`: exact accepted versions.
- `backend/app/modules/training/evidence_review.py` and `evidence_review_schema.py`:
  public owner-basis metadata, kept separate from human judgments.
- `frontend/src/evidence-review.ts`, `instructor-evidence-review-page.tsx` and its
  test: owner-basis contract, existing MUI alert and regression coverage.
- `backend/tests/test_owner_approval.py`: approval, scope and transport checks.
- `backend/scripts/probe_owner_approved_generation.py`: reproducible bounded local probe.
- This report and its frozen-plan/result JSON artifacts.

The workspace already contained numerous modified/untracked Tasks 45–51 files.
Those pre-existing changes were preserved; this inventory describes only edits
made for the present request.
