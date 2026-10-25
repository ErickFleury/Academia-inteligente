# Prescription rule review package — all requested goal families

**Version:** 2026-10-23-research-1. **Stage:** research extraction and technical
cross-check completed; independent methodological and exercise-professional
decisions pending. **No professionally approved rules or enabled profiles.**

The owner requested research for the other discussed goals and conversion into
real prescription rules rather than reuse of fictional test parameters.
Canonical scope is EXT-RF-AI-02, especially EXT-CA-AI-02.1/4/6/14/16–19/22.
The [domain contracts](training-prescription-domain-spec.md) and the existing
[methodological protocol](training-evidence-methodology.md) remain applicable.

The concrete review artifact is
[`training-prescription-rule-candidates.json`](training-prescription-rule-candidates.json).
It contains source locators, actual numerical findings, explicit candidate
translations, modality-specific accounting, exercise identities, required inputs,
conflicts and decisions for eleven goal families. It is deliberately a research
registry, not an approval-shaped `PolicyCatalog`: there are no invented reviewer
identities, signatures, appraisal ratings, corpus hashes or passage identifiers.
Numerical proposals are not passed off as published findings.

## 1. Research method and access record

Bounded follow-up performed on 2026-10-23 with public literature terms only.
This extends research; it is not a retrospectively prespecified systematic review,
an exhaustive search, a retraction clearance or completion of Task 45 appraisal.
No student information was sent to a search engine or literature service.

Queries included:

- `site.pmc.ncbi.nlm.nih.gov 2026 resistance training prescription muscle function hypertrophy physical performance healthy adults`
- `"Progression models in resistance training for healthy adults" progression rest endurance power`
- `"Quantity and quality of exercise" ACSM flexibility neuromotor 2011`
- `"Give it a rest" hypertrophy rest interval 2024`
- `"Optimising the Dose of Static Stretching to Improve Flexibility"`
- `"World guidelines for falls prevention" exercise progression`
- `site.cdc.gov physical activity talk test moderate intensity`
- `site.nsca.com power muscular endurance resistance training repetitions rest`
- `site.acefitness.org/resources/everyone/exercise-library bodyweight squat seated row`
- `site.nhs.uk strength-exercises balance-exercises`

Primary publication, professional-organization, author-repository and government
records were preferred. Third-party summaries were discovery leads only.
The registry records which parts were actually consulted for each source.
Repeated PubMed page fetches returned a footer only; the ACSM09 abstract was
successfully read as XML through the official NCBI E-utilities service using
PMID `19204579`. No publisher paywall was bypassed. ACSM09 publisher full text
returned 402; inaccessible chapter/table detail is not reconstructed from memory.
ACSM11 uses its authors' institutional abstract. Static-stretching and sport
reviews use publisher abstracts and retain full-methods/appraisal gaps.
The ACSM26 indexed primary discussion was inspected for effort and uncertainty,
in addition to the official summary previously consulted. REST24 and FALLS22
publisher full-text sections were consulted, but that is not a completed appraisal.

## 2. Coverage and proposed decision branches

Every profile references selection, volume, intensity, frequency, rest,
progression, restrictions and accounting. A filled reference list is not proof
that the dimension is operationally resolved. Every profile remains **partial /
awaiting review**, including the previously researched goals.

| Goal | Concrete research/decision branch | What still needs a scoped decision |
| --- | --- | --- |
| Strength | `STRENGTH_DOSE`, `NOVICE_LOADING`, `STRENGTH_REST`, `RESISTANCE_EFFORT`, `LOAD_PROGRESSION`; source paired-program alternative | Separate novice and experienced applicability, working load/effort, standalone novice rest and equipment increments |
| Hypertrophy | Weekly volume reference, historical loading emphasis, contemporary effort example and `HYPERTROPHY_REST`; paired-program alternative | Initial/session/week volume bounds, direct/indirect counting, effort and rest conflict resolution |
| Weight/fat loss | Existing domain section 5.1, aerobic and resistance components with explicit combined accounting | Complete combined policy and recovery; no individual body-weight prediction |
| Cardiorespiratory fitness | Adult health reference and talk-test intensity; bounded proposed starting/progression block | Select actual mode and response measure; review initial dose and progression before claiming adaptation-specific coverage |
| Local muscular endurance | Historical relative-load/high-repetition branch and a distinct published circuit example | Select one branch, finite dose/effort/rest, current applicability and endurance-specific progression |
| Power | Relative-load/fast-intent finding, historical set/rest structure, actual medicine-ball exercise entry | Exercise-specific speed, observed competence, supervision, stopping and progression; ball mass is not percent 1RM |
| Mobility/flexibility | General flexibility dose and a clearly labeled hold/rest decomposition; newer static-stretching synthesis retained separately | Named joint, active versus passive goal, actual stretches, intensity/range, side convention and training-session placement |
| Balance | Actual supported balance tasks; a separate older-adult fall-prevention branch | Baseline, environment, supervision, success criterion and challenge progression |
| Functional autonomy | Actual chair-rise/mini-squat entries plus proposed task/rest/progression structure | Named everyday task, current capacity, support needs and task-specific outcome |
| General health | Coherent combination of selected aerobic, resistance and relevant balance components | Select components and distribute total workload; a health target is not a compulsory starting dose |
| Sport performance | Actual endurance-athlete intensity-distribution review and explicit sport/event requirements | A complete event-specific protocol; no universal prescription for an unspecified sport |

Do not combine all linked numerical ranges by intersection or concatenation.
For example, a beginner repetition-maximum reference, a contemporary strength
enhancement finding and a paired program are different branches. The reviewer
selects/adapts a coherent branch for actual inputs; the AI cannot assemble a new
protocol by taking convenient numbers from each.

## 3. Source findings versus local translation

The registry distinguishes five substantive record types:

- `direct_finding` / `direct_recommendation`: a statement located in the inspected
  primary record. This still needs methodological and applicability assessment.
- `historical_direct_recommendation`: an older guideline retained as evidence,
  requiring currency assessment against contemporary findings.
- `published_professional_example`: an actual exercise/program entry published
  by the professional organization. It is not an experimentally established
  optimal dose or a policy for every person.
- `proposed_professional_translation`: an explicit candidate decision. The local
  rest windows, finite starting doses, hold decomposition and increments bearing
  this label need acceptance, amendment or rejection by the qualified reviewer.
  No person has approved them yet.
- `project_requirement` / `proposed_accounting_definition`: software and product
  behavior, not claims of physiological benefit or independent clinical evidence.

The source's recommendation strength, if reported, is recorded as that source's
judgment. It does not become a locally completed GRADE assessment. Global certainty
is `not_assessed`; no reviewer or adjudicator has signed these records.

## 4. Conflicts and applicability decisions

1. **Rest:** historical hypertrophy guidance, REST24 and the ACSM26 uncertainty
   statement do not support a universal short-rest requirement. The proposed
   standalone rest window is a decision to review, not an observed optimum.
2. **RM, repetitions and effort:** RM denotes capacity under a specific load;
   working repetitions and estimated RIR are different quantities. A simultaneous
   prescription must be feasible. RIR is not an automatically measured value,
   and its calibration requires an approved input/observation method.
3. **Progression:** the old RM-dependent load rule cannot be applied on a calendar,
   after unverified self-report, or to another modality. Its observation count,
   rounding and regression policy remain local decisions. No automatic saved-plan
   mutation is authorized. Retaining a tolerated dose is not automatically failure.
4. **Supersets/circuits:** rest after a pair, after an exercise, between sets and
   between rounds are distinct. The present isolated contract has only limited
   representation of those relations. Do not flatten a source circuit into a
   standalone-set prescription and claim equivalence.
5. **Frequency:** general health, a goal-specific enhancement association and a
   fall-prevention program have different outcomes/populations. A source number
   for one is not automatically the optimum for another.
6. **Mobility:** a static flexibility outcome does not establish active control,
   sport technique or rehabilitation. Review the actual joint and outcome rather
   than relabeling all mobility requests as stretching.
7. **Sport:** SPORT25 concerns endurance-trained athletes. It cannot supply a
   universal split, interval dose or training program for all sports/experience
   levels. Clarify the event and obtain the matching protocol.
8. **Health context:** none of these general rules clears every medication,
   complaint, injury, age/life stage or combination. This is an applicability gap,
   not a reason to exclude those students from the system.

## 5. Exercise identity and accounting review

Six concrete identity candidates have separate keys, original pt-BR labels,
equipment and exact source pages in the registry. A chair rise, supported squat
and unloaded squat are not aliases of a loaded squat. No copied execution text,
translation, image or numerical muscle fraction is imported. The set is a starting
review queue, not a complete exercise library or an adequate complete-body program.
The NSCA example supplies additional actual exercise choices to review as a
protocol branch; they do not silently become approved dictionary entries.

Accounting rules explicitly separate resistance sets/load, aerobic segment time
and intensity, stretching duration per side, balance attempts/support and functional
task repetitions. For each formula the registry states prerequisites and unknown
behavior. Candidate public-health aerobic equivalence must not be mistaken for
equivalent sport-training stimulus. Units cannot be converted merely to satisfy
the existing resistance-only candidate shape.

## 6. Promotion into executable policies and real evaluation

For each selected branch, reviewers must record:

1. Source currency and actual full methods/passages needed for its decisions;
   adopt/adapt/reassess, outcome-specific certainty and limitations using the
   existing methodology, plus independent judgments/conflicts/adjudication.
2. Actual population, experience and restriction combinations; benefits/harms,
   burdens, preferences and feasible alternatives; exact exercise variants.
3. Accepted finite dose bounds, units, recovery, observable progression/regression
   triggers, source-versus-translation rationale, input authority/validity and
   missing/conflict behavior. A `decision_needed` field is unresolved work.
4. Reviewer identities, competence, dated artifact-bound approval, scope and
   validity deadline. A functional instructor role does not create these records.
5. Allowed source artifacts, extraction quality, immutable hashes and retrieved
   passage IDs. A metadata-only source cannot become runtime evidence by copying
   a DOI into `EvidenceReference`. Reuse permission and scientific approval are
   separate decisions.
6. Required typed representation/validation for aerobic, timed/side-based,
   paired/circuit or other accepted modes before operational use. Extend only the
   existing architecture; no new technology or dependency is proposed here.
7. Reviewed feasibility within the existing passage budget; actual deployment
   positive and rejection cases, sealed independent evaluation and release scope.

The existing synthetic tests remain useful for validator/lifecycle mechanics,
but do not validate the scientific values here. Do not replace their fixtures
with this registry and call it professional approval. Real policy tests must
check approved applicability and documented boundary/transition decisions, and
must be separate from independently sealed evaluation answers.

The present change does not modify `prescription-policies.json`, the empty
approved-dictionary queue, provider prompts, runtime catalog, UI, migrations or
release flags. It supplies concrete extraction/decision records for the pending
Task 47 review. Scientific approval, reusable runtime support and the necessary
modality integration remain incomplete; none is concealed as a successful test.

## 7. Verification of this documentation change

Standard-library checks passed for JSON parsing, unique source/rule/goal IDs,
all 17 source records and 37 rule links, all eleven profiles' seven dimensions,
nonnegative/coherent numeric bounds and explicit units, six exercise identity
references, UTF-8 and local document links. The packaged executable policy and
dictionary were checked to remain pending with no decisions/approvals/exercises.
Scoped `git diff --check` passed. No application behavior was changed, so no
backend/frontend behavioral test suite or live-model evaluation was executed.
These checks establish artifact consistency, not prescription efficacy or safety.
