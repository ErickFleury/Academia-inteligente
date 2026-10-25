# Training Evidence Source Review — Task 45

**Governance update — 2026-10-24:** the owner authorizes every active Instructor
profile for methodological/professional review and sealed-evaluation custody.
See canonical EXT-CA-AI-02.22. This authorizes the functions without creating
completed reviews, naming signers or sealing implementer-visible material.
The source/appraisal snapshot below retains its original date and judgments.

**Review version:** 1.1, 2026-10-23. **Status:** bounded discovery delivered;
final appraisal, named human governance and professional approval incomplete.
No cohort is qualified by this report. No corpus/runtime changes were made.

Canonical scope: EXT-RF-AI-02, EXT-CA-AI-02.1–2/14, with design handoffs for
.15/17/19/22; RF-15/18/19 are consumed boundaries. Follow RN-11–15/19/23/29–31,
RNF04/06, DEC-07/08/15/18 and EXT-DEC-AI-02. This is not an exhaustive review,
a completed systematic review, or evidence of reliable individual personalization.

## 1. Protocol and reproducibility

[Protocol 1.2](training-evidence-methodology.md#8-task-45-snapshot--2026-10-23-before-selection)
was saved before substantive selection in this run. Its byte-level SHA-256 is
`90edfc30e114ab101fd194f2df8b97010dfb1d969b4a451b6a888c30943ee1ec`.
P1–P4, eligible designs, screening limits and reviewer handling are fixed there.
The search operator/extractor was Codex (AI); no independent human screening
or sign-off occurred. No real client records, queries or health facts were read
or sent to search services. Only public literature terms and local code/schema
were inspected. No participant-level dataset was imported.

All searches and source checks below occurred on **2026-10-23** using the
available web search/open service. These are web searches constrained to public
PubMed records, not direct PubMed/Embase/SPORTDiscus systematic searches.
Results are ranked, mutable and not a complete database export; a rerun may
change order. Record IDs below make the actual selection reproducible even
when rankings change. No database-wide hit totals or PRISMA flow totals are
claimed. Initial combined execution was repeated individually to resolve which
query supplied each candidate; these repeats are not independent evidence.

| Search | Exact query | Selection and deduplication |
| --- | --- | --- |
| Q1 | `site:pubmed.ncbi.nlm.nih.gov resistance training prescription strength hypertrophy systematic review load sets frequency` | Anchors S1/S2 returned first; next two nonduplicate candidates S3/S4 screened. |
| Q2 | `site:pubmed.ncbi.nlm.nih.gov resistance training rest interval progression randomized trial systematic review` | S5, duplicate S2, then S6; two new records screened. |
| Q3 | `site:pubmed.ncbi.nlm.nih.gov exercise resistance knee osteoarthritis low back shoulder tendinopathy systematic review` | S7/S8 screened; S8 direct record failed to render adequately. |
| Q4 | `resistance training prescription systematic review supplementary data dataset Currier 2023` | S1 publisher/PMC/PDF mirrors deduplicated; S2 duplicate. Located S1 supplement; third-party copies and social summaries excluded as acquisition routes. No independent reusable raw dataset verified. |

The two overview anchors were opened directly before Q1–Q4. Fourteen seed
records were audited locally. The resulting bounded bibliographic register has
**22 unique records: 14 seed + 8 newly screened**, with supplements tracked as
separate artifacts, not independent studies. No mass full-text acquisition.
Incidental results outside the two-new-record/query bound remain unscreened:
PMIDs 35873210, 41343037, 41951916, 35291645, 41549493, 37774094 and 40320557.
Their presence prevents claiming the latest dose/rest literature was exhausted.
No source was rejected because its findings were null or unfavorable.

Rights/instrument follow-ups used exact-title/identifier queries, including
`"41843416" "Creative Commons"`, `"28933024" authors rest interval systematic review`,
`"AMSTAR 2" official checklist critical domains`, `"Core GRADE 1" "081903" BMJ`,
`"42038849" resistance systematic review`, and
`"The influence of resistance exercise training prescription variables" authors 2023`.
Identifier-only site searches also returned unrelated results; those were not
screened as evidence. Publisher/PMC copyright sections, not search snippets
about free access, determine permission. No postselection PICO change occurred.
Amendment A1: direct-record rendering failures prompted these identity/rights
lookups; this changes access verification only, not scientific eligibility.
Human approval of A1 and protocol 1.2 remains pending.

## 2. Discovery services, documents and datasets

| Entity | Role and verified boundary |
| --- | --- |
| [PubMed](https://pubmed.ncbi.nlm.nih.gov/) | Bibliographic identifiers and discovery; a record is not licensed full text or a prescription dataset. |
| [PMC OA subset](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/) | Article licenses vary. Current documentation names Cloud, OAI-PMH, E-Utilities and BioC as permitted automated retrieval services; generic systematic page scraping is prohibited. Task 46 must select a documented route and recheck each artifact. |
| Publisher article | Individually screened evidence document. Article rights exclude separately credited material; do not include site chrome, images or media by default. |
| Supplement/raw data | Independently inspect license, schema, provenance and sensitive fields; article permission does not automatically license a linked external dataset. |

### Newly screened documents

`Scientific status=pending professional review` for S1–S8; S8 full-text access
is pending. These are provisional relevance decisions, not independent inclusion
or methodological quality judgments. Acquisition classification is separate.
Authors abbreviated with “et al.” have complete lists at the linked primary
record; no missing author metadata may be guessed during Task 46 attribution.

| ID | Document, authors, identifier and version | Relevance/locator and limitations | Acquisition classification and rights evidence |
| --- | --- | --- | --- |
| S1 | Brad S Currier et al. **Resistance training prescription for muscle strength and hypertrophy in healthy adults: a systematic review and Bayesian network meta-analysis**; DOI `10.1136/bjsports-2023-106807`, PMID 37414459; online 2023-07-06, issue 2023-09. [Record](https://pubmed.ncbi.nlm.nih.gov/37414459/), [full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC10579494/). | P1/P2: Methods eligibility/Table 1, prescription nodes and limitations; group comparisons of load/sets/frequency, not exact individual dosing. Competing interests disclosed by Phillips (nutrition-sector funding/fees); adjudicate relevance. | **metadata-only**: article Copyright/License explicitly CC BY-NC 4.0. Neither article nor adapted passages may enter the commercial RAG. |
| S2 | Brad S Currier et al. **American College of Sports Medicine Position Stand. Resistance Training Prescription for Muscle Function, Hypertrophy, and Physical Performance in Healthy Adults: An Overview of Reviews**; DOI `10.1249/MSS.0000000000003897`, PMID 41843416; online 2026-03-05, issue 2026-04-01. [Record](https://pubmed.ncbi.nlm.nih.gov/41843416/), [full text location](https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823). | P1–P3: Abstract eligibility and outcomes; healthy-adult overview. Material recommendation and overview methods need separate appraisal; publication date does not resolve applicability. Conflicts require full statement review. | **metadata-only**: PMC-indexed copyright statement is CC BY-NC-ND 4.0. Direct PMC page returned a browser challenge; publisher full-text link failed. Do not bypass access controls or infer commercial permission. |
| S3 | Jonathan C Mcleod, Brad S Currier, Caroline V Lowisz, Stuart M Phillips. **The influence of resistance exercise training prescription variables on skeletal muscle mass, strength, and physical function in healthy adults: An umbrella review**; DOI `10.1016/j.jshs.2023.06.005`, PMID 37385345; online 2023-06-28, issue 2024-01. [Full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC10818109/). | P1–P3: PICOS Table 1 and Methods 2.5; overview/published AMSTAR results must not be mistaken for this project's AMSTAR 2/GRADE. Check overlap and conflicts before reuse. | **metadata-only**: copyright section CC BY-NC-ND 4.0; full text readable via PMC after minimal PubMed rendering. |
| S4 | Philip Lyristakis, Daniel Wundersitz, Stephen Cousins, Minh Huynh, Emma Zadow, Brett A Gordon. **The Influence of Individual Resistance Training Variables on Muscle Strength: A Systematic Review and Meta-analysis**; DOI `10.1007/s40279-026-02432-5`, PMID 41995957; version of record 2026-04-17, issue 2026-08. [Publisher](https://link.springer.com/article/10.1007/s40279-026-02432-5). | P1: Methods 2.2/2.5 and Discussion limitations; adult strength, mainly untrained, chest/quadriceps; no individual optimum or complete hypertrophy/restriction policy. Authors declare no relevant conflicts. | **eligible for ingestion, article text only**: Rights and permissions explicitly CC BY 4.0. [Publisher PDF](https://link.springer.com/content/pdf/10.1007/s40279-026-02432-5.pdf) successfully rendered (15 pages). Scientific/policy approval remains pending. |
| S5 | Jozo Grgic, Brad J Schoenfeld, Mislav Skrepnik, Timothy B Davies, Pavle Mikulic. **Effects of Rest Interval Duration in Resistance Training on Measures of Muscular Strength: A Systematic Review**; DOI `10.1007/s40279-017-0788-x`, PMID 28933024; issue 2018-01. [Record](https://pubmed.ncbi.nlm.nih.gov/28933024/). | P1 rest: abstract separates training-status comparisons; modified Downs and Black is the authors' method, not a project RoB 2 assessment. Full text/conflicts not verified. | **metadata-only**: no artifact-level allowlisted reuse established. PubMed web-index abstract available; direct page rendered minimally. Publisher route requires rights/access review. |
| S6 | Tácito P de Souza Jr, Steven J Fleck, Roberto Simão, João P Dubas, Benedito Pereira, Elisa M de Brito Pacheco, Antonio C da Silva, Paulo R de Oliveira. **Comparison between constant and decreasing rest intervals: influence on maximal strength and hypertrophy**; DOI `10.1519/JSC.0b013e3181ddae4a`, PMID 20543741; 2010-07. [Record](https://pubmed.ncbi.nlm.nih.gov/20543741/). | P1/P2 rest: randomized trial, 20 recreationally trained young men, eight weeks; abstract/pre-post strength and muscle-size results. Null between-group differences do not prove equivalence. No unrestricted/population-wide progression rule. | **metadata-only**: abstract readable; full-text rights, protocol and conflicts unverified. No allowed acquisition candidate. |
| S7 | Rodrigo Núñez-Cortés et al. **Tailoring Resistance Exercise for Knee Osteoarthritis: An Intervention Systematic Review With Dose-Response Meta-analysis of the Effects of Intensity and Volume**; DOI `10.2519/jospt.2026.13477`, PMID 42676087; online 2026-08-06, issue 2026-09. [Record](https://pubmed.ncbi.nlm.nih.gov/42676087/). | P4 knee OA: abstract describes pain/function/strength and authors' low-to-very-low certainty. This is an attributed report, not our GRADE. Aggregate dose associations cannot establish an individual target or diagnose knee pain. | **metadata-only**: full-text/supplement rights and conflicts unresolved; no allowlisted permission verified. |
| S8 | Farzaneh Yazdi, Amirali Salajegheh, Fatemeh Yazdi Yahyaabadi, Pouria Salajegheh. **The Impact of Strength/Resistance Training on Related Outcomes of Patients with Knee Osteoarthritis: A Systematic Review and Meta-Analysis Study: Strength/Resistance Training in Knee Osteoarthritis**; DOI `10.31661/gmj.v14i.3720`, [PMID 42038849](https://pubmed.ncbi.nlm.nih.gov/42038849/), PMCID PMC12169121; article date 2025-04-16, Galen Med J 14:e3720. | P4: PubMed-indexed abstract identifies a review of knee-OA trials covering function, stiffness, pain and quality of life, with heterogeneous findings. Indexed conflict statement declares none. Full methods, subgroup applicability, corrections and version history remain unverified; no project appraisal or certainty rating. | **metadata-only**: identity resolved through the indexed primary record in follow-up F1; direct PubMed rendering remains minimal, PMC challenges access and publisher access failed. Artifact-level rights unverified; not an acquisition candidate. |

All retraction/correction checks are **incomplete**: no systematic Crossmark or
linked-notice verification was completed. An accessible current page is not a
certificate of no retraction. Task 46 rechecks notices before capture; Task 47
checks currency/impact before policy approval. No license/review deadline in the
live catalog is extended by this report.

### Supplement and raw-dataset register

| Artifact | Prescription/outcome content and sensitivity | Decision |
| --- | --- | --- |
| S1 `bjsports-2023-106807supp001.pdf`, linked under Supplementary Materials | Appendices describe study/program data; not verified as an independently licensed raw-data release. Associated Data says data available on reasonable request. No participant-level import requested. | **metadata-only**; no independent allowlisted supplement license verified. Do not treat the PDF or request-only data as an open dataset. |
| S4 publisher Supplementary file15, **Supplementary File 2: Meta-Data Spreadsheet** | Linked XLSX and data-code workbook; not opened or downloaded. Contains potentially relevant variables, but row granularity, personal/sensitive fields and credit exceptions are unverified. | **metadata-only pending artifact inspection**; do not infer file permission/content from article title. Task 46 may assess it separately, but it is outside the eligible subset below. |
| S4 [Figshare link](https://figshare.com/s/03f37d273d601fa8abcb) | Publisher-linked dataset; access failed in this run. Schema, outcome units, participant granularity, version/DOI and artifact license unknown. | **metadata-only**; no dataset import authorized. Prefer aggregate study/arm data if later verified, exclude all participant-level sensitive records. |
| Exercise/media catalogs | Not evidence documents or comparative outcome datasets; not searched as dose substitutes. | **excluded from prescription-dose evidence**; dictionary/media work is outside Task 45. |

## 3. Existing corpus audit

Baseline is [catalog.json](../backend/app/modules/knowledge/catalog.json), version 1,
SHA-256 `d628d3032c7c66d9fa1bc72966da046bfae85e41c1cfb710b0d96f1c3c5ccf68`:
14 sources, 9 technically approved sources with 18 passages, 5 metadata-only
records. Titles, authors, URLs, capture dates, licenses and review dates are
retained verbatim there; the IDs below join to those exact records. This audit
examines packaged passages, not a running database or embedding/index health.
`reviewed_by=repository-content-license-review` is technical review, not named
professional appraisal. Existing translated summaries are not full-text dosing
tables. No dose rules are inferred from omitted original-paper details.

| Seed source ID | Verified discovery/access in this run | Actual packaged coverage and acquisition disposition |
| --- | --- | --- |
| `nhs-strength` | [Text](https://www.nhs.uk/live-well/exercise/strength-exercises/) and [NHS terms §3](https://www.nhs.uk/our-policies/terms-and-conditions/) readable; OGL original text except exclusions. | `-1` gradual repetition progression, `-2` calf-raise execution; not gym-wide strength/hypertrophy dose. Existing text remains eligible; fuller text expansion is a low-priority Task 46 candidate, not a substitute for S1/S2. |
| `nhs-flexibility` | [Page](https://www.nhs.uk/live-well/exercise/flexibility-exercises/) readable; same NHS terms. | `-1/-2` neck rotation/hold; duration of a stretch is not inter-set rest or resistance intensity. Existing text eligible; no resistance-dose expansion proposed. |
| `nhs-balance` | [Page](https://www.nhs.uk/live-well/exercise/balance-exercises/) readable; same NHS terms. | `-1/-2` support and controlled stepping; no complete resistance program. Existing text eligible; no dose expansion proposed. |
| `biga-anatomy` | [Book license](https://open.oregonstate.education/anatomy/back-matter/creative-commons-license/) readable, CC BY-SA 4.0 subject to exceptions. | `-1/-2`, §10.6: adaptations/recovery background, no outcome-specific prescription policy. Existing text only; preserve share-alike attribution/adaptation notice. |
| `rojas-deep-squat-2024` | [Publisher](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2024.1477796/full) readable; copyright CC BY link. | `-1/-2` selection/population exclusion; knee pathology excluded. Cannot support adjustments for symptomatic knees. Pending professional review; no additional acquisition proposed. |
| `verville-low-back-2023` | [Publisher](https://link.springer.com/article/10.1007/s10926-023-10124-4) readable; Rights section CC BY 4.0 reconfirmed. | `-1/-2` pain/function findings and uncertainty, not complete dose/progression/rest. Pending professional review; no new acquisition proposed. |
| `pavlova-tendinopathy-2023` | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10579176/) challenged; [publisher](https://bjsm.bmj.com/content/57/20/1327) 403. | `-1/-2` dose associations/incomplete reporting. Existing license from 2026-10-13 retained, **not freshly verified**; no new acquisition eligible from this check. |
| `wu-rotator-cuff-2025` | [Publisher](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2025.1560597/full) readable; copyright CC BY link. | `-1/-2` exercise modalities/pain/function, no universal load or progression. Pending professional review; no new acquisition proposed. |
| `lin-knee-proprioception-2025` | [Publisher](https://www.frontiersin.org/journals/rehabilitation-sciences/articles/10.3389/fresc.2025.1596966/full) readable; copyright CC BY link. | `-1/-2` balance/WOMAC and uncertainty in diagnosed knee OA; not general hypertrophy or all knee pain. Pending professional review; no new acquisition proposed. |
| `br-physical-activity-2021` | [Guide](https://bvsms.saude.gov.br/bvs/publicacoes/guia_atividade_fisica_recomendacoes_gestores_profissionais.pdf) returned 503. | **metadata-only**; catalog NC-SA exclusion retained, not freshly reverified; zero passages. |
| `open-exercise-physiology` | [Book](https://pressbooks.openeducationalberta.ca/otep/) returned 403. | **metadata-only**; catalog NC exclusion retained, not freshly reverified; zero passages. |
| `who-low-back-guideline-2023` | [WHO](https://www.who.int/publications/i/item/9789240081789) timed out. | **metadata-only**, permission pending; important clinical recommendation gap retained. Zero passages. |
| `jospt-rotator-cuff-2025` | [Guideline](https://www.orthopt.org/uploads/content_files/files/Rotator_Cuff_CPG.pdf) returned 403. | **metadata-only**, permission pending; no AGREE II appraisal possible from this access result. Zero passages. |
| `bmj-knee-modalities-2025` | [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12522397/) challenged. | **metadata-only**; catalog NC exclusion retained, not freshly reverified; zero passages. |

Dimension audit of actual passages: exercise selection has narrow examples,
volume/intensity/frequency have condition-specific aggregate findings but no
complete goal/experience accounting, progression has general qualitative
guidance only, rest lacks a gym-program rule, and restriction adjustments lack
combined-profile applicability. No packaged source establishes every dimension.
S4 adds a technically eligible research route, not a replacement for excluded
high-relevance syntheses or a completed policy.

## 4. Appraisal, certainty and overlap records

Instrument consultation: [AGREE II instructions](https://www.agreetrust.org/resource-centre/agree-ii/agree-ii-instructions/)
and linked 2017 manual were readable. [AMSTAR 2 original paper](https://www.bmj.com/content/358/bmj.j4008)
returned 403; [official tool page](https://amstar.ca/Amstar-2.php) and guidance
were found in web indexing but direct downloads returned 404. [RoB 2](https://www.riskofbias.info/welcome/rob-2-0-tool)
confirmed the parallel/cluster/crossover versions; its linked full guidance
rendered only a Drive shell. [Core GRADE 1](https://www.bmj.com/content/389/bmj-2024-081903)
returned 403; [author abstract](https://pubmed.ncbi.nlm.nih.gov/40262844/) and
indexed primary record were available. [PRISMA 2020](https://www.prisma-statement.org/prisma-2020-statement)
and [NHMRC evidence-to-decision](https://www.nhmrc.gov.au/guidelinesforguidelines/develop/evidence-decision)
were consulted for reporting/decision boundaries. No instrument/form text is
copied into the corpus. These access checks **do not constitute application**.

All records below have reviewer A=`unassigned`, reviewer B=`unassigned`,
adjudicator=`unassigned`, review date/deadline=`unset`, final decision=`pending`.
AI extracted locators only. No independent judgments/disagreements exist yet;
do not invent consensus. Task 47 must retain both assessments and resolve each
material disagreement with identity, rationale, date and source version.

| Appraisal record | Material and planned method | Domain record/status and concrete remaining work |
| --- | --- | --- |
| A1 | S1/S4/S5/S7/S8 and intervention seed reviews Verville/Pavlova/Wu/Lin: AMSTAR 2, 2017 | Items 1–16 each `not_assessed`; protocol/search/excluded-study justification/primary-study bias/synthesis/bias interpretation/publication bias remain unjudged. Full instrument and supplements plus independent reviewers required. No overall confidence assigned. |
| A2 | S4 extraction notes for A1 | §2.4 uses PEDro/TESTEX; §3.2's certainty derivation needs review of bias/upgrading decisions. These are reported methods, not adopted domain judgments or a RoB 2/GRADE pass. |
| A3 | WHO/JOSPT guidelines; recommendation component of S2 if applicable: AGREE II 2017 | Scope, stakeholder involvement, rigor, clarity, applicability and editorial independence each `not_assessed`; full guideline/supporting materials and independent appraisers required. No normalized scores or approval assigned. |
| A4 | S2/S3 overviews; Rojas scoping review | Design/coverage extraction only. Formal overview/scoping appraisal method and any adaptation require methodological approval. Do not force AMSTAR 2 onto an overview or treat PRISMA as appraisal. |
| A5 | S6 bench/squat strength and muscle-size endpoint results: RoB 2 parallel trial 2019 | Randomization, deviations, missing outcomes, measurement and selective reporting each `not_assessed`; full trial/protocol/results needed. No result-level risk judgment from the abstract. |
| A6 | NHS educational pages and Biga textbook | Background/implementation examples only; not practice guidelines or trials. No AGREE II/RoB 2 claim; assess currency, provenance and applicability before any derived operational policy. |

### Outcome-specific certainty register

These are **candidate bodies**, not pooled new estimates. For every row, the five
GRADE domains (bias, inconsistency, indirectness, imprecision, publication bias)
are individually `not_assessed`; project certainty=`not_assessed`, independent
sign-off=`pending`. No absence of evidence is relabeled high/low certainty.

| Body | PICO/outcome/timepoint | Candidate sources and unresolved basis |
| --- | --- | --- |
| B1 | P1 strength change at reported program endpoint | S1/S2/S3/S4/S5/S6. S4 §3.2 reports high certainty after downgrade/upgrade; **published rating only**, not adopted. Partition by training status, measure and follow-up; retrieve eligible primary results/reusable appraisals before rating. |
| B2 | P2 muscle size change at reported endpoint | S1/S2/S3/S6; S4 is not hypertrophy evidence. Methods, overlap, precision, harms and restriction applicability unresolved; excluded licenses remain a runtime gap. |
| B3 | P3 physical function, adherence and adverse events by reported timepoint | S2/S3 and NHS background. Do not substitute strength/muscle-size outcomes for all fitness/adherence/harms claims; no independent body appraisal. |
| B4 | P4 pain/function/adverse events, separated by condition and follow-up | Verville/Pavlova/Wu/Lin/S7; S8 identity resolved in F1, full text/appraisal still pending. Published seed certainty statements remain attributed. Never combine unrelated diagnoses into one certainty estimate or apply clinical data to an undiagnosed complaint. |
| B5 | P1/P2 progression and inter-set rest effects by endpoint | S5/S6 and S1/S2/S3 candidate references; operational progression conditions and missing comparative harms data still unresolved. |

Overlap O1: S1/S2/S3 and S4's primary-study lists may share trials/reviews;
S5/S6 may overlap; S7/S8/Lin/BMJ knee sources may overlap. Exact DOI/arm/outcome
deduplication has **not** been performed, so no source counts are treated as
independent confirmation. Task 47 must build study-to-review/result mappings
before adopting certainty; do not sum participants across these sources.

## 5. Coverage matrix v1 — research applicability, not enabled runtime

Legend: `A=awaiting_review`, `U=unsupported`. These expand to the canonical
statuses; neither `supported` nor `partial` is awarded before final judgments.
Every row below covers selection (Sel), volume (Vol), intensity (Int), frequency
(Freq), progression (Prog), rest and restriction adjustments (Restr). Source IDs
join to exact article/section or packaged-passage locators above. `G` numbers
identify explicit gaps below, not silently missing cells.

Base population is adult eligibility **confirmed**, no reported restrictions,
conditions or medication use; no “healthy” diagnosis is inferred. All twelve
rows remain disabled for the future extension until inputs/policies/evaluation
are approved. Actual existing runtime behavior is unchanged by this task.

| Proposed goal | Experience | Sel | Vol | Int | Freq | Prog | Rest | Restr | Source/rationale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Strength | `none` | A | A | A | A | A | A | A | S1–S5, NHS-strength; G1/G2/G3/G4 |
| Strength | `beginner` | A | A | A | A | A | A | A | S1–S5; training-status mapping unapproved; G1–G4 |
| Strength | `intermediate` | A | A | A | A | A | A | A | S1/S2/S3/S5/S6; G1–G4, no direct app-enum mapping |
| Strength | `advanced` | A | A | A | A | A | A | A | S1/S2/S3/S5/S6; G1–G4, no advanced-specific pass |
| Hypertrophy | `none` | A | A | A | A | A | A | A | S1/S2/S3; G1–G4; S4 not a muscle-size source |
| Hypertrophy | `beginner` | A | A | A | A | A | A | A | S1/S2/S3; G1–G4 |
| Hypertrophy | `intermediate` | A | A | A | A | A | A | A | S1/S2/S3/S6; G1–G4 |
| Hypertrophy | `advanced` | A | A | A | A | A | A | A | S1/S2/S3/S6; G1–G4, subgroup applicability pending |
| General fitness/function | `none` | A | A | A | A | A | A | A | S2/S3 and NHS-strength/balance/flexibility; G1–G4/G7 |
| General fitness/function | `beginner` | A | A | A | A | A | A | A | Same locators; G1–G4/G7 |
| General fitness/function | `intermediate` | A | A | A | A | A | A | A | S2/S3; G1–G4/G7, background examples insufficient |
| General fitness/function | `advanced` | A | A | A | A | A | A | A | S2/S3; G1–G4/G7, applicability pending |

The following overrides apply to **each of the four experience levels and each
goal above**, rather than assuming a restriction is covered by a base row.

| Population/goal interaction | Sel | Vol | Int | Freq | Prog | Rest | Restr | Rationale/source or gap |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Diagnosed chronic primary low-back pain | A | A | A | A | A | A | A | Verville `-1/-2`; WHO metadata; G5, no whole-program rule |
| Diagnosed knee OA | A | A | A | A | A | A | A | Lin `-1/-2`, S7, BMJ metadata; G5; Rojas excluded pathology |
| Clinically established rotator-cuff-related pain | A | A | A | A | A | A | A | Wu `-1/-2`, JOSPT metadata; G5 |
| Clinically established tendinopathy | A | A | A | A | A | A | A | Pavlova `-1/-2`; G5, incomplete dose reporting |
| Symptom-only knee/back/shoulder pain, medication effects or unclassified limitation | U | U | U | U | U | U | U | G5; no diagnosis/clearance inferred from free text |
| Combined knee + back, shoulder + medication, or any multiple restrictions | U | U | U | U | U | U | U | G6; isolated condition sources do not establish interactions |
| Missing age/eligibility, minor, pregnancy/postpartum, other unreviewed population | U | U | U | U | U | U | U | G3/G5; no default adult eligibility or extrapolation |
| Unknown/ambiguous/mixed goal; weight loss, sport performance, clinical rehabilitation | U | U | U | U | U | U | U | G7; no approved goal mapping or complete searched body |

| Gap | Concrete missing support and Task 47 decision |
| --- | --- |
| G1 | Independent domain appraisal, outcome certainty and training-status-to-app-level applicability; adopt/adapt/reassess each usable published appraisal. |
| G2 | Complete selection/volume accounting/intensity/frequency/progression/rest policy with units and passage set; S1/S2/S3 are non-ingestible, so retain their scientific gap even if S4 is acquired. |
| G3 | Adult eligibility, confirmed weekly schedule and relevant baseline provenance absent; approve permitted minimal clarification or leave dependent cohort disabled. |
| G4 | Prescription dictionary, conservative operational choices and benefit/harm conditions require professional evidence-to-decision; six-passage feasibility remains unmeasured. |
| G5 | Restriction-specific applicability, required inputs, clinical boundaries and harms need professional decisions; symptom/medication interpretation not authorized by aggregate studies. |
| G6 | No examined body establishes combined-restriction rules; unsupported unless independently reviewed interaction policy exists. |
| G7 | Preserve original free-text goal, clarify ambiguous/mixed request, define explicit professionally reviewed family mappings; no silent classification of weight loss or general health as hypertrophy. |

## 6. Criterion register v1

All criteria are version 1 (2026-10-23), proposed by Codex; human reviewer and
approval=`unassigned/pending`. This separates source findings from software and
release choices; it introduces no numeric clinical ranges.

| Criterion ID/kind | Question/scope and basis | Rationale/limitations | Verification plan |
| --- | --- | --- | --- |
| C01 scientific | PICO-specific design/population/outcome relevance; protocol §2 and Core GRADE 1 | Relevance is not automatic applicability to app levels, restrictions or individuals. | Two independent screening/applicability records; adjudicate disagreements. |
| C02 scientific | Guideline, intervention review and trial-result methods; AGREE II 2017, AMSTAR 2 2017, RoB 2 2019 | Preserve domain judgments; unavailable information remains unassessed. No universal numeric quality score. | Complete A1–A6 with correct instrument/full instructions, locators and independent signatures. |
| C03 scientific | Certainty by outcome/timepoint; Core GRADE 2025 | Assess all five domains and overlap; published certainty not silently adopted. | B1–B5 and DOI/arm/outcome mapping; Task 47 adopt/adapt/reassess decisions. |
| C04 scientific | Benefits/harms, feasibility and derived operational rules; NHMRC evidence-to-decision | Evidence may inform conservative professional choices; exact load/diagnosis cannot be inferred. | Professional scoped decision per rule with inputs, conditions and rationale. |
| C05 technical | OGL-3.0/CC-BY-4.0/CC-BY-SA-4.0 only; canonical RAG contract and `knowledge/service.py` | Project license allowlist is not scientific quality. Source-level rights do not clear every supplement. | Task 46 artifact rights/capture/hash/attribution/exception check, current review deadline. |
| C06 technical | Zero-to-six final passages, 1024-dimensional BGE-M3, same providers; canonical RAG and DEC-03 | Limits may cause retrieval gaps despite available literature. | Task 47 measured development retrieval/coverage/resource experiment; separate literature/index/ranking/budget failures. |
| C07 product_policy | Two independent human material judgments and adjudication; protocol §3/EXT-CA-AI-02.14/22 | Project quality policy, no scientific efficacy threshold; AI is not a reviewer signature. | Governance assignments and dated independent appraisal/adjudication records. |
| C08 product_policy | Abstain for missing mandatory support/input, restriction conflict or technical failure; EXT-CA-AI-02.8 | Four reasons remain distinct; absence of evidence/outage does not prove harm. | Independently judged reason/conflict/clarification scenarios across every entry point. |
| C09 product_policy | Zero observed critical test failures plus supported positive controls; EXT-CA-AI-02.12/15 | Release suite gate, not zero population risk. Other sample/acceptance limits need approval. | Seal thresholds before Task 48; Task 51 offline and actual-deployment repeats. |
| C10 product_policy | Independent held-out custody and actual deployment evaluation; EXT-CA-AI-02.19/22 | Unassigned custodian means independence is not established. No developer self-certification. | Custodian seals hashes/answers outside repo/prompts; replace exposed cases; scoped release signatures. |
| C11 technical | Minimized authoritative own-client inputs, exact revisions and immutable history; RN-11/23/29/31, DEC-18 | No new medical field/retention or administrative-identity context authorized. | Task 47 readiness approval; Tasks 49–51 snapshot/isolation/stale-input checks; no raw sensitive diagnostics. |

## 7. Actual input-source inventory and clarification readiness

Inspected [onboarding schema](../backend/app/modules/onboarding/schema.py),
[models](../backend/app/modules/onboarding/models.py),
[PersonProfile/Client](../backend/app/modules/clients/models.py),
[generation](../backend/app/modules/training/generation_service.py),
[chat](../backend/app/modules/training/chat_service.py),
[adaptation](../backend/app/modules/training/adaptation_service.py),
[schedule parser](../backend/app/modules/training/completeness.py), and
[training item schema](../backend/app/modules/training/schema.py).
No client rows were examined. This is a schema/service inventory, not a new
collection form. Task 47 owns rule-specific readiness and DEC-18 decisions.

| Fact/representation | Actual authority, availability and provenance | Missing/conflict/confirmation action |
| --- | --- | --- |
| Goal: string ≤500; experience: `none/beginner/intermediate/advanced` | Completed own `Onboarding`, shared completion validation. `completed_at`/`updated_at` exist; not per-fact confirmation timestamps. | Preserve text; confirm narrower attempt goal explicitly. Missing/ambiguous mapping blocks affected rule; no overwrite of completed onboarding. |
| `height_cm` integer, `weight_kg` decimal | Structured completion fields, existing units and validation; not measurement-method or load-baseline evidence. | Do not derive age, body-composition goal or 1RM; send only if policy needs them. |
| Limitation/complaint, medication use and health-condition booleans + conditional detail strings | Completed onboarding; self-report rather than clinical diagnosis. Generation consumes completion data; chat includes selected health details based on relevant terms; adaptation consumes selected own facts. | Model context is not a complete input-readiness check. Conflicting later report requires explicit confirmation/professional review. No medication-effect inference. |
| Adult/age/population eligibility | **Missing**: neither inspected PersonProfile nor onboarding has birth date/age/adult-eligibility field; no demographic authority available for the proposed adult slice. | Task 47 must approve minimal permitted eligibility confirmation through existing flow or keep slice disabled; do not invent age from name/CPF or request birth date for literature search. |
| Requested focus/sessions/schedule | Authenticated free-text request; AI focus with scope/muscle grounding; `requested_training_schedule` parses 1–7 days/occurrences for full-body into A–G labels only. No day-of-week/recovery/availability typed confirmation. | Confirm actual seven-day schedule and session scope per attempt; labels/equipment are not weekly frequency proof. Existing parser does not satisfy future snapshot requirement. |
| 1RM/RPE/RIR/capacity, clearance or observed progression trigger | **Missing** as authoritative baseline/clearance/workout observation in the inspected input contract. Free-text `load_guidance` is output, not a measured baseline. | Keep dependent modes disabled; approve source, method, role and validity before collecting; do not add new medical inputs under Task 45. |
| Equipment | Existing EquipmentService training context and equipment-model references; operational state is not live availability. | Recheck appropriate active/operational state at persistence; professional dictionary/variation mapping pending. |
| Current/draft state | Existing training services, version/revision, ordered items and sole-draft lifecycle; free-text repetitions/load, sets/rest are not a validated typed schedule. | Bind exact revisions; revalidate full resulting plan on adaptation. Concurrency or legacy normalization failure requires controlled rejection/manual path. |
| Attempt confirmation/snapshot | Existing authenticated RF-18 messages, explicit training requests and RF-19 client confirmation paths exist; raw reports do not edit onboarding. **No minimized versioned policy input snapshot with per-fact confirmation/validity exists.** | Tasks 47/49/50 define readiness and explicit questions/confirmation; AI extraction remains provisional. No new retention policy or copied private chat in reviewer context. |

For future snapshots, record source ID/version, author/confirmer role, observed
and confirmed timestamps, representation/unit, permitted audience, policy-specific
validity and conflict resolution. None is defaulted to a universal health-data
expiry. Mutable goal/schedule/restrictions and referenced revisions must be
reconfirmed/rechecked when required; stale/missing facts cannot qualify a rule.
Health facts remain owner/functional-need only; administrative identifiers,
raw private conversations and other clients never enter evidence, search or
ordinary logs. Existing onboarding audit actors may establish who changed a
record; they are not independent clinical measurement or blanket clearance.

## 8. Responsibility and resource register v1

On 2026-10-23 the user designated **the instructor profile** in response to the
responsibility request. This is the functional role for professional prescription
review, consistent with RN-12/RN-31 and existing authorization. No actual reviewer
identity, qualifications, availability, conflicts or independence were supplied;
this does not establish methodological competence, separate independent
reviewers, custody or a signed appraisal. Named-governance criteria remain open.
No identity or approval is inferred from filesystem usernames or paper authors.
Codex is the identified discovery/documentation assistant only, not a
project/release owner, qualified reviewer, independent evaluator or custodian.

| Role | Actual identity / competence / conflicts / independence / availability | Required approval scope and proposed effort (not funded/approved) |
| --- | --- | --- |
| Project/release owner | **Unassigned**; competence/conflict declaration/availability unknown | Name people, approve bounded cohort/resources and final scoped release. Propose 1–2 hours for initial scope/assignment review. |
| Methodological reviewer A | **Unassigned**; appraisal/GRADE/evaluation competence and independence unverified | Protocol/amendments, domain judgments, certainty and sampling. Propose 4–8 hours initial methods + anchor appraisal triage, then re-estimate. |
| Qualified exercise-prescription reviewer B | **Functional role: instructor**, designated by user on 2026-10-23; actual person unassigned, professional qualification/conflicts/availability unverified | Independent applicability assessment, benefit/harms, operational rules/inputs and reference rubric. Propose 4–8 hours initial slice; do not approve broader restrictions implicitly. |
| Independent evaluator/adjudicator | **Unassigned**; custody/independence/access control not established | Resolve disagreements, hold sealed cases/answers, assess contamination/results. Propose 2–4 hours evaluation design and sealing, execution separately estimated. |
| Technical/corpus maintainer | **Unassigned**; named continuity owner/availability/conflicts unknown | Rights, capture/integrity, manifests, feasibility/resources, recovery and execution; no professional approval. Propose 2–4 hours article-only acquisition/inspection before broader ingestion estimates. |

These are project planning estimates, not methodological sample-size findings or
an authorized paid budget. No subscription or paid service was used/approved.
Each assignee must supply actual identity, relevant competence, conflicts,
independence, availability, signed scope/date and artifact hash before final
review. A/B must be different independent humans; overlapping roles do not
remove the independent evaluator requirement. Task 47 cannot seal or enable a
cohort with unresolved mandatory assignments. Source/license/retraction/policy/
input/model changes require named-owner impact review, affected-cohort suspension
and scoped reevaluation; historical approved plans remain unchanged.

## 9. Early independent evaluation protocol v1 — draft for Task 47 sealing

Questions: does every material prescription decision have applicable approved
support; does the system accept supported cases and reject unsupported ones;
does it distinguish conflict, missing information, insufficient support and
technical outage; do retries/reuse/transitions preserve isolation and state?
Task 51 executes this design after Task 47 approves/seals it. No case answers
or held-out data are created here.

Sampling proposal: purposive synthetic scenarios, stratified by all four app
experience levels, proposed goal families, known/unknown population, each named
restriction and interactions. Begin with the bounded adult strength `none`/
`beginner` slice; include clearly unsupported goals/combined restrictions and
missing age/schedule/baseline. Exercise every entry point: initial/targeted
generation, rebuild, chat edits/prescriptive answers, adaptation, correction,
cache reuse/idempotent replay, submission and instructor approval/manual paths.
Include positive controls plus boundary values, missing/stale/revoked evidence,
inapplicable sources, conflicting inputs/rules, typed-unit/volume errors,
revision races and separate runtime/startup outages. These are **strata**, not
held-out concrete examples or a claimed representative population sample.

Partition by scenario families before drafting instances; cosmetic paraphrases
must not cross partitions. Developers receive development/calibration fixtures.
Independent evaluator selects an untouched evaluation partition and custody
location, logs access and seals case IDs/hashes, reference-judgment hashes and
policy/corpus versions before Task 48. Reference judgments are made separately
by methodological/professional reviewers, reconciled by the adjudicator with
severity and rationale. Ambiguous/unresolved cases are reported and cannot
support a pass; exclusions require dated independent justification. Exposed
held-out cases are replaced independently before any new release claim.

| Outcome definition | Numerator/denominator and interpretation |
| --- | --- |
| Supported acceptance | Reference-supported cases whose complete candidate passes / all reference-supported cases; an always-reject implementation fails positive controls. |
| False rejection | Reference-supported cases rejected / all reference-supported cases, with reason and entry-point breakdown. Technical failures reported separately, never silently dropped from attempts. |
| Unsupported acceptance | Reference-unsupported cases publishing/saving/submitting actionable candidates / all reference-unsupported cases. Any critical unsupported publication is a critical failure. |
| Justified abstention | Reference-negative cases correctly rejected without state corruption / all reference-negative cases; report each of four reason categories separately. |
| Reason correctness | Correct reference reason among attempts with a defined expected reason / all such attempts; distinguish restriction conflict from missing input, support gap and technical failure. |
| Trace/retrieval/extraction correctness | Independently checked material decisions with valid applicable policy/passage/version/units / all checked material decisions; also report per-case mandatory-dimension coverage and extraction mismatches. |
| Integrity/critical failure | Unauthorized cross-client exposure, publication despite a mandatory rejection, approval bypass, corrupted saved state/history or concealed contradictory dosing. Count every occurrence and affected case/attempt. Final severity rubric requires professional/methodological approval. |

Report numerator/denominator per cohort, goal, restriction interaction, entry
point and reason. Preserve case-level versus repeated-attempt denominators;
repeats of one case are not independent samples. Propose case-level Wilson
intervals for binary suite proportions where defensible, with methodological
approval of clustering handling; purposive suite intervals do not estimate
population prevalence or clinical risk. Do not pool unlike cases into a
misleading overall confidence score. Severity/cost proposal: critical errors
block release; false rejection reduces usefulness and must be reported, not
hidden by abstention. Numerical cost weights and noncritical thresholds are
**pending approval**, not invented findings.

Operational plan proposal (not authorization): run deterministic fake-adapter CI
separately; propose three actual-deployment runs per sealed case initially to
inspect variability. The owner/methodologist must fix repeat counts, sample
counts per stratum and approved resource/cost budget in Task 47 after measured
development feasibility, before Task 48. Three is a planning proposal, not proof
of reliability or an approved release minimum. No paid execution budget exists.
Record every attempt, timeout, retry, duration, hardware, storage and prompt/
schema/model/digest/decoding/config/corpus/policy/validator versions. Preserve
the six-passage bound and configured timeout/retry policies; measure the target
environment rather than inventing latency promises. Actual deployment tests use
isolated synthetic identities/persistence with rollback or disposal, never real
client submission/activation. Fake CI cannot stand in for this evaluation.

Release: zero observed critical failures is the canonical product gate, plus
passing supported controls. Additional acceptance/false-rejection thresholds,
uncertainty requirements and final sample/resource budget remain **unsealed**.
No independent custodian has been assigned, no protected storage configured,
no held-out suite exists, no live-provider evaluation was run and no release
sign-off is claimed. Task 47 must resolve these gates; Task 51 executes them.

## 10. Bounded handoffs and completion evidence

**Task 46 eligible new subset:** S4 article **text only**, DOI/version and
publisher PDF route in section 2, CC BY 4.0 excluding separately credited
material. This is technical acquisition eligibility; provisional research may
proceed while professional appraisal is pending. Before indexing, capture exact
bytes/hash/date, attribution/full author list, license URL/statement, exceptions,
current notices, named technical review/deadline and extraction checks using
existing knowledge-module conventions. No source content/hash is invented here:
article bytes have not been saved as corpus artifacts. Existing NHS original
text is a separately verified optional expansion route, not evidence that the
major dose gaps are closed. Supplements/Figshare/S1/S2/S3/S5–S8 are excluded from
this eligible subset. Task 46 must perform actual acquisition/indexing and its
recovery runbook; this report does neither.

**Task 47 decisions:** assign and qualify humans; finalize A1–A6/B1–B5 and overlap;
approve PICO/goal/experience mappings and initial scope; decide whether adult
eligibility/schedule can be collected through the authorized flow; approve
input validity/conflict handling, dictionary/units/volume accounting and each
derived operational rule; resolve restriction combinations and non-ingestible
scientific gaps; measure retrieval feasibility; then approve/seal evaluation
custody, rubric, thresholds, sample/repeat counts and budgets before Task 48.

| Acceptance | Current evidence and honest remaining status |
| --- | --- |
| EXT-CA-AI-02.1 | Initial versioned matrix, all four levels, dimension statuses, restrictions/unknowns and locators/gaps recorded. No approved supported cohort. |
| EXT-CA-AI-02.2 | S4 text rights/route verified; ambiguous/NC sources and uninspected datasets remain metadata-only. Capture/hash/extraction/indexing is Task 46, not claimed here. |
| EXT-CA-AI-02.14 | Prespecified dated protocol, searches, appraisal/criterion/overlap/certainty registers delivered; **final appraisals and human review incomplete**, no tool applied merely by citation. |
| EXT-CA-AI-02.17/19 | Actual input inventory and early evaluation design delivered; readiness approval, custody and sealed references remain pending in Task 47. |
| EXT-CA-AI-02.22 | Role/resource/approval register delivered; **named human assignments, competence/conflict declarations and independent approvals missing**. Criterion stays open. |

Validation is documentation/source verification only: reviewed primary identifiers,
publisher license statements, supported acquisition links and access failures;
checked local catalog counts/locators, schema availability and protocol hash;
checked Markdown local targets and Git diff/whitespace. No tests of prose shape,
live AI providers, client datasets, downloads/indexing or runtime behavior were
added/run. Final human appraisal/governance acceptance remains open; research
delivery does not mark the whole task or canonical criteria complete.

## 11. Follow-up verification F1 — 2026-10-23

This follow-up audits the existing Task 45 artifacts; it does not claim to have
repeated the earlier Q1–Q4 selection. Protocol 1.2 remains byte-for-byte unchanged,
with the SHA-256 in section 1 reconfirmed locally. No PICO, screening bound,
scientific inclusion rule or acquisition subset changed. Review 1.1 resolves S8
identity and records the following repeatable access checks; all final human
judgments remain pending.

| Check and exact route/query | Observed result | Impact |
| --- | --- | --- |
| Open [S4 publisher article](https://link.springer.com/article/10.1007/s40279-026-02432-5), Methods 2.2, supplementary information, Rights and permissions and About this article | CC BY 4.0 article permission reconfirmed, subject to third-party credit exceptions; linked article PDF and separate metadata spreadsheet present. | S4 article-text-only acquisition handoff unchanged. Supplements remain outside the eligible subset; no workbook, corpus or embeddings acquired. |
| Web query `"42038849" knee osteoarthritis authors`, then open [PubMed](https://pubmed.ncbi.nlm.nih.gov/42038849/), [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12169121/) and [publisher](https://gmj.ir/index.php/gmj/article/view/3720) | Indexed PubMed record supplies S8 identity/abstract/conflict metadata above. Direct PubMed page remains minimal; PMC presents a browser challenge; publisher unavailable through this tool. Search results from secondary sites were not used as evidence. | Identity gap narrowed; full-text, artifact rights and professional appraisal still pending. S8 remains metadata-only and adds no supported matrix cell. |
| Open [S2 PubMed](https://pubmed.ncbi.nlm.nih.gov/41843416/) and its [PMC location](https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823/) | PubMed identity/date reconfirmed; PMC still presents a browser challenge. | No new full-text permission or acquisition approval established. |
| Open [AMSTAR 2 tool page](https://www.amstar.ca/Amstar-2.php) | Returned 404. | Full instrument consultation/application remains incomplete; no appraisal pass inferred. |
| Web query `site:pubmed.ncbi.nlm.nih.gov "s40279-026-02432-5" correction retraction`; inspect S4 publisher page for notices/Crossmark | Returned S4 record; no correction/retraction result or Crossmark link identified in this bounded response. | **Not a negative retraction certificate**. Systematic notice checks remain incomplete and must be repeated before acquisition/policy approval. |

Local verification reconfirmed the catalog hash in section 3, all 14 source
records, nine approved records and 18 packaged passages. Knowledge license and
six-passage constants, retrieval, onboarding schema, training schema/services
and existing RAG tests were inspected without reading client rows. This is a
packaged-corpus audit, not database/index verification. Local Markdown targets
and whitespace were checked; runtime/provider tests are outside this
documentation-only change. No runtime, canonical requirement, protocol, source
license allowlist or existing work outside Task 45 was modified.
