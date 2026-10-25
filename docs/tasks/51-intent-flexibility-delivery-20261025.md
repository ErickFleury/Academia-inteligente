# Current-request intent and native flexibility: delivery

Date: 2026-10-25. Canonical scope: RF-15/CA-15.2/7/11–13,
RF-18/CA-18.1/4/6–8, EXT-CA-AI-02.27/29/31–33, RN-13/16/29–31,
RNF02/05. See the [work plan](../training-intent-flexibility-work-plan.md).

## Incident findings

Account inspection was read-only and restricted to the designated client's own
recent conversation and plan metadata. No account identifier, health history,
raw transcript or private plan is exported into this report.

1. The reported single-goal request had a copied standalone client-role header.
   The anchored request classifier missed the command and routed it to generic
   chat, exposing the turn to historical mixed-goal context. The current message
   itself resolves to flexibility only. Its priority question was false.
2. The one-day retry entered the direct generation path and resolved flexibility
   correctly. Retained diagnostics report `incomplete_training_plan`; the exact
   historical candidate was not logged. The owner writer's technical dictionary
   contained only resistance exercises, and its schema required repetitions,
   resistance sets and numeric rest. It could not express the existing typed
   flexibility holds/side contract. This is separate from intent classification.
3. The retrieval query always added resistance/strength vocabulary. Even the first
   attempted modality fix ranked six passages from a time-efficient resistance
   review. Goal-specific static-stretching vocabulary now prioritizes relevant
   stretching research without selecting source IDs or weakening license,
   permission, relevance or freshness filters.
4. A source section with no citations on a clarification is conservatively marked
   insufficient evidence. That display is not proof of a retrieval outage or the
   cause of a candidate-validation failure. The retained generation reason was
   a validation/completeness failure.

## Implementation decisions

- Strip only a bounded copied client-role header for interpretation. Keep the
  original stored message and UUID replay. Normalize accents/case/whitespace for
  matching. Do not execute quoted assistant transcripts, negated commands or
  conditional generation requests.
- Share token-bounded current-goal recognition across generation, owner binding,
  chat refresh and retrieval. Respect explicit priorities and negated objectives;
  old conversation/onboarding goals cannot add an objective to an explicit new
  flexibility request. Genuine competing goals still require priority, and day
  count is optional.
- Support explicit generation commands followed directly by a recognized goal,
  as well as requests for singular/plural sheets and numeric/written counts.
- Add six technical stretching identities, scoped separately from the existing
  twelve resistance identities. Reuse `FlexibilityDose`, `ProjectionDetails`,
  existing persistence, client/instructor rendering and the ordinary review flow.
  No dependency, migration or new API field is introduced.
- The writer supplies holds, hold seconds, side and recovery; the domain renders
  seconds per side and preserves `sets=null`. No numeric kg, measured range,
  observed tolerance or diagnosis is invented. Clinical dose remains a proposal
  from supplied owner-accepted consultation rules, not a compiled qualification.
- Different left/right targets may have separate rows. Repeating a movement for
  the same side, or overlapping `each_side`/unilateral rows, remains a duplicate.
  Splitting side rows does not make A/B/C exercise selections distinct. Full-body
  flexibility covers upper/lower/trunk regions; resistance keeps its five patterns.
- Keep source/citation/content/input/hash checks, automatic review, one global
  correction and the existing four writer/four review/two focus/ten total HTTP
  call limits. Save complete routines atomically. No approved plan is changed.
- Canonicalize the technical flexibility title and exercise labels to pt-BR;
  presentation labels never replace writer-selected duration or side quantities.

## Development experiments and infrastructure interruption

- `20261025T211725Z`: the first native-hold writer recognized flexibility but
  emitted left/right rows for the same movement. The resistance-only duplicate
  rule rejected them twice before review. Zero proposals were saved. The original
  outputs remain unchanged in the linked development artifacts.
- `20261025T212158Z`: simple, copied-header and one-day requests all produced
  typed flexibility drafts through actual chat, without content correction. The
  copied-header case included a historical mixed-goal question; the new request
  still won. This run was interrupted during A/B/C when the Docker engine returned
  HTTP 500, backend health failed and host free memory was approximately 458 MB.
  The remaining cases are explicitly unfinished, not counted as successes.
- Docker Desktop was restarted; core application services were recovered and
  backend health returned `ok`. Verification was resumed sequentially to reduce
  memory pressure. A later title-only correction prevents English technical tags
  from reaching the Portuguese training preview.
- An offline full-suite run caught a negated rebuild instruction that the broader
  goal-negation handling had mistakenly authorized. The command-negation guard was
  corrected; the original regression remains intact.

These are exposed synthetic diagnostics with local `qwen3:4b`, real read-only
public PostgreSQL/BGE-M3 retrieval and isolated in-memory draft state. They are
not independent or clinical evaluation. The source/rule owner-approval registry
is unchanged, and appraisal/compiled-qualification flags remain false.

## Final verification

**Final full backend suite: 1,299 passed in 117.32 seconds**, including opt-in
isolated PostgreSQL tests, after the command-negation regression was corrected.
The new intent/flexibility suite passed **39 tests**; related chat/rebuild/schedule
checks passed **157 tests**. Existing frontend grouping, projection and review
contracts passed **20 tests in 30.50 seconds**, with no frontend implementation
change. Ruff lint/formatting and Git whitespace checks cover the affected files.

The final actual-provider matrix passed **7/7 generation cases, including all five
native-flexibility requests, plus 3/3 expected refusals**. Every generation saved
one isolated proposal, none was activated, and every case used zero content
corrections. Chat cases also replayed the same request UUID without another model
call. Source eligibility/freshness, source/rule/configuration/dictionary/content
bindings, goal, labels, quantities, side overlap and distinct exercise selections
were revalidated in a read-only public PostgreSQL session.

Command: `docker compose exec -T backend python scripts/probe_owner_rag_runtime.py --flexibility-matrix`.
Configuration: `qwen3:4b`, `owner-assisted-rag-12 / owner-rag-13`, temperature
zero. All frozen implementation fingerprints remained unchanged during the run.
The matrix was executed separately from the full backend suite after recovery.

| Case | Result / sheets | Rows | Writer / review / focus HTTP calls | Reported seconds |
| --- | --- | --- | --- | --- |
| Plain flexibility, no days | proposal A | 6 | 1 / 1 / 1 | 42.953 |
| Copied client header and prior mixed-goal question | proposal A | 6 | 1 / 1 / 1 | 20.441 |
| Explicit one-day flexibility | proposal A | 6 | 1 / 1 / 1 | 26.705 |
| Three-day flexibility | proposal A/B/C | 6 / 3 / 6 | 3 / 3 / 1 | 124.706 |
| Flexibility, explicitly excluding hypertrophy | proposal A | 6 | 1 / 1 / 1 | 52.628 |
| Strength regression | proposal A/B/C | 3 / 3 / 3 | 3 / 3 / 1 | 52.030 |
| Hypertrophy regression, no days | proposal A | 5 | 1 / 1 / 0 | 27.942 |
| Genuine competing goals | priority clarification, no draft | 0 | 0 / 0 / 0 | 0.124 |
| Conflicting counts/labels | schedule clarification, no draft | 0 | 0 / 0 / 0 | 0.037 |
| Retrieval outage | technical refusal, no draft | 0 | 0 / 0 / 0 | 0.031 |

Row counts include separate side targets; they are not universal exercise counts.
All five flexibility cases cited current stretching research from the actual
retrieved corpus. Typed holds remained seconds per side with recovery separate;
there were no resistance sets or numeric external loads in those sheets.
No provider-server failure was recorded in the final matrix. Timings are the
probe's process-clock measurements, not a wall-time/service-latency guarantee on
this memory-constrained local runtime.

Evidence: [frozen plan](51-intent-owner-rag-runtime-20261025T214009Z-plan.json),
[complete final result](51-intent-owner-rag-runtime-20261025T214009Z-result.json),
[assertion summary](51-intent-flexibility-final-summary-20261025.json),
[all seven generated routines](51-intent-flexibility-generated-sheets-20261025.md).
Historical evidence: [first failure](51-intent-owner-rag-runtime-20261025T211725Z-result.json),
[interrupted partial results](51-intent-owner-rag-runtime-20261025T212158Z-result.json),
[explicit interruption record](51-intent-owner-rag-runtime-20261025T212158Z-execution.json).

The local backend was recreated with the final implementation and reports healthy;
`GET /health` returns `status: ok`. The read-only
[post-deployment readiness audit](51-intent-flexibility-readiness-20261025T221010Z.json)
found 66 public vectors, 37 owner-accepted rules, owner RAG authorized and no RAG
release blockers. The same source/rule approval registry remains in force.
Pre-existing core and biometric services stopped by the Docker recovery were
returned to running state. The diagnostic writing model was unloaded from memory
without deleting models; ordinary requests load it through the existing adapter.

The [account-preservation audit](51-intent-flexibility-account-preservation-20261025.json)
compared complete saved version/item fingerprints before and after final testing
and deployment in read-only transactions. All rows match. Only boolean assertions
are exported; no private plan, identity or health data enters these artifacts.

## Changed files

| Area | Files |
| --- | --- |
| Shared current-request interpretation | `backend/app/modules/training/request_intent.py` (new), `chat_service.py`, `owner_rag.py` |
| Retrieval | `backend/app/modules/training/knowledge_query.py` |
| Native flexibility and validation | `backend/app/modules/training/owner_rag_flexibility.py` (new), `owner_rag_schema.py`, `owner_rag_load.py`, `selection.py`, `completeness.py` |
| Technical identities and configuration | `backend/app/modules/training/owner-rag-exercises.json`, `owner-rag-authorization.json` |
| Provider and explicit live diagnostics | `backend/app/integrations/ai.py`, `backend/scripts/probe_owner_rag_runtime.py` |
| Offline regressions | `backend/tests/test_training_intent_flexibility.py` (new), `test_owner_rag_load.py` |
| Canonical clarification and evidence | `docs/requirements.md`, the work plan, this report and linked synthetic/redacted artifacts |

Pre-existing modified/untracked work was preserved. No commit or push was made.

## Use and remaining limits

`Gere uma ficha de treino de flexibilidade.` should generate one default session
without a priority/day question. `Gere uma ficha de flexibilidade em três dias,
A/B/C.` explicitly requests three sessions. A copied standalone client-role
header is accepted; stored history remains intact.

Actual unavailable sources/providers, missing required measurements, genuine
restriction conflicts and unresolved ambiguity retain controlled failure paths.
These checks do not establish individual suitability or a universal model success
rate. Long-term active mobility and sport-specific optimization are not silently
relabelled as measured static-stretching outcomes. Instructor approval remains
necessary before activation.
