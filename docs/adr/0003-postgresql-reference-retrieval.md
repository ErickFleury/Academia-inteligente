---
status: accepted
---

# Keep reference retrieval in PostgreSQL

On 2026-10-19, the owner selected PostgreSQL full-text search combined with
pgvector semantic search for administrator-provided training references. This
keeps retrieval inside the existing database architecture and avoids operating
a separate vector database, at the cost of installing and maintaining a database
extension, its Python integration, and embedding configuration. The pilot must
compare hybrid retrieval against a full-text baseline rather than assume vectors
improve results.

Private compact client memory remains in ordinary Client-scoped database queries,
separate from the shared reference index. This preserves distinct access and
deletion lifecycles and avoids making relevant restrictions depend on semantic
ranking. Authoritative onboarding and plans remain in their existing workflows.

The pgvector extension and Python integration are approved dependencies. The
owner approved pilot evaluation thresholds in the canonical requirements and
requires local embeddings with optional hosted support under
[ADR 0004](0004-local-operation-and-optional-hosted-ai.md). Exact dependency
versions and PostgreSQL deployment compatibility remain unverified;
`embeddinggemma` is selected as the initial local embedding model, subject to
quality/resource verification. See the
[research note](../ai-rag-technology-research-2026-10-19.md) for primary-source
evidence and alternatives, and the
[canonical requirements](../requirements.md#rag-and-multiagent-assistant-design--2026-10-19)
for the implementation approval boundary.
