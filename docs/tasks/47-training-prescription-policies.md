# Task 47 — Reviewed Prescription Policies and Supported Profiles

**Current owner-RAG scope — 2026-10-25:** owner-authorized consultation drafting,
37-rule inventory and a bounded technical identity dictionary are implemented.
Independent appraisal/sealing is optional for this mode under the canonical owner
amendment. See [current delivery](46-59-owner-rag-delivery.md). The compiled clinical
qualification status and historical prerequisites below describe that separate scope.

**Status:** draft schema/artifact and technical retrieval probe implemented on
2026-10-23; accounting helpers and authoritative onboarding snapshot builder added
in isolated development. Professional contracts, reviewed feasibility and independent seal
pending. Task incomplete. **Feature task:** EVID-IMPL-03.

Evidence: [policy review package](../training-prescription-policy-review.md).
Zero approved policies/dictionary entries and no enabled cohort. The user assigned
initial responsibilities to the instructor profile; named/qualified independent
reviews and held-out custody have not been established. Operational enablement
prerequisites remain unsatisfied; synthetic records do not supply approval.
The subsequent [all-goal rule review package](../training-prescription-rule-review.md)
and [structured registry](../training-prescription-rule-candidates.json) provide
actual reference-derived parameters, professional program examples and separate
proposed translations across all eleven discussed goal families. They are concrete
review inputs, not approved executable policies or independent evaluation results.
The [approved development exception](../training-prescription-development-amendment.md)
permits isolated implementation/tests of Tasks 48–50 while these gates are pending.

## Objective

Owner scope update (2026-10-24): implement the protected instructor review and
custody workspace under EXT-CA-AI-02.23–25. This supersedes the earlier file-only
boundary for these functions. All active instructors are eligible; actual
distinct people must perform the independent assessments. See the
[instructor workflow](../training-evidence-instructor-workflow.md). No general
corpus uploader or automatic policy publication is authorized.

Turn applicable evidence into versioned, professionally reviewed prescription
rules that software can check, while explicitly retaining unsupported profiles.

## Requirements covered

- EXT-RF-AI-02: EXT-CA-AI-02.1/4/6–7/14; design ownership for .16–19/22.
- RF-15/CA-15.4–5/11–13; RF-18/CA-18.5–7; RF-19/CA-19.1/3/5 integration.

## Related rules and constraints

RN-11–RN-20, RN-23, RN-29–RN-33; RNF04–06; DEC-07/08/15/18 and
EXT-DEC-AI-02. Health data must influence applicability, but a diagnosis must not
be inferred from a complaint. Neither technical source approval nor AI extraction
is a qualified professional's prescription-policy approval.

## Prerequisites and required reading

Tasks 45–46 source review, ingested artifacts and exact passage locators are
available. Read `AGENTS.md`, the overview, EXT-RF-AI-02 and listed canonical
RF/CA/rules/RNF/decisions, including RAG contract and section 9.2. Inspect current
onboarding, focus, plan schema, completeness/selection, equipment and lifecycle
services. Read source passages before drafting a rule; titles/abstracts alone
are insufficient to reconstruct unreported prescription detail.
Read the [methodological protocol](../training-evidence-methodology.md), especially
sections 3–5, Task 45's actual appraisal/certainty records and criterion register.
Pending methodological judgments cannot be represented as completed GRADE ratings.
Read [the execution contracts](../training-prescription-execution-contracts.md),
sections 1–4 and 7. Consume Task 45 input/evaluation/owner records and Task 46's
actual corpus manifest. Operational gate enablement waits for this task's
approved contracts, retrieval-feasibility report and sealed evaluation plan.

## Permitted scope and expected behavior

1. Define versioned policy schemas/artifacts in the existing backend training/
   knowledge modules and a human-readable coverage report under `docs/`.
2. Define goal mappings without changing stored free-text goals. Preserve all
   four existing experience levels. Unknown/multiple/ambiguous goals require
   an explicit reviewed combination/mapping or clarification/abstention.
3. Record included populations, exclusions, restriction interactions, required
   inputs, and evidence certainty. Missing age, clinical clearance, schedule,
   baseline capacity or other required facts cannot be filled by assumption.
   Produce the per-cohort input-readiness matrix: typed fact, authoritative
   service/source, confirmation, timestamps, policy-defined validity, permitted
   audience and missing/stale/conflict action. Define minimal request-specific
   supplements for Task 49's existing authenticated clarification flow; never
   rewrite completed onboarding. Fields outside approved medical/retention scope
   retain their decision gates. A mandatory unavailable input prevents enablement.
4. Specify selection, volume, intensity, frequency/recovery, progression/regression,
   rest and restriction adjustments. Encode units, ranges, calculation methods,
   per-exercise/session/week constraints and missing-context behavior. Distinguish
   direct study findings from approved conservative translations into practice.
5. Link every rule to source/passage versions and precise locators. Record
   contradictory evidence and approved resolution; do not choose by citation
   count, model confidence or favorable effect size alone. No universal optimum.
   Create a structured evidence-to-decision record for every material rule:
   relevant outcome certainty, benefits/harms/burdens, preferences, feasibility,
   alternatives, applicability, derivation and reason for the chosen bounds.
   Do not turn an aggregate association into an unexplained individual optimum.
6. Record named qualified reviewer, review date/deadline and approval scope.
   A developer or AI may draft extraction for review, but cannot impersonate
   that reviewer. Until approved, rules remain pending and cannot enable cohorts.
   Lower certainty alone is not an automatic prohibition: conditional use needs
   an explicit approved rationale, checkable conditions and stated uncertainty.
   Missing coverage or an unresolved conflict cannot be renamed conditional use.
7. Version updates and revocations without rewriting prior decision snapshots.
   Produce explicit supported/partial/unsupported/awaiting-review coverage and
   decision requests containing the actual proposed rules/evidence for review.
8. Finalize the typed contract v1 in the execution contracts, the bounded reviewed
   exercise-key/alias/variation dictionary, and per-policy volume-accounting methods.
   Define muscle contributions, schedule semantics, discriminated intensity units,
   approved instruction keys and conditional progression without inventing clinical
   ranges or implementing exercise CRUD/completed-workout tracking.
9. Run the pre-gate retrieval-feasibility experiment on the Task 46 corpus using
   reviewed development cases and reference passages. Measure existence/indexing/
   retrieval/selection coverage under six final passages and operational resource
   budgets. Allow a small join/coverage harness, not Task 48's production gate.
   Fix permitted extraction/ranking gaps; disable nonviable cohorts and document
   any architectural proposal instead of silently increasing the passage budget.
10. Adopt, adapt or reassess existing appraisals/recommendations explicitly,
    recording question/population/version/currency compatibility and local gaps.
    Use named methodological/professional sign-offs from Task 45; assign source/
    policy-change impact and reenablement ownership. Do not redo all reviews by
    default or claim GRADE use without its actual methodological records.
11. Seal the evaluation protocol, independent cases/answers, hashes, thresholds,
    repeated-run and operational budgets before independent evaluation and operational enablement. Keep
    held-out material with the independent evaluator; developers get development
    cases and public protocol/hash metadata only. Unresolved decisions leave
    the affected cohort/design gate open, not implicitly approved.

Only policy/schema/dictionary helpers, a development retrieval-feasibility harness,
input/evaluation contracts, related tests and coverage documentation
are in scope. No new clinical thresholds invented by this task, production
generation enablement, automatic diagnosis or exercise-catalog CRUD.

## Acceptance criteria

- EXT-CA-AI-02.1/4: every enabled cohort has approved applicability and all
  mandatory prescription dimensions; missing approval leaves it disabled.
- EXT-CA-AI-02.6: machine-readable policies define units, bounds, dependencies,
  required inputs and source links without deriving a person's exact kg load
  or 1RM from demographics. Professionally approved relative guidance is allowed.
- EXT-CA-AI-02.7: conflicts/uncertainty remain explicit; metadata relevance or
  a source's general exercise advice cannot become full prescription support.
- Critical combined-restriction and unknown-profile examples are represented.
- EXT-CA-AI-02.14: every material rule has a versioned evidence-to-decision record
  linked to actual appraisal/outcome-certainty judgments and reviewer decisions.
  Scientific findings, professional operational choices and product constraints
  remain distinguishable; no invented universal quality/eligibility score.
- EXT-CA-AI-02.16–19/22: typed dictionary/accounting and input-readiness contracts
  are approved, actual corpus retrieval feasibility/resource results are recorded,
  and evaluation materials are sealed before gate implementation. No cohort with
  unresolved mandatory inputs or infeasible six-passage coverage is enabled.

## Tests and validation

Use synthetic policies to test schema/units, unknown mappings, conflicting rules,
interaction cases, missing facts, expired review, version updates and provenance
integrity. Keep synthetic approval isolated from runtime artifacts.
Test evidence-to-decision record completeness, conditional-use boundaries and
the distinction between uncertainty, missing coverage and restriction conflicts.
Check dictionary/alias ambiguity, muscle accounting and schedule calculations;
run the development retrieval experiment with the real corpus/embedding search,
reporting it separately from fake-provider tests. Verify sealed-case custody and
adopt/adapt/reassess records without exposing held-out answers to developers.
Separately record professional review of real policy content; tests cannot provide it.
Run affected policy/onboarding/focus tests and review the Git diff.

## Completion requirements

Report files, tests, approved and pending cohort counts, reviewer evidence and
open decisions. If no real policy is professionally approved, implementation
scaffolding may be reported separately but this enabling task remains incomplete.
No commit or push.

## Ready-to-use Codex prompt

Read `AGENTS.md`, this task and Required reading. Draft traceable computable
policies and explicit evidence-to-decision records only from the appraised,
reviewed ingested evidence. Obtain already-authorized professional decisions where
available, and keep unapproved profiles unsupported.
Finalize typed/input contracts, run six-passage feasibility on development cases,
and seal independent evaluation before independent evaluation and operational enablement.
Do not invent ranges, reviewer identities or missing client inputs. Implement
policy/schema and the owner-authorized review/custody scope, run focused tests,
review the diff, and report files,
tests, decisions and pending professional approvals in at most 10 lines. Do not
commit or push.
