# All owner-approved rules: development test report ? 2026-10-24

Scope: the request to test all other approved rules and return their output (RF-15 / EXT-RF-AI-02). All 37 exact approved rule versions were exercised, including the 25 absent from the earlier strength/hypertrophy writer contexts. No source/rule approval, production code, deployment setting or numeric rule was changed.

## Results

**74 distinct synthetic cases, 55 strict passes and 19 failures; 20 of 37 rules passed both cases.** Among the 25 newly covered rules, 13 passed both cases and 12 had at least one failure. There were 69 matching accept/reject/clarify decisions; correctness of the quantity, unit and JSON null was checked separately.

Failures: **5 decision mismatches, 5 wrong quantities, 9 unit/null contract errors**. These are purposive development cases, not population accuracy estimates or evidence of clinical efficacy.

## Method and run history

The local deployed model `qwen3:4b` was invoked through the existing Ollama adapter. Each approved rule received a manually specified application fragment and counterexample, with fixed independent numeric/decision oracles. All cases are fully synthetic and implementer-visible. Expected decisions and values were not supplied as answer keys to the model; case identifiers are opaque and order was shuffled deterministically. Requested output-unit keys are supplied as contract metadata.

These calls use a dedicated rule-fragment schema/prompt and `think=false`. They evaluate rule interpretation and arithmetic; they do not invoke the ordinary full-sheet prompt, live RAG, automatic exercise reviewer or student lifecycle. DATABASE_URL was empty for these model probes. This distinction prevents presenting a fragment classification as a generated, qualified training sheet.

The initial frozen run used 13 calls. Four batches failed case-ID/count validation, leaving 20 cases unscorable. Their original failures remain recorded. A separately frozen diagnostic ran those ten rules once each, with one rule per request and a schema restricting response IDs/count. The scenarios, decision/numeric oracles and pass criteria were unchanged. These ten calls produced scoreable responses. No scored failure was retried until it passed.

**Total: 23 local model calls, 94 case presentations, 74 distinct scored cases.** Initial run and diagnostic are preserved separately, with model/registry/context/case/schema hashes and budgets. Both matched the approved rule versions. No live client data was read or written.

- [Original frozen plan and oracles](51-all-owner-rules-plan.json)
- [Original results, including invalid batches](51-all-owner-rules-result.json)
- [Isolated diagnostic plan](51-all-owner-rules-isolated-plan.json)
- [Isolated diagnostic results](51-all-owner-rules-isolated-result.json)
- [Combined summary and all outputs](51-all-owner-rules-summary.json)

## Rule-by-rule machine results

Each score is out of two prespecified cases. Values below are synthetic test outputs, not exercise recommendations. Passing the machine criteria does not grade the accuracy of free-text rationale.

| Rule | Newly covered | Strict passes | Application output | Failure details |
| --- | --- | --- | --- | --- |
| AEROBIC_ACCOUNTING | yes | 1/2 | accept; 30.0 moderate_equivalent_minutes | application: expected {"decision": "accept", "value": 60, "unit": "moderate_equivalent_minutes"}; actual {"decision": "accept", "value": 30.0, "unit": "moderate_equivalent_minutes"} |
| AEROBIC_DOSE | yes | 1/2 | accept; 150.0 moderate_minutes_per_week | counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "reject", "value": null, "unit": "null"} |
| AEROBIC_INTENSITY | yes | 2/2 | accept; None None | none |
| AEROBIC_RECOVERY | yes | 2/2 | accept; None None | none |
| AEROBIC_START_PROGRESS | yes | 0/2 | accept; 30.0 minutes_per_week | application: expected {"decision": "accept", "value": 35, "unit": "minutes_per_week"}; actual {"decision": "accept", "value": 30.0, "unit": "minutes_per_week"}; counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "reject", "value": null, "unit": "null"} |
| BALANCE_DOSE | yes | 2/2 | accept; 8.0 seconds_per_attempt | none |
| BALANCE_FUNCTION_ACCOUNTING | yes | 2/2 | accept; 2.0 successful_attempts | none |
| BALANCE_RECOVERY | yes | 1/2 | accept; 45.0 seconds | counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "accept", "value": null, "unit": null} |
| COMBINED_GOALS | yes | 2/2 | accept; None None | none |
| ENDURANCE_DOSE | yes | 1/2 | accept; 50.0 kg | counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "accept", "value": null, "unit": null} |
| ENDURANCE_SETS | yes | 1/2 | accept; 18.0 repetições | application: expected {"decision": "accept", "value": 18, "unit": "repetitions"}; actual {"decision": "accept", "value": 18.0, "unit": "repetições"} |
| FALL_PREVENTION | yes | 2/2 | accept; 12.0 weeks | none |
| FLEXIBILITY_ACCOUNTING | yes | 1/2 | accept; 60.0 seconds_per_side_per_week | application: expected {"decision": "accept", "value": 120, "unit": "seconds_per_side_per_week"}; actual {"decision": "accept", "value": 60.0, "unit": "seconds_per_side_per_week"} |
| FLEXIBILITY_DOSE | yes | 2/2 | accept; 60.0 seconds_per_side | none |
| FLEXIBILITY_NEWER_EVIDENCE | yes | 2/2 | accept; None None | none |
| FLEXIBILITY_STRUCTURE | yes | 2/2 | accept; 60.0 seconds_per_side | none |
| FUNCTION_DOSE | yes | 2/2 | accept; 5.0 repetitions | none |
| FUNCTION_STRUCTURE | yes | 1/2 | accept; 6.0 repetitions | counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "reject", "value": null, "unit": "null"} |
| HYPERTROPHY_LOADING | previous context | 2/2 | accept; 8.0 rm_repetitions | none |
| HYPERTROPHY_REST | previous context | 2/2 | accept; 150.0 seconds | none |
| HYPERTROPHY_VOLUME | previous context | 2/2 | accept; 10.0 reference_sets_per_muscle_per_week | none |
| LOAD_PROGRESSION | previous context | 1/2 | accept; 50.1 kg | application: expected {"decision": "accept", "value": 51, "unit": "kg"}; actual {"decision": "accept", "value": 50.1, "unit": "kg"} |
| NOVICE_LOADING | previous context | 2/2 | accept; 10.0 rm_repetitions | none |
| POWER_DOSE | yes | 2/2 | accept; 50.0 kg | none |
| POWER_REPETITIONS | yes | 1/2 | accept; 3.0 repetitions | counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "reject", "value": null, "unit": "null"} |
| POWER_STRUCTURE | yes | 1/2 | accept; 240.0 seconds | counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "accept", "value": 160.0, "unit": "seconds"} |
| RESISTANCE_ACCOUNTING | previous context | 1/2 | accept; 60.0 kg_repetitions | application: expected {"decision": "accept", "value": 120, "unit": "kg_repetitions"}; actual {"decision": "accept", "value": 60.0, "unit": "kg_repetitions"} |
| RESISTANCE_EFFORT | previous context | 2/2 | accept; 2.0 rir | none |
| RESTRICTIONS | previous context | 1/2 | accept; None None | application: expected {"decision": "clarify", "value": null, "unit": null}; actual {"decision": "accept", "value": null, "unit": null} |
| SELECT_RESISTANCE | previous context | 0/2 | accept; None null | counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "reject", "value": null, "unit": "null"}; application: expected {"decision": "accept", "value": null, "unit": null}; actual {"decision": "accept", "value": null, "unit": "null"} |
| SOURCE_ENDURANCE_CIRCUIT | yes | 1/2 | accept; 59.0 kg | counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "reject", "value": null, "unit": "null"} |
| SOURCE_MEDICINE_BALL_POWER | yes | 2/2 | accept; 120.0 seconds | none |
| SOURCE_PAIRED_RESISTANCE | previous context | 2/2 | accept; 120.0 seconds_after_pair | none |
| SPORT_SPECIFICITY | yes | 1/2 | accept; None None | application: expected {"decision": "clarify", "value": null, "unit": null}; actual {"decision": "accept", "value": null, "unit": null} |
| STRENGTH_DOSE | previous context | 1/2 | accept; 80.0 kg | counterexample: expected {"decision": "reject", "value": null, "unit": null}; actual {"decision": "reject", "value": null, "unit": "null"} |
| STRENGTH_REST | previous context | 2/2 | accept; 240.0 seconds | none |
| WEIGHT_DIRECTION | yes | 2/2 | accept; None None | none |

## Important observed failures

- ENDURANCE_DOSE accepted equality at boundaries that require strictly more than 15 repetitions and strictly less than 90 seconds.
- POWER_STRUCTURE returned accept for 160 seconds even while its explanation said the minimum is 180 seconds.
- BALANCE_RECOVERY accepted increasing challenge/removing support after losing control, contrary to the supplied rule.
- LOAD_PROGRESSION computed 50 kg + 2% as 50.1 kg instead of 51 kg.
- AEROBIC_START_PROGRESS returned 30 instead of 35 weekly minutes after adding five minutes to one of three ten-minute sessions.
- RESISTANCE_ACCOUNTING returned 60 instead of 120 kg-repetitions by omitting the second weekly occurrence.
- AEROBIC_ACCOUNTING returned a numeric field of 30 while explaining the correct 30 + 2*15 = 60.
- FLEXIBILITY_ACCOUNTING returned 60 instead of 120 seconds per side/week by omitting the second occurrence.
- SPORT_SPECIFICITY and RESTRICTIONS returned accept instead of the prespecified clarify. Their explanations did recommend requesting missing information; these two category mismatches alone do not establish that an actionable unsupported prescription was generated. The fragment accept/required-action clarify distinction is a limitation of this diagnostic rubric.
- Nine otherwise matching cases failed exact unit/null representation, including the string "null" in place of JSON null and a translated API unit key.

Free-text rationales were not scored and can still be incorrect even with matching structured fields. For example, a NOVICE_LOADING counterexample explanation expanded RIR incorrectly as "repetitions in range"; the rule describes repetitions in reserve. This observation is retained as an additional limitation, without retrospectively changing the frozen pass criteria.

## Integrated qualified generation and software checks

Eleven additional offline integration cases entered the actual InitialTrainingGenerationService qualified path, with valid synthetic completed onboarding and the real packaged policy/execution artifacts. All eleven goal families rejected before retrieval/writing with `category=insufficient_support`, `reason=approved_goal_policy_required`. No training version was saved. This verifies the current incomplete-executable-policy boundary; it does not claim full generation success. The normal deployed rollout flag was not changed.

```powershell
docker compose run --rm -T --no-deps -e DATABASE_URL= backend python -m pytest tests/test_owner_rule_probe.py tests/test_owner_approval.py -q
```

**26 passed in 8.83 seconds.** The tests cover all-rule/case coverage, fixed oracles, answer-key separation, response completeness, incorrect units/quantities, revocation/version binding, unchanged diagnostic oracles and the eleven integrated generation blocks. All external adapters in these tests are fake. The real model experiments above ran separately.

Ruff lint/format checks passed for the three added Python files. Scoped/full git diff whitespace checks were performed. No frontend was changed, so frontend checks were not repeated. No new dependency, commit, push, professional judgment, release sign-off or source-approval update was made.

## Files changed

- `backend/scripts/owner_rule_probe_cases.py`: manually specified synthetic cases and fixed expected results.
- `backend/scripts/probe_all_owner_rules.py`: bounded model calls, exact-owner-version checks, scoring and separately recorded diagnostic selection.
- `backend/tests/test_owner_rule_probe.py`: offline harness integrity and integrated generation tests.
- This report and the five linked JSON plan/result/summary artifacts.

The uncommitted work predating this request was preserved. Production source code, owner registry, policy ranges, credentials and student data were not modified. Complete executable policies/contracts and actual operational evaluation remain open; the model failures above cannot be treated as a passed rule set.
