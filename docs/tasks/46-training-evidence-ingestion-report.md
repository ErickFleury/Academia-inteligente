# Task 46 ingestion report — 2026-10-23

**Status:** acquisition/indexing and recovery tooling implemented and verified
within the bounded S4 subset. Scientific appraisal, named human governance and
professional prescription policy approval remain pending. No cohort enabled.

## Acquisition and extraction

Downloaded S4 official publisher HTML, DOI `10.1007/s40279-026-02432-5`, article
version 2026-04-17. CC BY 4.0 and third-party exceptions were checked at the
[publisher Rights and permissions section](https://link.springer.com/article/10.1007/s40279-026-02432-5#rightslink).
The [publisher PDF](https://link.springer.com/content/pdf/10.1007/s40279-026-02432-5.pdf)
was consulted for extraction cross-checks; HTML was the captured/extracted
artifact, not a PDF/OCR conversion. No paid service, new dependency or provider.

- Capture: `2026-10-23T14:46:06.577329+00:00`, 486,495 bytes.
- Raw HTML SHA-256: `02eba4f1486e7a2a37949fb29bc3e2677699184bbc91651270a8e911f1465711`.
- Extractor: `springer-heading-paragraphs/1`, standard-library HTMLParser.
- Selection: one passage `lyristakis-strength-2026-dosage`, 7,418 characters;
  complete Conclusions (Sec16), eligibility (Sec5) and limitations (Sec15).
- Normalized text SHA-256: `a70e48b3b4b960c873303491abda2ea237c401e408f3dcc02aefa3b1bf5e5796`.
- Numeric worked examples retain durations/units and the accompanying eligibility
  and caveats. No claim of an individual optimum, 1RM or approved range is made.
- Acquired: one article; accepted: one bounded text selection; rejected eligible
  artifacts: zero. Task 45 metadata-only sources/supplements/datasets were never
  requested/imported. A redundant overlapping selection was removed before
  packaging, rather than indexed as independent evidence.

The [acquisition manifest](46-training-evidence-acquisition.json) preserves the
license statement, raw hash, attribution linkage, Python/extractor version,
recipe hash and selection locator/hash. The packaged catalog retains the same
provenance and complete author attribution, modification notice and technical
review deadline 2027-10-23. Technical review is explicitly Codex-assisted, not a
named professional appraisal or a completed maintainer assignment. Raw captures
remain in the ignored local cache, outside Git and Docker images.

## Actual indexing and idempotency

Executed on isolated Compose project `academia-evidence`, PostgreSQL database
`evidence_final`, with the repository's PostgreSQL/pgvector image and migrations
through `20261017_34`. No production/client records were read or altered.

```powershell
docker compose -p academia-evidence up -d postgres knowledge-ollama
docker compose -p academia-evidence run --rm knowledge-model
docker compose -p academia-evidence build backend
```

The isolated `evidence_final` database was created through the container's
`createdb -U "$POSTGRES_USER" evidence_final`. With `POSTGRES_DB=evidence_final`
temporarily set for these Compose runs (the original environment was restored):

```powershell
docker compose -p academia-evidence run --rm --no-deps backend python -m alembic upgrade head
docker compose -p academia-evidence run --rm --no-deps backend python -m app.modules.knowledge.ingestion
docker compose -p academia-evidence run --rm --no-deps backend python -m app.modules.training.prescription_feasibility
```

The acquisition ran locally with the existing Python executable:

```powershell
cd backend
.venv/Scripts/python.exe -m app.modules.knowledge.acquisition --refresh --publish
.venv/Scripts/python.exe -m app.modules.knowledge.acquisition --publish
```

The second acquisition command verified/resumed cached original bytes and
republished after correcting pt-BR limitation metadata; no new source extraction
or review was invented. An earlier isolated initial indexing run was repeated
on the fresh `evidence_final` database to bind the final manifest to exact final
catalog bytes.

| Evidence | Final operational result |
| --- | --- |
| Catalog SHA-256 | `c6f0448559ae7e53168e21c7f4415e1b9001a585e66b01628e1930c975b9fb54` |
| Sources / passages | 15 bibliographic records, 10 technically approved sources, 19 passages; increment is one source/one passage |
| Embedding model | BGE-M3, 1024 dimensions, digest `7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab` |
| Fresh first run | 19 texts, two embedding calls; 19 committed vectors; 5.587 seconds |
| Unchanged second run | 19 vectors, zero texts/calls; 0.038 seconds |
| Retrieval probe | S4 selected first among six final passages; 8,608 context characters; 0.106 seconds |

The [indexing manifest](46-training-evidence-indexing.json) records every managed
passage's embedding-content hash/model/dimensions. This is actual BGE-M3 proof,
separate from fake-provider CI. The [development probe](46-training-evidence-development-retrieval.json)
is **not** reviewed prescription feasibility: zero reviewed cases, no applicable
rule/dimension reference set, no writer call, no enabled policy/cohort. Its
bibliographic `supported` value cannot establish prescription eligibility.

## Verification and recovery

The acquisition fixtures cover content type/size, unexpected redirects, retry
limits, denied access, NC/unknown rights, missing sections, extraction drift,
cache integrity, path traversal, manifest mismatch and publication preservation.
Bootstrap checks packaged selection integrity before embedding; revoked sources
remain removable even when their old text is invalid. Reconciliation uses the
existing transaction and leaves historical citation snapshots/private sources
unchanged.

The [recovery runbook](../training-evidence-recovery.md) gives exact acquisition,
startup, existing-volume, last-known-valid and fresh-database procedures.
PostgreSQL tests use isolated schemas to verify failed-batch rollback, service
restoration, no revoked/removed/changed/expired fallback content, and actual
manual create/approve API availability during embedding outage. Fresh startup
failure propagates rather than announcing readiness. These injected-failure
checks are not a production outage or a live-writer evaluation.

The broader knowledge/policy/training suite passed **488 tests** with
`TEST_POSTGRES=1`; **45** targeted acquisition/recovery/policy/startup checks
passed after final hardening (see the integrated
[verification status](51-training-prescription-verification-report.md)).
Ruff checks passed. No frontend changes/build or live-writing-provider tests
were required/run. Initial local Python could not import SQLAlchemy; application
tests/indexing therefore used the existing Docker dependencies, with no added
dependency. The standalone standard-library acquisition remained usable locally.

The canonical requirements, existing plan lifecycle and writing providers were
not changed. Raw caches/models are untracked. No commit/push. Named technical
maintenance, notice refresh, final source appraisal and policies are explicit
handoffs; this technical ingestion does not close Tasks 47–51.
