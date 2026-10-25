# Training Evidence Methodological Protocol

**Protocol version:** 1.2 — 2026-10-23. **Status:** bounded discovery protocol
prespecified before this run's substantive source selection. Independent human
appraisals, certainty ratings, professional decisions and evaluation results
remain pending. This snapshot does not claim final methodological approval.

`docs/requirements.md`, EXT-RF-AI-02, remains canonical. This protocol supports
EXT-CA-AI-02.14 and does not approve prescription ranges or certify any cohort.
Task 45 finalizes a dated protocol snapshot before substantive source selection;
subsequent changes must be justified rather than fitted to favorable results.
The [execution contracts](training-prescription-execution-contracts.md) define
the typed/input schemas, early feasibility and evaluation gates, lifecycle matrix,
startup recovery and named governance supporting EXT-CA-AI-02.15–22.

## 1. Keep four decisions separate

| Decision | Required record | What it cannot establish |
| --- | --- | --- |
| Scientific inclusion | Relevant question, design-appropriate appraisal, applicability and evidence limitations | Permission to ingest or an individually effective prescription |
| Download/index eligibility | Artifact-level allowed license, provenance, extraction fidelity and review status | Scientific strength or professional prescription approval |
| Prescription eligibility | Approved applicable policy, required inputs, supported decisions and validated parameters | Clinical effectiveness for an individual |
| Product release | Prespecified tests, held-out evaluation, approved thresholds and measured scope | Zero real-world risk or universal coverage |

The six-passage limit, existing embedding dimensions and license allowlist are
project constraints. Mandatory abstention outside the supported scope and zero
observed critical test failures are product release policies. Do not present
these numbers/policies as findings from exercise science. If an architectural
limit causes insufficient retrieval despite available evidence, record a technical
coverage gap for evaluation; do not relabel the literature as absent.

## 2. Prespecify questions and search

For each goal family and material prescription dimension, record a PICO question:
population (experience, relevant age/health scope and restrictions), intervention
(exercise type and prescription variables), comparator, outcomes and follow-up.
Include adverse effects, feasibility/adherence and restrictions where relevant,
not only strength or hypertrophy outcomes. Preserve unknown client inputs.

Before screening, record databases/services, exact search strings, dates, language
and date limits with reasons, eligible designs, outcomes and exclusions, update
strategy, reviewers and amendment log. Use the same rules for favorable, null
and unfavorable findings. Do not use journal prestige, citation count, recency
alone or convenient open access as a scientific inclusion rule.

Search relevant guidelines and syntheses first for efficiency, then seek direct
studies or supplements for unresolved questions and updates. This search order
does not give every review automatic precedence over a better applicable study.
Record duplicate publications and overlapping primary studies so one population
is not counted as several independent confirmations.

Discover important sources even if reuse rights are unavailable. Keep these as
metadata-only scientific gaps; excluded text cannot support runtime generation.
Record unavailable full text separately from a negative scientific appraisal.
If a bounded review cannot establish completeness, describe that limit and the
search coverage rather than calling the review exhaustive.

Use [PRISMA 2020](https://www.prisma-statement.org/prisma-2020-statement) to make
the selection/reporting process transparent where applicable. Reporting-checklist
completion is not a methodological-quality rating. A project-specific adaptation
must be identified as such rather than claimed to be a full systematic review.

## 3. Appraise the document and the body of evidence

| Material | Method and recorded output |
| --- | --- |
| Practice guideline | [AGREE II](https://www.agreetrust.org/resource-centre/agree-ii/): record domain judgments, rigor, applicability, editorial independence and relevant recommendations; follow the instrument's instructions. |
| Eligible intervention systematic review | [AMSTAR 2 original methods paper](https://www.bmj.com/content/358/bmj.j4008): document critical/noncritical weaknesses and confidence. Do not derive an overall numeric score by adding items. |
| Randomized-trial result | [RoB 2](https://www.riskofbias.info/welcome/rob-2-0-tool): select the design-appropriate version and assess bias for the result relevant to the question. |
| Other design, overview or supplementary dataset | Choose and justify an appropriate appraisal method before use. Do not force a randomized-trial instrument onto a different design. A dataset inherits no automatic scientific reliability from its download portal. |
| Body of evidence for an outcome | [GRADE/Core GRADE](https://www.bmj.com/content/389/bmj-2024-081903): record certainty and reasons involving bias, inconsistency, indirectness, imprecision and publication bias. Certainty is not a single label assigned to every conclusion in a paper. |

Record instrument title/version, reviewer judgments, source locators and justified
departures from instructions. Preserve domain results; do not combine unlike
instruments, license status or similarity scores into a universal quality score.
For reused published appraisals, record their question/version and verify whether
they apply to this project's population, outcomes and newer evidence.
Task 47 records an explicit adopt/adapt/reassess decision with applicability,
currency and local gaps, rather than automatically repeating a complete review.

The project requires two independent human assessments for final inclusion and
material appraisal decisions, with complementary methodological and exercise-
prescription competence and documented conflicts of interest. This is a project
quality-control policy, not an exercise-science threshold. Follow a tool's own
appraiser instructions when stricter. Resolve disagreement with a recorded
adjudication; unavailable reviewers leave final decisions pending. Discovery,
license checking and provisional extraction can continue without pretending the
required assessments have occurred. AI can assist extraction, not sign approval.
Task 45 must name those people and their competencies, availability, conflicts,
resource plan and adjudicator in the responsibility register. A role title is
not a completed approval; Task 51 needs actual scoped release sign-offs.

Methods references are consultation sources, not automatic embedding candidates.
Check their own instrument/form/content reuse conditions before copying tools
into code or the corpus; this protocol imports no instrument text or new license.

## 4. Turn findings into explicit prescription decisions

Task 47 must create an evidence-to-decision record for each material rule using
a prespecified framework. [NHMRC's evidence-to-decision guidance](https://www.nhmrc.gov.au/guidelinesforguidelines/develop/evidence-decision)
describes a transparent passage from evidence to recommendations that includes
professional judgments rather than treating a review as a prescription itself.

Each project record must contain:

- the PICO question, applicable cohort and required client inputs;
- outcome-specific findings, certainty, limitations and exact source versions;
- relevance to goal, experience, combined restrictions and actual gym context;
- benefits, harms, burdens, preferences, feasibility and equipment constraints;
- the directly reported finding, separately from professional interpretation;
- proposed bounds/units, selection and calculation rules, missing-input behavior,
  alternatives, conflicts and any conditions for use;
- recommendation/decision rationale, reviewer identities, conflicts of interest,
  approval scope/date/deadline and policy version.

The evidence need not prescribe every exact numeric choice literally. A qualified
professional may approve a conservative operational rule within supported bounds,
with the derivation and uncertainty visible. Never transform an aggregate mean,
threshold category or population-level dose association into an unexplained
individual optimum or exact kg load. No diagnosis may be inferred from symptoms.

Lower certainty is not automatically evidence of harm or grounds for universal
rejection. A conditional recommendation can be enabled only when its applicability,
limits and benefit/harm judgment are explicitly approved and computable. Missing
coverage cannot be disguised as conditional support. If conflicting guidance
remains unresolved or conditions cannot be checked, abstain for that request.

## 5. Explain why generation did not produce a candidate

Task 48 finalizes machine-readable codes; Tasks 49–50 preserve the distinctions:

| Outcome category | Trigger | Permitted next step and explanation |
| --- | --- | --- |
| Documented restriction conflict | Candidate violates an applicable reviewed restriction rule | Discard candidate; identify the prescription conflict within authorized context and offer professional review. Do not infer a new diagnosis or prohibit all exercise. |
| Missing or ambiguous required input | A rule needs information not reliably available | Ask a specific question through the existing authorized flow or defer. No guessing or candidate publication. |
| Insufficient applicable support | Unsupported cohort/dimension, unapproved policy, unresolved evidence conflict, expired support or unverified conditions | Abstain and offer professional/manual assessment. Explain lack of support for automated prescription, not proven harm. |
| Technical unavailability | Acquisition/search/embedding/writer fails or bounded processing expires | Controlled retry/manual path; no claim that the client is unsuitable or literature is absent. |

All categories prevent publishing the failed candidate and preserve saved state.
Clarification or recovery may start a new validated attempt. Invalid provenance,
out-of-policy parameters and stale revisions remain explicit subreasons; do not
collapse them into model confidence or a vague safety score. Only qualified
instructors may use the existing manual authoring workflow.

## 6. Prespecify independent evaluation

Task 45 starts evaluation design; Task 47 seals reference cases/answers, outcome
definitions, reviewer rubric, error severity/costs, sampling rationale, operational
repeat/budget plan and release thresholds before Task 48 gate implementation.
Task 51 executes that protocol with the evaluated policy/validator versions.
Separate development/calibration
cases from held-out evaluation; reusing a tuned test set is not independent
confirmation. Expected judgments are professionally/methodologically reviewed,
not generated by the writer being evaluated.
Keep sealed held-out cases/answers outside implementation prompts, developer
fixtures and runtime corpus under independent custody. Exposure followed by
tuning requires a new independently sealed set before a release claim.

Report each outcome category separately, with case counts by cohort and relevant
restriction interactions. Measure unsupported acceptance, supported acceptance,
false rejection, justified abstention and inappropriate reason assignment. Include
source/claim applicability, extraction fidelity, retrieval coverage and actual
parameter validation; merely counting references is insufficient.

Use denominators and uncertainty estimates appropriate to the sampling design,
including limitations of small synthetic suites. Label purposive fixtures as
scenario coverage rather than population prevalence/risk estimates. Mandatory
operational evaluation uses the actual deployment configuration and prespecified
repeated runs, records every attempt/failure and remains separate from offline
CI. Unavailable operational access or missing results leaves scope disabled;
offline adapter tests alone do not establish live-model reliability.

Zero observed critical failures remains a project release gate for the critical
suite, not proof of zero population risk. Supported positive controls must also
pass. Additional acceptance/false-rejection/sample-size limits require recorded
professional/methodological approval before evaluation; no arbitrary percentage
is supplied here. Unmeasured cohorts remain unsupported.

## 7. Required artifacts and handoffs

| Owner | Artifact/evidence |
| --- | --- |
| Task 45 | Dated protocol, source/appraisal/criterion records, input inventory, named responsibility/resource register and early evaluation design; important non-ingestible sources remain gaps |
| Task 46 | Independently verified acquisition eligibility, extraction fidelity, attribution/provenance and actual indexing evidence; no scientific pass inferred from license |
| Task 47 | Per-rule decisions, adopt/adapt/reassess records, typed/dictionary/input contracts, six-passage feasibility report and preimplementation evaluation seal |
| Tasks 48–50 | Typed/backend-owned eligibility, confirmed inputs, explicit lifecycle transitions and reason categories, protected held-out custody and pt-BR projections |
| Task 51 | Execute sealed offline and mandatory actual-deployment evaluation, separate runtime/startup recovery, per-cohort results and named scoped release sign-offs |

Maintain a criterion register recording `criterion_id`, criterion kind
(`scientific`, `technical`, `product_policy`), question/scope, primary methodological
or evidence reference, judgment/threshold rationale, reviewer/version, known
limitations and planned verification. These are proposed documentation fields,
not a new API or framework dependency. Referencing this protocol does not mark
any review or experiment complete.

## 8. Task 45 snapshot — 2026-10-23, before selection

This is an AI-assisted bounded scoping exercise, not a systematic review. No
human reviewers are assigned in the available project records; do not fabricate
their identities. Discovery may proceed, but final inclusion, appraisal and
certainty judgments require the independent assessments in section 3.

| PICO | Population | Intervention/comparator | Outcomes and follow-up |
| --- | --- | --- | --- |
| P1 strength | Adults without reported restrictions; separate all four recorded experience levels | Resistance exercise selection, load, sets and frequency versus other doses/no exercise | Strength, adherence and adverse events at each reported intervention endpoint; no imposed duration cutoff |
| P2 hypertrophy | Same population, with training status extracted rather than inferred | Resistance volume/load/frequency, rest and progression versus alternate prescriptions | Muscle size, adherence and adverse events at reported endpoints |
| P3 general fitness | Same population; no assumption that unknown age means adult | Resistance programs versus no program/other program | Physical function, feasibility and harms; distinguish strength from general health claims |
| P4 restrictions | Separately diagnosed knee OA, chronic primary low-back pain, rotator-cuff-related pain and tendinopathy; unknown or combined restrictions kept separate | Condition-specific exercise adjustments versus comparator programs/usual care | Pain, function, adverse events and adherence at each reported follow-up; no diagnosis from symptoms |

Proposed first slice for feasibility only: adult, `none`/`beginner`, explicit
strength goal, no reported limitations, conditions or medication use, confirmed
schedule and equipment. Adult eligibility and schedule are unresolved inputs;
this is not an enabled cohort or a claim that screening proves health.
Hypertrophy and general fitness are proposed goal families, not existing enums.
Weight loss, sport performance, rehabilitation and unknown/mixed goals are gap
strata until separately reviewed. No automatic free-text mapping is approved.

Search plan: consult the supplied PubMed/PMC and publisher starting links;
then run the following literal web-search queries using the available web
search service, recording returned candidates, not claiming native database
search counts. Search English/Portuguese records, all publication dates through
the run date; English/Portuguese readable text is a resource limit. No humans-only
search filter that could conceal mixed samples; screen population manually.

1. `site:pubmed.ncbi.nlm.nih.gov resistance training prescription strength hypertrophy systematic review load sets frequency`
2. `site:pubmed.ncbi.nlm.nih.gov resistance training rest interval progression randomized trial systematic review`
3. `site:pubmed.ncbi.nlm.nih.gov exercise resistance knee osteoarthritis low back shoulder tendinopathy systematic review`
4. `resistance training prescription systematic review supplementary data dataset Currier 2023`

Bound: inspect the two named anchors, all 14 local catalog records, and up to
two additional nonduplicate scholarly candidates per query in returned order
that materially address a gap. Prioritize synthesis/guidelines; examine linked
trials/supplements for unresolved dimensions, with any unexamined references
reported as search limitations. Do not replace inaccessible studies with an
assumed negative appraisal. Deduplicate by DOI/PMID; flag review overlap before
any synthesis. Include guidelines, intervention reviews and relevant trials;
retain textbooks/media only as background, not prescription-dose evidence.
Exclude nonhuman studies, unrelated outcomes and participant-level data import.

Methods to consult: AGREE II 2017 user manual/23-item instrument for guidelines;
AMSTAR 2 (2017, 16 items) for intervention reviews; RoB 2 dated 22 August 2019
for individually randomized parallel-trial results (select another official
variant if appropriate); Core GRADE 2025 series for outcome-specific certainty.
Overview/scoping-review records receive descriptive design/coverage/overlap
extraction only in this run; a methodological reviewer must approve a suitable
formal appraisal before their findings become policy. No invented total score.
Two independent humans record domains and locators separately, then adjudicate
with the independent third reviewer; AI notes are provisional extraction only.
GRADE bodies are defined by PICO/outcome/timepoint, with overlap removed and
bias, inconsistency, indirectness, imprecision and publication bias justified.
Unavailable instruments/full text/domain evidence leave the relevant judgment
`not_assessed`, never a pass. Published ratings remain attributed, not adopted.

Search refresh: rerun before Task 47 approval and after material corrections,
retractions or scope changes. This bounded run cannot certify absence of
retractions. Record corrections/conflict statements when accessible; missing
checks remain pending. The source-review report contains screening, appraisal,
criterion, input, governance and evaluation registers. No held-out answers are
created in the repository. Task 47 must seal an independently owned plan first.

Amendment log: 1.1 (2026-10-22) was a specification; 1.2 (2026-10-23) adds
prespecified PICO, search/resource limits and explicit missing-review handling
before selection. Subsequent deviations must be dated in the source-review
search log with reason, impact and reviewer status; none is silently backdated.
