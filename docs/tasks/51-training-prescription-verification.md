# Task 51 — Independent Prescription Verification and Release Boundaries

**Owner operational amendment — 2026-10-25 delivery:** the owner explicitly rejects
an evaluator/independent-case prerequisite for assisted RAG. Technical regression,
actual local RAG/provider verification and an exact owner authorization now govern
that mode. The actual positive/outage runs and preserved failures are recorded in
[current delivery](46-59-owner-rag-delivery.md). Independent/clinical qualification
below is separate optional scope; no completed independent evaluation is claimed.

**Status:** prerequisite/status report delivered on 2026-10-23; independent
operational prescription evaluation and release not executed. Task incomplete.
**Feature task:** EVID-IMPL-07.

Current [isolated development evidence](48-50-isolated-prescription-development-report.md)
follows the owner-approved exception: development may precede sealing, while
independent evaluation and operational enablement still require the actual seal,
reviewed feasibility, approved real policies and named scoped release sign-offs.

Evidence: [verification status report](51-training-prescription-verification-report.md).
Actual corpus indexing and development tests are reported separately; they do
not substitute for professionally approved policies, a preimplementation seal,
independent reference judgments or actual-deployment writer evaluation.

## Objective

Verify accepted and rejected prescriptions against independent reviewed criteria,
report coverage honestly, and enable only cohorts whose release gates are met.

## Requirements covered

- EXT-RF-AI-02: EXT-CA-AI-02.12/15 execution and .22 release; integrated .1–22.
- RF-15–RF-19 and EXT-RF-INST-02/03 only for the changed generation/review journey.
- EXT-RF-LANG-01 and RNF01–RNF06 for affected surfaces and integration.

## Related rules and constraints

RN-04/05, RN-11–RN-20, RN-23, RN-29–RN-33; DEC-07/08/15/18,
EXT-DEC-AI-02. A writer, second model or passing software test cannot provide
independent professional approval or establish individual clinical effectiveness.
No real client intervention, paid benchmark service or live-provider CI tests.

## Prerequisites and required reading

Execution starts after Tasks 45–50 are implemented within approved scope, but
evaluation design starts in Task 45 and must be sealed through Task 47 before
independent evaluation and operational enablement under the approved exception.
Read `AGENTS.md`, the
overview, EXT-RF-AI-02 and listed canonical RF/CA/extensions/rules/RNF/decisions,
including RNF measurement protocol and privacy section 9.2. Inspect source and
coverage reports, manifests, actual indexing evidence, professional policy
approval, gate contracts, all prescriptive entry points and related tests.
Read [the methodological protocol](../training-evidence-methodology.md), sections
5–7, the Task 45 criterion register and Task 47 evidence-to-decision records.
Read [the execution contracts](../training-prescription-execution-contracts.md),
including the typed/input contracts, sealed-case custody, transition matrix,
four recovery paths and named release authority. No new rubric designed from
current outputs may replace the sealed protocol.

## Permitted scope and expected behavior

1. Verify the preimplementation Task 47 seal and execute that versioned synthetic
   suite under the independent evaluator's custody. Check hashes, reference
   professional/methodological judgments, case partitions, thresholds, severity,
   sampling/uncertainty plan, repeated-run count and resource budget. Exposed or
   tuned held-out cases require independent replacements and an amendment before
   another release claim. Do not disclose answers to developers during tuning.
2. Cover supported goal/experience cohorts and meaningful restriction combinations,
   plus unknown goals/profiles, missing facts, insufficient dose evidence,
   contradictory studies, weak/out-of-population evidence, invented citations,
   expired reviews, unavailable embeddings/writer, stale revisions and replay.
3. Include positive controls: a reviewed supported request should generate an
   applicable structured proposal and reach instructor review without activation.
   Include cases where generic/related citations exist but do not justify the
   chosen sets/repetitions/intensity/progression; these must reject.
4. Evaluate all prescriptive paths, atomicity, privacy, manual fallback, fresh/
   existing-volume bootstrap and revocation. Review reasoning traces against
   actual source passages; do not count citation presence as grounded correctness.
5. Report denominators and results by cohort/dimension: coverage, supported
   acceptance, unsupported/unsafe acceptance, justified rejection, false rejection,
   and provenance/parameter correctness. Separate retrieval failures from writer,
   policy and validation failures. Explain uncertainty and untested populations.
   Check correct assignment of restriction conflict, missing input, insufficient
   support and technical failure. Report conditional-policy cases separately.
   Give uncertainty estimates appropriate to the sampling design; a purposive
   synthetic fixture suite is not a population failure-rate sample. Prespecify
   repeated runs when assessing writer variability, without live-provider CI.
6. Critical contraindication, unsupported acceptance and state/privacy failures
   must be zero in the versioned critical suite. Additional quality/sample-size
   thresholds and clinical rubric require EXT-DEC-AI-02 professional decisions;
   do not invent them or tune them after seeing results. Passing an always-reject
   gate is prohibited: required supported positive cases must pass too.
   Zero observed failures is a release gate for the evaluated suite, not proof
   of zero real-world risk; insufficient sample coverage cannot be hidden.
7. Perform the mandatory sealed operational suite using the actual deployment
   writer/provider, embedding model, corpus, policies and validator, with synthetic
   clients and isolated persistence or verified rollback. Run the prespecified
   repeated attempts across supported positives/critical negatives and all
   prescriptive paths; record per-attempt failures, timing, configuration/prompt/
   schema/model identities, versions/hashes and provider version limitations.
   Automated CI remains offline with fake external adapters. No real-client
   submissions/activations, new subscription or unapproved paid evaluation is
   authorized. Missing operational access/budget/results leaves the configuration
   unevaluated and disabled; fake tests cannot complete this acceptance gate.
8. Create `docs/tasks/51-training-prescription-verification-report.md` mapping
   EXT-CA-AI-02.1–22 to evidence. Record artifact/policy/validator/model versions,
   reviewed cohort allowlist, disabled cohorts, blockers and re-evaluation triggers.
   Do not mark blocked criteria complete or change historical RF completion claims.
9. Verify all transition-matrix rows, complete-result legacy adaptation checks,
   confirmed input changes, dictionary/accounting/projection equivalence and
   runtime manual authoring. Separately execute Task 46's four startup/recovery
   paths, including fresh-database unavailability and no restoration of revoked
   content. Do not claim manual availability before successful initialization.
10. Obtain the named methodological/professional sign-offs and project owner's
    explicit scoped release decision. Record enabled cohort/configuration allowlist,
    disabled scope, change-impact/retraction ownership and reevaluation triggers.
    An unsigned or unevaluated profile remains disabled; do not infer approval
    from the presence of a test report.

Permitted scope: focused evaluation fixtures/tests/scripts and verification/report
documentation; narrowly necessary fixes must remain within Tasks 45–50 scope.
No clinical trial, automatic release of plans, broad refactor or product expansion.

## Acceptance criteria

- EXT-CA-AI-02.12: frozen professionally reviewed cases include positive and
  critical negative controls, per-cohort results and independent trace review.
- All integrated .1–22 criteria have concrete evidence or an explicit open item;
  fake-provider checks and operational indexing are reported separately.
- Critical failures prevent affected release; absent professional policy/rubric
  decisions leave cohorts disabled and verification incomplete.
- The report claims only verified scope and behavior; no universal reliability,
  clinical efficacy or guarantees for an individual student.
- EXT-CA-AI-02.14: source appraisals, outcome certainty and rule derivations are
  traceable to actual records. Technical constraints/product policies are not
  represented as scientific thresholds; incomplete reviews remain open.
- EXT-CA-AI-02.15/19/22: independent cases were sealed before gate implementation,
  actual-deployment repeated-run evaluation passed prespecified thresholds, and
  named scoped sign-offs exist. An operational evaluation cannot be waived.
- EXT-CA-AI-02.16–18/20–21: typed/input/retrieval feasibility and lifecycle/recovery
  evidence matches the specified contracts; failures preserve saved state and
  truthful readiness. Changes after evaluation receive impact assessment before
  affected automation is reenabled.

## Tests and validation

Run the changed training/knowledge/backend integration suite, including real
PostgreSQL persistence/migration/concurrency checks with fake external providers.
Run affected frontend tests, lint/build and relevant manual review/viewport checks.
Verify independent manual creation and history preservation during outages.
Run the mandatory operational suite separately from CI and report every sealed
case/run, including failed attempts and unexecuted checks. Verify the recovery
runbook on isolated fresh/existing state; no destructive resets of real data.
Record commands, counts, failures and unexecuted checks; inspect the final diff
and confirm no unrelated files, real client data, secrets or raw archives changed.

## Completion requirements

Report files, tests, professional/operational evidence, supported release scope
and unresolved issues. Do not close the task on synthetic tests alone when real
indexing or professional decisions remain pending. No commit or push.
Actual-deployment evaluation and release sign-off are mandatory completion items;
an unevaluated model/configuration cannot inherit another configuration's result.

## Ready-to-use Codex prompt

Read `AGENTS.md`, this task and Required reading. Verify Tasks 45–50 against an
independent preimplementation-sealed, professionally reviewed evaluation suite containing both
supported positives and critical rejection cases. Report per-cohort evidence,
atomicity/privacy/manual-fallback checks and outstanding release decisions;
never substitute writer self-review for independent validation. Run related
checks, review the diff, and provide the report plus a response of at most
10 lines. Do not commit or push.
Execute mandatory actual-deployment evaluation and separate startup/runtime
recovery checks; obtain named scoped release sign-offs. Do not waive these items
because fake-provider CI passed or because operational access is unavailable.
