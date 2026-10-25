# Training prescription remediation specification

Version: 1.0, 2026-10-24. Status: specified; implementation and release pending.

Owner request: specify how to resolve the rejected-sheet and approved-rule test
failures. This document is the implementation map for Tasks 52–59.
The sole canonical specification remains [requirements.md](requirements.md),
especially **EXT-CA-AI-02.26–33**. Examples below operationalize those criteria;
they do not establish new clinical ranges or supersede canonical requirements.

## 1. Scope and current evidence

Direct ownership: RF-15, RF-18, RF-19 and EXT-RF-AI-02. Required dependencies:
RF-16/RF-17 and EXT-RF-INST-02/03 for presentation, revision and professional
review; RF-11–13 for existing authorized onboarding; RF-32/RF-33 and EXT-RF-EQP-01
for equipment eligibility. Apply RN-12–19, RN-29–31, RNF01–06, DEC-07/08/15/16,
the owner source/rule approval amendment and the established frontend design.

The original evidence must remain reproducible:

- [Two full-sheet attempts](tasks/51-owner-approved-generation-result.json):
  hypertrophy passed the listed automatic checks; strength was rejected as
  `ambiguous_exercise`. The rejected report identifies session A, not the exact
  movement; do not guess which movement caused the rejection.
- [All-rule experiment](tasks/51-all-owner-rules-report.md): 37 rules, 74 distinct
  fragment cases, 55 strict passes and 19 failures. These used a custom fragment
  prompt with `think=false`, not the ordinary full-sheet pipeline or live RAG.
- [Exact results](tasks/51-all-owner-rules-summary.json): five decision mismatches,
  five wrong quantities and nine unit/null errors. Two decision mismatches concern
  fragment acceptance versus an operational clarification action; their prose did
  recommend asking for missing facts. Do not label those two as demonstrated unsafe
  full-sheet acceptance.
- Four initial batches failed ID/count validation. Their ten rules were tested
  once more in isolated requests with constrained IDs/count. Preserve both plans
  and results rather than replacing the initial failures.
- The packaged dictionary, executable contracts and accounting mappings are empty;
  the sole packaged policy has no goal mappings or decisions. Eleven synthetic
  qualified-generation paths reject with `approved_goal_policy_required`.
- Owner acceptance covers exact versions of 24 sources and 37 proposed rules.
  Current `PrescriptionPolicy`, `ExerciseDictionary`, `AccountingMethod` and
  `require_current_runtime_reviews` still require independent HumanReview records.
  The owner alternative is exposed for consultation but is not yet an end-to-end
  compiled-policy authorization path. This is an implementation gap.

### Problem-to-deliverable map

| Observed problem | Required result | Task | Canonical criterion |
| --- | --- | --- | --- |
| Accepted research cannot become a complete executable policy; owner basis is not consumed by runtime | Coherent explicit branches, complete contracts and truthful artifact-bound authorization | 52 | .26 |
| Ambiguous exercise; resistance-only shapes cannot preserve other modalities | Stable exercise/variation keys and explicit supported modality structures | 53 | .27 |
| Wrong percentages, weekly totals and per-side durations | Backend calculation and accounting with exact regression oracles | 54 | .28 |
| String `"null"`, translated unit keys, missing/duplicate IDs | Narrow schema and deterministic representation-only boundary | 55 | .29 |
| Exclusive bounds ignored; loss of control accepted; action labels conflict | Backend limits, precedence and explicit required action | 56 | .30 |
| Multiple alternatives and incomplete profiles can be given to the writer together | Applicable branch and minimal rule/exercise/passage envelope | 57 | .31 |
| A repairable sheet rejection ends without a directed correction; nested retries can obscure budgets | One bounded correction, shared budgets and atomic save | 58 | .32 |
| Fragment checks can be confused with full generation or scientific validation | Separate regression, integration, model experiment and release evidence | 59 | .33 |

## 2. Architecture and invariants

Use the existing React/TypeScript/MUI frontend, FastAPI modular monolith,
PostgreSQL/pgvector, provider adapters and Docker Compose. No new dependency,
service, provider/model selection, paid integration or authentication role is
part of this specification. Preserve BGE-M3 vector dimensions and the final
zero-to-six-passage bound. A future need for a new dependency or architecture
must pass the existing decision process.

The authoritative pipeline is:

1. Resolve authenticated ownership, completed onboarding, request and revision.
2. Resolve goal/focus and required facts; obtain actual missing confirmations.
3. Resolve an authorized coherent policy branch and supported modality.
4. Select applicable exercise identities and eligible current evidence.
5. Build the backend-owned choice/calculation envelope.
6. Write a structured candidate, compute derived quantities and validate it.
7. Perform the supplementary automatic exercise review; correct once if eligible.
8. Revalidate current dependencies and revision, then atomically save the proposal.

Model self-assessment and citations cannot authorize an invalid candidate.
Instructor plan approval/activation remains separate. Existing current/history
is immutable. Keep the single-draft, authorization, equipment and replay rules.
Preserve rejected-attempt atomicity and manual authoring after successful backend
initialization. Additive metadata must not create new plan lifecycle states.

## 3. Task 52 / PRES-REM-01: executable policies and approval basis

**Inputs:** [research registry](../backend/app/modules/training/review-rule-candidates.json),
[owner acceptance](../backend/app/modules/training/owner-evidence-approval.json),
policy/execution/accounting artifacts, existing source hashes and input contracts.

### Deliverables

Create a versioned readiness matrix covering every rule and every existing goal
family: strength, hypertrophy, weight loss, cardiorespiratory fitness, muscular
endurance, power, mobility/flexibility, balance, functional autonomy, general
health and sport performance. Each row identifies:

- exact research rule, source/version/hash and applicable passage locators;
- direct finding versus local translation, reference association or product rule;
- applicable population/experience, goals, restrictions and required facts;
- selected branch, compatible components and explicitly excluded alternatives;
- exact units, any approved bounds, stop/regression conditions and input authority;
- dictionary/accounting/execution versions and missing implementation/decisions;
- supported, partial or unsupported status with a specific reason.

Compiling this registry must not infer an upper bound from an open literature
range, turn a reference plateau into a cap, merge a circuit and standalone sets,
or invent a missing progression/symptom rule. Every unresolved substantive choice
is an explicit decision item, with its affected profile suspended.

### Approval contract

Use a discriminated approval basis for executable policy components:

| Basis | Required verification | Scientific representation |
| --- | --- | --- |
| `owner_decision` | Existing owner instruction plus an explicit completed-bundle authorization, exact dependency/compiled hashes and scope | `professional_review_performed=false`; certainty may remain `not_assessed` |
| `independent_review` | Current actual app review references, independent identities, artifact binding and applicable deadlines | Preserve the actual recorded assessments; do not manufacture them |

Reuse the existing registry/record mechanisms. Extend their schemas explicitly
where a completed-bundle authorization needs a new record kind; the current
source/rule-only registry does not already approve a new bundle hash. Keep source
reuse rights, technical review deadlines and revocation as independent checks.
Apply the selected basis consistently to policy, dictionary, accounting and
runtime; changing only one schema would leave another hidden professional-only
block. Owner approval of a research rule does not choose an unresolved branch.

Bind authorization to substantive compiled policy, dictionary, execution,
accounting and input-contract versions, and to exact source/rule approval
dependencies. Exclude approval bookkeeping from the substantive digest to avoid
circular signatures. Material changes invalidate affected authorization and
qualification. Historical approved plans remain unchanged.

**Primary implementation surfaces:** `prescription_policy.py`,
`prescription_accounting.py`, `owner_approval.py`, `evidence_review.py`,
`prescription_runtime.py` and their packaged artifacts. Use the existing evidence
workspace to display actual basis and readiness; do not add fake instructor rows.

**Verification:** an explicitly authorized complete fixture works using owner
basis with no HumanReview rows; an absent/stale/revoked owner authorization fails;
the actual independent-review path retains its current checks. Compilation with
missing bounds/branch/authority fails with a named gap. At least one genuinely
complete scoped real-policy positive must be demonstrated before claiming actual
bundle readiness; an inventory full of blocked entries is not that positive.

## 4. Task 53 / PRES-REM-02: exercise identity and modality structures

Extend the existing bounded dictionary rather than building exercise CRUD.
Every selectable variation has a stable `exercise_key`, `variation_key`, pt-BR
label, unambiguous aliases, movement identity, permitted dose mode, relevant
muscle/task mapping and equipment constraints. Do not invent muscle fractions.

The writer receives only allowed keys. The renderer supplies the corresponding
label and does not ask the model to recreate names. Never identify an exercise
only as a resource such as `halteres`. Do not merge distinct movements or infer a
loaded variation from an unloaded/supported one. A machine reference must resolve
to an active model with an active operational unit; this is not live availability.

Mode-specific typed structures must preserve the following distinctions:

| Mode | Required quantities/relations | Invalid representation to reject |
| --- | --- | --- |
| Resistance | Working/warmup role, sets, repetitions, intensity/load convention | RM relabeled as working repetitions plus RIR |
| Continuous aerobic | Segment duration, intensity method, occurrence, rest tagged `not_applicable` | Zero inter-set rest used as a substitute for inapplicability |
| Static flexibility | Target, side, holds, seconds per hold, separate recovery | Both sides combined and reported as duration for each side |
| Balance/function | Task identity, attempts/completions, support/supervision, side/steps/hold as applicable | Failed attempt counted as completed hypertrophy work |
| Pair/circuit | Group ID, ordered members, rounds and rest relation | After-pair rest copied to each standalone item |

Reuse the current typed contracts where they express the distinction. Version
extensions and update validator, projection, frontend and persisted trace together.
If a mode cannot yet be represented, return an explicit controlled unsupported-mode
reason for that branch; do not publish a lossy conversion. Existing legacy plans
remain renderable with their original identifiers/text and qualification status.

Automatic rejection feedback for an ambiguous exercise must identify session,
item/position, reason and permitted alternatives. Expand reviewer output or add
backend item checks so a whole-session `ambiguous_exercise` code is not the only
available diagnosis. In synthetic probes, retain the failed item needed to
reproduce the defect. Ordinary logs must not contain rejected personal plans.

**Surfaces:** dictionary/contract/schema/renderer, `completeness.py`,
`selection.py`, equipment service consumption and existing prescription review UI.

**Verification:** resource-only/ambiguous names reject; valid recognized movements
pass; unknown keys and equipment variants reject; aliases never select two
movements. Each supported mode round-trips without changing units, side, grouping
or rest meaning. The rejected strength exercise is reproduced with item-level
evidence before claiming its specific defect was fixed.

## 5. Task 54 / PRES-REM-03: authoritative arithmetic and accounting

Place calculations in existing training domain/accounting services. Use Decimal
for fractional load/duration/equivalence and integers for counts. Reject NaN,
infinity, negative quantities and unit mismatches. Preserve API decimal encoding
compatibility; locale formatting belongs to the pt-BR renderer.

The writer proposes allowed intent: exercise/variation, permitted dose choice,
approved progression action and its confirmed input references. Backend services
calculate derived values and render them. Omit redundant model-computed totals
from the writer schema where possible. If a supplied primary field contradicts
the derived result, reject it with exact field feedback; do not silently certify
a different dose or take the explanation as authority.

### Required arithmetic regression oracles

| Case | Confirmed synthetic inputs | Authoritative result |
| --- | --- | --- |
| NUM-01 | Current 50 kg, permitted proposed increase 2% | `50 * (1 + 2/100) = 51 kg` |
| NUM-02 | Three 10-minute sessions, add 5 minutes to exactly one | `15 + 10 + 10 = 35 minutes/week` |
| NUM-03 | 2 working sets × 3 reps × total external 10 kg, 2 occurrences | `120 kg_repetitions/week` for that exercise/variation |
| NUM-04 | Distinct 30 moderate minutes and 15 vigorous minutes; approved factor 2 | `60 moderate_equivalent_minutes`; unclassified warmup excluded |
| NUM-05 | 2 holds × 30 seconds per side, 2 occurrences | `120 seconds/side/week`; recovery excluded |

These are arithmetic fixtures, not new exercise prescriptions. Add boundary,
fractional, duplicate-occurrence and missing-input cases around them.

Reuse `summarize_development_workload` for resistance calculations. Extend typed
accounting for other supported modes. Sum actual confirmed occurrences, not
template letters or nominal program weeks. Keep direct/indirect work separate;
fractional weights require an explicit approved mapping. Keep warmup/recovery and
unknown intensity time separate. Prevent overlapping segments from double counting.

Percentage load requires a current measurement for the same exercise/variation
and an approved load convention. Availability of a machine stack/increment is a
constraint, not permission to round arbitrarily. Rounding/increments come from
an explicit applicable policy; if absent, request the needed decision rather
than invent one. Unknown load, side, schedule or completion cannot become zero.

**Surfaces:** `prescription_accounting.py`, `prescription_validation.py`, typed
contracts, projection and immutable validation trace. Unit-test arithmetic without
any model; integration-test that a permissive/faulty writer cannot override it.

## 6. Task 55 / PRES-REM-04: constrained schema and representation boundary

Build on `prescription_writer_schema.py` and existing adapters. Derive closed
choices from the current envelope: exercise/variation IDs, session/occurrence IDs,
mode tags, units, instruction IDs and dimension-specific rule IDs. Require fields
and prohibit extra properties. Where list completeness is known, constrain counts
and IDs and validate uniqueness/completeness after decoding.

Actual JSON null is distinct from the string `"null"`. Contract unit keys remain
English; labels and feedback remain pt-BR. Reject a provider that ignores scalar,
enum or domain constraints. Tightening the transport schema never replaces domain
validation or grants permission to default missing values to acceptance.

A deterministic representation adapter may support a small versioned alias map
when a known token has exactly one meaning, including an explicitly documented
localized unit token. Test native schema output and alias conversion separately.
Unknown aliases reject. Conversion may not touch numbers, infer an action,
reinterpret RM/RIR, fill a missing value or repair a scientific contradiction.
JSON null compatibility and any alias policy must be explicit in schema version
tests, not silently added after a failed experiment to improve its score.

**Verification:** all nine observed unit/null defects have tests. Incorrect dose
with correct formatting still fails domain checks. Booleans cannot stand for
numeric quantities; numeric strings require an explicitly permitted versioned
numeric representation. A model returning
duplicate/missing/unrequested IDs fails regardless of its explanation. Provider
fallback does not skip these checks.

## 7. Task 56 / PRES-REM-05: exact bounds, conditions and required action

### Bounds contract

Represent endpoints and comparison type explicitly, for example:

```json
{"minimum": "15", "minimum_inclusive": false,
 "maximum": null, "maximum_inclusive": null, "unit": "repetitions"}
```

An absent endpoint is open, not zero or an invented cap. A literature reference
association has a separate reference representation and cannot be passed as a
finite executable safety range. Validate the endpoint/flag combinations. Existing
inclusive ranges require a deliberate versioned migration preserving meaning.

| Test | Expected backend behavior |
| --- | --- |
| `>15` repetitions: 15 then 16 | Reject 15; accept 16 if the rest of the applicable policy passes |
| `<90` seconds: 90 then 89 | Reject 90; accept 89 conditionally as above |
| `[180,300]` seconds: 160, 180, 300, 301 | Reject, accept, accept, reject conditionally as above |
| Circuit load `<60%`: measured 1RM 100 kg; 59 then 60 kg | Accept 59; reject 60 conditionally as above |

These fixture limits already exist in accepted research; applicability and
complete-dose authorization remain separate. An inclusive comparison cannot be
substituted merely because the base `NumericRange` currently has inclusive bounds.

### Conditions and action contract

Evaluate approved observation/stop/regression conditions in backend logic from
confirmed facts. A control-loss observation cannot select a challenge increase.
Missing observation is missing input, not success. A model `accept` or a
contradictory explanation cannot override these conditions.

Keep plan lifecycle status and outcome categories unchanged. Add/version action
metadata in the existing outcome contract as needed. Evaluate separately:

- whether a fragment faithfully describes a rule;
- whether required facts permit a proposal now;
- the next action: proceed with validation, ask for a named missing fact, abstain,
  or apply the recorded interruption/regression path.

Use the existing four categories: `restriction_conflict`, `missing_input`,
`insufficient_support`, `technical_unavailability`. A verified documented conflict
takes its applicable stop/regression path; otherwise missing required facts lead
to clarification, unresolved applicability to insufficient support, and external
failure to controlled technical feedback. Do not infer conflict from disclosure
alone. Do not infer a diagnosis from evidence gaps or an outage.

For an unspecified sport, request sport/event and the actually required capacity
facts. For unresolved medication/restriction applicability, preserve access and
the manual path while clarifying only authorized necessary facts. Do not silently
rewrite completed onboarding or collect unsupported medical details.

**Surfaces:** policy/contract schema, `prescription_validation.py`, clarification
and chat adapters, client/instructor outcome presentation. Preserve English API
reason codes and pt-BR messages. Validate source and input provenance before
testing clinical applicability; no numeric symptom threshold is introduced here.

## 8. Task 57 / PRES-REM-06: scoped writer envelope and evidence

Resolve free-text goals using explicit supported mappings and confirmed priorities.
An AI focus suggestion is a candidate interpretation, not authoritative scope.
Unknown/ambiguous or mixed goals require the existing clarification mechanism.
Preserve hypertrophy, fat loss, sport or other requested goals without automatically
replacing them with rehabilitation/general health.

Choose one coherent applicable branch. Include only its rules and genuinely
compatible components. For example, a paired protocol's rest relation and a
standalone hypertrophy rest choice must not be merged without an explicit branch
decision. A fragment's acceptance does not fill the rest of the policy dimensions.

The writer envelope contains exact versions/hashes, minimized confirmed facts,
allowed dictionary IDs, permitted parameter choices, calculation input references,
instructions/conditions and evidence links. Narrow all choice sets before writing.
Do not send the entire research registry as an operational policy. This is a
selection change inside existing services, not a larger model/context window.

Use existing source-scope, permission, deadline and revocation filters before
ranking. Retain the final maximum of six passages and record which dimension and
material decision each actually supports. Metadata-only consultation approval
does not authorize putting excluded source text into embeddings/model context.
If a complete applicable branch cannot fit the bound, return a coverage reason
and record the gap. Clarification cannot manufacture an unavailable policy.

**Surfaces:** `prescription_runtime.py`, `prescription_development.py`,
`prescription_feasibility.py`, `knowledge_query.py` and `prescription_writer_schema.py`.

**Verification:** targeted requests retain their muscles; mixed goals preserve
confirmed priorities; restriction combinations require actual applicability;
unknown sport requests ask for missing facts. No unused branch/exercise or another
client's data reaches the writer. Correct citations with an unsupported dose fail.

## 9. Task 58 / PRES-REM-07: directed correction and persistence

Reuse `request_selected_training` / `prepare_with_selection` rather than introducing
a separate generator. A repairable defect yields structured session/item/field
feedback, stable reason, allowed choices and the relevant rule. Examples include
an ambiguous movement, known schema representation error or a candidate outside
an already complete policy envelope.

The correction uses the same authenticated request, confirmed facts, goal and
applicable support. It may repair the representation or choose another authorized
option; it cannot change a user's facts, approve new rules, alter an accepted
numeric bound or treat missing applicability as resolved. Missing input goes back
to clarification; revoked evidence/unavailable policy/outage stops the attempt.

### Shared attempt budget

One logical request has at most two content candidates: original plus one
correction. Preserve the existing maximum one transient transport retry per stage.
Count actual model HTTP calls in one shared object across nested helpers:

| Stage | Maximum calls per logical attempt, including transport retries |
| --- | --- |
| Writer | 4: two candidates, at most two transport attempts each |
| Automatic exercise review | 4: at most one review per candidate, each with at most one transient retry |
| Focus interpretation | 2: one result reused across correction, at most one transient retry |
| All model calls | 10 absolute maximum; unused stages do not transfer allowance |

These are upper bounds, not a requirement to make extra calls. Structured domain
rejections use the single content-correction policy; they do not restart transport
retry counters indefinitely. Idempotent replays do not start fresh model attempts.

Set a bounded operation deadline from permitted stages and configured adapter
timeouts; each call receives the remaining time or its adapter timeout, whichever
is shorter. Preserve OpenAI's ten-second configured attempt policy and Ollama's
approved configurable timeout. Record call counts, stage durations and exhaustion
without prompts, private health content or model chain of thought in normal logs.

After correction, rerun schema, identity, modality, calculation, applicability,
bound, condition, citation, automatic-review and freshness checks. Re-read the
expected revision/dependencies immediately before atomic save. A stale revision
requires refresh; it is not permission for an AI correction against unknown state.
Persistent failure preserves the sole draft and its submission/validation state,
current plan and history. No rejected exercise table or partial adaptation is
published from that attempt.

Use existing client/instructor shells for `Gerando proposta…`, `Corrigindo a
proposta…` and controlled pt-BR failure/clarification feedback. Keep any retained
saved draft clearly distinct from the discarded attempt. Check responsive and
accessible feedback under DEC-16; do not introduce credential or approval flows.

## 10. Task 59 / PRES-REM-08: verification and completion

### Separate evidence layers

1. **Offline domain/adapter regressions:** real boundary/calculation/action code,
   fake providers and malicious/permissive candidate outputs. Keep arithmetic,
   units, explanation, decision and support checks separately reported.
2. **Integration:** actual initial/targeted/rebuild/chat draft-edit/adaptation,
   cached/idempotent replay, confirmation, submission and instructor approval
   paths, using the actual versioned contracts. Check PostgreSQL concurrency,
   rollback and authorization where persistence is affected.
3. **Exposed development model experiments:** actual configured writer, schema,
   retrieval, validator and automatic reviewer; synthetic clients and isolated
   persistence. Freeze cases, versions, repetitions, expected outcomes, resource
   budgets and run scope before execution. Preserve every failed run.
4. **Independent operational evaluation/release:** retains existing separate
   custody, untouched cases and explicit release gates. Developer-visible tests
   cannot substitute for this layer. Owner source/rule acceptance is not a
   fabricated professional opinion or an already completed evaluation.

The new fragment diagnostic must separate `fragment_valid` from `required_action`.
For SPORT_SPECIFICITY/RESTRICTIONS, evaluate whether the system asks for missing
facts rather than inferring unsafe generation from the word `accept` alone.
Preserve the old frozen rubric and scores; version the new rubric before its run.
Grade explanation consistency explicitly where it is being claimed, or mark it
ungraded. The observed incorrect RIR expansion must not be hidden by a passing
structured answer. Clinical accuracy is never inferred from fragment scores.

### Required acceptance cases

| Suite | Minimum concrete coverage |
| --- | --- |
| Policy/approval | Complete scoped owner-basis positive; actual independent-review compatibility; absent/revoked/changed authorization; unassessed certainty rendered truthfully; no fabricated records |
| Identity/modality | Ambiguous movement, allowed alternative, wrong variation/equipment; full/targeted scope; every claimed dose mode and relation |
| Arithmetic | NUM-01–05, fractional quantities, unknown facts, sides, distinct and repeated occurrences, overlap, rounding/increment policy missing |
| Format | Nine observed representation defects; strict enums/nulls; unknown alias; duplicate/missing IDs; correct format with invalid content |
| Limits/actions | Exclusive/inclusive endpoints, control loss, conflict precedence, absent measurements, unspecified sport, access preserved for disclosures |
| Correction | Original invalid then valid correction; two invalid candidates; transient retry; reviewer outage; budget/deadline exhaustion; facts/support/revision changed during repair |
| Persistence/privacy | No partial save; unchanged draft/current/history on rejection; concurrent same request; another client's context/trace denied; manual fallback after initialization |
| UI | pt-BR feedback, exact exercise/field issue where authorized, retained-draft distinction, keyboard/accessibility and three DEC-16 viewports |

For every goal/profile advertised as enabled, include a real-policy positive that
reaches a reviewable proposal without activation and critical negative controls
that reject. Missing executed positives or an always-reject implementation prevents
a success claim. Inventory coverage of eleven families does not promise that every
restriction combination is supported. Report blocked branches and missing decisions
individually, not as tested successful generations.

Start verification scaffolding alongside 52; run end-to-end completion after
52–58. Frontend changes require related tests, lint/build and affected journey
verification. Run targeted backend tests, PostgreSQL checks for changed persistence,
configured lint/format and final diff review. Preserve established test requirements.

### Delivery report

Record exact files, commands/results, versions/hashes, policy/branch allowlist,
remaining blocked rules/profiles, actual call counts/latencies, failed/rejected
outputs and decisions still needed. Label the difference between a repaired
format, corrected backend quantity, valid model candidate, qualified proposal and
released configuration. No automatic rollout, model upgrade, commit or push.

## 11. Traceability of all 37 accepted rules

This table assigns implementation and verification responsibility; it is not a
claim of complete operational coverage or a new prescription approval.

| Rule IDs | Primary remediation | Required discriminator |
| --- | --- | --- |
| RESISTANCE_EFFORT, NOVICE_LOADING, HYPERTROPHY_LOADING | 52, 53, 55, 56 | RM, working repetitions and calibrated RIR remain distinct |
| SELECT_RESISTANCE | 53, 57, 58 | Confirmed focus, actual movement and equipment |
| STRENGTH_DOSE | 52, 54, 56 | Applicable branch and current exercise-specific measurement |
| HYPERTROPHY_VOLUME | 52, 54, 56 | Reference association versus approved individual bound |
| STRENGTH_REST, HYPERTROPHY_REST | 52, 56, 57 | Experience/loading and selected rest relation |
| LOAD_PROGRESSION | 54, 56, 58 | Observed condition, exact percentage and authorized increment |
| SOURCE_PAIRED_RESISTANCE | 53, 54, 57 | Rest after pair and actual selected members |
| SOURCE_MEDICINE_BALL_POWER | 52, 53, 56 | Specific task competence/space and actual ball selection |
| SOURCE_ENDURANCE_CIRCUIT | 53, 54, 56 | Circuit rounds, after-exercise rest and strict load bound |
| ENDURANCE_DOSE, ENDURANCE_SETS | 52, 55, 56 | Strict endpoints, finite proposed branch and correct units |
| POWER_DOSE, POWER_STRUCTURE, POWER_REPETITIONS | 52, 54, 56 | Measured load, recovery bound and interruption condition |
| AEROBIC_DOSE, AEROBIC_INTENSITY | 52, 53, 56 | Health reference versus starting dose and actual intensity method |
| AEROBIC_START_PROGRESS, AEROBIC_RECOVERY | 53, 54, 56 | One selected occurrence and explicit rest inapplicability |
| FLEXIBILITY_DOSE, FLEXIBILITY_STRUCTURE, FLEXIBILITY_NEWER_EVIDENCE | 52, 53, 54, 56 | Target/side/hold and aggregate reference versus individual prescription |
| BALANCE_DOSE, FALL_PREVENTION, BALANCE_RECOVERY | 52, 53, 56 | Actual population, task/support and observed control |
| FUNCTION_DOSE, FUNCTION_STRUCTURE | 52, 53, 54, 56 | Task-specific capacity and observed reassessment |
| WEIGHT_DIRECTION | 52, 57 | Weight, fat and lean-mass outcomes preserved without promises |
| SPORT_SPECIFICITY | 56, 57, 59 | Missing event-specific facts require clarification |
| RESTRICTIONS | 52, 56, 57, 59 | Authorized inputs and applicability; disclosure is not an access ban |
| RESISTANCE_ACCOUNTING | 53, 54 | Working/warmup, muscle mapping and actual weekly occurrences |
| AEROBIC_ACCOUNTING | 53, 54 | Approved equivalence, classified segments and no overlap |
| FLEXIBILITY_ACCOUNTING | 53, 54 | Duration per side and occurrence; separate recovery |
| BALANCE_FUNCTION_ACCOUNTING | 53, 54, 56 | Attempts versus completed tasks and actual support/supervision |
| COMBINED_GOALS | 52, 57 | Confirmed priorities and compatible complete components |

Tasks 55, 58 and 59 supply schema, correction and verification checks across all
rules; a listed primary owner does not exempt a rule from those cross-cutting checks.

## 12. Decision gates and implementation handoff

Keep these unresolved when the source artifacts do not determine them:

- A coherent choice among linked alternative protocols and any new finite bounds.
- Supported actual populations, restriction combinations and input validity/authority.
- Exercise variants, task success/stop criteria, muscle mappings and rounding rules.
- Authorization of the completed substantive bundle under the selected basis.
- Evaluation cases, repetitions, resource limits, outcome thresholds and scoped release.

Technical maintainers may implement generic types, calculators and failure paths
with explicit synthetic fixtures while these decisions are open. They cannot
silently resolve the affected prescription choice by editing an approved status.
Do not require the owner to repeat the already recorded source/rule acceptance;
distinguish genuinely new artifact/branch decisions from existing authorization.

Implementation follow-up: the generic remediation contracts, runtime integration
and regressions are implemented; see the [delivery report](tasks/46-59-owner-rag-delivery.md).
The later canonical owner amendment permits assisted RAG without independent
evaluation or compiled clinical qualification. The original specification-only
handoff below is retained as planning history, not the latest execution status.

Implementation order: **52 → 53 → 54 → 55 → 56 → 57 → 58 → 59**. Prepare 59's
offline fixtures and test harness alongside 52. At every task, read its canonical
criterion, inspect current implementation, preserve unrelated work, add focused
behavioral tests and report files, tests, decisions and unresolved items. This
request delivers the specification only; none of Tasks 52–59 is marked complete.
