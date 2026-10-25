# Optional A/B/C generation: delivery and verification

Subsequent 2026-10-25 follow-up: [current-request intent and native flexibility](51-intent-flexibility-delivery-20261025.md)
fixes copied client-role headers, goal-specific retrieval and typed stretching
holds while preserving optional A/B/C generation. The results below retain their
original historical configuration and measurements.

Date: 2026-10-25. Scope: RF-15/CA-15.11–13, RF-18 and owner-assisted
EXT-RF-AI-02/.27–29/.31–33. Canonical requirements: `docs/requirements.md`.
Execution plan: [optional three-day work plan](../training-optional-three-day-work-plan.md).

## Investigation and change

Read-only inspection of the designated account confirmed recent explicit
three-day requests resulted in a draft with A only. An older current plan had
A/B/C. Its recent strength request also retained a hypertrophy binding. No
private health information, raw transcript or account identifier is exported.
The exact item-level cause of historical refused requests cannot be recovered
from the retained generic diagnostic reasons alone.

The schedule parser previously discarded requested days unless focus was
explicitly full-body. Day selection now operates independently of muscle focus;
explicit counts/labels are retained through generation, review, binding and
revalidation. Without an explicit schedule, existing single-session behavior
remains. Conflicting counts/labels require clarification. Explicit goals take
precedence over model analysis and onboarding; mixed goals need a stated primary.

Two/three sheets are generated and reviewed separately within one shared logical
attempt. Their final routine is saved atomically; no fragment can replace the
existing draft. There is one total content correction, at most four writer,
four review and two focus HTTP calls, ten total. Transport retries count.

The structured writer selects technical identities with qualitative load guidance.
For later days it can choose among schema branches omitting an identity from each
previous selection. This enforces variation without a fixed routine or backend
selection of clinical dose. Full-body branches retain all five required movement
patterns per sheet. Domain validation remains authoritative if a provider ignores
the schema; the existing literal, cited and reviewed repetition exception remains
available when no distinct complete branch can be represented.

Automatic review uses day-scoped positions and forbids passing responses with
nonempty failure arrays. Backend checks independently reject contradictory
responses. Duplicate correction identifies the conflicting item positions.
Invalid numeric ranges, missing sheets, duplicates, copied selections, wrong
goals and missing full-body patterns cannot be silently accepted.

Explicit generation may replace an obsolete AI binding; merely viewing,
submitting or approving a plan cannot recertify or rewrite it. The source/rule
owner-approval registry is unchanged. No dependencies, migration, API fields or
frontend changes were introduced by this follow-up. Professional and independent
appraisal flags remain false; ordinary instructor approval is still required.

## Actual-provider development history

All attempts use synthetic profiles, in-memory SQLite draft state, real read-only
public PostgreSQL/BGE-M3 retrieval and the configured local `qwen3:4b`. These are
exposed technical diagnostics, not an independent evaluation or clinical trial.

| Frozen run (UTC) | Findings |
| --- | --- |
| 16:50:54 | Whole-routine labels exposed review position errors and reversed repetition ranges. Hypertrophy A/B/C passed; other multi-day cases failed. |
| 17:04:09 | All five generation cases returned proposals, but manual inspection found the full-body sheets lacked required movement coverage. This was not accepted as full-body success. |
| 18:13:59 | Pattern slots prevented incomplete full-body acceptance, but whole-routine generation still copied selections after correction. |
| 18:44:14 | Per-session transport exposed within-day duplicates and contradictory automatic reviews. Multi-day cases failed without partial saves. |
| 20:01:23 | Short session instructions and consistent review allowed A, but B copied A twice and was correctly rejected. |
| 20:11:14 | Variation decoding produced distinct A/B/C for strength with three writer, three review and one focus call, no correction; exactly one isolated draft, no activation. |

Earlier failures are retained unchanged alongside the final frozen evidence. A
probe's `technical_failure` with `InvalidTrainingGenerationError` describes an
exhausted invalid candidate, not necessarily a network/provider outage.

## Final verification

The frozen actual-provider matrix returned **7/7 generation cases and 3/3 expected
refusals**. Every proposal was revalidated against the current source permissions,
freshness, source/rule hashes, content hash, dictionary, load representation,
requested goal, requested labels and distinct unordered movement selections in a
read-only PostgreSQL session. Full-body coverage also passed the deterministic
per-sheet pattern check. All seven saved exactly one isolated proposal and none
was activated. All ten used zero content corrections.

Command: `docker compose exec -T backend python scripts/probe_owner_rag_runtime.py --schedule-matrix`.
Model/configuration: `qwen3:4b`, `owner-assisted-rag-9 / owner-rag-10`, temperature
zero. The writer received five or six actual public passages. Runtime fingerprints
remained unchanged throughout the matrix. The subsequent chat-only refresh and
plural-request change does not alter the writer, reviewer, dictionary, generation
service or these cases' direct-generation path; it is covered by six additional
chat regression/replay cases and the final backend suite.

| Case | Sheets / items | Writer / review / focus HTTP calls | Seconds |
| --- | --- | --- | --- |
| Strength, onboarding said hypertrophy | A:3, B:3, C:3 | 3 / 3 / 1 | 45.829 |
| Hypertrophy | A:3, B:3, C:3 | 3 / 3 / 1 | 66.823 |
| Muscular endurance | A:3, B:3, C:1 | 4 / 3 / 1 | 172.959 |
| Full body, strength | A:6, B:6, C:6 | 3 / 3 / 1 | 287.730 |
| Two-day hypertrophy | A:3, B:3 | 3 / 2 / 1 | 193.945 |
| No explicit schedule | A:5 | 1 / 1 / 0 | 36.217 |
| Mixed goals, explicit hypertrophy priority | A:3, B:3, C:3 | 3 / 3 / 1 | 67.798 |

Two `provider_server` failures were recovered by the existing bounded transport
retry, one in endurance and one in the two-day case. Those retries are included
in the table and do not create extra content corrections. Ambiguous goals,
conflicting day counts/labels and unavailable retrieval produced respectively
`goal_priority_confirmation_required`, `training_schedule_confirmation_required`
and `retrieval_unavailable`, with zero model calls and zero drafts.

Evidence: [frozen plan](51-owner-rag-runtime-20261025T201258Z-plan.json),
[complete result](51-owner-rag-runtime-20261025T201258Z-result.json),
[assertion summary](51-optional-three-day-final-summary-20261025.json), and
[all seven generated routines](51-optional-three-day-generated-sheets-20261025.md).
The earlier successful strength-only run is retained separately; it is not counted
as another independent matrix case.

## Tests and deployment

- Before the final chat refresh fix: full backend including opt-in isolated
  PostgreSQL tests, **1,254 passed in 488.89 seconds**.
- After the chat fix: optional schedules, owner RAG and chat, **97 passed in
  25.43 seconds**. This includes requests containing only ABC, a new goal,
  twice-weekly frequency, plural sheets and written/numeric three-sheet counts.
  A repeated request UUID does not regenerate or increment the revision again.
- Final complete backend suite, including opt-in isolated PostgreSQL cases:
  **1,260 passed in 218.98 seconds**, after all production-code changes.
- Ruff lint and formatting checks passed for all thirteen affected Python files;
  `git diff --check` passed (existing LF/CRLF advisories only).
- Frontend grouping/rendering contract checks passed **7 tests**; frontend
  implementation is unchanged by this task.
- Local backend was force-recreated after the tests; `GET /health` returned
  HTTP 200 with `status: ok`. The read-only post-deployment readiness audit found
  **66 public vectors, 37 owner-accepted rules, owner RAG authorized and no RAG
  release blockers**. Compiled clinical prescription remains unauthorized;
  professional/independent appraisal is not claimed or required for this owner mode.
  Audit: [post-deployment readiness](51-optional-three-day-readiness-20261025T203427Z.json).

Read-only account audit: the designated account's saved statuses, version numbers,
revisions, item counts and day-label structures still match the initial
inspection. The diagnostics did not generate for that account or edit any of its
draft/current/history records. Only boolean assertions are exported in the
[preservation result](51-optional-schedule-account-preservation-20261025.json).

## Files changed in this follow-up

| Area | Files |
| --- | --- |
| Request, scope, completeness and duplicate feedback | `backend/app/modules/training/completeness.py`, `focus.py`, `selection.py` |
| Shared generation, chat and bounded attempt | `generation_service.py`, `chat_service.py`, `prescription_budget.py` in that module |
| Owner binding, dictionary, schema and authorization | `owner_rag.py`, `owner_rag_schema.py`, `owner-rag-exercises.json`, `owner-rag-authorization.json` in that module |
| Provider contract and safe diagnostics | `backend/app/integrations/ai.py`, `ai_diagnostics.py` |
| Diagnostics and tests | `backend/scripts/probe_owner_rag_runtime.py`, `backend/tests/test_training_optional_schedule.py`, `test_training_completeness.py` |
| Canonical clarification and evidence | `docs/requirements.md`, the work plan, this report, generated sheets and linked synthetic/redacted JSON artifacts |

The repository had substantial existing modified/untracked work before this
follow-up. It was preserved; no unrelated refactor, dependency, commit or push was
performed.

## Practical use and limits

Use `Gere um treino de hipertrofia em três dias, fichas A, B e C.` To replace an
existing draft explicitly, `Refaça meu treino de hipertrofia em três dias, fichas
A, B e C.` For full-body coverage add `de corpo inteiro`; letters alone do not
invent that muscle scope or a weekly calendar. Without requested days, the
generator keeps a single session. State the primary objective when combining goals.

This verifies technical generation for the exposed synthetic cases, not universal
model availability or individual clinical suitability. Real provider failures can
still cause controlled refusal after the bounded retries. Observed latency ranged
from 36 to 288 seconds, partly while the full backend suite was running; this is
not an isolated performance benchmark. The unspecified-scope endurance C contains
one exercise: it is not represented as full-body, and no universal exercise count
or optimal dose is inferred. Detailed individual exercise balance/dose remains
subject to instructor review. The active approved plan is never changed by draft
generation, and missing mandatory measurements or genuine incompatibilities remain
valid reasons to block a candidate.
