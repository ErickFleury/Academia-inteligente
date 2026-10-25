# Task 46 — Licensed Training Evidence Download and Vectorization

**Status:** bounded technical implementation and actual indexing verified on
2026-10-23; professional appraisal/governance remain separate open gates.
**Feature task:** EVID-IMPL-02.

Evidence: [ingestion report](46-training-evidence-ingestion-report.md), public
acquisition/indexing manifests and [recovery runbook](../training-evidence-recovery.md).
S4 text was acquired and indexed with real BGE-M3; unchanged second run made no
embedding requests. No prescription cohort or release was approved.

## Objective

Actually download the eligible Task 45 subset, extract verifiable passages and
index them through the project's existing embedding and knowledge bootstrap.

## Requirements covered

- EXT-RF-AI-02: EXT-CA-AI-02.2–3/21; corpus handoff for .18/22.
- RF-15/CA-15.7, RF-18/CA-18.6–7 and RF-19/CA-19.5, shared RAG integration.

## Related rules and constraints

RN-11, RN-23, RN-29, RN-32/33; RNF01/04–06; DEC-08/18 and EXT-DEC-AI-02.
Preserve commercial-reuse allowlist, reviewed-source filtering, 1024-dimensional
BGE-M3 embeddings and zero-to-six retrieval. Technical review is not professional
prescription approval. No new paid service, dependency or vector database.

## Prerequisites and required reading

Task 45 has identified at least one eligible artifact. Read `AGENTS.md`, the
feature overview, Task 45 results, EXT-RF-AI-02, the listed RF/CA/rules/RNF and
decisions, complete approved RAG contract, and canonical sections 6.1.1/9.2.
Inspect `knowledge/{catalog.json,models.py,bootstrap.py,startup.py,service.py}`,
`integrations/embeddings.py`, Compose startup, Alembic conventions and knowledge
tests. Reuse existing implementation rather than building another indexing stack.
Read the [methodological protocol](../training-evidence-methodology.md), sections
1–3 and 7. Use Task 45's scientific and acquisition statuses separately; eligible
indexing is not approval to prescribe. Important non-ingestible evidence stays a
documented gap, and methodological tools are not automatically importable content.
Read [the execution contracts](../training-prescription-execution-contracts.md),
sections 4 and 6–7, including the preserved fail-closed startup boundary.

## Permitted scope and expected behavior

1. Add a reproducible acquisition command in the existing backend/script layout.
   Use approved public URLs/official acquisition APIs and documented rate limits,
   bounded timeouts/retries and safe resume. Verify allowed redirect destinations,
   content type, artifact size and integrity; do not add a user-supplied URL fetcher.
2. Capture original artifact and license evidence, timestamp, stable identifier,
   revision, hash and extraction-tool version in a manifest. Keep raw caches out
   of Git; package only approved bounded text and required attribution through
   existing catalog conventions, retaining traceability to original snapshots.
3. Prefer reusable structured full text. Preserve sections, table headers/units,
   population exclusions and caveats. Verify extraction against the source,
   particularly numeric ranges and dose tables. If reliable extraction needs an
   unapproved parser/OCR dependency, report it; quarantine that artifact meanwhile.
4. Produce chunks with exact section/table/page locators and source hashes.
   Keep recommendations with their conditions/limitations; avoid orphaned numbers.
   Deduplicate source versions/identifiers and overlapping imported passages.
   Translations/summaries retain original provenance and adaptation notices.
5. Extend the existing idempotent bootstrap only as needed. Reuse unchanged
   embeddings; re-embed changed content; exclude revoked/removed/expired content
   from new retrieval. Preserve historical citation snapshots and private sources.
6. Perform the actual acquisition/indexing on an appropriate local environment.
   Record sources/files/chunks acquired, rejected counts/reasons, model/dimensions,
   hashes, vector counts, and a second-run idempotency result. Reconcile failed
   batches atomically; never announce a complete corpus from a partial import.
7. Create the concrete recovery runbook for runtime outages, failed bootstrap
   on an existing volume, last-known-valid catalog recovery and a fresh database
   without a valid corpus. Preserve startup failure/readiness behavior; manual
   endpoints are promised only after successful initialization. Include exact
   repository-standard commands/manifests, rollback verification and integrity
   checks; do not delete volumes, blindly reverse migrations or restore revoked/
   expired sources. If no valid fallback exists, report unavailable readiness.
8. Give Task 47 a reproducible corpus/embedding manifest and a development-only
   retrieval experiment harness; never acquire held-out evaluation answers as
   corpus text. Preserve source-to-policy impact identifiers for maintenance.

Permitted areas: backend knowledge/embedding integration, acquisition scripts,
focused migrations/tests, packaged catalog and ingestion/runbook documentation.
No generation-policy changes or new corpus-management UI.

## Acceptance criteria

- EXT-CA-AI-02.2: unlicensed, NC, pending, corrupted and failed-extraction content
  does not enter embeddings or writer context; artifact provenance is verifiable.
- EXT-CA-AI-02.3: the eligible subset is actually downloaded and has validated
  `vector(1024)` rows in PostgreSQL; a fake-adapter test is not operational proof.
- An unchanged second run requests no replacement embeddings; changed text is
  re-embedded, removals/revocations stop retrieval and failures preserve the prior
  consistent corpus. Fresh and existing-volume startup paths remain valid.
- No artifact containing participant/client records is imported into shared data.
- EXT-CA-AI-02.21: runbook and isolated checks distinguish runtime availability
  from startup failure; valid recovery preserves data, source revocations and
  existing bootstrap guarantees. No degraded-startup mode is introduced.

## Tests and validation

Use local HTTP/document fixtures and fake embeddings for acquisition errors,
license exclusion, hash/extraction failures, deduplication, retries and rollback.
Run affected `test_knowledge*` tests, including real-PostgreSQL migration/search
checks with fake providers. Separately run the operational acquisition/indexing
and record exact commands/results without secrets. Review Git diff and caches.
Exercise all four recovery paths on isolated state; failures must retain truthful
readiness and never make revoked/expired content retrievable.

## Completion requirements

Report files, tests, actual download/vector counts, idempotency evidence and gaps.
If every source is ineligible/unavailable, report the blocker and leave actual
ingestion incomplete. No commit/push or clinical-coverage claim.

## Ready-to-use Codex prompt

Read `AGENTS.md`, this task, its Required reading and Task 45 evidence. Reuse the
approved knowledge stack to implement and run reproducible eligible acquisition,
extraction and indexing. Do not ingest metadata-only text or add dependencies
without approval. Run fixture/PostgreSQL checks separately from the operational
download, review the diff, and report files, tests, acquired/indexed counts,
decisions and unresolved issues in at most 10 lines. Do not commit or push.
