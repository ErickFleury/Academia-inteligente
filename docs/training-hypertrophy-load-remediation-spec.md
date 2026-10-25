# Hypertrophy: unmeasured external-load generation remediation

Version 1.0, 2026-10-25. Status: implemented and verified for the qualitative-load scope.

Implementation follow-up: 1,206 backend tests passed, including PostgreSQL;
five of five frozen actual-provider hypertrophy repetitions produced qualitative
drafts, with no activation and no fabricated kg. Source-outage and ambiguous-goal
controls rejected without model calls or saves. See the
[delivery, all generated sheets and remaining limits](tasks/51-hypertrophy-load-remediation-delivery-20261025.md).

The owner requested another hypertrophy test and, if it failed, a specification
of possible causes and remedies. This is an implementation map for the existing
owner-assisted RAG amendment and EXT-CA-AI-02.27–29/31–33 in
[requirements.md](requirements.md), the sole canonical specification. It introduces
no clinical dose, professional appraisal requirement, provider or dependency.

## 1. Reproduced incident

The [frozen hypertrophy-only test](tasks/51-owner-rag-runtime-20261025T141932Z-plan.json)
used the same model digest, source/rule versions, synthetic intermediate profile
and production implementation as the previous attempts. PostgreSQL retrieval was
read-only; synthetic onboarding/proposals existed only in in-memory SQLite.

The [result](tasks/51-owner-rag-runtime-20261025T141932Z-result.json) was rejected
after 34.651 seconds, with one writer and one automatic-review HTTP call, zero
focus calls and zero saved proposals. Item 3, dumbbell row, contained
`Halteres (2 kg por braço)`. The automatic reviewer returned `complete: true`
with no item issues; `owner_rag.bind()` subsequently rejected it as
`missing_input / measured_baseline_required_for_external_load`.

The writer received six passages and nine goal-scoped rules. A read-only scan of
those six current passages found no numeric kg expressions matching the existing
guard's pattern. This does not prove the origin of the invented value, but does
not support treating it as an individualized measurement copied from those passages.
Writer/reviewer envelopes measured 33,604/34,483 JSON characters; token truncation
was not measured and must not be asserted.

## 2. Causes and hypotheses

| Finding | Evidence status | Remedy and verification |
| --- | --- | --- |
| `load_guidance` remains unrestricted prose although exercise IDs and repetitions are constrained | Confirmed in `owner_rag_schema.py` and `ai.py` | Narrow unmeasured-load choices at the adapter boundary; validate permitted choices against the selected exercise in the backend |
| The kg check runs after exercise selection/review returns, outside its content-correction loop | Confirmed in `generation_service.py`, `selection.py` and `owner_rag.bind()` | Validate load provenance inside candidate validation, before automatic review, while retaining the final pre-save check |
| A generated unsupported number is reported as missing user input, and that category cannot enter the existing correction whitelist | Confirmed by the result and code | Distinguish a repairable model-generated value from a genuinely mandatory missing measurement |
| Automatic exercise review accepted the kg-bearing candidate | Observed; its exercise-completeness verdict is not a load-provenance guarantee | Make deterministic load checks authoritative; do not depend on an extra model review to establish provenance |
| The model completes a familiar dumbbell prescription despite the prompt's prohibition | Hypothesis; the instruction already prohibits invented kg | Compare the current free-text transport with constrained choices using frozen cases; adding the same prohibition alone is insufficient evidence of a fix |
| Large or competing context distracts the model | Hypothesis; character counts alone do not establish attention failure or truncation | Inspect actual prompt composition and applicable rules; measure token/truncation data if available, preserving the six-passage and existing context limits |
| Bibliographic examples might be mistaken for individual observations | General hypothesis, not demonstrated by the six passages in this run | Keep source findings distinct from authoritative client measurements; test a public-source numeric example as an adversarial input |

## 3. Intended behavior

A hypertrophy consultation draft may continue to use an exercise with external
equipment without inventing a numerical external load, where the current assisted
mode permits qualitative guidance. Missing kg is not automatically a reason to
replace hypertrophy with another goal or reject an otherwise permitted qualitative
draft. If the requested decision actually requires a measured baseline or a
calculation, keep the existing clarification/rejection path; never invent that fact.

Source/rule approval, draft generation and ordinary instructor plan approval remain
separate. No automatic activation, professional signature or compiled qualification
is introduced. Existing clinical choices and unrelated endurance-rule discrepancies
are outside this specification's completion claim.

### 3.1 Constrain the unmeasured-load writer contract

- Add technical load capabilities to the existing exercise dictionary only where
  needed: bodyweight or external equipment with unmeasured load. These describe
  exercise representation, not a clinical dose or an assertion of tolerance.
- In owner-RAG unmeasured mode, narrow the existing `load_guidance` wire field to
  a closed set of qualitative values. Preserve the public plan field as a string;
  no new public API contract or database column is needed for this fix.
- Example pt-BR values: `Peso corporal` and
  `Halteres; carga a definir na revisão do instrutor.` The backend validates the
  permitted choice against the selected exercise; a dumbbell movement cannot
  become a bodyweight exercise merely to avoid the load check.
- Schemas may offer the union of current qualitative choices when provider schema
  support requires it, but backend exercise/value compatibility remains mandatory.
  Numeric kg, alternative units, spelled-out weights or claims about measured
  capacity cannot be encoded through unrestricted prose in this mode.
- Do not turn height, body mass, experience, retrieved study loads or an assistant
  statement into an individual load baseline. Numeric measured-load support is a
  separate capability; this work does not silently enable it.

### 3.2 Validate inside the existing bounded correction

Extract a pure candidate-load validation function shared by the selection paths
and final binding. Do not duplicate the current regex across services.

1. Resolve exercise identities and validate plan structure.
2. Validate qualitative-load representation and exercise compatibility.
3. A model-generated unsupported load, when a qualitative draft is allowed,
   produces a repairable candidate error with exact item position,
   `field: load_guidance`, a stable reason and the permitted qualitative choices.
4. Use the existing single content correction. It may rewrite the indicated load
   field; it must not infer kg, change the goal, alter confirmed client facts or
   silently change valid sets/repetitions/rest/exercise choices.
5. Run the mandatory automatic exercise review on the valid candidate. Any review
   correction shares the same correction allowance; the load failure does not
   obtain a separate second correction.
6. Revalidate citations, current source/rule approval, inputs, revision and final
   content immediately before the atomic save. Keep `bind()` as a defensive guard.

A genuinely required absent measurement stays `missing_input` and is not converted
into a repairable model error. An exhausted correction rejects and preserves the
prior draft/current plan. Never silently remove `2 kg` from a persisted or candidate
string and describe the altered prescription as validated; retain original and
corrected candidates separately in synthetic diagnostics.

The limits remain two content candidates, at most four writer/four review/two focus
HTTP calls and ten total, with the current adapter timeout and shared remaining
deadline. No retry-until-success loop, larger context or rejection-gate bypass.

## 4. Implementation map and compatibility

| Area | Expected change |
| --- | --- |
| `owner_rag_schema.py`, `owner-rag-exercises.json` | Versioned technical load capability and constrained qualitative choices |
| `owner_rag.py` | Pure candidate validation, distinct failure semantics, final provenance/binding guard |
| `selection.py` | Invoke the shared validator inside the existing correction budget; whitelist only the narrow recoverable error |
| `generation_service.py`, `chat_service.py`, `adaptation_service.py` | Reuse the validator for new/changed candidates and the complete materialized adaptation; preserve untouched approved history |
| `app/integrations/ai.py` | Apply the scoped qualitative schema to the existing writer calls; preserve the provider-independent adapter |
| Owner-RAG authorization | Prepare a versioned writer/dictionary configuration with exact hashes and technical verification evidence; do not reuse a now-mismatched authorization or alter source approval hashes to conceal a change |
| Focused tests and probe | Add regression cases and frozen actual-provider repetitions; preserve every prior failure/result |

Inspect replay, submission and approval revalidation before changing binding data.
If the dictionary/configuration changes, retain current source/input/content hash
checks and explicitly classify affected old AI drafts as requiring regeneration or
the existing manual path. Do not rewrite approved history. No frontend redesign is
required; existing pt-BR feedback must distinguish missing measurements, rejected
model content and service unavailability without exposing provider internals.

## 5. Acceptance and test matrix

| ID | Required result |
| --- | --- |
| HYP-LOAD-01 | A permitted qualitative hypertrophy draft without a measured kg baseline can be saved with actual supplied citations and no numeric external-load claim |
| HYP-LOAD-02 | A first candidate containing invented kg is rejected before model review and receives at most one correction with item/field/allowed-choice feedback |
| HYP-LOAD-03 | A corrected candidate uses a permitted exercise-compatible qualitative load, preserves other valid decisions, receives automatic review and passes final binding |
| HYP-LOAD-04 | An invalid correction or a load error after a prior correction rejects; no third content candidate, partial plan, replacement of a prior draft or approved-plan change occurs |
| HYP-LOAD-05 | A genuinely mandatory missing measurement still clarifies/rejects; source numeric examples, demographics and another client's observations cannot supply it |
| HYP-LOAD-06 | Bodyweight/external-equipment mismatches and numeric-unit/spelled-out-weight bypasses fail the closed contract/domain check; no silent kg stripping |
| HYP-LOAD-07 | Initial generation, chat editing and adaptation use the same load check; final full-plan adaptation, replay, submission, approval and dependency revocation retain their protections |
| HYP-LOAD-08 | Actual source/rule citations, absence of professional/independent appraisal and ordinary instructor activation requirements remain truthful; no compiled-qualification badge |
| HYP-LOAD-09 | Existing single-correction and HTTP/deadline bounds hold under mixed load, schema, review and transient transport failures |

Run the focused owner-RAG, selection, chat, adaptation, lifecycle, authorization and
budget tests impacted by implementation. The current test that rejects invented
loads must not simply be deleted: retain explicit exhaustion/no-save coverage and
add the allowed repair-to-qualitative path. Tests use synthetic fixtures and fake
providers; no live service dependency enters the regression suite.

Separately freeze five hypertrophy repetitions using the same synthetic
intermediate profile as this incident, actual public retrieval and the same model.
Record the new exact contract/dictionary/configuration, expected qualitative
proposal, citations, each intermediate answer, all HTTP calls, elapsed time and
activation state before scoring. All five must produce reviewable qualitative
proposals within budget, with no invented load; otherwise the positive acceptance
criterion remains unmet. Critical negative cases must reject. Preserve failures
and distinguish software correctness from professional prescription quality; five
successes do not establish universal clinical or operational reliability.

## 6. Delivery sequence and completion boundary

1. Capture the baseline incident and write the failing deterministic regressions.
2. Implement the closed qualitative contract and pure candidate validator.
3. Integrate the existing correction loop and all affected prescriptive paths.
4. Verify final binding, compatibility, authorization hashes and atomic persistence.
5. Run focused regressions and the frozen actual-provider experiment; publish both
   positive and negative outcomes without changing old scores.

The original specification-only handoff preserved incident evidence and did not
change runtime behavior. The subsequent owner-requested implementation and scoped
technical verification are recorded in the delivery linked above. Neither stage
claims professional appraisal or automatic plan activation.
