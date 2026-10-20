---
status: accepted
---

# Require local operation and keep hosted AI optional

On 2026-10-19, the owner clarified that the project must operate fully locally
without mandatory paid services, while also supporting optional OpenAI APIs with
their associated usage costs. This extends the previous development/test-only
Ollama scope. Local operation must cover the orchestrator, all specialists,
embeddings, reference ingestion/retrieval, and durable client memory; a local
chat model alone does not satisfy the requirement.

Generation and embeddings use separate replaceable adapters. The hosted
embedding option discussed in Q27 remains optional; no hosted call may silently
substitute for a local failure. Embed reference passages and minimized queries,
not private memory or entire conversations, and keep query embeddings temporary.
An embedding-model change requires reindexing rather than mixing vector spaces.
The trade-off is maintaining and testing two supported execution paths while
avoiding a mandatory paid API dependency.

Local generation and embeddings are the default; enabling OpenAI requires
explicit configuration and credentials. Generation and embeddings remain
independently configurable. The application must operate disconnected after
initial installation/model downloads, with external networking blocked and paid
credentials removed for verification. Local Keycloak/Mailpit support local
invitation and recovery messages; addresses use manual entry without ViaCEP,
images use local uploads, and installed models/dependencies load locally.
Packaging an installer that itself needs no internet is outside this scope.

The owner's desktop is the initial verification baseline; a potential deployment
target is a laptop with an RTX 2070 and seventh-generation Intel Core i7. CPU
operation and optional GPU acceleration are required. Desktop GPU access was
verified outside the sandbox on 2026-10-19; this does not establish laptop
capacity or successful model inference. Existing quality/latency targets remain
requirements, and benchmark failures cannot silently trigger paid processing.

The owner selected Ollama `embeddinggemma` as the initial local embedding model,
retaining the existing `qwen3:8b` local chat-model configuration. Retrieval quality,
resource use, and deadline compliance must be measured before declaring support;
these are not guaranteed by selecting the models. Measured target-hardware
performance and exact artifact compatibility remain unverified.
This is an accepted requirement, not evidence that existing deployment already
meets it. [Canonical requirements](../requirements.md#rag-and-multiagent-assistant-design--2026-10-19)
remain authoritative.
