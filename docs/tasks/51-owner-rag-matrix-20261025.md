# Owner-approved RAG matrix: 2026-10-25

The owner reiterated approval of all current consultation sources and proposed rules and requested actual generated-sheet outputs. All 24 source and 37 rule hashes already matched the owner registry; no approval was fabricated, broadened to changed versions, or rewritten. Professional and independent appraisal remain absent. Reuse permissions and excluded/pending sources remain unchanged.

## Method and outcome

Two explicitly exposed five-case rounds used real PostgreSQL/BGE-M3 retrieval and the configured local `qwen3:4b` writer/reviewer. The second round repeated the same cases once, after the first revealed generation failures. Both plans were frozen before their respective rounds; all failures are retained. This is a development diagnostic, not independent evaluation. Public PostgreSQL access was read-only; synthetic clients, onboarding and proposals existed only in memory.

The corpus audit recorded 66 vectors and 37 accepted research rules. Goal-specific primary rules reached the writer, with at most six complete passages per call. Source approval is not clinical validation.

**3 of 6 ordinary generation attempts produced accepted proposals. All 4 negative controls refused without model calls or saved proposals.** The full pipeline is demonstrated for strength and one hypertrophy attempt; consistent generation across goals is not established. Resistance-muscular-endurance failed both attempts.

| Round | Case | Outcome | Seconds | Writer / review HTTP calls |
| --- | --- | --- | --- | --- |
| 1 | initial-strength | proposal: proposal | 59.851 | 1 / 1 |
| 1 | initial-hypertrophy | rejected: measured_baseline_required_for_external_load | 22.892 | 1 / 1 |
| 1 | initial-muscular-endurance | technical_failure: InvalidTrainingGenerationError | 47.186 | 2 / 0 |
| 1 | ambiguous-goal | rejected: goal_priority_confirmation_required | 0.307 | 0 / 0 |
| 1 | retrieval-outage | rejected: retrieval_unavailable | 0.030 | 0 / 0 |
| 2 | initial-strength | proposal: proposal | 52.209 | 1 / 1 |
| 2 | initial-hypertrophy | proposal: proposal | 43.028 | 1 / 1 |
| 2 | initial-muscular-endurance | rejected: measured_baseline_required_for_external_load | 23.565 | 1 / 1 |
| 2 | ambiguous-goal | rejected: goal_priority_confirmation_required | 0.259 | 0 / 0 |
| 2 | retrieval-outage | rejected: retrieval_unavailable | 0.018 | 0 / 0 |

The first hypertrophy attempt and second muscular-endurance attempt invented an unmeasured kg load and were blocked. The first muscular-endurance attempt repeated exercises after its bounded correction; the service returned `InvalidTrainingGenerationError`, recorded as `technical_failure` by the generic probe handler. Raw answers diagnose an invalid candidate rather than a retrieval outage. No rejected candidate is presented below as an accepted sheet.

## Accepted generated sheets

All three are a single session A. No weekly schedule was supplied. Synthetic profiles were 170 cm / 70.50 kg, without reported limitations, conditions or medication; experience was beginner for strength and intermediate for hypertrophy. These are actual model outputs, not professionally reviewed individual prescriptions. Numerical external loads were not supplied.

### Sheet 1: round 1, initial-strength

Treino de força para iniciante

Generated objective: Aumentar a força muscular para iniciantes

| Exercise | Sets | Repetitions | Load guidance | Rest (seconds) |
| --- | --- | --- | --- | --- |
| Agachamento com peso corporal (Dia A) | 3 | 8-12 | Peso corporal | 180 |
| Flexão de braços (Dia A) | 2 | 8-12 | Peso corporal | 180 |
| Remada curvada com halteres (Dia A) | 2 | 8-12 | Halteres | 180 |
| Abdominal curto (Dia A) | 2 | 10-15 | Peso corporal | 120 |

Cited passage IDs: `biga-anatomy-1`, `nhs-strength-1`, `biga-anatomy-2`, `pavlova-tendinopathy-2023-1`, `iversen-time-efficient-2021-06`, `nhs-strength-2`.

### Sheet 2: round 2, initial-strength

Treino de Força para Iniciantes

Generated objective: Ganhar força

| Exercise | Sets | Repetitions | Load guidance | Rest (seconds) |
| --- | --- | --- | --- | --- |
| Agachamento com peso corporal (Dia A) | 2 | 8-12 | Peso corporal | 180 |
| Flexão de braços (Dia A) | 2 | 8-12 | Peso corporal | 180 |
| Remada curvada com halteres (Dia A) | 2 | 8-12 | Halteres | 180 |
| Abdominal curto (Dia A) | 2 | 8-12 | Peso corporal | 180 |
| Elevação de panturrilhas em pé (Dia A) | 2 | 8-12 | Peso corporal | 180 |

Cited passage IDs: `biga-anatomy-1`, `nhs-strength-1`, `biga-anatomy-2`, `pavlova-tendinopathy-2023-1`, `iversen-time-efficient-2021-06`, `nhs-strength-2`.

### Sheet 3: round 2, initial-hypertrophy

Treino para hipertrofia muscular

Generated objective: Aumentar o diâmetro das fibras musculares através do treinamento resistido, com foco na incorporação de proteínas estruturais e miofibrilas.

| Exercise | Sets | Repetitions | Load guidance | Rest (seconds) |
| --- | --- | --- | --- | --- |
| Agachamento com peso corporal (Dia A) | 3 | 8-12 | Peso corporal | 120 |
| Flexão de braços (Dia A) | 3 | 8-12 | Peso corporal | 120 |
| Remada curvada com halteres (Dia A) | 3 | 8-12 | Halteres | 120 |

Cited passage IDs: `biga-anatomy-1`, `iversen-time-efficient-2021-06`, `iversen-time-efficient-2021-03`.

## Verification and changed files

The 14 owner-RAG regression tests passed (`python -m pytest -q tests/test_owner_rag.py`). Ruff checks, formatting and CLI help passed for the updated probe. Backend health returned `status: ok`. All accepted citations belonged to provided passages; current source/rule hashes matched the registry. Both rounds used identical implementation fingerprints and writer configuration; no model prompt or production gate was changed between rounds. Total actual model calls: seven writer and five automatic review calls. No plan was activated.

Changed in this request: `backend/scripts/probe_owner_rag_runtime.py` adds the optional matrix, frozen synthetic profiles and measured rule IDs/case progress; this report, summary and preserved diagnostic artifacts document results. Existing production source/rule approvals were retained. No unrelated implementation changes, commit or push were made.

Unresolved: unmeasured-load hallucinations, repeated exercises on muscular endurance, and a lack of professionally/independently assessed prescription quality. These results demonstrate retrieval/context/citations and successful generation in the accepted cases; they do not guarantee every future generation or every goal.

## Artifacts

- [Derived summary and accepted projections](51-owner-rag-matrix-20261025-summary.json)
- [Read-only corpus audit](51-tasks-46-51-readiness-20261025T140306Z.json)
- [Round 1 plan](51-owner-rag-runtime-20261025T140256Z-plan.json)
- [Round 1 progress](51-owner-rag-runtime-20261025T140256Z-progress.json)
- [Round 1 result](51-owner-rag-runtime-20261025T140256Z-result.json)
- [Round 2 plan](51-owner-rag-runtime-20261025T140604Z-plan.json)
- [Round 2 progress](51-owner-rag-runtime-20261025T140604Z-progress.json)
- [Round 2 result](51-owner-rag-runtime-20261025T140604Z-result.json)
