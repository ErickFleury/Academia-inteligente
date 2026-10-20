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
- Bounded orchestrator and four workflow integrations: implemented behind
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
- Evaluation, offline checks, hardware evidence, and rollout: pending.

No acceptance-completion or laptop-performance claim is made. Optional production
hosting configuration will be reconciled with the local/hosted modes before
integrated completion; the first checkpoint targets the local development stack.
