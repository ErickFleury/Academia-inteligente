# Hypertrophy qualitative-load remediation: implementation delivery

Subsequent 2026-10-25 follow-up: optional multi-day scheduling is implemented and
verified in the [A/B/C delivery](51-optional-three-day-delivery-20261025.md). The
results below remain the historical single-session experiment for this remediation.

Date: 2026-10-25. Owner request: implement the [specific remediation](../training-hypertrophy-load-remediation-spec.md) and provide an actual hypertrophy sheet. Canonical scope: owner-assisted RAG and EXT-CA-AI-02.27?29/31?33.

## Outcome

**Implemented and verified: five of five frozen actual-provider hypertrophy repetitions produced reviewable qualitative-load drafts.** Each used one writer and one automatic-review HTTP call, without content correction, and saved exactly one isolated proposal. None was activated. The original failed kg-bearing candidates remain unchanged in their historical reports.

The full backend suite, including opt-in PostgreSQL cases, returned **1,206 passed in 149.99 seconds**. The focused owner-RAG/load suite returned **40 passed**; related generation/chat/adaptation/prescription checks returned **111 passed** before the final full suite. Ruff lint and formatting checks passed for all ten affected Python files. No frontend code changed; no new frontend or manual visual verification is claimed.

## What changed and why

- The technical exercise dictionary now identifies bodyweight versus external equipment with unmeasured load. The writer schema offers closed pt-BR qualitative values instead of unrestricted load prose. It cannot prescribe numeric kg, alternate weight units, spelled-out weights or measured capacity through that field. Backend checks also verify each choice against its exercise. No clinical dose was added.
- A pure shared validator checks load before the automatic exercise review, inside the existing single-correction loop. Unsupported generated content receives exact item/field/allowed-choice feedback. A load correction must preserve all other prescription fields; review/schema/load errors share one correction allowance. The final binding check remains authoritative.
- Explicit requests for calculated or measured external loads still require missing-input clarification. This change does not implement measured-load calculation or derive it from body mass, height, experience or retrieved study examples.
- Generation, draft chat edits and adaptations use the same validator. Exact server-snapshotted items of an approved adaptation base retain their historical representation through content hashes; changed items must meet the new contract. The complete resulting plan is checked, and a change to a retained item removes that exact-item exception. No approved base is rewritten.
- The authorization binds the new dictionary and `owner-assisted-rag-3 / owner-rag-4` writer configuration to the owner's actual implementation instruction. Source/rule approval hashes did not change. Older AI bindings with different authorization/configuration/dictionary hashes require regeneration or the existing manual path. There are no new dependencies, API fields, database columns or automatic plan activations.

## Verification against the spec

| Acceptance | Evidence |
| --- | --- |
| HYP-LOAD-01/03 | Five actual qualitative drafts; deterministic repair-to-qualitative regression; final binding guard |
| HYP-LOAD-02 | Invalid load is rejected before review; exact position/field/allowed feedback; two candidates at most |
| HYP-LOAD-04 | Invalid/exhausted correction and valid-field-change regressions; existing draft, revision and submission state preserved |
| HYP-LOAD-05 | Four explicit mandatory-measurement request cases; source numeric example/demographics cannot supply a baseline |
| HYP-LOAD-06 | Closed schema, equipment mismatch and eight unrestricted/numeric/spelled-out bypass cases |
| HYP-LOAD-07 | Initial, chat repair/replay, full adaptation, preserved approved history, dependency/submission revalidation and configuration-change regressions |
| HYP-LOAD-08 | Actual citations and source/rule/content hashes checked for all five drafts; professional/independent/compiled-qualification flags remain false |
| HYP-LOAD-09 | Mixed schema/load/review correction tests plus existing shared HTTP/deadline budget regressions in the complete suite |

## Frozen actual-provider experiment

Command: `docker compose exec -T backend python scripts/probe_owner_rag_runtime.py --matrix --case initial-hypertrophy --repetitions 5`.

Each synthetic profile was intermediate, with hypertrophy as its explicit goal, 170 cm / 70.50 kg and no reported conditions, medications or limitations. No individual external-load baseline or weekly schedule was supplied. Public PostgreSQL/BGE-M3 retrieval was real and read-only; client/proposal state was in-memory SQLite. The same configured `qwen3:4b` model was retained. Each writer received six complete passages. All runtime implementation fingerprints stayed unchanged during the experiment.

| Repetition | Outcome | Seconds | Writer / review calls | Exercise count |
| --- | --- | --- | --- | --- |
| 1 | proposal, not activated | 58.251 | 1 / 1 | 3 |
| 2 | proposal, not activated | 22.481 | 1 / 1 | 5 |
| 3 | proposal, not activated | 21.410 | 1 / 1 | 6 |
| 4 | proposal, not activated | 16.874 | 1 / 1 | 4 |
| 5 | proposal, not activated | 18.029 | 1 / 1 | 4 |

Median: 21.410 seconds; mean: 27.409 seconds. The full backend suite ran concurrently; these timings are exposed diagnostics, not an isolated performance benchmark.

Additional actual controls (`ambiguous-goal`, `retrieval-outage`) both rejected with zero model calls and zero proposals. Source/input/content bindings and the original permission/freshness filters remain active.

## Actual generated sheets

All outputs below are single-session A drafts for synthetic profiles. They have no professional or independent appraisal and claim no compiled clinical qualification. Qualitative external load is intentionally awaiting ordinary instructor review; it is not a measured or recommended kg value.

### Repetition 1

Treino para Hipertrofia Muscular (Intermediário)

Generated objective: Hipertrofia muscular

| Exercise | Sets | Repetitions | Load guidance | Rest (seconds) |
| --- | --- | --- | --- | --- |
| Agachamento com peso corporal (Dia A) | 3 | 8-12 | Peso corporal | 120 |
| Flexão de braços (Dia A) | 3 | 8-12 | Peso corporal | 120 |
| Remada curvada com halteres (Dia A) | 3 | 8-12 | Halteres; carga a definir na revisão do instrutor. | 120 |

Cited passages: `biga-anatomy-1`, `iversen-time-efficient-2021-06`, `iversen-time-efficient-2021-03`, `iversen-time-efficient-2021-07`.

### Repetition 2

Treino para Hipertrofia Muscular - 3 dias completos

Generated objective: Hipertrofia muscular

| Exercise | Sets | Repetitions | Load guidance | Rest (seconds) |
| --- | --- | --- | --- | --- |
| Elevação de panturrilhas em pé (Dia A) | 2 | 8-12 | Peso corporal | 60 |
| Flexão de braços (Dia A) | 2 | 8-12 | Peso corporal | 60 |
| Remada curvada com halteres (Dia A) | 2 | 8-12 | Halteres; carga a definir na revisão do instrutor. | 60 |
| Agachamento goblet com halter (Dia A) | 2 | 8-12 | Halteres; carga a definir na revisão do instrutor. | 60 |
| Abdominal curto (Dia A) | 2 | 8-12 | Peso corporal | 60 |

Cited passages: `biga-anatomy-1`, `iversen-time-efficient-2021-06`, `iversen-time-efficient-2021-03`, `iversen-time-efficient-2021-07`.

### Repetition 3

Treino para Hipertrofia muscular (Intermediário)

Generated objective: Aumentar o diâmetro das fibras musculares através de resistência controlada e sobrecarga progressiva, sem dor ou lesão.

| Exercise | Sets | Repetitions | Load guidance | Rest (seconds) |
| --- | --- | --- | --- | --- |
| Elevação de panturrilhas em pé (Dia A) | 2 | 8-12 | Peso corporal | 60 |
| Rosca direta com halteres (Dia A) | 2 | 10-15 | Halteres; carga a definir na revisão do instrutor. | 60 |
| Flexão de braços (Dia A) | 2 | 12-15 | Peso corporal | 60 |
| Agachamento goblet com halter (Dia A) | 2 | 8-12 | Halteres; carga a definir na revisão do instrutor. | 60 |
| Remada curvada com halteres (Dia A) | 2 | 10-15 | Halteres; carga a definir na revisão do instrutor. | 60 |
| Abdominal curto (Dia A) | 2 | 12-15 | Peso corporal | 60 |

Cited passages: `biga-anatomy-1`, `iversen-time-efficient-2021-06`, `iversen-time-efficient-2021-03`, `iversen-time-efficient-2021-07`, `nhs-strength-1`, `biga-anatomy-2`.

### Repetition 4

Treino para hipertrofia muscular - intermediário

Generated objective: Hipertrofia muscular

| Exercise | Sets | Repetitions | Load guidance | Rest (seconds) |
| --- | --- | --- | --- | --- |
| Agachamento com peso corporal (Dia A) | 3 | 8-12 | Peso corporal | 120 |
| Flexão de braços (Dia A) | 3 | 8-12 | Peso corporal | 120 |
| Remada curvada com halteres (Dia A) | 3 | 8-12 | Halteres; carga a definir na revisão do instrutor. | 120 |
| Abdominal curto (Dia A) | 2 | 10-15 | Peso corporal | 60 |

Cited passages: `biga-anatomy-1`, `iversen-time-efficient-2021-06`, `iversen-time-efficient-2021-03`, `iversen-time-efficient-2021-07`, `nhs-strength-1`.

### Repetition 5

Proposta de treino para hipertrofia muscular

Generated objective: Aumentar o diâmetro das fibras musculares através de treinamento resistido com foco em músculos específicos e corpo inteiro, seguindo orientações de tempo eficiente para adultos com experiência intermediária.

| Exercise | Sets | Repetitions | Load guidance | Rest (seconds) |
| --- | --- | --- | --- | --- |
| Agachamento com peso corporal (Dia A) | 3 | 8-12 | Peso corporal | 120 |
| Flexão de braços (Dia A) | 3 | 8-12 | Peso corporal | 120 |
| Remada curvada com halteres (Dia A) | 3 | 8-12 | Halteres; carga a definir na revisão do instrutor. | 120 |
| Abdominal curto (Dia A) | 2 | 10-15 | Peso corporal | 60 |

Cited passages: `biga-anatomy-1`, `iversen-time-efficient-2021-06`, `iversen-time-efficient-2021-03`, `iversen-time-efficient-2021-07`, `nhs-strength-1`.

## Deployment and compatibility

After both experiments and the full suite completed, local backend was force-recreated with `docker compose up -d --no-deps --force-recreate backend`. Its health endpoint returned `status: ok`; current owner-RAG authorization/configuration and `technical_verification_status: passed` were verified. A post-restart read-only audit still found 66 vectors, 37 accepted rules and authorization for the assisted scope. Zero compiled clinical policies/seals remain truthful and are not assisted-RAG prerequisites. No volume reset or real-client generation was performed.

## Changed files

| Area | Files |
| --- | --- |
| Shared load/domain contract | `backend/app/modules/training/owner_rag_load.py` (new), `owner_rag_schema.py`, `owner_rag.py`, `owner-rag-exercises.json`, `owner-rag-authorization.json` |
| Shared correction and workflow integration | `selection.py`, `generation_service.py`, `chat_service.py`, `adaptation_service.py` |
| Tests | `backend/tests/test_owner_rag_load.py` (new), `test_owner_rag.py` (canonical positive fixtures and stronger exhausted-load rejection) |
| Actual-provider diagnostics | `backend/scripts/probe_owner_rag_runtime.py` (frozen repetitions, case IDs, expected load mode and universal proposal counts) |
| Documentation | Specific specification status, this delivery, summary and preserved new plan/progress/result/readiness artifacts |

No commit or push was performed. Pre-existing unrelated changes were preserved. Tests and source files elsewhere in the dirty workspace are not attributed to this request.

## Limits and unresolved work

No known failure remains for this spec's tested qualitative-load scope. Numerical measured-load prescription remains a separate capability. Five exposed synthetic successes do not establish universal generation reliability, clinical validity, weekly-volume adequacy or professional efficacy. The previously observed endurance-rule discrepancy is a separate unresolved scope; this delivery does not claim to fix it.

## Artifacts

- [All accepted projections and hash checks](51-hypertrophy-load-remediation-20261025-summary.json)
- [Five-repetition frozen plan](51-owner-rag-runtime-20261025T143818Z-plan.json)
- [Raw intermediate answers](51-owner-rag-runtime-20261025T143818Z-progress.json)
- [Complete five-repetition result](51-owner-rag-runtime-20261025T143818Z-result.json)
- [Negative-control frozen plan](51-owner-rag-runtime-20261025T144041Z-plan.json)
- [Negative-control result](51-owner-rag-runtime-20261025T144041Z-result.json)
- [Post-restart read-only readiness](51-tasks-46-51-readiness-20261025T144948Z.json)
