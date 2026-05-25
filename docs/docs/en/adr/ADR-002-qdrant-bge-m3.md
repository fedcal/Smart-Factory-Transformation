---
tags:
  - adr
  - architecture
  - knowledge
---

# ADR-002 — Qdrant + BGE-M3 hybrid retrieval

- **Status:** Accepted
- **Phase:** Phase 5 (Knowledge Layer)
- **Date:** 2026

## Context

The knowledge layer must retrieve technical documents (SOPs, manuals, domain
knowledge) in **Italian and English**, with robust retrieval quality on mixed
queries and textile technical terminology. Requirements:

- native multilingual support (IT/EN corpus);
- hybrid dense + sparse retrieval to combine semantic similarity and lexical
  matching of technical terms;
- self-hosting (no dependency on cloud embedding services);
- filtering by ACL/metadata at the vector store level.

Purely dense retrieval misses exact lexical matches (machine codes, acronyms); a
pure keyword search misses cross-lingual semantic similarity.

## Decision

We adopt **Qdrant** as the vector store and **BGE-M3** as the multilingual
embedding model, in **hybrid retrieval (dense + sparse)** mode. The choice of
BGE-M3 is backed by an A/B evaluation against `multilingual-e5-large` documented
in the knowledge layer eval results.

Code and docs reference:

- `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py` —
  `RetrievalPipeline` (hybrid + `restricted` audit).
- [A/B results — BGE-M3 vs multilingual-e5-large](../knowledge-layer/eval-results.md).
- [Hybrid retrieval pipeline](../knowledge-layer/retrieval-pipeline.md).

## Consequences

**Positive**

- superior retrieval quality on IT/EN corpus (A/B validated);
- lexical + semantic matching in the same pipeline;
- ACL/metadata filters applied natively by Qdrant.

**Negative / trade-off**

- BGE-M3 has a larger compute footprint than lighter embeddings;
- hybrid mode increases indexing complexity (sparse + dense).

Decision implemented and validated in the Phase 5 knowledge layer.
