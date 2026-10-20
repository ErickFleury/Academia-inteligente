# RAG and orchestration technology research

Date: 2026-10-19. Status: research for the ongoing design interview, **not an
approved implementation specification or dependency selection**. The canonical
[requirements](requirements.md#rag-and-multiagent-assistant-design--2026-10-19)
remain authoritative. No packages were installed or infrastructure changed.

## Repository baseline

The backend already defines provider protocols and Pydantic response models in
[ai.py](../backend/app/integrations/ai.py), uses synchronous SQLAlchemy sessions in
[database.py](../backend/app/database.py), and configures PostgreSQL
`18.6-bookworm` in [Compose](../docker-compose.yml). This note evaluates options
within that monolith; it does not verify published image availability or exact
dependency compatibility with those pins.

## Retrieval within PostgreSQL

PostgreSQL provides document/query normalization, weighted text fields, and
ranking through `tsvector`, `tsquery`, and text-search functions. This supports a
lexical retrieval baseline without an embedding service. GIN is the documented
preferred full-text index type. [Text-search controls](https://www.postgresql.org/docs/18/textsearch-controls.html),
[index types](https://www.postgresql.org/docs/18/textsearch-indexes.html).

pgvector supports exact and approximate vector search and documents hybrid
retrieval with PostgreSQL full-text search, using reciprocal rank fusion or a
cross-encoder to combine results. It requires installation on the database
server and `CREATE EXTENSION vector` in each target database. Upstream documents
PostgreSQL 18 Bookworm images. Exact search is the default; approximate indexes
trade recall for speed, and filtering can reduce returned matches.
[pgvector documentation](https://github.com/pgvector/pgvector).

Its Python integration documents SQLAlchemy vector columns and distance
expressions, plus Psycopg 3 type registration. This fits the repository's database
access style without requiring an async rewrite. The integration package is a
separate proposed dependency from the server extension; exact Python 3.13 and
existing dependency-pin compatibility still require an installation test.
[pgvector Python integration](https://github.com/pgvector/pgvector-python).

**Design recommendation, pending approval:** compare PostgreSQL lexical search
against hybrid retrieval on representative pt-BR questions before deciding
whether the extra embedding/deployment work is justified. Keep a common
retrieval result contract containing source/version, passage location, and
content. For a small initial corpus, start the vector experiment with exact
search, then measure before selecting an approximate index. Do not assume that
adding vectors guarantees better grounding.

| Choice | Proposed project tradeoff |
| --- | --- |
| Full-text baseline first | Smaller initial change; evaluate missed paraphrases and mixed-language terminology explicitly. |
| Hybrid retrieval from the first pilot | Enables a direct semantic-plus-lexical comparison; requires embedding configuration, backfill, and extension deployment. |

**Unresolved deployment work:** choose between a reproducible extension build
on the approved base and a verified upstream image; validate exact PostgreSQL
patch level, architecture, volume layout, migration privileges, backup/restore,
and CI availability before changing Compose. Select embedding provider/model,
dimensions, corpus language handling, and re-embedding policy separately.
Record embedding configuration with each indexed version. None is selected here.

For compact client memory, a separate design hypothesis is simpler: load a
bounded set of own-client facts through normal database queries before adding a
second vector index. Shared reference retrieval and private client context
should retain separate authorization and lifecycle contracts.

## Bounded orchestration versus a graph runtime

Pydantic supports validating JSON against models and generating JSON Schema;
it does not supply an agent scheduler. [Pydantic models](https://pydantic.dev/docs/validation/latest/concepts/models/).

**Design recommendation, pending approval:** implement a small explicit runtime
around the existing provider boundary. The LLM returns a validated routing
decision from an allowed specialist set; backend code performs delegation,
retrieval, result validation, and final synthesis. Track a single deadline,
remaining calls/tokens, and allowed transitions for the whole request. Specialists
cannot recursively create agents or bypass domain services. This is a proposed
architecture, not a claim that existing protocols already implement routing.

LangGraph provides a runtime for stateful orchestration, mixing deterministic
and LLM-driven steps. Its documented capabilities include persistence,
interruptions, and streaming; using LangChain itself is not required.
[LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview).
Its checkpointers persist thread state, while stores hold application-defined
cross-thread data. In-memory checkpoints do not survive process restart;
persistent checkpoints require their own storage and retention handling.
[LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence).

**Decision criterion:** prefer the explicit runtime for bounded synchronous
requests if existing application state can handle confirmations and retries.
Reconsider LangGraph when the product needs to resume the same multi-step run
after worker failure, pause within it for human input, or coordinate sufficiently
complex branches to justify the extra runtime. Durable client facts alone do not
establish that need. If selected later, checkpoint deletion must participate in
client erasure and transcript-retention policies; it must not become an accidental
permanent transcript archive.

Neither option automatically establishes business authorization, idempotency,
client isolation, total deadlines, or instructor approval. These remain explicit
application responsibilities under the canonical requirements.

## Text-based PDF ingestion

pypdf's upstream project metadata identifies it as pure Python, declares Python
3.9 or newer, and explicitly lists Python 3.13. This supports considering it as
a candidate, but does not validate any chosen release against this repository.
[pypdf project metadata](https://github.com/py-pdf/pypdf/blob/main/pyproject.toml).

pypdf extracts embedded text and is not OCR software. Image-only scans cannot
yield their text through extraction alone. PDFs lack a dependable semantic
structure for tables, paragraphs, and headings, so successful extraction does
not guarantee correct reading order. Its documentation also warns that large
content streams can consume substantial memory.
[pypdf extraction documentation](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).

**Design recommendation, pending approval:** use pypdf behind an ingestion
adapter for the accepted text-PDF scope; parse Markdown and text separately.
Reject unsupported/empty extraction with an actionable administrator message,
and show extracted text before activation. Preserve page locations for citations.
Choose explicit file/page/processing limits; do not activate partial or failed
indexes. Define handling for encrypted documents and poor table extraction.
OCR remains outside the accepted initial scope.

## Embedding provider follow-up

The interview subsequently accepted PostgreSQL hybrid retrieval; the embedding
provider remains an open decision. Earlier recommendations above record the
options investigated, not a replacement for the current canonical requirements.

Official OpenAI documentation confirms the model ID `text-embedding-3-small`,
used through `/v1/embeddings`, with **1,536 dimensions by default**. Its output
dimensions can be reduced through the `dimensions` parameter. This is an
embedding model choice, independent of conversational model selection.
[Official OpenAI embeddings guide](https://developers.openai.com/api/docs/guides/embeddings).

Ollama exposes `POST /api/embed` with a model name and a text string or batch of
strings. Its `truncate` option defaults to true; setting it false rejects inputs
that exceed the model context window. [Ollama embedding endpoint](https://docs.ollama.com/api/embed).
Ollama's catalog lists `embeddinggemma` as a locally runnable 300M-parameter
embedding model trained on over 100 languages, requiring Ollama 0.11.10 or
later. That establishes a multilingual candidate, not measured pt-BR fitness
or proven performance on the deployment machine.
[Ollama EmbeddingGemma catalog](https://ollama.com/library/embeddinggemma).
Indexing and queries should use the same embedding model.
[Ollama embedding guidance](https://docs.ollama.com/capabilities/embeddings).

**Pilot recommendation, pending owner approval:** offer hosted
`text-embedding-3-small` at its default dimensions as the initial comparison
baseline when hosted processing is acceptable; this avoids introducing a new
locally served embedding model into that pilot. Offer local Ollama
`embeddinggemma` when keeping embedding inputs on the configured local service
is the priority. This is an operational design judgment, not a quality or cost
ranking. Benchmark the local candidate against the same retrieval cases and
deadline before treating it as interchangeable. Keep the existing chat-model
configuration: no conversational model replacement was researched or approved.

Use a separate provider-neutral embedding adapter and explicit provider/model
configuration. Embed administrator-provided reference passages and a minimized
reference-search query, not durable client memories or complete conversations.
A search query can still contain sensitive health information: formulate only
the necessary topic and restrictions, excluding identities, unrelated history,
and unnecessary personal details. For example, prefer a generic exercise-safety
topic to copying a client's narrative. Minimization is not a guarantee of
anonymity. Hosted query processing must be an explicit design choice.

Never silently switch local embedding requests to a hosted provider on failure.
Return a controlled retrieval failure or an explicitly designed lexical-only
fallback. Version the provider, model, dimensions, and preprocessing contract;
changing embedding spaces requires rebuilding the reference index before
switching query traffic. Keep query embeddings ephemeral unless a separate
retention decision permits storage. Validate dimensions and finite output values,
and choose explicit input limits rather than accepting silent truncation.

Account access, actual model availability, local hardware capacity, model artifact
pinning, license review, and pt-BR retrieval quality remain unverified. No model
was downloaded and no embedding API request was made.

## Mandatory local operation follow-up

The owner subsequently required complete local operation without a paid-service
dependency, while permitting optional paid OpenAI adapters. This **supersedes the
hosted-first pilot recommendation above**. Local capability is mandatory; this
does not by itself approve a new default, replacement chat model, or final
embedding model selection. The existing `qwen3:8b` configuration and candidate
`embeddinggemma` provide the following investigation baseline:

1. Ollama documents local inference and a local-only mode: set
   `OLLAMA_NO_CLOUD=1`, or `disable_ollama_cloud: true` in its server configuration,
   then restart. This disables Ollama cloud models and web search. Model
   provisioning still normally downloads artifacts from the internet.
   [Ollama FAQ](https://docs.ollama.com/faq#how-do-i-disable-ollamas-cloud-features).
2. Ollama publishes a locally runnable `qwen3:8b` artifact and identifies its
   license as Apache 2.0. The model creator also documents local execution.
   This supports a baseline without a paid inference API; it is not evidence
   that the deployment machine meets response deadlines.
   [Ollama Qwen3 8B](https://ollama.com/library/qwen3:8b),
   [Qwen model card](https://huggingface.co/Qwen/Qwen3-8B).
3. `embeddinggemma` is available for local Ollama execution. Google's model card
   specifies a 2K input context, default 768-dimensional output, and distinct
   query/document retrieval prefixes. It links the Gemma Terms of Use, which
   govern this model; do not describe it as Apache-licensed. Local execution
   removes a hosted embedding-API dependency, subject to those model terms.
   [Ollama catalog](https://ollama.com/library/embeddinggemma),
   [Google model card](https://ai.google.dev/gemma/docs/embeddinggemma/model_card),
   [Gemma terms](https://ai.google.dev/gemma/terms).
4. Ollama supports JSON Schema in the `format` field and documents Pydantic
   response validation. It also documents separate thinking/final-answer fields
   and configurable thinking behavior. Validate routing and specialist schemas
   against the selected local runtime/model; schema-shaped output alone does not
   prove correct routing or domain behavior. Verify retrieval prefixes, context
   limits, and thinking configuration rather than assuming provider parity.
   [Structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
   [thinking controls](https://docs.ollama.com/capabilities/thinking).

**Recommended acceptance evidence:** after provisioning pinned runtime/model
artifacts, exercise ingestion, indexing, all four assistant workflows, and
memory updates with external networking blocked and no paid-provider credentials.
Verify no cloud fallback, then measure cold/warm latency and concurrent resource
use on the actual hardware. This disconnected verification has not been run.
Neither local availability nor disabling Ollama cloud alone proves the entire
application can operate disconnected. Keep optional paid adapters replaceable
and explicitly selected; they cannot become prerequisites for the local path.

## Local hardware verification follow-up

The owner approved using the desktop as the initial baseline and identified a
possible deployment laptop with an RTX 2070 and seventh-generation Intel Core
i7. The desktop was observed to have an i9-9900K (8 cores/16 logical processors)
and approximately 31 GiB RAM. The laptop's RAM, usable VRAM, precise CPU model,
and performance have not been measured; desktop results cannot establish them.

On 2026-10-19, `nvidia-smi` failed inside the sandbox but succeeded when rerun
outside it at the owner's request. The earlier inference that the driver was
unavailable was incorrect. Successful command evidence:

```text
GPU: NVIDIA GeForce RTX 2070 SUPER
Driver: 550.163.01
Driver-reported CUDA compatibility: 12.4
Total VRAM: 8192 MiB
Used VRAM: 1837 MiB
Free VRAM: 6132 MiB
GPU utilization: 0%
```

Memory and utilization are point-in-time observations. This verifies host driver
access, not container GPU passthrough, model inference, concurrent-stack memory
capacity, or deadline compliance. No drivers or services were changed and no
model was downloaded or executed for this check.

The owner also approved local defaults and offline runtime after provisioning,
using local Mailpit delivery, manual address entry, and local image uploads.
Generation and embeddings may independently opt into explicitly configured paid
OpenAI services; disconnected verification must succeed without them.

## Evidence limits

Sources are upstream documentation and source metadata accessed for this note.
No prototype, package-resolution test, corpus benchmark, or deployment test was
run. Library versions, model choice, retrieval quality, latency, memory capacity,
and exact deployment pins remain decisions or experiments, not verified outcomes.
# Execution-budget implementation verification

Official [OpenAI reasoning documentation](https://developers.openai.com/api/docs/guides/reasoning)
states that `max_output_tokens` includes reasoning and visible output, and that
exhaustion can yield an incomplete response with no useful answer. The adapter
therefore rejects incomplete output and counts the complete output allocation
when usage is unknown. Optional hosted calls disable response storage.
[Ollama's Modelfile reference](https://docs.ollama.com/modelfile) documents
`num_predict` as an output ceiling and `num_ctx` as the context-window setting.
The local adapter sets both explicitly during bounded orchestration. Conservative
input sizing rejects overflow instead of dropping restrictions. These controls
do not establish usable latency or VRAM capacity; real local benchmarks remain
necessary.

