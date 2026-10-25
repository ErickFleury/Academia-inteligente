# Task 48 — Coverage-Aware Retrieval and Prescription Validation

**Current owner-RAG scope — 2026-10-25:** consultation-source integrity, scope,
freshness and owner authorization are enforced without an independent-evaluation
gate. Typed compiled qualification remains a separate tested path. See
[current delivery](46-59-owner-rag-delivery.md); historical compiled-scope gates below
do not block the newly authorized assisted RAG mode.

**Status:** shared typed validator and operational adapters implemented under the
development exception; PostgreSQL migration verified (2026-10-24). Real-policy,
reviewed-feasibility, independent-evaluation and enablement gates remain open.
**Feature task:** EVID-IMPL-04.

Task 47 lacks approved contracts, reviewed dimension feasibility and the required
independent evaluation seal required for operational release. See the
[integrated status report](51-training-prescription-verification-report.md).
The [isolated development report](48-50-isolated-prescription-development-report.md)
records the original isolated scope. The
[operational follow-up](45-51-operational-integration-follow-up.md) records later
adapter integration, real indexing and PostgreSQL verification.
No synthetic approval or instructor-role assignment satisfies operational
enablement. The [approved development exception](../training-prescription-development-amendment.md)
permits isolated implementation/tests with synthetic policies; real-student
runtime generation remains outside that exception.

## Objective

Create one backend-owned evidence and policy gate that determines whether a
candidate prescription is eligible before any generation flow can persist it.

## Requirements covered

- EXT-RF-AI-02: EXT-CA-AI-02.5–7/13/16–20; consume .22 approvals.
- RF-15/CA-15.7/11–13, RF-18/CA-18.6–7, RF-19/CA-19.5 shared integration.
- RF-17 and EXT-RF-INST-02 consumed revision/history boundaries.

## Related rules and constraints

RN-04/05, RN-11–RN-20, RN-23, RN-29–RN-33; RNF01/04–06; DEC-07/08/15/18,
EXT-DEC-AI-02. Preserve current providers, embedding dimensions, source permissions,
scope filters and maximum six final passages. No new dependencies without approval.

## Prerequisites and required reading

Task 47's design exit must be satisfied for operational enablement: actual
corpus feasibility, approved typed/input/policy contracts and a sealed independent
evaluation plan exist. Isolated development may proceed under the approved
2026-10-23 sequencing exception. Synthetic fixtures exercise those contracts but cannot
enable unapproved real profiles. Read `AGENTS.md`, overview,
EXT-RF-AI-02, listed canonical RF/CA/rules/RNF/decisions, RAG contract and sections
6.1.1/7.2/9.2. Inspect knowledge retrieval, `training/knowledge_query.py`, schema,
focus/completeness/selection, lifecycle persistence, writing-adapter contracts
and current evidence tests before editing.
Read [the methodological protocol](../training-evidence-methodology.md), sections
1 and 4–6. Consume approved evidence-to-decision records rather than assigning
certainty/contraindications from model confidence or technical retrieval scores.
Read [the execution contracts](../training-prescription-execution-contracts.md),
sections 1–5. Implement contract v1 and the transition matrix; do not reopen units,
exercise identity or input authority as ad hoc implementation choices. Developers
must not inspect sealed evaluation cases or answers while tuning the gate.

## Permitted scope and expected behavior

1. Define shared eligibility/result/reason contracts separately from the existing
   four-value bibliographic `knowledge_status`. Provider output cannot populate
   or override a passing backend validation record.
   Distinguish documented restriction conflict, missing required input,
   insufficient applicable support and technical unavailability. Invalid
   provenance, parameter and stale-state errors retain explicit subreasons.
2. Resolve policy applicability from authorized inputs; filter ineligible sources
   and populations before selection. Include general prescription and specific
   restrictions without allowing either to consume the whole evidence budget.
3. Select at most six final passages whose collective coverage satisfies every
   mandatory rule. Selection may use current hybrid ranking inside that bound;
   failure to cover all dimensions means abstention. Do not concatenate arbitrary
   documents into one fake passage to evade limits or change source text at runtime.
4. Implement the specified typed contract v1, reviewed versioned exercise keys,
   discriminated dose/intensity units, schedule, progression and restriction-rule
   links. Compute muscle/session/week totals using the approved dictionary and
   accounting method. Render legacy display fields from validated typed values
   and approved instruction keys; reject contradictory prescriptive prose instead
   of parsing it into a pass. Manual content keeps its unqualified path.
5. Check item/session/week constraints, interacting restrictions and the complete
   resulting plan for adaptations. A targeted sheet with unknown weekly context
   must not claim validated whole-week volume/frequency. Apply the approved
   policy's required-input rule or abstain.
   AI adaptations must normalize and qualify all resulting items, including
   unchanged legacy/manual rows. If that is impossible, reject the AI candidate
   and preserve the base; do not qualify just the changed rows or prior history.
6. Require each material decision to map to an approved rule, current source
   version and actually retrieved locator. Validate quote/locator integrity and
   provenance; existence of the citation ID alone is insufficient. Rule creation
   is professionally reviewed in Task 47 rather than delegated to a second LLM.
7. Preserve schema/equipment/completeness/variation/duplicate validation. Any
   automatic review can add a rejection, never waive a missing rule or evidence.
8. Persist immutable policy/evidence/validator version trace bound to content
   revision. Add only needed Alembic changes; historical rows remain readable
   and explicitly unvalidated, with no fabricated default pass.
9. Bind the trace to input snapshot/hash, dictionary/accounting version, rendered
   content hash and exact revision. Input/policy/dictionary/model changes invalidate
   affected reuse according to the dependency-impact map. Implement validation
   metadata separately from existing plan states and immutable AI lineage.

Permitted areas: knowledge/training domain services and schemas, AI/embedding
adapter contracts only when necessary, focused migrations/tests. No frontend,
new AI provider/model, independent vector service or broad lifecycle refactor.

## Acceptance criteria

- EXT-CA-AI-02.5: relevant-but-inapplicable sources and incomplete six-passage
  sets cannot pass; search errors and expired evidence retain accurate reasons.
- EXT-CA-AI-02.6–7: unsupported parameter, wrong population, invented source,
  unresolved conflict, missing input and partial support all reject; an applicable
  complete fixture passes. Writer `supported` and automatic-review approval do
  not change those outcomes.
- EXT-CA-AI-02.13: trace binds to exact revision/source hashes/policy versions;
  edits or source/policy revocation invalidate current qualification without
  rewriting approved historical snapshots.
- EXT-CA-AI-02.16–20: typed-to-display equivalence, input authority/freshness,
  deterministic volume accounting, unknown exercise rejection and complete-result
  adaptation checks are demonstrated. Task 47's measured coverage and sealed
  evaluation prerequisites cannot be bypassed using synthetic approvals.

## Tests and validation

Add unit/contract tests and PostgreSQL integration tests for filtering, bounded
coverage, attribution integrity, typed units/totals, conflicting restrictions,
missing schedule, provenance/version migration and client isolation. Distinguish
all four abstention categories, and include approved
conditional-use positive/negative cases without treating low certainty alone
as a contraindication. Use fake providers and explicit synthetic professional-policy
fixtures. Run affected
`test_knowledge*`, `test_training_rag.py`, and new focused validation tests.
Review diff, generated API changes and migration compatibility.
Add contract round-trip/projection tests, conflicting text/dose cases, multi-joint
accounting, repeated schedule days, input-snapshot invalidation and legacy-base
adaptation rejection. Preserve sealed-case custody and historical compatibility.

## Completion requirements

Report files, tests/results, schema decisions and unresolved domain gates.
Keep unapproved real cohorts disabled. No commit/push.

## Ready-to-use Codex prompt

Read `AGENTS.md`, this task and Required reading. Implement shared coverage-aware
retrieval and deterministic policy/provenance checks in the existing modules,
with a revision-bound trace and separate prescription eligibility. Preserve the
approved six-passage/1024-dimension/provider architecture. Test positive and
negative synthetic policies without enabling unapproved profiles, review the
diff, and report files, checks, decisions and gaps in at most 10 lines. Do not
commit or push.
