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
- Durable memory, client UI, and erasure: implemented as the next checkpoint.
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
- Bounded orchestrator and four workflow integrations: pending.
- Evaluation, offline checks, hardware evidence, and rollout: pending.

No acceptance-completion or laptop-performance claim is made. Optional production
hosting configuration will be reconciled with the local/hosted modes before
integrated completion; the first checkpoint targets the local development stack.
