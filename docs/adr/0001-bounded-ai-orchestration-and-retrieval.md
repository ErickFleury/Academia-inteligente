---
status: accepted
---

# Bounded AI orchestration and reference retrieval

On 2026-10-19, the owner approved the design direction of an LLM orchestrator
that selects narrowly scoped specialist agents and combines their results
across conversational onboarding, initial training generation, training chat,
and adaptation. The purpose is grounded training guidance and reliable request
handling, assessed through representative conversations and factual grounding
alongside latency and cost. This replaces solely deterministic workflow routing
as the intended AI coordination approach, while backend services retain
authority over permissions, validation, persistence, and approval. The trade-off
is more flexible delegation at the cost of additional execution complexity;
agent execution must therefore be bounded.

The initial specialist boundaries match onboarding, initial plan generation,
training questions, and plan adaptation. Retrieval is a shared tool rather than
a mandatory extra agent. Agents run inside the existing FastAPI modular
monolith, retaining the provider-independent OpenAI/Ollama adapters.

The owner selected a small explicit Python orchestration runtime around those
adapters. The LLM selects allowed specialists, while backend code enforces
delegation, tool permissions, deadlines, and output validation. Specialists
cannot recursively spawn agents. A graph framework is not selected: current
bounded requests do not justify its additional state and lifecycle machinery.
Resumable long-running agent workflows would require a separate decision.

Initial retrieval tests will use administrator-supplied training references from
sources deemed trustworthy; instructor approval of those references is not
required. Authoritative client facts and plan state remain in existing database
flows. The owner subsequently refined the conversation-history requirement into
compact, evolving client memory retained until account deletion, rather than
requiring indefinite transcript storage; see [ADR 0002](0002-durable-client-memory.md).

Administrators initially upload text-based PDF, Markdown, and plain-text sources,
with explicit activation, replacement, and withdrawal. Titles and versions
support citations; obsolete content stops participating in retrieval. The owner
approved pypdf for text-PDF extraction, administrator extraction preview, and
successful extraction/indexing as activation prerequisites. Replacement is
atomic; failure preserves the previous active version unless withdrawn.
Unsupported or failed documents receive actionable feedback. OCR is outside
this initial scope. Shared-reference storage is described in
[ADR 0003](0003-postgresql-reference-retrieval.md).

Substantive knowledge-based training guidance should expose compact supporting
references. Missing or conflicting evidence requires clarification or instructor
referral; ordinary conversation and explanations of saved plans need not cite
documents. The owner accepted provisional end-to-end deadlines of 30 seconds
for conversation and 60 seconds for plan generation/adaptation, including
delegation, while retaining individual adapter timeout/retry limits. Exhaustion
returns a controlled response rather than unbounded execution.

A conversational reply and its validated memory/plan changes commit together
only after required processing succeeds; failure preserves prior saved state,
and retry cannot apply changes twice. Direct memory-screen edits remain
independent of AI availability.

The owner retained the existing configured chat model, allowing explicit per-role
configuration overrides but no automatic provider/model escalation. Execution is
limited to four generation-model calls for conversation and six for plans,
including retries, with at most two retrieval rounds. Aggregate input/output
token ceilings are 32,000/4,000 for conversation and 64,000/12,000 for plans;
all limits share the total deadline and must not cause truncation of required
restrictions. Full-text retrieval may serve as fallback when embeddings fail,
but only supported guidance may be presented as grounded.

Version checks protect newer client edits, instructor changes, forgotten memory,
and withdrawn references from conflicting in-flight work. Rollout is feature
flagged in reference-retrieval, memory, and orchestration stages, beginning with
a test client after verification. Disabling orchestration preserves memory
controls and existing onboarding/instructor workflows. Numeric pilot capacities
and evaluation thresholds are recorded in the canonical requirements.

The owner subsequently confirmed the detailed design and authorized implementation,
including complete local operation alongside
optional paid OpenAI support; see [ADR 0004](0004-local-operation-and-optional-hosted-ai.md).
Local operation is now the default, with offline-after-provisioning acceptance
and `embeddinggemma` selected for local embeddings. Detailed contracts and the
evaluation rubric are consolidated in the
[confirmed design](../ai-rag-multiagent-design.md). Implementation checkpoints and
remaining evidence gates are tracked in [task 45](../tasks/45-local-rag-multiagent-implementation.md).
The canonical requirements and approval boundary
are recorded in [requirements.md](../requirements.md#rag-and-multiagent-assistant-design--2026-10-19).
