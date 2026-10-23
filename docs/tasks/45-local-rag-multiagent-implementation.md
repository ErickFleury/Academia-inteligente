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
