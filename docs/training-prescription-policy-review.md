# Task 47 policy review package — draft 1

2026-10-23. Canonical EXT-RF-AI-02 remains unchanged. **Zero approved policies,
zero approved dictionary entries, zero newly enabled cohorts.** This is preparatory
schema/review work, not completion of Task 47 or a production prescription gate.

**Owner governance clarification — 2026-10-24:** all active Instructor profiles
are authorized for methodological/professional review and sealed-evaluation
custody. Canonical EXT-CA-AI-02.22 records this functional authorization. It does
not identify which instructors have actually completed the independent reviews
or provide their judgments, artifact-bound approvals or protected evaluation seal.
The historical role-assignment discussion below precedes this clarification.

**Development follow-up:** the [approved sequencing exception](training-prescription-development-amendment.md)
now permits isolated Tasks 48–50 work before those operational prerequisites.
Typed validation, accounting, owned-onboarding snapshots, lifecycle integration
and reusable UI are described in the [development report](tasks/48-50-isolated-prescription-development-report.md).
The original prerequisite discussion below now applies to operational enablement;
it does not prohibit the explicitly approved isolated development.

The later [domain contracts](training-prescription-domain-spec.md) consolidate
the owner's six contract decisions and researched references. The initial slice
below remains a feasibility proposal, not a restriction of the product audience.
Students reporting medication use, injuries or complaints are not categorically
excluded; applicable support and all existing qualification gates still apply.

**All-goal research follow-up — 2026-10-23:** the
[concrete rule review package](training-prescription-rule-review.md) and
[structured research registry](training-prescription-rule-candidates.json) now
supply real source findings, published professional examples and explicitly
proposed operational choices for eleven goal families. This is distinct from
the still-pending executable policy artifact described below: no corpus hashes,
independent appraisal or human approval were invented to populate it. Use this
package for the next actual adopt/adapt/reassess and applicability decisions;
synthetic test parameters remain mechanics fixtures, not prescription evidence.

## Responsibility and prerequisite decision

The user assigned the **instructor profile** to all initial responsibilities on
2026-10-23, and confirmed no policies, reviewers or evaluation seals already exist.
Record the functional assignment for project/release, methods, prescription,
evaluation/adjudication and technical maintenance; no individual name, competence,
conflicts, availability or signed judgment was provided. An application role is
not a completed appraisal or an independent custodian. A single instructor cannot
satisfy the current requirement for two independent human assessments and an
independently protected evaluation set. No approval, reviewer identity or seal is
invented. This document does not change that requirement. Task 48 implementation
and Tasks 49–51 therefore retain their prerequisite gate.

## Implemented draft contracts

- `backend/app/modules/training/prescription_policy.py`: evidence references bind
  source/passage/artifact hashes, locators, appraisal and outcome certainty;
  decisions distinguish findings from professional interpretation and
  adopt/adapt/reassess, benefits/harms, feasibility, alternatives and conditions.
- Policy records distinguish pending/approved/revoked, all four existing
  experience values, exact goal mappings, population and restriction interactions.
  An approval-shaped record requires all seven dimensions, separate independent
  methodological/professional records, current review deadline, assessed certainty,
  dictionary/accounting versions and approved required-input authority. Structural
  validation cannot verify a signer's competence, signatures or underlying science.
- Parameter bounds declare units/methods and dependencies. Fractional counts,
  nonfinite/inverted/negative ranges and missing kg/percent-1RM dependencies reject.
  These are representation checks, not supplied clinical ranges.
- Dictionary records reject ambiguous aliases and duplicate keys. No real exercise
  key, muscle contribution fraction, volume method or progression threshold is
  invented. The typed candidate/projection contract is now implemented only in
  isolated development; see the [development report](tasks/48-50-isolated-prescription-development-report.md).
- `prescription-policies.json` contains one **pending** adult-strength initial
  slice (`none`/`beginner`) with no goal mappings, decisions, numerical bounds,
  approvals or exercises. No generation service imports this artifact/module.

## Concrete evidence-to-decision queue

The acquired S4 passage is `lyristakis-strength-2026-dosage`; its artifact,
selection and embedding hashes are in the [Task 46 report](tasks/46-training-evidence-ingestion-report.md)
and public manifests. It retains Conclusions, Eligibility and Limitations.
Task 45 A1/A2/B1/B5 appraisals remain unassessed. No published certainty rating
is adopted by this package.

| Dimension | Available finding/provenance | Pending professional decision and gap |
| --- | --- | --- |
| Selection | S4 limits outcomes to particular muscle groups; conclusions/limitations explicitly restrict generalization | Approve bounded exercise identity/variation and actual-gym dictionary; no universal selection rule follows |
| Volume | S4 reports composite dosage and worked population-level examples | Assess bias/certainty, then approve any derivation, accounting units and session/week/muscle constraints; no individual optimum or fractional muscle credits supplied |
| Intensity | S4 examples report relative intensity under study assumptions | Establish whether relative guidance is applicable and which measured input/method is required; no inferred 1RM or kg |
| Frequency | S4 examples combine frequency with program duration and dose | Approve an actual seven-day schedule/recovery rule and input authority; day labels alone are insufficient |
| Progression | S4 does not establish an approved operational progression policy | Retain gap; review other eligible evidence, observable triggers, actions, limits and regression rules before approving |
| Rest | No acquired complete applicable rest policy | Retain Task 45 S5/S6 rights/appraisal gaps; no arbitrary rest bound |
| Restrictions | S4 eligibility excludes current diagnosed medical/musculoskeletal conditions; limitations constrain extrapolation | Do not translate symptoms into diagnoses or claim coverage of combined restrictions; approve interaction rules from applicable reviewed evidence |

For each eventual rule, reviewers must complete `EvidenceDecision`, source-version
currency/adopt-adapt-reassess rationale, separate judgments/adjudication and
approval scope/deadline. Permission to ingest and a successful retrieval are not
scientific or prescription approval. Lower certainty is not automatically harmful;
conditional use needs an explicit bounded benefit/harm decision.

## Input-readiness matrix for proposed first slice

**Owner decision — 2026-10-23:** the student's completed onboarding is the
authoritative source for student input data. Consume only the authenticated
student's authorized structured record, using the existing shared completion
validation. Available fields are training goal, the four existing experience
levels, height, weight, and self-reported limitations/complaints, medication use
and health conditions with their conditional details.

This selects the source of existing student facts; it does not approve every
field as necessary for every rule, authorize additional collection, or certify
the proposed adult-strength cohort. Minimize each attempt to the facts its
reviewed policy actually requires. Age/adult eligibility, a confirmed seven-day
schedule, measured load/capacity and clearance are not established by this
onboarding. Dependent rules remain pending or unsupported until their missing
inputs and authority are resolved; no values may be inferred from height,
weight, names, equipment or an AI response. Existing request-scope and equipment/
revision inputs remain separate consumed boundaries. The owner has not specified
that onboarding replaces these operational inputs or prohibited the already
authorized clarification flow. No onboarding/runtime change is made here.

| Input | Existing authority / confirmation and time | Pending validity, permitted audience and missing/conflict action |
| --- | --- | --- |
| Goal/experience | Completed own onboarding; explicit attempt request can narrow goal without modifying onboarding; only record-wide timestamps exist | Approve exact mappings and request confirmation/validity; owner/instructor with functional need; clarify unknown/mixed goals |
| Restrictions/conditions/medications | Completed own onboarding, self-report; later chat extraction is provisional | Approve effective-fact reconciliation/time validity; owner/instructor only; conflicting reports require clarification/professional review, no diagnosis or silent overwrite |
| Adult eligibility | No authoritative age/birth-date field exists in inspected schema | Minimal permitted eligibility confirmation and retention remain unapproved; missing input prevents slice enablement |
| Schedule/session scope | Existing authenticated request and A–G parser; no confirmed typed seven-day schedule | Approve attempt confirmation, exact schedule/current-state reference and missing-context action; no inferred weekly completeness |
| Load baseline/clearance/progression observation | No approved authoritative measurement/clearance/workout-observation contract | Keep dependent modes unsupported; instructor must define permissible collection/method/validity before use; no new medical field collected |
| Equipment and plan revisions | Existing operational equipment service and exact saved current/draft revisions | Recheck at persistence; policy must define mapping and concurrency/input invalidation; no live availability inference |

`InputReadiness` defines representation, source, authority, confirmer role,
timestamps, policy-specific validity, audience and missing/conflict behavior.
No new client fact collection, universal health expiry or completed-onboarding
rewrite is implemented. The eventual minimized snapshot and UI belong to 49–50.

## Development retrieval probe and remaining design exit

The real Task 46 PostgreSQL/BGE-M3 probe retrieved S4 within six passages; see
`docs/tasks/46-training-evidence-development-retrieval.json`. It is a technical
smoke check with **zero reviewed development cases** and dimension coverage
`not_assessed`. Other retrieved general/condition-specific passages do not prove
applicability. This does not satisfy EXT-CA-AI-02.18. No writer is called.

Before operational enablement: identify/qualify separate reviewers and independent custody;
complete applicable appraisal/EtD records, dictionary/accounting/input contracts;
approve bounded positive/negative development references; measure all mandatory
dimensions under six passages and operational budgets; seal independent cases,
answers, thresholds, repeats, costs and hashes outside this repository. Task 45's
evaluation draft is the starting point, not a seal. No held-out answers were
created/read and no release/configuration is approved. These are prerequisites,
not tasks that synthetic fixtures or one instructor-role designation can certify.
