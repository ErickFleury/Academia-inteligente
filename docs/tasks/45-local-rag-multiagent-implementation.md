# Local RAG and multiagent implementation

Status: in progress. Canonical scope and acceptance are the
[2026-10-19 requirements amendment](../requirements.md#rag-and-multiagent-assistant-design--2026-10-19).
The owner confirmed the [design](../ai-rag-multiagent-design.md) and requires a
commit before code changes and after every major tested implementation.

## Checkpoints

- Baseline: `b3da985` records the design and preceding application state. The
  pre-existing untracked audio recording is excluded.
- Local provider foundation (`4f51a03`): independent bounded embedding adapter, local
  generation defaults, CPU/optional-GPU Compose configuration, explicit model
  provisioning, and provider contract tests. Implementation complete for this
  checkpoint; actual model inference remains pending. Validation: embedding and
  existing generation-provider tests, Ruff, CPU/GPU Compose validation, and
  `git diff --check`.
- Reference persistence/import/retrieval and administrator UI (`402ad63`): implemented.
  Versioned administrator uploads, bounded extraction/import with retries,
  preview and explicit activation/withdrawal, PostgreSQL full-text/vector RRF,
  namespace isolation and lexical fallback are covered by 13 focused tests
  (including two real PostgreSQL tests in disposable schemas). The PostgreSQL
  18.6 image builds with pgvector 0.8.7; migration upgrade/downgrade passed.
  Three interface tests and frontend type checking passed. Backend regression:
  547 passed, 42 opt-in tests skipped, with the test CORS origin explicitly set.
  One existing authentication assertion was made deterministic with a fake
  invalid token instead of depending on a live Keycloak server. Ruff and diff
  whitespace checks passed. Live embedding quality remains unverified.
- Durable memory, client UI, and erasure (`4fed71e`): implemented.
  Client-only inspection/correction/forgetting requires no AI service. Compact
  reports have dates and attribution; bounded agent proposals require whole
  first-person source sentences, reject inferred diagnoses/uncertainty, and use
  revision checks plus a non-content event cutoff against stale replay.
  Integration with conversational agents follows in the orchestration checkpoint.
  Memory survives short transcript expiry and is erased with a Client even when
  an employee Account survives. Validation: 15 focused memory/PostgreSQL/migration
  checks, 34 memory/erasure/shared-account checks before the last additional case,
  six new interface tests, 28 existing routing tests with local test OIDC URLs,
  TypeScript, Ruff, and backend regression (558 passed,
  44 opt-in tests skipped). Live conversational extraction quality is pending.
- Bounded orchestrator and four workflow integrations (`1f99df0`): implemented behind
  `AI_ORCHESTRATION_ENABLED` plus an explicit Client UUID allowlist. The LLM
  chooses the backend-permitted specialist or clarification; the runtime owns
  reference retrieval, source-grounded memory proposals and citation validation.
  Conversational inference releases the client lock and rejects intervening
  memory/plan/reference/message changes before the reply transaction. Existing
  completion, confirmation, single-draft and instructor approval gates remain.
  Supporting citations accompany replies, generated drafts and adaptations.
  Validation: 11 enabled-path workflow tests; two real PostgreSQL concurrency
  tests; migration upgrade/downgrade; 10 training UI tests including citation
  rendering; TypeScript/Ruff; backend regression (575 passed, 46 opt-in skipped).
  Live model routing, grounding, latency and offline evaluation remain pending.
  Provider execution-budget foundation (`70c84dc`): request-local call, input,
  output, retrieval and time ceilings; bounded HTTP waiting without a work queue;
  explicit per-role model overrides within the selected provider; controlled
  context/output exhaustion. Validation: 27 budget/provider/diagnostics tests,
  Ruff and diff checks. Real-inference deadline checks follow.
- Offline/deployment foundation (`9feb122`): implemented. Local defaults and both model
  provisioning services now apply to production configuration too. PostgreSQL
  bootstrap installs pgvector before non-superuser app migrations. Optional
  per-role models reach containers. Offline override clears paid credentials,
  blocks external routing, disables ViaCEP and external equipment images.
  Ollama context allocation uses a conservative per-request bound instead of
  reserving 32K for every short route. Validation: 32 focused deployment,
  budget, agent and offline tests; 10 equipment/chat interface regressions; Ruff.
  Fresh isolated offline database migrated to head; local API health, OIDC
  discovery and Mailpit API responded successfully with outbound access blocked.
  Docker internal-only networks did not publish normal browser-facing ports on
  this host; complete offline browser/login verification is still outstanding.
  A 41-case synthetic local retrieval/answer evaluation is now running.
- Evaluation, complete offline workflow checks, hardware evidence, and rollout:
  desktop evaluation and offline protocol/workflow evidence recorded; human
  grounding acceptance, CPU/laptop qualification and rollout remain pending.

No acceptance-completion or laptop-performance claim is made. Optional production
configuration now supports explicit local/hosted adapters; Compose configuration
validation passed with synthetic credentials, without deploying production services.

## Pilot-driven corrections (`965c93b`)

A frozen 41-case synthetic corpus and explicit local-only evaluation/workflow/
protocol runners are available. Real evaluation found model-loading contention,
query normalization failures and unsupported conflict resolution. Corrections
keep embeddings in RAM, reuse modest generation context, bound query correction,
normalize Portuguese retrieval with a matching GIN index, and add a final
orchestrator grounding/conflict check. Existing call, token and time ceilings
remain unchanged. Onboarding extraction cannot invoke reference guidance.
Clarification cannot carry a draft mutation; database revalidation locks honor
remaining time. Pilot document limits can be lowered through configuration.

Offline PKCE login, authenticated admin access, frontend delivery and local
Mailpit delivery passed with outbound networking blocked and paid credentials
removed. See [evaluation evidence](../ai-rag-evaluation.md) for the failed
iterations, final verification status and human-review rubric. The feature flag
remains disabled; synthetic results do not establish laptop or corpus capacity.

Validation for the pilot-correction checkpoint: 635 backend tests passed with
`TEST_POSTGRES=1`, including all PostgreSQL opt-in scenarios; 242 frontend tests
passed; TypeScript, Ruff and diff checks passed. The full run exposed the local
reset utility's explicit table allowlist dependency: it now erases private memory
and preserves shared reference versions/passages, verified only in a disposable
schema. No real application reset was executed. Migration through `20261019_35`
passed upgrade/downgrade testing and was applied only to the isolated offline stack.
All four local workflows produced successful synthetic outcomes, retaining the
client/instructor review gates. Final full-corpus grounding review is pending.

The complete 965c93b evaluation reached 37/37 lexical and hybrid retrieval, with
39 delivered responses and two controlled memory-validation failures. Its answer
review found omitted procedure conditions and unsupported conflict resolution;
the retrieval score therefore does not establish acceptance. Raw synthetic
reports and the revised review contract are documented in the evaluation report.

## Final grounding correction (`f87e46c`)

The review contract now lists omitted prerequisite conditions and incompatible
statements before its verdict. Any listed issue blocks delivery even when a
boolean verdict incorrectly accepts it. Specialist instructions preserve operating
prerequisites and keep passage IDs out of client text. Two additional regression
cases cover inconsistent review verdicts. Migration-test setup now isolates its
Alembic marker from an already migrated base schema. Validation: 637 backend
tests passed with PostgreSQL checks enabled, Ruff, and diff whitespace checks.
The complete local evaluation and final human-review worksheet accompany this
checkpoint's evidence report; pilot acceptance remains separate from implementation.

## Plan tool permissions (`314f7fa`)

A local adaptation rerun proposed a memory mutation without permission and was
correctly rejected. The plan-routing schema now permits only an empty memory
change list; backend permission checks still reject a provider that ignores it.
Validation: all four local workflows passed again, including a 37.051-second
adaptation request; all 638 backend tests passed with PostgreSQL checks enabled.
The 41-case chat evaluation reached 37/37 lexical/hybrid recall, but the >=95%
human grounding gate is not claimed. Cold and warmed CPU-only q03 probes both
hit the 30-second deadline. See the [evidence report](../ai-rag-evaluation.md) and
[review worksheet](../evaluations/2026-10-19-local-assistant/f87e46c-review.md).

## Outstanding acceptance work

The final memory guard (`6fdef5c`) also rejects first-person questions as uncertain
agent evidence, preserving both facts and revision on rejection. Full backend
validation after this guard: 639 passed with PostgreSQL checks enabled. The
frontend remains at 242 passing tests; TypeScript/Ruff checks passed. No live
paid API was used, and no real application data was migrated or reset.

- Human claim-by-claim grounding review and correction of the flagged answer
  quality issues. Retrieval success does not satisfy this gate.
- A CPU-only profile that meets the existing deadlines; the selected 8B model
  failed both CPU probes. No paid fallback or relaxed deadline was introduced.
- Actual RTX 2070/seventh-generation i7 laptop measurements, concurrent capacity
  and disconnected browser-ingress verification. Protocol checks and component
  tests are recorded with their narrower scope.
- Deliberate test-client rollout after verification. Defaults remain disabled.

## Fluid training control correction (2026-10-23)

Scope: the owner-requested RF-15/RF-18 conversation and durable-memory refinement
in the canonical specification. Checkpoints began at `b92d5d6`; `d48643b` adds
dynamic personal questions, semantic plan/draft intent, bounded earlier-message
recall and compact structured answers. Migration `20261023_38` adds nullable
answer metadata to existing memory facts. Raw quotations remain in expiring chat
state; only current validated reports become durable facts. Manual corrections,
forgetting, ownership, optimistic revisions and source-event cutoff remain enforced.

The reproduction identified fixed question topics, copied rejected assistant
prose, personal schedules in search queries, definitions displacing prescription
passages, missing activity-selection passages, and false-positive model review.
The correction separates client reports from reference evidence, retains valid
answers on a source-gap reply, and adds prescription/population/coverage ranking.
There are still at most two retrieval rounds and five passages in the working
context. A specialist may request the remaining search; a proposal may use one
correction when time remains for validation. Neither extends the request budget.

The reviewer must inspect every proposed item. Necessary backend checks now
compare exercise names and numerical sets/repetitions/rest/duration against the
actual cited passages. They recognize bounded Portuguese/English forms and simple
explicit weekly allocations. The generator receives extracted quantities with
source labels and units. These checks are conservative: an unrecognized synonym
or source format may cause abstention. They do not establish medical applicability,
verify every free-text claim, or replace instructor approval and human accuracy
evaluation. Unchanged draft values may use the saved record; changed prescriptions
still require evidence.

On the desktop, the 12,288-token local context used 85% GPU residency and reproduced
60-second plan timeouts. An 8,192-token context used 100% GPU residency. A synthetic
supported plan completed generation and item review in 17.08 seconds before the
final source-parser guard; a real-account replay exposed unsupported prescriptions
despite a positive model verdict, motivating that independent guard. Subsequent
read-only replays rejected unsupported prescriptions rather than saving them.
No real-account messages, memories or plans were written by these replays. Local
chat and plan defaults now use the measured smaller window; truncation/context
shifting remain disabled, so oversized requests fail explicitly. This is desktop
evidence, not a laptop-capacity or full-corpus accuracy claim.

Regression coverage includes natural plan requests, non-catalog questions,
free-form corrections, topic changes, earlier own-message recall, transcript
expiration, source-gap memory persistence, forgetting/replay suppression,
source quantity checks, population/measurement/activity retrieval, per-item review,
bounded repair and existing plan/instructor/privacy workflows. The final test
result and deployed checkpoint are reported with this task's delivery.

Final regression run: **803 passed**, including PostgreSQL tests, with two existing
Alembic configuration warnings. Ruff lint passed; all eleven changed Python files
passed formatting checks. The repository-wide format check still reports three
unrelated pre-existing test files, which were left unchanged.

With the final source guard enabled, a synthetic, fully supported local plan
completed routing, generation and review in **34.12 seconds / three calls**.
The read-only test-account replay recovered all five previously supplied answers
and did not repeat them. It still failed to produce an acceptable proposal: the
model combined alternative activities, added unsupported stretching and mismatched
the documented weekly amount. The backend rejected it without saving a plan or
requesting those personal answers again. This remains a real-source generation
quality limitation; the passing synthetic control does not resolve it. The final
8,192-token probe showed **89% GPU / 11% CPU** residency, rather than the earlier
100% GPU observation, so full GPU residency is not guaranteed under current
desktop memory pressure. No paid model or deadline relaxation was introduced.

### Follow-up: preserve source alternatives and intensity conditions

The next replay exposed a more specific false positive: the model paired the
vigorous-activity weekly quantity with moderate-activity wording. A deterministic
regression reproduced that error. Source extraction now retains explicit intensity
conditions beside each weekly quantity, preserving ordinary commas while still
recognizing decimal commas. The backend rejects a mismatched or omitted intensity
when allocating a conditioned weekly dose. Ambiguous clauses do not become
allocation candidates. Quantity values still come from the references.

When retrieved passages support continuous-activity alternatives but provide no
resistance doses, the generation schema permits one documented alternative, with
its supported name, quantities and explained weekly allocation. It still permits
clarification when none meets the request or client conditions; this is not a
required personal questionnaire or a replacement for a requested resistance plan.
Sources with resistance doses retain the general plan schema. Semantic review and
instructor approval remain required.

Final verification after this correction: **807 backend tests passed**, including
PostgreSQL tests, with two existing Alembic warnings. Ruff lint and formatting of
changed files passed. The final read-only test-account replay reused all five
answers and produced a single-activity proposal with matching source duration and
intensity in **24.06 seconds**, passing the numerical guard and model review. This
supersedes the earlier failed replay for that case; it is not a full-corpus human
accuracy result or medical clearance. No account messages, memories or plans were
saved by the replay. GPU residency remained 89% in the final probe.

Deployment uses migration `20261023_38`, system-wide RAG (`true` / `*`), and the
8,192-token chat/plan windows. Conversation/memory, grounding, and context-allocation
checkpoints are `d48643b`, `4b2db0b`, and `e1e27c3`; this follow-up has its own commit.

### Draft-edit request budget correction (2026-10-23)

Baseline: `b9489fc`. The owner-reported draft substitution failed with
`input_token_limit` after routing recognized `edit_draft`: it still used the
ordinary-chat budget. A read-only replay reproduced the failure before the
specialist call. The conservative cumulative reservation was 32,711 against
the 32,000 chat ceiling; this was an application budget failure, not a source
refusal or proof of model-context overflow.

Authorized edits of an owned editable draft now use the existing plan limits:
60 seconds, six model calls and 64,000/12,000 aggregate input/output ceilings.
Promotion retains the request start time and every consumed counter, both for
edits recognized before routing and for semantic edit intent recognized by the
orchestrator. Ordinary chat and requests without an editable draft keep chat
limits. The 8,192-token local context window and source/instructor checks remain.

Draft prompts omit unused initial-plan allocation/quantity derivatives and the
duplicate conversation-style instructions, removing 1,747 UTF-8 bytes in the
reproduction. Complete source passages, personal answers, saved draft and client
restrictions remain available; no truncation or larger model window was added.

Validation: five new regression cases first reproduced three failures, then
passed. The full backend suite passed **812 tests**, including PostgreSQL tests,
with two existing Alembic warnings; Ruff lint and changed-file formatting passed.
The same real-account request completed generation and review in read-only replays
of 32.44 and 28.74 seconds without the budget error. The inspected reply asked
about limitations relevant to stair climbing and returned no draft update.
This verifies the technical failure is removed, not that the substitution has
been applied. Replays saved no account messages, memories or plan changes.

### Draft-edit clarification state correction (2026-10-23)

Baseline: `118999d`. The repeated stair-climbing question was persisted as an
ordinary answer with `clarification=null`; the following personal reply became
an unstructured memory statement. Both requests returned HTTP 200, bypassing the
structured answered-question checks. This was distinct from the earlier budget
failure.

Authorized draft editing now requires either a structured draft update or a
structured clarification, including in the provider's output schema. A personal
clarification stores the owned draft identifier/revision and original retained
user-event identifier alongside its dynamic questions. Request text is resolved
from that same conversation rather than copied into durable memory. The router
interprets free-form answers against those fields and chooses resume, replace,
cancel or ordinary chat. An already-answered question gets at most one correction
within the existing request budget. Authoritative onboarding restrictions remain
available and cannot be cleared by a new report.

The router now receives the saved draft's name/exercises and cannot choose initial
generation while that draft exists. Continuation metadata is discarded for a
changed draft, absent/expired or foreign request, or a later memory-reset cutoff.
Reloads and retries retain the original pending command without double-applying
the edit; uncertainty keeps the request pending and a replacement request gets
its own source event. Existing ordinary prose questions are not retroactively
converted into authorization metadata: resubmitting the edit starts the corrected
flow.

Read-only local verification with corrected pending-question metadata recognized
“não tenho limitações” under the pending topic, selected resume/edit_draft, and
did not repeat the question. It completed in 31.11 seconds, then rejected the
generated replacement at source validation (exercise choice/duration). This
verifies continuation, not a successful or medically approved stair prescription.
No production conversation, memory or draft was written by the harnesses.

Live verification also found a separate lost GPU device in the Ollama container:
host NVIDIA access worked but container NVML failed and inference fell back to
CPU. Recreating only the existing Ollama container restored device access while
preserving model volumes/configuration; no dependency or GPU-driver change was
made. Temporary diagnostic scripts and outputs are removed after verification.

Final validation: **822 backend tests passed**, including PostgreSQL tests and
ten new clarification cases, with two existing Alembic warnings. Ruff lint and
formatting of changed Python files passed. The new cases cover persisted/reloaded
continuation, idempotency, schema constraints, cancellation/topic changes,
replacement, uncertainty, repeat-question repair, ownership, expiry, forgetting,
durable answers and preservation of onboarding restrictions.

### Optional OpenAI generation configuration (2026-10-23)

At the owner's request, the deployment's ignored `.env` now selects
`AI_PROVIDER=openai` and `OPENAI_MODEL=gpt-6-luna`, with empty per-role model
overrides. All generation roles inherit Luna. The existing Ollama embedding
configuration (`embeddinggemma`) and system-wide RAG remain active; no reference
reindexing or application-code changes were needed. The backend was recreated
and its health endpoint returned HTTP 200. Credentials were neither printed nor
committed. The pre-change code checkpoint is `c6d102d`.

A single synthetic Responses API preflight, initiated with Sol before the owner
selected Luna, returned HTTP 429 / `credit_balance_exhausted`. No generation
completed, and no further live requests were made after that billing failure.
Luna account/model access and end-to-end answer quality therefore remain
unverified. The configured OpenAI chat requires funded API billing before it can
operate. No client conversation, memory, or plan was modified by this check.

Validation: 45 mocked adapter/budget tests passed
(`test_openai_onboarding_adapter.py`, `test_ai_budget.py`); runtime configuration
confirmed the OpenAI adapter, Luna for all generation roles, local embeddings,
and enabled RAG. These tests made no paid API calls.

Operational rollback: set `AI_PROVIDER=ollama` in the local `.env` and run
`docker compose up -d --no-deps --force-recreate backend`. The existing local
model configuration and model volumes were retained. Git checkout alone does
not revert the ignored deployment configuration.

### Confirmed health corrections and client presentation (2026-10-23)

The owner approved correcting outdated completed health information through chat
and hiding source details from clients. Checkpoint: `5df79c8`. Canonical scope and
acceptance are recorded in the corresponding amendment to `docs/requirements.md`.

The router now sees the current health record and can propose a correction,
resolved complaint, or changed status using an actual current-message quotation.
The backend shows the complete previous/proposed health category and requests
confirmation. It rechecks the original own-conversation source, record snapshot
and revision, forgetting cutoff, expiry, and full confirmation utterance. Free-form
intent interpretation remains model-driven; ambiguity or denial cannot clear the
record. Another correction starts a new reviewable proposal. Long health fields
are displayed completely rather than truncated to the model's short-reply limit.

Confirmed changes use completed-onboarding validation and a non-content audit
entry, preserving unrelated categories, completion date, and approved/current
plans. Persistence shares the reply transaction and existing client lock, domain
revision check, request fencing and idempotency. Current health is used by later
turns and by a resumed draft edit or initial plan request. Pending metadata uses
existing expiring chat storage; no migration, dependency or data backfill is needed.
The correction is a client report, not medical clearance. Existing saved records
are not automatically rewritten when this code is deployed.

Client chat, adaptation and plan screens no longer display citation footers.
Prompts and controlled fallback replies omit source/retrieval commentary while
the grounding checks and stored compact citations remain intact. Administrative
reference management remains available. Previously saved prose is not rewritten.

Validation: **849 backend tests passed**, including isolated PostgreSQL reload,
retry and concurrent-update checks; **16 client UI tests passed**, frontend build,
Ruff lint/format and Git whitespace checks passed. Two existing Alembic warnings
and the existing frontend bundle-size warning remain. The full suite requires its
isolated rollout/CORS settings instead of inheriting the LAN deployment values.
OpenAI credentials were removed from test processes; no paid live evaluations or
production account health/chat changes were performed. Live Luna interpretation
and end-to-end answer quality still require user testing.

The backend was recreated and returned HTTP 200 from `/health`; the loaded router
includes health corrections. Runtime remains OpenAI `gpt-6-luna`, local Ollama
`embeddinggemma`, and system-wide RAG. The secret-bearing `.env` is not committed.

### Health retry recovery and readable memory statements (2026-10-23)

Scope: RF-12, RF-16, RF-18/RF-19 and the confirmed-health/RAG-memory amendment.
Checkpoint: `da2d6ca`. The latest observed chat failure followed a successful
OpenAI response (about 8.5 seconds) with backend HTTP 422 validation failure.
The original structured response was not logged, so its exact rejected field
cannot be reconstructed. A synthetic regression reproduced rejection when a
retry quoted an earlier own health report instead of the current retry message.

The router and backend now permit a proposal from the bounded retained own user
messages supplied in context. Database validation checks actual ownership, role,
sequence, context availability, expiry, forgetting cutoff and newer health-record
updates. Whole source sentences preserve negation, and surrounding uncertainty
still prevents a proposal. Pending confirmation remains bound to the original
report and current health revision. A retry never supplies consent; only the
current reply to the displayed proposal can authorize persistence.

Invalid health evidence or inconsistent model-proposed fields now asks for
clarification without breaking the chat turn or changing health data. Allowlisted
health error codes improve diagnostics without logging personal content.

Structured compact memories display self-contained statements without repeating
their eliciting question, with initial capitalization and terminal punctuation.
New structured memories use the same formatting. Existing rows are formatted on
read; evidence, attribution and dates remain unchanged. Short contextual answers,
measurements and manual edits retain their wording. A scoped read-only check
confirmed the requested display for the test account without modifying its data.

Automatic approval review rejected a live replay because it would transmit the
account's health/chat context externally. The replay was not performed; diagnosis
and verification used synthetic providers. Live model interpretation still needs
user testing, and the original payload-specific diagnosis remains unverified.

Validation: **870 backend tests passed**, including isolated PostgreSQL checks;
Ruff lint/format and Git whitespace checks passed. The two existing Alembic
configuration deprecation warnings remain. The backend was recreated and its
health endpoint returned HTTP 200. Runtime remains OpenAI `gpt-6-luna` with local
Ollama `embeddinggemma` and enabled orchestration. No production health records
were edited, and no paid model evaluations were performed for this fix.

### Owner-approved OpenAI timeout increase

The latest observed request exceeded the ten-second provider wait and returned
HTTP 503 with `deadline_exceeded`; the preceding two requests completed in about
7.2 seconds. The owner approved increasing the local `.env` setting
`AI_TIMEOUT_SECONDS` from 10 to 25 seconds. The existing adapter already reads
this setting and caps each wait at the remaining orchestration budget; total
conversation and plan limits remain 30 and 60 seconds respectively. Luna, local
embeddings and retry behavior remain unchanged. No source-code change is needed.

Validation: 45 mocked adapter and budget tests passed without paid API calls.
The secret-bearing `.env` remains ignored and is not committed. To roll back,
set `AI_TIMEOUT_SECONDS=10` and recreate the backend; Git rollback alone cannot
restore this deployment setting. The preceding code return point is `1dc0bea`.
After backend recreation, runtime verification confirmed a 25-second provider
timeout, a 30-second conversation budget and HTTP 200 from `/health`.

### Incomplete hosted response handling

Scope: shared provider adapter supporting RF-12, RF-16, RF-18/RF-19 and the
bounded RAG orchestration amendment. Checkpoint: `1d1c782`.

After the timeout increase, a provider call returned an incomplete response in
about 9.7 seconds, producing controlled HTTP 503. This was below the active
25-second timeout. The historical log omitted the provider's incomplete reason,
so output-limit exhaustion remains a likely explanation, not a proven diagnosis
of that exact request. The original response was not retrieved or replayed.

A mocked regression reproduced the failure when routing required 1,500 output
tokens under the old 1,000-token allowance. Hosted orchestrator calls now request
up to 2,000 output tokens, capped by the remaining aggregate budget. Local Ollama
routing remains at 1,000. Actual usage is reconciled before later stages; total
chat/plan ceilings remain 4,000/12,000 output tokens, four/six calls and 30/60
seconds. The active model remains Luna and the provider timeout remains 25 seconds.

Incomplete responses now classify `max_output_tokens` and `content_filter`
separately, with unknown or malformed details mapped to a generic category.
Provider diagnostics include only an allowlisted role and category, never raw
response content or arbitrary reason text. Partial responses remain unusable,
including legacy calls outside orchestration. No automatic incomplete-response
retry or additional paid evaluation was introduced. Classification follows
[official OpenAI structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs).

Regression coverage checks completion beyond the old routing limit, remaining
budget for specialist/review calls, non-retryable partial-output rejection,
safe handling of malformed details and diagnostic privacy. Actual live completion
on the user's original request remains to be verified through normal user testing.

Validation: **880 backend tests passed**, including isolated PostgreSQL workflows;
Ruff lint/format and Git whitespace checks passed. Two existing Alembic deprecation
warnings remain. No live provider evaluations or production account edits were
performed. The secret-bearing `.env` is unchanged and remains excluded from Git.
After backend recreation, `/health` returned HTTP 200; runtime checks confirmed
`gpt-6-luna`, the 25-second provider timeout and 30/60-second total budgets.

### Rebuilding the sole draft through chat

Owner-approved scope: RF-15/RF-18 full-draft rebuild, with RF-16 visibility and
existing instructor approval/grounding requirements. Checkpoint: `939a298`.
The reported request completed with HTTP 200 but returned an evidence
clarification through the chat specialist. Inspection found no distinct full
rebuild action, and the direct initial-generation shortcut merely announced that
a draft already existed. Existing edit context could continue to frame the task
as the previous exercise substitution. The exact live routing output was not
retained, so the latter model interpretation is not asserted as proven.

The router now distinguishes `rebuild_draft` from `edit_draft`, ordinary chat and
initial creation. An explicit new-plan request with an existing proposal delegates
replacement content to the existing initial-plan specialist, then persists into
the same owned proposal/revision through the chat service's validated atomic edit.
There is no second draft, implicit approval, activation or current-plan mutation.
The generation phase retains the same request source, budget origin/counters,
memory snapshot and domain revision, including the cost of its first router call.

Rebuild context carries complete onboarding, current health (including an explicitly
confirmed staged correction), equipment, applicable current-plan context, compact
memory and source-validated personal answers. It omits prior edit commands,
rejected prescriptions and the prior exercise target from the new generation and
review context. Stored facts/history are not deleted. New explicit exercise or
modality requirements remain in the original rebuild request. Technical quantities
still require references and per-exercise checks; source gaps cannot be replaced
with fabricated doses or requests for the client's technical prescription.

Missing personal information or health confirmation preserves a backend-owned
pending rebuild with the original event, draft identity and revision. Answers
resume generation after refresh without another plan command. Cancellation, topic
changes, replacement requests and existing retention/forgetting boundaries govern
continuation. Failure preserves the previous draft, and retries remain idempotent.
The generic initial-plan shortcut is retained for the legacy disabled-rollout path;
enabled chat sends an existing draft's request through intent interpretation.

Synthetic regressions cover rebuild/replay, continuation, health confirmation,
personal memory, replacement of an old edit, cancellation/topic changes,
completed-onboarding and ownership gates, concurrent revisions, provider/evidence
failures and preservation of the approved current plan. No live account request
was replayed or paid model evaluation performed; model interpretation and evidence
adequacy on the original request still require normal user testing.

Validation: **894 backend tests passed**, including isolated PostgreSQL workflow
checks; Ruff lint/format and Git whitespace checks passed. The two existing
Alembic configuration deprecation warnings remain. The full suite also verifies
the compatibility fallback when a provider returns an initial-creation action
despite an existing draft. Cancellation is resolved before rebuild authorization
and budget promotion. No frontend/API migration or new dependency was required.
Backend recreation completed; `/health` returned HTTP 200 and runtime inspection
confirmed the new action, `gpt-6-luna` and the 25-second provider timeout. Deployment
did not replay the account's request or rewrite its existing draft/history.
