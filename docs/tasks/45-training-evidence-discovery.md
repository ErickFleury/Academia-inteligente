# Task 45 — Training Evidence Discovery and Coverage Review

**Status:** research/documentation delivered on 2026-10-23; final human appraisal
and named governance pending (task not fully complete). **Feature task:** EVID-IMPL-01.

Execution evidence: [source review and coverage matrix](../training-evidence-source-review.md)
and [prespecified protocol 1.2](../training-evidence-methodology.md). The report
records the S4 article-text acquisition subset for Task 46, source/access/license
gaps, input inventory and early evaluation design. EXT-CA-AI-02.14/22 remain open
for independent human judgments and actual named assignments; no cohort or
release is approved and no corpus/runtime change is claimed.

Follow-up verification F1 (2026-10-23) is recorded in source review 1.1, section
11: protocol/catalog hashes reconfirmed, S4 article rights rechecked, S8 identity
resolved from indexed primary metadata, access limitations retained. Final human
appraisal and named assignments remain open; this is not a full-task completion.
The user designated the instructor profile for professional review; the source
review responsibility register records this role without inventing a named
reviewer, competence declaration or independent sign-off.

## Objective

Find evidence collections that can fill prescription gaps and document exactly
which goals, experience levels, populations, and restrictions they can support.

## Requirements covered

- EXT-RF-AI-02: EXT-CA-AI-02.1–2/14; design handoffs for .15/17/19/22.
- RF-15/CA-15.5/7–8, RF-18/CA-18.6–7, RF-19/CA-19.5 as consumed boundaries.

## Related rules and constraints

RN-11–RN-15, RN-19, RN-23, RN-29–RN-31; RNF04/RNF06; DEC-07/08/15/18 and
EXT-DEC-AI-02. No clinical ranges, source licenses, or professional approvals
may be invented. Do not submit real client data to literature search services.

## Prerequisites and required reading

Read `AGENTS.md`, `docs/evidence-qualified-training-specification.md`, and the
listed canonical RF/CA, EXT-RF-AI-02, related rules, RNF and decisions in
`docs/requirements.md`, including the complete approved RAG contract and sections
6.1.1 and 9.2. Inspect the knowledge catalog/models/service, training retrieval,
onboarding schema and existing RAG tests. Supporting history is not authoritative.
Read [the methodological protocol](../training-evidence-methodology.md), including
its primary methods references. Consult the appropriate instrument instructions
before applying it; a citation to the instrument is not a completed appraisal.
Read [the execution contracts](../training-prescription-execution-contracts.md),
sections 1, 3 and 7–8, for early evaluation, input inventory and named ownership.

## Permitted scope and expected behavior

1. Finalize a dated snapshot of `docs/training-evidence-methodology.md` before
   substantive selection. Prespecify PICO questions, search limits, eligible
   designs/outcomes, appraisal methods/versions, reviewers, disagreement handling,
   certainty assessment and amendments. Label project adaptations honestly.
2. Create `docs/training-evidence-source-review.md`. Record dated search
   strategies, exact queries, consulted services, screening criteria, results,
   exclusions and limitations. Start from the overview's primary-source links;
   independently verify current content and reuse conditions.
3. Audit the existing corpus against exercise selection, volume, intensity,
   frequency, progression, rest and restriction adjustments. Search guidelines,
   reviews, trials and their supplementary datasets for missing dimensions.
   Exercise/media catalogs may supplement selection; they cannot establish dose.
4. Record title, authors, identifier/URL, publication/version dates, study design,
   population, outcomes, parameter detail, certainty/limitations, conflicts or
   retractions, full-text location, artifact-level license and access method.
5. Separate discovery databases, individual evidence documents, and raw datasets.
   Check whether a dataset actually encodes prescription/outcome data and whether
   participant-level sensitive data can be excluded. No personal dataset import.
6. Apply AGREE II, AMSTAR 2 or RoB 2 only to the appropriate material/result;
   justify other methods for other designs. Record domain judgments and use
   GRADE for outcome-specific certainty across the relevant body of evidence.
   Preserve overlap between studies/reviews and independent human assessments/
   adjudication. AI assistance cannot supply missing reviewer sign-off. Do not
   replace these judgments with a total score or PRISMA checklist completion.
7. Produce the initial coverage matrix using the actual four experience levels
   and explicitly proposed goal families. Include restriction interactions,
   unknown goals and missing population data. Do not enumerate actual clients.
8. Classify candidates as eligible for ingestion, metadata-only, excluded, or
   pending professional review. Separate technical permission from prescription
   applicability. Record gaps even when no suitable source exists.
9. Present the bounded eligible subset for Task 46 and the concrete professional
   decisions required in Task 47. Do not call the literature review exhaustive.
   Retain scientifically important but non-ingestible sources as explicit gaps;
   do not silently substitute weaker evidence because its license is convenient.
10. Create the protocol's criterion register distinguishing scientific criteria,
    technical limits and product policies, with references, rationale, review
    status and verification plans. Hand certainty/applicability results to Task
    47 and prespecified outcome definitions to Task 51.
11. Name the project/release owner, methodological/professional reviewers,
    independent evaluator/adjudicator and technical maintainer. Record competence,
    conflicts, independence, availability, effort/resource plan and approval
    responsibilities; do not create fictitious sign-offs. Propose a bounded first
    cohort slice tied to available inputs and evidence instead of promising all
    goals/levels at once. Unassigned reviewers leave final approval pending.
12. Inventory actual authorized input fields and existing clarification paths.
    Record available/missing data, ownership and confirmation needs for Task 47.
    Draft the independent evaluation protocol now: questions, outcome definitions,
    sampling/partition strategy, reference judgments, candidate operational repeat/
    resource budgets, and held-out custody. Task 47 must seal the reviewed plan
    before Task 48 implementation; Task 51 executes it, not designs it from scratch.

Only documentation changes and small local screening manifests under existing
knowledge-module conventions are permitted. No corpus import, runtime refactor,
provider/model change, paid subscription or new dependency belongs here.
Provisional research/acquisition candidates can be documented while reviewers
are unavailable; final appraisal completion must remain explicitly pending.

## Acceptance criteria

- EXT-CA-AI-02.1: every proposed cohort/dimension has a status, rationale and
  source locator or a documented gap; unknown/combined profiles are addressed.
- EXT-CA-AI-02.2: every download candidate has verified artifact-level permission
  under the current allowlist and a supported acquisition route; ambiguous/NC
  sources are metadata-only. Search availability is not recorded as reuse rights.
- Another developer can repeat the recorded searches and understand why each
  candidate was included/excluded. No claim of reliable individual personalization.
- EXT-CA-AI-02.14: dated protocol, PICO/search records, design-appropriate appraisal,
  outcome certainty, overlap and criterion register are present. Final material
  judgments have independent reviewer/adjudication records; missing review leaves
  final appraisal incomplete. Neither an allowed license nor a recent publication
  is treated as scientific quality. No method is claimed to have been applied
  merely because its name appears in the report.
- EXT-CA-AI-02.17/19/22: input-source inventory, named responsibility/resource
  register and early evaluation protocol exist with honest pending statuses.
  Held-out data/answers have an independent custodian and are excluded from
  implementation prompts, public fixtures and runtime evidence.

## Tests and validation

Documentation/source verification only: check identifiers, links, license
statements, protocol version/amendments, appraisal records and reviewer status,
search reproducibility, matrix completeness, and absence of client
data. Report inaccessible text and unresolved rights. Do not run live-provider
tests or add tests that merely check prose formatting. Review the Git diff.

## Completion requirements

Report files changed, sources/services checked, decisions and unresolved gaps.
Research can finish with unsupported cohorts; pending rights, appraisal and
professional reviews must remain explicit and affected completion criteria open.
Do not commit or push.

## Ready-to-use Codex prompt

Read `AGENTS.md`, this task and its Required reading. Inspect the current corpus
and prescription inputs. Prespecify the methodological protocol, execute bounded
primary-source research, and create appraisal/criterion records, source review
and coverage matrix. Establish input readiness inventory, named governance and
early independent evaluation design for Task 47 sealing. Modify only this task's
scope. Do not
download a bulk corpus, implement generation, invent clinical approval or change
technology. Verify source/license evidence, review the diff, and report files,
checks, decisions and gaps in at most 10 lines. Do not commit or push.
