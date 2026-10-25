# Task 49 — Atomic Training Generation with Mandatory Abstention

**Current owner-RAG scope — 2026-10-25:** assisted generation/chat/adaptation,
dependency revalidation, bounded correction and ordinary submission/approval are
implemented. An actual local writer/reviewer run produced a reviewable proposal;
an outage control made zero model calls and saved nothing. See
[current delivery](46-59-owner-rag-delivery.md). Independent evaluation is optional
for this mode under the later canonical owner instruction.

**Status:** operational generation/chat/adaptation/review adapters and routes
implemented under the development exception (2026-10-24); actual-provider
evaluation, professional acceptance and release remain incomplete.
**Feature task:** EVID-IMPL-05.

See the [integrated status report](51-training-prescription-verification-report.md).
The [approved development exception](../training-prescription-development-amendment.md)
permits the [isolated integration harness](48-50-isolated-prescription-development-report.md).
The original harness refuses ordinary database scopes. The later
[operational follow-up](45-51-operational-integration-follow-up.md) registers
authorized operational adapters; the deployment gate remains disabled and its
packaged policy artifacts contain no approved cohort.

## Objective

Apply the shared evidence/prescription gate to every AI path that can produce
or change a workout. Discard unsupported output without publishing a partial
prescription or mutating saved training state.

## Requirements covered

- EXT-RF-AI-02: EXT-CA-AI-02.8–10/13/17/20–21; consume .16/19/22 contracts.
- RF-15/CA-15.1–13, RF-18/CA-18.1–8, RF-19/CA-19.1–5 integration.
- RF-17 and EXT-RF-INST-02/03 only for atomic draft/review/history preservation.

## Related rules and constraints

RN-04/05, RN-11–RN-20, RN-23, RN-29–RN-33; RNF01/04–06; DEC-07/08/15/18,
EXT-DEC-AI-02. No automatic approval, generic workout fallback, warning-only
bypass, extra editable draft, diagnosis or live-provider dependence in tests.

## Prerequisites and required reading

Task 48 shared gate exists. Read `AGENTS.md`, feature overview, EXT-RF-AI-02,
listed canonical RF/CA/rules/RNF/decisions, complete RAG contract, RF-18 request
and submission policies, EXT-RF-INST-02/03, sections 7.2/9.2 and the existing
equipment operational policy. Inspect generation/chat/adaptation services,
lifecycle/review/collection services, routes, providers, diagnostics and tests.
Read [the methodological protocol](../training-evidence-methodology.md), sections
4–6, for conditional policies and distinct abstention/recovery outcomes.
Read [the execution contracts](../training-prescription-execution-contracts.md),
especially input snapshots and the explicit draft/approval transition matrix.

## Permitted scope and expected behavior

1. Inventory initial generation, targeted requests, full rebuild, draft editing,
   adaptation generation/acceptance, cached returns and idempotent replays.
   Make all prescriptive paths call the same gate rather than copy checks.
2. Perform input/applicability/evidence checks before calling the writer where
   possible. Validate candidate parameters and provenance before persistence or
   serializing any actionable training content into chat or previews.
3. Return stable reason codes and authorized pt-BR explanations for abstention.
   Separate documented restriction conflict, missing/ambiguous input, insufficient
   applicable support and technical unavailability. Missing support or a timeout
   must not become a diagnosis, a claim of harm or a prohibition on exercise.
   Qualified explanatory chat can continue; a request cannot bypass the gate by
   asking for a workout as prose instead of a structured sheet.
4. Keep rejected candidates transient. Persist no partial plan/operations or
   raw rejected workout. Existing permitted chat may retain the explanation,
   without reproducing the discarded prescription or exposing private data.
5. Reuse existing bounded retries/corrections. Do not retry missing evidence
   until a model agrees, lower policy thresholds, or replace support with a
   generic routine. Preserve controlled external-error semantics.
6. Bind success to exact draft/current revision and policy/evidence versions.
   Recheck eligibility at writes, AI reuse, submission and approval of qualified
   AI drafts. Expired/revoked support or content changes require revalidation.
   Preserve the existing sole-draft/idempotency/stale-base rules.
7. Treat legacy AI drafts as unvalidated. They remain visible as saved content,
   but cannot be replayed as a newly qualified result or newly submitted/approved
   as qualified AI content without revalidation. Preserve approved history.
8. Keep manual instructor creation/editing usable during corpus/provider outages
   after successful backend initialization. A failed schema/knowledge bootstrap
   still prevents backend readiness and manual endpoints; follow Task 46 recovery,
   not a new degraded mode or a promise of pre-initialization availability.
   Explicit manual editing clears affected AI qualification/citations under the
   existing policy; changing an origin flag must not silently bypass validation
   or misrepresent AI content as professionally authored.
9. Implement confirmed request-specific input snapshots in the existing client
   clarification flow according to Task 47's readiness matrix. Preserve fact
   authority, confirmation/time validity and conflict handling; bind the exact
   snapshot/hash to the attempt. Do not rewrite completed onboarding or collect
   medical/retention data beyond existing approvals. Missing facts get a focused
   clarification rather than an invented default or endlessly repeated question.
10. Implement the transition matrix for legacy, edited, expired and manual drafts.
    An instructor may explicitly assume an existing saved draft on exact revision,
    recording responsibility/reason and preserved AI lineage, even without cosmetic
    edits. Clear AI qualification; ordinary manual approval remains a separate
    existing instructor action. Never offer this action for discarded candidates.
11. For AI adaptation, validate the complete resulting normalized plan and totals,
    including unchanged legacy/manual items. Inability to qualify the base means
    controlled AI abstention/manual review, not partial qualification or silent
    historical recertification. Apply input/evidence staleness at approval as well
    as generation; keep all transitions concurrency checked.

Permitted areas: backend training/lifecycle/review routes/services, AI adapter
contracts only where necessary, focused tests and API documentation. No frontend
redesign, unrelated refactoring, provider/model change or equipment CRUD.

## Acceptance criteria

- EXT-CA-AI-02.8–9: each prescriptive path rejects unknown profile, incomplete
  evidence, out-of-policy output, contradictory restrictions and provider outage;
  no rejected workout appears in chat, preview, proposal or review queue.
- EXT-CA-AI-02.10: rejection preserves version/item/operation counts, exact saved
  content, revision, submission timestamps, current-plan selection and history.
  Successful writes remain atomic; simultaneous requests cannot overwrite state.
- EXT-CA-AI-02.13: caches/replays/legacy content cannot bypass current eligibility;
  manual workflow and approved historical snapshots remain intact.
- Supported complete fixtures succeed in all applicable paths with proper client
  confirmation/submission/instructor approval, never automatic activation.
- EXT-CA-AI-02.17/20–21: confirmed input snapshots, manual assumption/audit and
  every transition-matrix row are enforced. Runtime failure preserves manual
  authoring; failed bootstrap remains unavailable until documented recovery.

## Tests and validation

Use fake adapters and reviewed synthetic policies. Parameterize critical cases
across all entry points, prose bypasses, stale/idempotent/cached returns, source
revocation after generation, correction failure, transaction rollback and races.
Assert distinct outcome codes and appropriate follow-up for restriction conflicts,
missing inputs, support gaps and outages, including no false prohibition on exercise.
Test late conflicting/stale facts, confirmation replay, preserved onboarding,
instructor-only manual assumption without content edits, immutable AI lineage,
expired submitted drafts, complete legacy-base adaptation, and inability to
expose a discarded candidate through the manual path. Separate runtime-outage
manual API tests from startup/readiness recovery tests owned by Task 46/51.
Run affected generation/chat/rebuild/targeted-request/adaptation/submission/review/
lifecycle/RAG tests, including real PostgreSQL concurrency checks. Update former
warning-only generation expectations; preserve qualified non-prescriptive chat.
Review the diff and API error compatibility.

## Completion requirements

Report files, tests/results, entry-point coverage, decisions and unresolved gates.
No unsupported cohort enablement, commit or push.

## Ready-to-use Codex prompt

Read `AGENTS.md`, this task and Required reading. Integrate Task 48's shared gate
across every prescriptive AI entry point, including prose, cached and replayed
results. Discard rejected candidates atomically while preserving saved drafts,
approved history and manual authoring. Run focused positive/negative/concurrency
tests, review the diff, and report files, checks, decisions and gaps in at most
10 lines. Do not commit or push.
