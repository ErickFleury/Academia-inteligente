# Training evidence acquisition and recovery

Task 46, 2026-10-23. Uses the existing migration/bootstrap transaction and
fail-closed Compose dependencies. No degraded startup mode or clinical approval.
The technical report is [Task 46 evidence](tasks/46-training-evidence-ingestion-report.md).

## Reproduce acquisition and indexing

From the repository root, using the existing configured Compose environment:

```powershell
docker compose run --rm --no-deps backend python -m app.modules.knowledge.acquisition --refresh --publish
docker compose up -d postgres knowledge-ollama
docker compose run --rm knowledge-model
docker compose run --rm --no-deps backend python -m alembic upgrade head
docker compose run --rm --no-deps backend python -m app.modules.knowledge.ingestion
docker compose run --rm --no-deps backend python -m app.modules.training.prescription_feasibility
```

The acquisition command accepts no URL or source supplied by a user. It fetches
only Task 45 S4 official HTML, verifies redirects/content type/5 MB bound,
uses a 30-second request timeout and at most one retry, and respects bounded
Retry-After or defers. The publisher's public `/authorize` and `/transit`
cookie handshake is allowed only on `idp.springer.com`; no login, credentials,
challenge solving or bypass is implemented. The final document must be the
specified article on an allowed publisher host. No parallel/bulk crawling.

`backend/app/modules/knowledge/acquisition-s4.json` pins reviewed paragraph
hashes and locators. Complete Conclusions, Eligibility and Limitations paragraphs
form one 7,418-character passage; duplicated overlapping selections are not
indexed separately. This is a bounded static extraction, not dynamic passage
concatenation to evade the six-passage limit. No tables, figures, supplements,
dataset or instrument text is imported. Tables remain unextracted rather than
flattened without headers. No new parser/OCR dependency is used.

Inspect numeric statements against the publisher HTML/PDF before changing the
recipe. In this capture the conclusion's three worked examples and their program
durations, units, population scope and limitations were preserved together;
these are reported examples, not approved individual rules or inferred 1RM.
Any paragraph/rights drift blocks publication. A failed refresh leaves the prior
catalog and successful capture intact. Default acquisition resumes the last
capture only after verifying its byte hash; use `--refresh` to recheck current
publisher content. Resume is reproducibility, not a fresh notice/license check.

Raw HTML is stored under `backend/.cache/training-evidence/<sha256>.html`.
`s4-manifest.json` records bytes/hash/capture/rights/extractor/Python/recipe and
selection hashes. `s4-indexing.json` records committed vector rows, actual model
digest, timings and unchanged second-run calls. `development-retrieval.json`
records an exploratory search, **not reviewed cohort feasibility**. These caches
are excluded from Git and Docker images; the packaged catalog carries bounded
text and provenance, and the report retains public operational manifests.

The ingestion command requires PostgreSQL, runs the existing bootstrap in a
transaction twice and verifies vector counts/dimensions before reporting success.
Changed text receives embeddings; an unchanged second run requests none.
Failure rolls back its transaction; do not use a partial report as readiness.
This standalone command does not provision demo accounts or bypass normal startup.

## Runtime service outage after successful initialization

1. Inspect `docker compose ps` and `docker compose logs --tail 100 knowledge-ollama`.
   Keep client queries and medical data out of diagnostics.
2. AI requests depending on failed retrieval/embeddings must return controlled
   unavailability. Existing manual instructor APIs and `/health` remain available
   after successful initialization. The current pre-Task-49 writer behavior is
   unchanged; this runbook does not claim the future mandatory abstention gate.
3. Restore the service with `docker compose up -d knowledge-ollama`, then run
   `docker compose run --rm knowledge-model` if its approved model is missing.
4. Run the ingestion command above to verify integrity/idempotency; retry AI
   only after its dependencies recover. Never activate a training plan as a probe.

The isolated PostgreSQL recovery test exercises unavailable embeddings plus real
manual create/approve API requests on synthetic state. It does not prove live
writer behavior or production uptime.

## Failed bootstrap on an existing volume

1. Inspect `docker compose logs --tail 100 backend-init`. Migrations/bootstrap
   must exit successfully before backend/frontend startup; do not start the
   backend with `--no-deps` as a workaround.
2. Diagnose source review/provenance, embedding availability, schema compatibility
   and the current catalog manifest. The corpus transaction rolls back on failure;
   demo-account initialization/migrations have their own existing boundaries.
3. Restore the failed dependency or deploy the corrected approved catalog; rerun
   `docker compose up backend-init` and require exit code zero.
4. Run `docker compose up -d backend frontend` and verify `/health` and the
   recorded ingestion manifest. No manual API availability is promised while
   initialization is unsuccessful. Never delete a volume or reset clients.

## Last-known-valid catalog

Preserve a compatible known-good local catalog and its deployment/manifest hash
before a change. Keep the **latest** authoritative source removals, corrections,
licenses and review deadlines available independently of that fallback.

Place the proposed fallback at
`backend/.cache/training-evidence/catalog-fallback.json` and run:

```powershell
docker compose run --rm --no-deps backend python -m app.modules.knowledge.recovery --candidate .cache/training-evidence/catalog-fallback.json
```

This validator compares against the current packaged catalog: it rejects source
removal/revocation, changed licenses/identity, expired reviews, missing/changed
passages, inconsistent extraction hashes or an empty eligible corpus. It never
writes the catalog/database. The maintainer must additionally check current
publisher notices and any newer revocation/impact records; passing local checks
does not certify currency or scientific validity. Missing authoritative current
records leave recovery unavailable.

Only after these checks may the operator replace the packaged catalog with the
verified fallback, redeploy a schema-compatible version and rerun normal
initialization. Do not blindly downgrade Alembic, restore removed/corrected text,
extend review dates to make boot pass or infer that an older policy stays valid.
Revalidate affected policies separately before any future cohort reenablement.

## Fresh database without a valid corpus

Normal startup must remain unsuccessful until migrations and eligible bootstrap
finish. No backend, `/health` or manual authoring is promised before that point.
Repair acquisition/permissions/model availability and rerun normal initialization.
If no valid source/corpus is available, report unavailable readiness and preserve
the database; there is no authorized empty-corpus or degraded-startup shortcut.

## Isolated verification commands

Use `-p academia-evidence` for separate services/volumes; these are not the user's
normal application database. Do not point opt-in integration tests at live data.

```powershell
docker compose -p academia-evidence up -d postgres knowledge-ollama
docker compose -p academia-evidence run --rm knowledge-model
docker compose -p academia-evidence run --rm --no-deps -e TEST_POSTGRES=1 backend sh -c 'python -m pytest tests/test_knowledge*.py tests/test_prescription_policy.py tests/test_training*.py -q'
```

Tests use UUID-isolated schemas, local HTTP fixtures and fake external adapters.
They separately cover runtime manual availability, existing-corpus rollback and
recovery, fallback revocation/removal/expiry protection and fresh-corpus failure.
Startup tests verify failure propagation. Actual BGE-M3 indexing is a separate
operational command, not part of CI or an independent prescription evaluation.
Stop isolated services with `docker compose -p academia-evidence stop`; preserve
their volumes for inspection. No destructive reset is necessary.
