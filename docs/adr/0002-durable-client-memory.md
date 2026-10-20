---
status: accepted
---

# Durable compact client memory

On 2026-10-19, the owner chose compact client information, including reported
health issues and preferences, that agents can update during conversations and
that persists until client account deletion. This refines the earlier request
for conversation-history retrieval: continuity should not depend on indefinitely
retaining complete chat transcripts. The trade-off is reduced transcript storage
and context size in exchange for explicit correction, provenance, and deletion
rules for long-lived sensitive information.

Conversational information remains attributed evidence, not an automatic update
to authoritative onboarding or approved plans. Explicit corrections supersede
earlier conversational claims; ambiguity requires clarification. Memory consists
of individual compact facts grouped into health reports, preferences, and
training goals, with attribution and last-update dates. Agents propose specific
changes for backend validation. Clear first-person statements and corrections
may update memory automatically, but uncertain statements require clarification
and no diagnoses may be inferred. Potentially outdated health reports must be
reconfirmed when relevant before consequential training proposals.

Clients may inspect, correct, and delete individual memories through a focused
"Memória do assistente" view and conversation. Forgetting a memory also prevents
old retained messages from recreating it. Memory and derived search data belong
to Client and are erased with that Client, including when a shared employee
Account survives. This does not change authoritative record-update workflows.

The owner retained existing five-day onboarding and 30-day training-chat
persistence to support reload, retry, confirmation, and adaptation behavior.
Compact memory survives transcript expiration. Each fact retains its normalized
statement, attribution, dates, and originating event identifier. Extraction is
validated against the original message during processing; after expiration the
system must not imply that the source quotation remains available.

Memory is loaded through ordinary Client-scoped queries rather than shared
document vector search, so relevant restrictions do not depend on similarity
ranking. Inspection is initially limited to the owning client and backend
operations serving that client. Reference administrators do not gain access;
instructors retain their existing access to authoritative onboarding and plans.
The initial configurable capacity is 50 current facts and 8,000 characters per
client. Consolidate duplicates and superseded facts; when full, ask the client
to review memory rather than silently discard health information. Version checks
prevent in-flight agent work from overwriting newer corrections or restoring
forgotten memory; conflicting requests return a retryable conflict.

The accepted retention direction supersedes the first interview round's lack of
authorization for durable derived memory. Implementation and validation evidence
are recorded in [task 45](../tasks/45-local-rag-multiagent-implementation.md); this
ADR records the decision and does not itself establish acceptance. [Canonical requirements](../requirements.md#rag-and-multiagent-assistant-design--2026-10-19)
remain authoritative.
