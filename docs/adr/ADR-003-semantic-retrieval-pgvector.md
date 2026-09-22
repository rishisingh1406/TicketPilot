# ADR-003 — Semantic Retrieval with PostgreSQL + pgvector

* **Status:** Accepted
* **Date:** 2026-09-22
* **Decision Type:** Retrieval architecture
* **Scope:** Knowledge retrieval for TicketPilot

## Context

TicketPilot needs to retrieve relevant knowledge from a small SaaS support knowledge base so that generated responses can be grounded in documented information.

The initial knowledge base contains approximately 20 chunks covering areas such as:

* Account access
* MFA and security
* Billing
* Subscription management
* API usage
* Data privacy

The retrieval system must:

1. Find semantically relevant knowledge rather than relying only on keyword matching.
2. Return only currently valid knowledge.
3. Provide the retrieved chunk and similarity distance to downstream components.
4. Keep durable knowledge and retrieval data in the same database.
5. Avoid introducing unnecessary infrastructure for the current scale.
6. Leave a clear path for scaling retrieval if the knowledge base grows.

The knowledge base also contains historical/outdated chunks. These must remain stored for auditability and historical context but must not be returned as active knowledge during normal retrieval.

## Decision

TicketPilot will use **PostgreSQL with pgvector** for semantic retrieval.

Knowledge chunks and their embeddings will be stored in PostgreSQL.

The embedding model is:

`BAAI/bge-small-en-v1.5`

Each embedding has **384 dimensions**.

Similarity will be measured using **cosine distance**.

The initial retrieval strategy will use **exact nearest-neighbor search**:

1. Embed the user's query.
2. Calculate cosine distance between the query embedding and stored chunk embeddings.
3. Filter to `is_current = true`.
4. Order by cosine distance ascending.
5. Return the requested `top_k` results.

The current implementation does not use an approximate nearest-neighbor index such as HNSW.

HNSW may be introduced later if measured retrieval latency or database scale demonstrates that exact search is no longer sufficient.

## Why PostgreSQL + pgvector

PostgreSQL is already the system of record for TicketPilot.

Using pgvector allows the system to keep:

* Knowledge content
* Source metadata
* Timestamps
* Current/outdated state
* Embeddings

inside the same durable database.

This avoids introducing a separate vector database and the additional operational concerns that come with another infrastructure dependency.

The current knowledge-base size does not justify that additional operational complexity.

## Why Semantic Retrieval

Keyword-based retrieval can fail when the user's wording differs from the wording used in the documentation.

For example:

> "I forgot my password. How can I reset it?"

can retrieve a password-reset document even when the document uses different wording.

Semantic embeddings allow retrieval based on meaning rather than exact keyword overlap.

## Freshness Policy

Knowledge chunks contain an `is_current` field.

Normal retrieval must apply:

```text
is_current = true
```

Historical chunks remain stored but are excluded from normal retrieval.

This makes freshness a retrieval invariant rather than a responsibility delegated to the LLM.

Testing confirmed that outdated knowledge remains in PostgreSQL while current retrieval results contain only `is_current = true` chunks.

## Retrieval Contract

The retrieval component accepts:

```text
db
query
top_k
```

It returns:

```text
KnowledgeChunk
distance
```

for each retrieved result.

The retriever validates:

* Query must not be empty.
* `top_k` must be greater than zero.
* `top_k` must not exceed the configured maximum.

The retriever does not generate an answer. Its responsibility ends at returning relevant knowledge.

## Embedding Strategy

Embeddings are generated when knowledge chunks are ingested.

Query embeddings are generated when retrieval is requested.

The same embedding model is used for both document and query embeddings:

```text
BAAI/bge-small-en-v1.5
```

Embeddings are normalized before storage/query comparison, and cosine distance is used for similarity ordering.

## Why Exact Search Initially

The current corpus is approximately 20 chunks.

At this scale, exact nearest-neighbor search is simple and provides predictable behavior without introducing an additional indexing strategy.

Prematurely adding an approximate nearest-neighbor index would add configuration and operational complexity without a demonstrated requirement.

The system will therefore optimize based on measured behavior rather than anticipated scale.

If the knowledge base grows significantly or retrieval latency becomes unacceptable, HNSW can be evaluated using actual benchmarks.

## Alternatives Considered

### 1. PostgreSQL with keyword/full-text search

Rejected for primary retrieval.

Keyword retrieval is simpler but does not provide the semantic matching required when users phrase questions differently from the documentation.

### 2. Separate Vector Database

Rejected for the current system.

A dedicated vector database would introduce another infrastructure dependency while the current knowledge base is small and PostgreSQL already owns durable application state.

This option can be reconsidered if future scale or retrieval requirements justify it.

### 3. PostgreSQL + pgvector with HNSW immediately

Rejected for the initial implementation.

HNSW may improve approximate nearest-neighbor performance at larger scale, but there is currently no measured requirement that justifies introducing it.

It remains a future optimization rather than a current architectural requirement.

## Failure Behavior

Embedding generation or database retrieval failures must not result in an ungrounded customer-facing answer.

Retrieval failure will be handled by the higher-level agent workflow.

The agent must be able to:

* retry where appropriate,
* detect that reliable knowledge is unavailable,
* avoid fabricating an answer,
* escalate to human support when necessary.

The retrieval component itself should not silently return fabricated or fallback knowledge when the database or embedding operation fails.

## Consequences

### Positive

* Semantic retrieval based on meaning.
* PostgreSQL remains the single durable system of record.
* No separate vector database to operate.
* Current/outdated knowledge can be enforced at the database query level.
* 384-dimensional embeddings provide a relatively small storage footprint.
* Exact search keeps the initial implementation simple.
* HNSW remains available as a measured future optimization.

### Negative

* Embedding generation adds computation during ingestion and retrieval.
* PostgreSQL now handles both relational and vector workloads.
* Exact nearest-neighbor search may become too slow as the corpus grows.
* Embedding-model changes may require re-embedding existing knowledge.
* Retrieval quality depends partly on the chosen embedding model and chunking strategy.

## Validation

The retrieval implementation has been tested against the real TicketPilot knowledge base.

The password-reset test confirmed that the semantically relevant `account_access_faq` chunk is retrieved as the top result.

The freshness test confirmed that outdated knowledge chunks are excluded from normal retrieval.

The current knowledge base contains:

```text
20 total chunks
17 current chunks
3 outdated chunks
```

All stored embeddings use the expected 384-dimensional representation.

## Future Re-evaluation Triggers

This decision should be revisited when one or more of the following occurs:

* Knowledge-base size increases substantially.
* Exact vector search becomes a measurable latency bottleneck.
* Retrieval quality becomes insufficient.
* Multiple embedding models or versions must coexist.
* PostgreSQL vector workload begins affecting transactional application workloads.
* Benchmarking demonstrates that HNSW provides a meaningful improvement.

Until those conditions occur, PostgreSQL + pgvector with exact nearest-neighbor search remains the chosen retrieval architecture.

## Decision Summary

TicketPilot uses:

```text
PostgreSQL
    +
pgvector
    +
BAAI/bge-small-en-v1.5
    +
384-dimensional embeddings
    +
cosine distance
    +
exact nearest-neighbor search
    +
is_current = true filtering
```

A separate vector database and HNSW index are intentionally not introduced at the current scale.
