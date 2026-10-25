# Evidence-Qualified Training Prescription Specification

Status: planned — owner-requested specification, 2026-10-22. No implementation,
corpus expansion, professional approval, or reliability claim is completed here.

The [owner-approved development exception](training-prescription-development-amendment.md)
subsequently permits isolated Tasks 48–50 implementation before review/sealing,
without operational enablement. See the [development report](tasks/48-50-isolated-prescription-development-report.md).
Historical preimplementation gates in this planning document are superseded only
for that isolated scope; all professional and independent release gates remain.

`docs/requirements.md` is the sole canonical implementation specification.
This document decomposes EXT-RF-AI-02 into Tasks 45–51 and records the inspected
baseline. In a conflict, stop the affected work for a human decision.

## Objective and scope

Close the demonstrated gap between retrieving related literature and supporting
a training prescription for a particular goal, experience level, and student
profile. Search for evidence collections, download and vectorize eligible
material, then refactor generation to produce only evidence-qualified proposals
for the explicitly supported scope. Discard a candidate when support cannot be
established. Instructor approval remains mandatory and does not make unsupported
AI generation acceptable.

Coverage includes exercise selection, volume, intensity, frequency, progression,
restriction adjustments, and rest. Prescription evidence includes guidelines,
systematic reviews, original studies, and reusable supplementary datasets where
appropriate. An exercise-name/muscle/media dataset alone cannot supply dose,
progression, comparative outcomes, or population-specific safety evidence.

Original RF ownership: RF-15 generation, RF-18 prescriptive chat/draft editing,
RF-19 adaptation. RF-16/RF-17 and EXT-RF-INST-02/03 are necessary display,
revision, review, and history dependencies. EXT-RF-AI-02 owns the new coverage
and abstention criteria. Onboarding and equipment are consumed boundaries.
No unrelated RF, catalog CRUD, diagnosis, rehabilitation service, automatic
activation, or major technology change is included.

## Inspected baseline

- `backend/app/modules/knowledge/{models,service,bootstrap,startup}.py` and
  `catalog.json` already provide reviewed/licensed sources, passages, hybrid
  search, and idempotent startup indexing.
- PostgreSQL/pgvector and a separate Ollama BGE-M3 embedding adapter already
  exist. Preserve 1024 dimensions, zero-to-six final passages, source/license
  filters, private-client isolation, and the configured writing providers.
- The canonical seed review identifies fourteen bibliographic candidates and
  nine sources with selected indexed text. This is a technical/license review,
  not professional approval of prescription rules or complete coverage.
- `knowledge/service.py` can mark retrieved current material `supported` without
  proving support for every prescription dimension. Citation resolution checks
  retrieved IDs and canonical metadata; it does not establish dose applicability.
- `training/knowledge_query.py` combines general prescription and restriction
  retrieval. `generation_service.py`, `chat_service.py`, and
  `adaptation_service.py` integrate evidence with the existing lifecycle.
- `completeness.py` and `selection.py` enforce useful structure, session coverage,
  variation, duplicate correction, and automatic-review checks. These checks
  remain, but neither structural completeness nor model review proves adequacy.
- `TrainingPlanItemInput` has sets, free-text repetitions/load guidance, rest,
  and equipment; it does not by itself encode validated weekly volume,
  frequency, progression, or the evidence behind each decision.
- Onboarding has a free-text `training_goal` and experience levels `none`,
  `beginner`, `intermediate`, `advanced`. Do not invent a finite existing goal
  enum, silently classify all free text, or infer unrecorded health/age data.

## Source discovery starting points

These links were inspected on 2026-10-22 as research starting points. They are
not an approved import list or a completed literature review.

| Source | Role in Task 45 | Boundary |
| --- | --- | --- |
| [PubMed](https://pubmed.ncbi.nlm.nih.gov/) | Discover guidelines, reviews, original trials and persistent identifiers | Bibliographic discovery is separate from permission to ingest full text. |
| [PMC Open Access Subset](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/) | Locate reusable full text and associated supplements | Verify each artifact's license and use the currently permitted automated retrieval services; membership alone is insufficient. |
| [Currier et al., 2023, PMID 37414459](https://pubmed.ncbi.nlm.nih.gov/37414459/) | Candidate synthesis concerning training load, sets and weekly frequency | Healthy-adult evidence is not automatic support for a client with restrictions or an exact individual load. Full-text and supplement rights remain to be screened. |
| [ACSM position stand, 2026, PMID 41843416](https://pubmed.ncbi.nlm.nih.gov/41843416/) | Candidate recent overview of resistance-training prescription evidence | Evaluate full-text reuse, population applicability and prescription gaps; a free article link does not establish the allowed license. |
| Existing seed bibliography | Audit what is already available and what actually supports each dimension | Do not relabel technical review as professional approval or count multiple summaries of one study as independent evidence. |

PMC explicitly restricts automated acquisition to its documented services and
requires article-level license checks; use its linked current documentation
when implementing downloads. Metadata-only candidates may inform discovery;
their excluded text must not enter embeddings or writing-model context.

## Required artifacts and coverage model

Task 45 first prespecifies the dated [methodological protocol](training-evidence-methodology.md),
including PICO questions, search/screening rules, design-appropriate appraisal,
outcome certainty, reviewers, amendments and the criterion register. AGREE II,
AMSTAR 2, RoB 2 and GRADE serve different purposes; neither tool names nor PRISMA
reporting alone provide an evidence-quality pass. Scientific inclusion remains
separate from download permission, technical limits and product release policy.

Task 45 then creates `docs/training-evidence-source-review.md` with search dates,
queries, services, inclusion/exclusion criteria, screened candidates, and gap
analysis. Prefer a bounded, reproducible search over an arbitrary source quota.
Retain important non-ingestible evidence as a documented gap; do not silently
replace it with weaker evidence because that evidence is easier to download.

Task 47 creates the versioned machine-readable prescription-policy artifact
inside the existing backend modules, plus a human-readable coverage report.
Every material rule requires an evidence-to-decision record linking actual
appraisal/outcome-certainty findings to professional operational choices,
benefit/harm judgments and conditions for use. Lower certainty alone is not
automatic prohibition; conditional use must be approved, bounded and checkable.
Each coverage entry records:

- goal family and explicit mappings from supported free-text goals;
- experience, population inclusion/exclusion, restrictions and combinations;
- exercise selection, volume per session/week and relevant muscle allocation,
  intensity representation, frequency/recovery, progression/regression, rest,
  and restriction-specific adjustments;
- source/passage version and precise locator, outcome studied, certainty and
  limitations, including whether guidance is direct or professionally derived;
- allowed bounds/units, selection/calculation rules, required inputs, conflict
  resolution, reviewer identity/date/deadline and policy version;
- `supported`, `partial`, `unsupported`, or `awaiting_review`, with reasons.

Do not force a full combinatorial Cartesian product. Define supported cohorts,
explicit exclusions, required interaction cases, and an unknown-case rejection
rule. Every advertised cohort must have complete mandatory dimension coverage.
No fixed clinical threshold or prescription range is supplied by this spec.

Downloaded snapshots, manifests, normalized passages and embedding reports must
be reproducible and follow the repository's artifact/storage conventions.
Do not commit unreviewed bulk archives, personal datasets, or model weights.
Source hashes and stable locators must connect rules to the exact captured text.

## Generation and abstention contract

1. Resolve the authenticated client and authoritative completed onboarding;
   preserve the user's requested goal, muscles, schedule, and restrictions.
2. Resolve an applicable reviewed policy. Request missing required information
   through existing authorized flows or abstain. Never guess a profile, medical
   diagnosis, medication effect, training availability, prior load, or 1RM.
3. Retrieve a bounded evidence set covering all mandatory dimensions. Scope,
   license, review validity and applicability precede ranking. A partial set
   is not made complete by a writer's assertion.
4. Build a backend-owned prescription envelope: allowed choices/bounds,
   calculations, required evidence links, and prohibited choices.
5. Let the provider propose structured content within that envelope. Treat
   retrieved text as untrusted data. Keep existing provider adapters replaceable.
6. Validate decisions and session/week aggregates in domain services. Every
   material decision must resolve to an applicable rule and retrieved locator;
   adaptations validate their affected totals against the resulting whole plan.
   A targeted sheet is not silently treated as the client's entire weekly plan.
   Missing schedule context cannot produce invented weekly guarantees.
7. Retain existing schema, equipment, completeness, variation and duplicate
   checks. Automatic AI review is supplementary and cannot authorize unsupported
   content. Corrections obey the existing bounded retry budget.
8. Recheck exact revision, evidence/policy validity, and concurrency at the
   persistence boundary. Only a fully passing candidate becomes a previewable
   proposal. Persist the validation trace with the exact revision.
9. Otherwise discard the candidate and return a controlled reason. Do not emit
   its exercise table in chat, save partial operations, replace the saved draft,
   submit a review request, or alter approved history.

Keep `knowledge_status` and its four current values for bibliographic context.
Add a separate backend-owned prescription decision rather than overloading that
field. Candidate contract names to finalize in Task 48:
`prescription_eligibility`, `prescription_validation`, `reason_codes`,
`policy_version`, `validator_version`, and `evaluated_revision`.
Recommended reason categories: unsupported profile, ambiguous/missing input,
coverage gap, expired/unavailable evidence, unresolved conflict, out-of-policy
parameter, restriction conflict, invalid provenance, and stale revision.
These are product outcomes, not raw provider errors or new plan lifecycle states.
Use the methodological protocol's four distinct outcome categories: documented
restriction conflict, missing/ambiguous required input, insufficient applicable
support and technical unavailability. Lack of evidence or an external outage
does not establish harm or prohibit the client's exercise. Keep provenance,
parameter and concurrency errors as explicit subreasons. Clarification/recovery
may initiate a fresh validated attempt; none permits publishing a failed candidate.

Task 51 prespecifies sampling, reference judgments, error severity/costs and
release thresholds before held-out evaluation. Report supported/unsupported
acceptance, false rejection, reason correctness, cohort denominators and suitable
uncertainty estimates. Zero critical failures is a test-suite release condition,
not proof of zero real-world risk; an always-reject implementation cannot pass.

A retained saved draft may remain visible after an unsuccessful replacement;
the UI must distinguish it from the discarded attempt. Pre-extension AI drafts
are not automatically certified or deleted. Reuse/submission/approval as qualified
AI content requires current revalidation; explicit manual instructor authoring
clears AI qualification and preserves the existing professional workflow.
Approved historical/current plans are never silently rewritten or revoked.

## Dependencies and task order

| Task | Deliverable | Prerequisites | Canonical criteria |
| --- | --- | --- | --- |
| [45](tasks/45-training-evidence-discovery.md) | Prespecified methods, source appraisal, screening and coverage gaps | Read current knowledge/onboarding/training boundaries | EXT-CA-AI-02.1–2/14 |
| [46](tasks/46-training-evidence-ingestion.md) | Actual eligible downloads, extracted passages and embeddings | 45: eligible source subset | EXT-CA-AI-02.2–3 |
| [47](tasks/47-training-prescription-policies.md) | Evidence-to-decision records, reviewed rules and applicability matrix | 45–46; professional decisions for enabled cohorts | EXT-CA-AI-02.1/4/6–7/14 |
| [48](tasks/48-training-prescription-evidence-gate.md) | Coverage-aware retrieval, validation and versioned trace contracts | 46–47 | EXT-CA-AI-02.5–7/13 |
| [49](tasks/49-training-generation-abstention.md) | Shared atomic gate across every prescriptive AI path | 48; existing lifecycle/equipment contracts | EXT-CA-AI-02.8–10/13 |
| [50](tasks/50-training-evidence-review-ui.md) | Client abstention and instructor evidence-review UX | 49; existing MUI shells and review UI | EXT-CA-AI-02.11/13 |
| [51](tasks/51-training-prescription-verification.md) | Prespecified independent evaluation and limited release report | 45–50; professional/methodological evaluation decisions | EXT-CA-AI-02.12; integrated 1–14 |

Execute research and licensed acquisition without waiting for clinical ranges.
An absence of reusable/applicable evidence is a valid documented finding; it
does not authorize fabricated coverage or emptying negative cases from evaluation.
Task 46 requires actual indexing of an eligible subset to claim completion.
If no such subset exists, report the concrete blocker and leave ingestion open.
Unapproved cohorts stay disabled. Infrastructure/contracts can use explicitly
synthetic test policies while professional decisions are pending; those policies
must never enable real-client generation.

## Decision and completion boundaries

EXT-DEC-AI-02 requires a qualified professional's recorded decisions on supported
cohorts, prescription bounds, contraindications, required inputs, evidence
conflicts, and the independent evaluation rubric/release thresholds.
Methodological review of appraisal/certainty judgments and evaluation design is
also required; drafting this protocol is not evidence that review has occurred.
Do not ask for these again when already recorded for the affected scope. New dependency,
license, paid source, provider/model, retention, or architecture proposals need
their own explicit approval; none is necessary to write this specification.

Each task follows the repository task template: objective, RF/extension mapping,
rules/RNF/decisions, required reading, permitted scope, criteria, tests and a
ready-to-use prompt. Completion reports include changed files, exact checks and
results, important decisions, and unresolved issues. No commit/push is implied.
Real data acquisition is an operational run; deterministic tests use local
fixtures and fake embedding/writing adapters. Final verification must distinguish
software correctness, operational indexing, professional policy review, and
unmeasured individual effectiveness.
