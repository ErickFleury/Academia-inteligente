# Licensed evidence expansion follow-up

The owner authorized further research/acquisition for the prescription gate.
`docs/requirements.md` EXT-CA-AI-02.1–5 and .14 remain authoritative. This
report distinguishes acquired evidence from completed vector indexing and from
professional prescription-policy approval.

## Acquired material

Nine article subsets were downloaded from Europe PMC's full-text XML endpoint.
Each captured artifact explicitly identifies CC-BY-4.0 permission in its JATS
permissions. The recipe pins authors, title, DOI, PMCID, article version,
selection boundaries and hashes. The public acquisition manifest records the
capture, license evidence, original artifact hash, extractor and passage hashes:
[`46-training-evidence-expansion-acquisition.json`](46-training-evidence-expansion-acquisition.json).

**Indexing scope:** complete original XML captures are retained locally, but only
the recipe's selected original-text passages are embedded. These are bounded
extractions, not AI-generated article summaries and not full-article indexing.
All nine articles are represented; their unselected sections are not searchable
through this corpus. Source/context boundaries and the listed exclusions apply
to every extraction.

| Source | PMCID | Passages | Research contribution; professional review pending |
| --- | --- | ---: | --- |
| Singer et al., 2024 | PMC11349676 | 3 | Inter-set rest and hypertrophy, with review limitations |
| Iversen et al., 2021 | PMC8449772 | 9 | Time-efficient resistance training: selection, dose and rest |
| Schumann et al., 2022 | PMC8891239 | 4 | Concurrent aerobic/resistance training and compatibility |
| Ingram et al., 2025 | PMC12152101 | 2 | Stretching mechanisms and scope; oversized result selection omitted |
| Smart et al., 2023 | PMC10015931 | 3 | Isometric exercise and hypertension; authors' protocol table |
| Su et al., 2026 | PMC13539497 | 14 | Exercise and diabetes; subtype, medication and applicability context |
| Lafontant et al., 2025 | PMC12107660 | 5 | Exercise/body-fat evidence with interpretation limits |
| Bao et al., 2026 | PMC13581003 | 1 | DEPP methods and limitations, not its underlying protocol database |
| Price et al., 2025 | PMC12186601 | 6 | Asthma/exercise context and limitations; adapted Table 3 excluded |

The catalog now contains 24 bibliographic records, 19 technically eligible
sources and 66 passages, including these 47 new passages. Technical review of
permission/extraction is **not** scientific appraisal or professional approval.
All enabled-cohort lists remain empty. None of these article titles authorizes
an individual prescription, medication adjustment or clinical combination.

## Coverage and exclusions

Resistance training/rest, concurrent training, fat loss and stretching have
additional material for appraisal. Diabetes, hypertension and asthma provide
condition-specific candidates only within their reported populations. The
eleven goal families and four experience levels still require the reviewed
coverage matrix and decision records; sport-specific, balance, autonomy and
clinical combinations cannot inherit unrelated support. Every medication,
injury or complaint combination remains awaiting explicit applicability review.

NC/ND candidates remain metadata-only under the existing license allowlist.
The JAMA aerobic-weight-loss candidate was not ingested because the captured
permission did not establish the required license version. A 2026 broad
clinical candidate was quarantined for an incomplete diastolic threshold in its
hypertension contraindications; no replacement number was invented. An
unavailable diabetes-tailoring endpoint was not imported. DEPP's database,
underlying publications, third-party illustrations and supplementary data were
not acquired by association with the article license.

## Reproduction and actual indexing status

From `backend/`, use the existing Python environment:

```text
python -m app.modules.knowledge.acquisition_expansion --publish
```

Cached original XML files reside under ignored `.cache/training-evidence/expansion/`.
`--refresh` requests the pinned official artifacts again. Publication validates
the whole batch before updating the catalog and preserves unrelated records.

The initial 40-passage layout passed 65 knowledge/PostgreSQL tests, but real
BGE-M3 embedding rejected a passage exceeding Ollama's physical token-batch
limit. That transaction rolled back. An experimental model-option adjustment
was reverted. The final 47-passage layout uses shorter complete paragraph
selections, retaining original eligibility/limitation context; one oversized
selection is explicitly omitted in the recipe.

Docker subsequently became stuck in startup and its container API timed out.
Infrastructure recovered on the 2026-10-24 follow-up. Migration `20261023_35`
and final-layout indexing then completed in the isolated `academia-evidence`
PostgreSQL database, preserving the normal application database and volumes.

The [actual indexing manifest](46-training-evidence-expansion-indexing.json)
records 66 committed `vector(1024)` rows. The first run embedded 47 new texts in
three calls (251.802 seconds); the unchanged second run made zero embedding calls
(0.105 seconds). BGE-M3 digest is
`7907646426070047a77226ac3e684fbbe8410524f7b4a74d02837e43f2146bab`;
catalog SHA-256 is
`75d95cd342a4c99794e1cd712c3cb5f259530ed15263111399b29a6257c1297f`.
These timings are this local run, not an end-to-end performance acceptance result.

Reproduce against the isolated database after starting PostgreSQL and the existing
BGE-M3 service:

```text
docker compose -p academia-evidence run --rm --no-deps backend python -m alembic upgrade head
docker compose -p academia-evidence run --rm --no-deps backend python -m app.modules.knowledge.ingestion --report-name expansion-indexing
```

The command executes atomic bootstrap twice, checking committed vector
count/dimensions and unchanged-run idempotency. Run database-bootstrap tests
**after** ingestion completes: bootstrap uses a database-wide advisory lock even
when tests have separate schemas. An initial concurrent suite hit this lock and
is not considered a clean verification run.

## Expanded-corpus technical retrieval

The [retrieval manifest](46-training-evidence-expansion-retrieval.json) records
nine implementer-authored topic queries against the real PostgreSQL hybrid search
and BGE-M3 provider. All nine retrieved their respective target source within six
passages. Warm-query times were 0.105–0.179 seconds. This is a technical smoke
check with known source topics, not a reviewed development-case experiment or an
independent relevance, applicability, prescription or dimension-coverage judgment.
No writer was invoked and no client plan was created or activated.

The exact [probe script](46-training-evidence-expansion-probe.py) can be run from
the repository root with PowerShell:

```powershell
Get-Content -Raw docs/tasks/46-training-evidence-expansion-probe.py | docker compose -p academia-evidence run --rm -T --no-deps backend python
```

Public manifests are copies of the ignored local operational evidence under
`backend/.cache/training-evidence/`. No independent held-out cases were supplied
or accessed. Scientific approvals and all enabled-cohort lists remain pending
and empty respectively. The six-passage limit, providers and architecture remain
unchanged.
