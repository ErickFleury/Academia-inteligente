# Training Prescription Execution Contracts

**Version:** 1.0 — 2026-10-22. **Status:** specification only. No operational
evaluation, clinical rule approval, profile enablement or runtime change is
completed by this document. `docs/requirements.md`, EXT-CA-AI-02.15–22, is canonical.
This document supplies concrete implementation contracts supporting Tasks 45–51.

The [domain contracts](training-prescription-domain-spec.md), dated 2026-10-23,
record the owner's audience/onboarding/evaluation decisions and the selected
exercise, prescription and accounting references. They complement these technical
contracts; reference selection does not complete professional approval or sealing.

## 1. Stage gates and independent evaluation

| Stage | Owner | Required exit evidence |
| --- | --- | --- |
| Research design | Task 45 | Named reviewers/owners, PICO questions, proposed initial cohort slice, input-source inventory, appraisal and evaluation protocol v1, case-selection and resource plan |
| Corpus | Task 46 | Eligible acquired/indexed subset, extraction/provenance checks, recovery runbook and reproducible corpus manifest |
| Domain design | Task 47 | Approved policy/dictionary/input contracts, feasibility and sealed evaluation before operational enablement; the approved exception permits earlier isolated development |
| Gate and flows | Tasks 48–50 | Typed validator, atomic transitions, input confirmation, outcome UX and deterministic integration tests |
| Release | Task 51 | Mandatory actual-deployment evaluation, independent judgments, outage/recovery checks and explicit scoped sign-off |

Task 45 defines evaluation questions, sampling, outcome categories, case
partitioning and reference-judgment procedures. Task 47 seals case IDs/hashes,
answers, severity, cohort thresholds, repeat counts, operational budgets and
approval records before independent evaluation and operational enablement.
The [owner-approved development exception](training-prescription-development-amendment.md)
allows isolated Tasks 48–50 development with synthetic policies before review/
feasibility/sealing; it grants no real-student enablement. Changes after sealing need a
dated rationale and independent replacement of any exposed/tuned held-out cases.

Keep held-out synthetic cases and answer keys under the independent evaluation
owner's access control, outside implementation prompts, normal repository fixtures,
runtime corpus and policy-tuning data. Publish their hashes and protocol metadata,
not the sealed answers to developers. Development fixtures remain available.
If the same person sees held-out answers and tunes implementation against them,
that set no longer supports an independent release claim.

Task 51 must execute the sealed suite with the actual deployment writer/provider,
embedding model, corpus, policies, validator and decoding configuration. It must
include supported positives, critical negatives, all prescriptive entry points,
source applicability, displayed content and repeat-run variability. Record exact
model identity/digest when exposed, provider/model version limitations, prompt and
schema versions, corpus/policy hashes, sampling parameters, hardware, durations,
timeouts, attempts and per-case outcomes. Do not conceal failed attempts as retries.

Use isolated synthetic clients and isolated test persistence or verified rollback;
create no real-client content, submissions or activations. Use existing authorized
providers only; paid runs require an already approved operational budget, never
an implicit new subscription. Offline fake-provider CI remains separate. Provider
unavailability or absent budget leaves the affected deployment unevaluated and
disabled, not provisionally reliable. A model/configuration change requires impact
assessment and relevant reevaluation before re-enabling affected scope.

## 2. Typed prescription contract v1

The backend owns this logical contract; Task 48 implements equivalent Pydantic,
provider schema, persistence and OpenAPI types within existing modules. It must
not defer domain units/semantics to free-text parsing. No clinical range is set
here: bounds and recognized alternatives come from Task 47 approved policies.

| Component | Required fields and semantics |
| --- | --- |
| Envelope | `schema_version`, `scope` (`session_sheet` or `plan_revision`), requested goal/focus, `input_snapshot_id`, `policy_version`, `exercise_dictionary_version`, base/current/draft revision identifiers where applicable |
| Schedule | Stable `session_id`, ordered sessions, explicit days/occurrences in a seven-day schedule when weekly claims are made; no frequency inferred from an exercise-name suffix or letter alone |
| Exercise | `exercise_key`, approved variation key, `session_id`, position and canonical equipment-model relationship when needed; keys resolve against a reviewed versioned dictionary |
| Dose | Positive integer `sets`; discriminated `repetitions` with integer min/max, or `duration_seconds` with numeric min/max; units cannot be interchanged or guessed |
| Intensity/load | Tagged mode `rir`, `rpe`, `percent_1rm`, `external_load_kg` or `approved_relative_instruction`; typed range or reviewed instruction key; numeric modes identify their scale/method. Percent/absolute load requires valid measured baseline/input provenance when the applicable policy requires it |
| Recovery | `rest_seconds` plus approved inter-session recovery/schedule rules; item rest and day recovery are distinct quantities |
| Progression | Approved rule ID, observable condition key, required baseline, action type, amount/unit, bounds and stop/regression conditions; no automatic progression event is applied without observed authorized input |
| Restriction decisions | Approved applicable rule IDs, confirmed input-fact references and permitted adjustments/exclusions; no inferred diagnosis or medication effect |
| Evidence trace | Material decision path, rule ID/version, retrieved passage ID/source hash/locator, direct or professionally derived choice, and validation result bound to content hash/revision |

The dictionary is a bounded reviewed artifact inside existing training/knowledge
modules, not new exercise CRUD or a new technology. Each entry has stable key,
pt-BR label, approved aliases/variations, movement and muscle mappings needed by
policies, equipment constraints and lifecycle/version status. Unknown or ambiguous
exercise/variation keys cannot qualify. Name similarity alone is not identity.

Task 47 defines a versioned accounting method for each relevant policy: how sets
contribute to exercise/session/week/muscle volume, how indirect contributions are
handled, and what is excluded. Do not invent fractional muscle credits. Task 48
computes totals from dictionary mappings and actual schedule, tests multi-joint
and repeated-day cases, and records accounting-method version in the trace.

Generate pt-BR exercise tables, dose/load text and progression guidance from
validated typed fields and reviewed instruction templates. Writer-supplied prose
cannot add a second dose, load or progression instruction; prescriptive notes
must use approved instruction keys. Reject unknown/contradictory dosing content.
Legacy free-text fields remain compatible projections for existing consumers;
manual instructor content remains possible without an AI-qualified badge.

For `session_sheet`, qualify only the declared session scope. If its policy needs
weekly context, require the actual schedule/current-plan context or abstain; never
advertise a sheet as a validated whole-week plan. For `plan_revision`, normalize
and check the complete resulting schedule, including unchanged items and totals.
Progression is prescribed conditional guidance, not workout tracking or automatic
mutation of an approved plan; completed-workout RFs remain out of scope.

## 3. Input readiness and provenance

Task 45 inventories actual available fields. Task 47 produces an approved
input-readiness matrix for each proposed cohort/rule, not merely a list of desired
facts. No cohort can be enabled with an unresolved mandatory data dependency.

| Input | Authority and acquisition rule |
| --- | --- |
| Goal and experience | Completed structured onboarding; an explicit confirmed request can define this attempt's narrower goal/scope without overwriting onboarding |
| Reported restrictions, conditions and medications | Authorized structured onboarding and explicitly confirmed later reports; contradictory reports require clarification/professional review, not silent last-write-wins or AI diagnosis |
| Population/age eligibility | Existing authorized person-domain fact only if actually available and permitted; derive minimal age/range rather than sending birth date. Otherwise obtain a permitted confirmed eligibility fact or keep the cohort unsupported |
| Requested schedule, session availability and sheet scope | Explicit authenticated request/clarification, confirmed for the attempt; never infer training frequency from availability of equipment or an A/B/C label |
| Baseline load/capacity or clearance required by a policy | Documented authorized source/confirmation and valid method; if collection/authority is not approved, do not collect it or enable the dependent mode |
| Equipment and current training state | Existing equipment and training services, including operational state and exact current/draft revisions; recheck at persistence |

For each fact, specify typed representation/unit, source and authority, author/
confirmer role, observation/confirmation timestamps, policy-defined validity,
conflict resolution, permitted audience and missing/stale action. Do not invent
one universal health-information expiry. Reconfirm mutable request facts for a
new attempt; changes to restrictions, goal, schedule or referenced training state
invalidate dependent validation and cached outcomes.

Task 49 implements a minimized confirmed `input_snapshot` and snapshot hash within
the existing authenticated training clarification flow; Task 50 presents the
necessary questions/confirmation in pt-BR. A field extraction by AI is provisional
until confirmed. Do not rewrite completed onboarding or promote raw chat to
authoritative medical fact. Retain only required effective facts/references under
existing protected training-history rules, not copied raw conversations, birth
dates or administrative identity. New medical data/retention beyond approved
boundaries needs the existing DEC-18 decision before collection or enablement.

## 4. Retrieval-feasibility experiment before gate implementation

Task 47 uses the Task 46 corpus and development cases only. For each case,
reviewers identify applicable supporting passages/rules for every mandatory
dimension; then the existing hybrid retriever is evaluated under its six-passage
final-context limit. A policy-to-passage join/coverage harness is allowed here;
the production gate remains Task 48. Do not use held-out evaluation cases.

Report whether a sufficient evidence set exists in the reviewed literature,
whether eligible text was acquired/indexed, whether supporting passages were
retrieved, whether the selected six cover all required decisions, and why any
dimension failed. Record applicable-source retrieval, dimension coverage,
extraneous/inapplicable passages, ranking/deduplication errors and the smallest
known supporting set. More internal candidates may be examined within bounded
existing search conventions; no more than six final passages reach the writer.

Record corpus/case/policy versions, hardware, embedding/search time, context size,
provider calls/retry budget, end-to-end timing and storage/resource use. Set
operational budgets before operational enablement from measured target-environment constraints
and existing RNF/DEC limits; do not silently extend timeouts or invent universal
latency targets. Fix extraction/chunking/ranking errors within approved limits.
If a cohort still cannot be supported, leave it disabled and produce a concrete
decision proposal for any architectural change. Do not claim absent science when
the failure is the index, ranking or passage budget.

## 5. Draft and approval transitions

These are validation metadata conditions, not new RF-17 plan lifecycle states.
Existing sole-draft, expected-revision, role, submission, approval and immutable
history constraints always apply.

| Current condition/action | Required behavior |
| --- | --- |
| New passing AI candidate | Atomically save the sole proposal and content/input/policy/evidence trace; retain the existing client-submission gate |
| Failed generation/edit/adaptation | Discard candidate; no candidate display/submission/operations, and no saved draft/history mutation |
| Saved legacy or unvalidated AI draft | Readable and explicitly unqualified; AI reuse/submission/approval requires complete normalization and current validation, or explicit instructor manual assumption |
| Qualified draft edited by AI | New revision must pass the complete relevant gate; prior submission and qualification do not carry forward |
| Qualified draft edited manually | Save under existing instructor permissions; clear current AI qualification and unvalidated citations, preserve original AI lineage and edit/actor metadata |
| Evidence/policy/input becomes stale or revoked | Keep saved content and history; prevent qualified AI reuse/submission/approval until revalidated; surface reason and authorized manual path |
| Instructor assumes an existing saved draft manually | Explicit instructor-only action on exact revision, with recorded responsibility/reason and immutable lineage. It may adopt saved content without cosmetic edits; clear AI qualification and retain ordinary manual review/approval. A flag change or client action is insufficient |
| Manual draft approval during runtime AI outage | Existing instructor action and non-AI schema/equipment/concurrency rules apply; no AI/embedding call or implied AI qualification |
| AI adaptation of legacy/manual current plan | Normalize and validate every resulting item, schedule and affected totals against applicable current rules. If unchanged legacy content cannot qualify, reject the AI candidate and offer manual review; do not silently qualify only changed rows |
| Approval of a newly qualified revision | Recheck exact content, inputs, support and base revisions; create the next current version atomically. Never recertify or rewrite the prior immutable version |

Manual assumption applies to an already saved accessible draft, never to a
discarded candidate. UI and API preserve lineage separately from current editor/
responsibility; manual actions cannot forge an AI pass. Manual assumption is an
extension of existing instructor edit/review, not a client override or automatic
activation. Its audit reason must not unnecessarily reproduce sensitive data.

## 6. Runtime availability and startup recovery

Preserve current fail-closed startup: migrations and knowledge bootstrap must
succeed before the backend accepts requests. Do not label a failed boot as ready
or introduce a degraded-startup mode. During successful runtime, embedding,
search or writing outages reject dependent AI generation while manual training
and other independent endpoints continue to work.

Task 46's runbook must distinguish:

1. Runtime outage: return controlled AI failure; verify manual authoring and
   independent endpoints remain usable; restore the failed service normally.
2. Failed bootstrap on an existing database: keep readiness false, preserve the
   transactionally consistent prior corpus/data, diagnose provider/catalog/schema
   failure, restore service or correct/redeploy the catalog and rerun the existing
   idempotent startup. Do not delete volumes, reset clients or announce manual
   API availability before successful initialization.
3. Last-known-valid catalog recovery: use a recorded compatible catalog/deployment
   manifest only if its sources, licenses, reviews and revocations are still valid;
   never roll back safety/license revocations, blindly downgrade migrations, or
   restore expired evidence merely to make boot pass.
4. Fresh database without a valid corpus: no backend/manual API is available until
   an eligible corpus is initialized. Report this operational limitation clearly.

Task 51 exercises all four paths separately with isolated state. Guaranteeing
manual authoring before successful initialization would require a new architectural
decision; this specification does not promise or implement it.

## 7. Accountable governance and maintenance

Task 45 creates a named responsibility/approval register before final appraisals:

| Role | Authority and evidence |
| --- | --- |
| Project/release owner | Names responsible people, approves initial scope/resources and records the final scoped release decision after required sign-offs |
| Methodological reviewer | Verifies appraisal/certainty/evaluation methods, independence, reference judgments and any adopt/adapt/reassess decision |
| Qualified exercise-prescription reviewer | Approves applicability, operational ranges/conditions, restriction handling and professional evaluation expectations |
| Independent evaluator/adjudicator | Holds sealed evaluation material, records disagreements/results and ensures exposed cases are not used as independent confirmation |
| Technical/corpus maintainer | Owns acquisition/provenance, integrity, manifests, configuration, deployment/recovery and technical evaluation; cannot grant clinical approval |

Record actual identity, competence, conflict disclosures, availability, estimated
effort, approval scope, dates and artifact hashes; unassigned roles remain pending.
Roles may overlap where competence allows, but two independent assessments cannot
be supplied by the same person, and a developer exposed to held-out answers cannot
self-certify independence. No automated agent may invent reviewer sign-off.

Task 47 must consider reusing existing guideline recommendations/appraisals and
certainty summaries: record `adopt`, `adapt` or `reassess`, source/version,
question/population/currency compatibility, gaps and reviewer agreement. Reuse
does not bypass local applicability or licensing checks. Reassess only unresolved
or outdated questions instead of silently undertaking an unlimited new review.

For each released cohort, maintain an impact map from sources, policies,
dictionary/input-contract versions and model/configuration to validation/release
records. A retraction, correction, license change, review expiry, new restriction
rule or configuration change immediately invalidates affected qualification for
new/reused proposals; the responsible owner records scope, reason and reenablement
checks. Suspend only affected automation when dependencies are known; uncertain
impact cannot be assumed harmless. Approved historical plans remain unchanged.
Use existing authorized review/status surfaces to show impact, not a new messaging
service. Reenable only after updated review and scoped offline/operational checks.

## 8. Review-finding traceability

| Finding | Canonical acceptance | Owning tasks |
| --- | --- | --- |
| Actual-model evaluation optional | EXT-CA-AI-02.15 | 45/47 design; 51 mandatory execution |
| Prescription contract too open | EXT-CA-AI-02.16 | 47 dictionary/accounting; 48 schema/validation; 50 projections |
| Required input unavailable | EXT-CA-AI-02.17 | 45 inventory; 47 readiness; 49–50 confirmation/snapshot |
| Six-passage viability unmeasured | EXT-CA-AI-02.18 | 46 corpus; 47 experiment; 48 enforce measured scope |
| Evaluation designed too late | EXT-CA-AI-02.19 | 45 protocol; 47 sealing; 48–50 protected implementation; 51 execution |
| Legacy/manual transitions ambiguous | EXT-CA-AI-02.20 | 48 metadata; 49 lifecycle; 50 UX; 51 transitions |
| Availability/startup tension | EXT-CA-AI-02.21 | 46 runbook; 49 runtime isolation; 51 recovery |
| Governance not executable | EXT-CA-AI-02.22 | 45 assignments; 47 approvals; 51 release; named owners maintain |
