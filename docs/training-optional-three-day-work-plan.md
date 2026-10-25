# Optional three-day RAG generation: work plan

Date: 2026-10-25. Scope: RF-15/CA-15.11–13, RF-18, owner-assisted
EXT-RF-AI-02/.27–29/.31–33. Canonical requirements remain in requirements.md.
The owner explicitly requests optional three-day sheets beyond full-body wording.

## Investigation

Read-only inspection was limited to the owner-designated account's recent training
requests, response/session metadata and saved versions. No health facts, identity
IDs, raw client transcripts or private records are copied into this document.
Recent explicit three-day requests resulted in a proposal containing only A;
an older approved version already had A/B/C. Approved history must be preserved.

Confirmed causes:

1. `requested_training_schedule` discards day requests unless focus is `full_body`.
   The focus analyzer allows that scope only for explicit full-body wording.
   Ordinary requests for three days therefore become an empty schedule and A only.
2. Owner RAG writes the complete routine in one bounded candidate, but the existing
   variation comparison only checks per-session sequential generation. Whole-routine
   A/B/C needs equivalent validation without multiplying candidate/call budgets.
3. Goal scope can come from model focus or onboarding instead of the explicit
   request. The inspected draft's binding retained hypertrophy when the new request
   specified strength. Mixed goals can likewise be silently reduced to one goal.
4. Recent metadata includes incomplete-plan and redundant-prescription refusals.
   Source/model outputs are not retained for these live requests, so their exact
   item-level causes cannot be reconstructed from generic reason codes alone.

Possible contributing cause: goal words may be misclassified as muscle targets;
the current focus validator checks literal occurrence but not technical muscle
vocabulary. This must be tested rather than attributed to a specific historical call.

## Execution

1. Add a canonical clarification: session selection and muscle scope are independent;
   explicit A/B/C or three days retains three sheets, while an unspecified schedule
   remains unspecified. Targeted schedules stay targeted, not forced to full-body.
2. Parse explicit counts/labels deterministically, detect incompatible/unsupported
   schedules without guessing, and preserve them through request, schema, review,
   binding, reuse and rendering. Do not invent a calendar or weekly dose.
3. Ground goal and focus in the actual request before retrieval. Use onboarding
   only when no goal is specified. Mixed goals without an explicit primary goal
   require clear clarification, not silent substitution or a provider error.
4. Constrain the whole-routine writer to the requested session structure and
   qualitative loads. Validate every requested sheet and compare complete exercise
   selections across days, including the existing cited-review repetition exception.
   Keep one correction/two candidates and the shared HTTP/deadline budgets.
5. Add focused regression tests: explicit/implicit schedules, targeted requests,
   omitted/extra days, copied days, goal mismatch, mixed-goal clarification, chat
   rebuild, existing-draft rollback/replay and instructor/client rendering contracts.
6. Freeze actual-provider synthetic cases for three-day strength/hypertrophy,
   default single-session and critical refusals. Preserve all attempts and outputs.
   Run relevant tests and the full backend suite; update exact runtime authorization,
   deploy locally, verify health and confirm the inspected account's saved history
   was not modified by diagnostics.

## Completion criteria

- Explicit three-day requests can produce distinct A, B and C sheets in one atomic
  reviewable proposal, with actual citations, requested goal and qualitative load.
- No day request does not force A/B/C; explicit one/two-day requests retain scope.
- Missing/copy/extra-day output receives at most one correction; remaining failure
  preserves the previous draft and current plan. No always-reject implementation.
- Ambiguous goal/schedule, actual missing measurements and source outages remain
  controlled refusals or clarifications. No invented clinical dose or activation.
- No production client records or sensitive values enter fixtures, artifacts or logs.
- Report actual test outcomes and limits; no universal generation guarantee follows
  from a finite synthetic sample. No new dependencies, provider or architecture.

## Execution refinements discovered by actual-provider diagnostics

- Whole-routine transport successfully restored labels but exposed repeated
  selections, mismatched per-day review positions and reversed repetition ranges.
  Position-scoped review decoding and a stronger representation-only numeric
  pattern address those errors without changing clinical dose bounds.
- A review accepted a full-body routine whose individual days lacked required
  movement patterns. The bounded technical dictionary now names those patterns;
  full-body wire slots and deterministic per-day validation enforce the existing
  CA-15.13 coverage requirement, independently of the model's completeness verdict.
  These slots do not prescribe a universal exercise count or dose.
- Whole-routine generation still copied entire selections after correction.
  For two/three sheets, restore the existing per-session generation mechanism,
  explicitly showing previously selected technical IDs. All fragments share the
  same request budget and a single global content-correction allowance. No fragment
  is saved independently; the final complete routine is validated and saved once.
  This replaces step 4's initial monolithic transport strategy for initial/rebuild
  generation, without multiplying the permitted attempts or HTTP limits.
- Owner-RAG sampling is recorded as temperature zero. Model/provider, six-passage
  bound, context size, adapter timeouts and clinical approval limitations remain.
- Explicit regeneration may refresh an obsolete technical configuration's draft;
  viewing/submission/approval cannot silently recertify it or change approved history.
- Diagnostic plans/results from every stage remain unchanged. A model-accepted
  draft is not scored as covering full body merely because its status is proposal.
- Per-session decoding now lets the writer choose a branch that omits at least
  one technical exercise identity from each earlier selection. This prevents
  exact copied sets without prescribing an exercise template, sets, repetitions,
  loads or rests. Branches that empty a required full-body slot are excluded;
  when no distinct complete branch exists, the original reviewed-evidence repeat
  exception remains available through ordinary domain validation. A provider
  that ignores decoding constraints is still rejected by the domain check.
- Review decoding distinguishes a passing session with empty failure arrays from
  a failing session. Contradictory provider output remains a controlled failure.
  Duplicate correction feedback identifies the actual conflicting item positions.
- Four late regression cases reproduced a separate chat shortcut: an existing
  one-sheet draft was reused for explicit `ABC`, goal-only or twice-weekly
  instructions, and plural `fichas` bypassed direct generation. Refresh detection
  must use the same schedule/goal semantics, and plural sheet requests must enter
  the generation path. Request-UUID replay must still avoid duplicate generation.

## Completed execution

The final actual-provider matrix passed seven generation cases and three expected
refusals. The complete final backend suite passed 1,260 tests, including isolated
PostgreSQL cases; the focused owner/chat/schedule suite passed 97 tests. The local
backend was recreated and its health/readiness checked. Account inspection and
public-corpus retrieval were read-only; the designated account's saved versions
were preserved. Exact outputs, all earlier failures, changed files, deployment
evidence and practical limitations are in the
[delivery report](tasks/51-optional-three-day-delivery-20261025.md).
