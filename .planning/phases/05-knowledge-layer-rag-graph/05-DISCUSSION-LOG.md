---
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
discussed_at: "2026-05-18"
mode: discuss (interactive)
areas_discussed: 4
sub_questions: 11
---

# Phase 5 Discussion Log — Knowledge Layer (RAG + Graph)

This log is for human audit/retrospective only. Downstream agents (researcher, planner, executor) consume `05-CONTEXT.md` instead.

## Area selection

**Question:** Quali aree vuoi discutere per Phase 5 (Knowledge Layer)?

**Options offered:**
1. Schema RAG: collection topology + chunking + ACL
2. Hybrid retrieval & rerank pipeline
3. Graph DB: Neo4j vs Memgraph + GraphRAG pattern
4. Ingest pipeline + reindex + A/B eval

**User selection:** Tutte e 4 le aree.

---

## Area 1 — Schema RAG: collection topology + chunking + ACL

### Q1.1 — Qdrant collection topology

**Options offered:**
1. ✅ **Per categoria, multilingua nella stessa collection** (4 collections: sop/manuals/troubleshooting/training, lingua in payload)
2. Per categoria × lingua (8 collections, BM42 ottimizzato per lingua)
3. Una sola collection `knowledge` unified con payload filter

**User selection:** Opzione 1. Cross-lingual nativo BGE-M3 sufficiente; sparse BM42 mixed-language compensato da rerank.

**Captured as:** D-61.

### Q1.2 — Chunking strategy

**Options offered:**
1. Heading-aware Markdown + soft cap 512 token
2. Fixed-token sliding window 512 + overlap 64
3. ✅ **Semantic chunking (LlamaIndex SemanticSplitter)** con BGE-M3, buffer=1, breakpoint percentile 95

**User selection:** Opzione 3. SOP procedurali traggono vantaggio da split semantico; BGE-M3 riusato; cost ingest ~30s su CPU accettabile.

**Captured as:** D-62.

### Q1.3 — ACL enforcement + tag source

**Options offered:**
1. ✅ **Pre-filter Qdrant + nuovo campo `acl_level` esplicito nel frontmatter** (con migrazione 41 SOP)
2. Pre-filter Qdrant + mapping deterministico da `audience` esistente
3. Post-filter in retrieval tool (no Qdrant filter) — ⚠ leak risk

**User selection:** Opzione 1. Enforcement at engine level + esplicito campo `acl_level` = audit-friendly + zero leak risk. Migrazione 41 SOP accettata.

**Captured as:** D-72.

---

## Area 2 — Hybrid retrieval & rerank pipeline

### Q2.1 — Fusion strategy

**Options offered:**
1. ✅ **BM42 nativo Qdrant + Query API single-shot** con Prefetch + Fusion RRF
2. Dense Qdrant + BM25 puro separato + RRF client-side
3. BGE-M3 unified (dense + sparse + colbert) + Qdrant multi-vector

**User selection:** Opzione 1. Single round-trip, server-side fusion ottimizzata, BM42 IDF-aware nativo.

**Captured as:** D-63 (parte 1).

### Q2.2 — Rerank stage

**Options offered:**
1. ✅ **Sempre attivo con BGE-reranker-v2-m3**
2. Opt-in per tool/agent (default off)
3. No rerank Phase 5; deferred Phase 11

**User selection:** Opzione 1. Stesso vendor di BGE-M3 (allineato), MIT, multilingue nativo. Latency overhead accettabile (HITL workflow non è hot-path real-time).

**Captured as:** D-63 (parte 2).

### Q2.3 — Cross-lingual strategy IT↔EN

**Options offered:**
1. ✅ **Single multilingual collection, fiducia nelle representations BGE-M3** (no query translation, no glossary expansion)
2. Query fan-out: query translate via LLM + 2 retrievals + RRF
3. Glossary-aware query expansion (offline, no LLM at query time)

**User selection:** Opzione 1. KISS Phase 5; verifica via A/B eval test set cross-lingual subset.

**Captured as:** D-64.

---

## Area 3 — Graph DB: Neo4j vs Memgraph + GraphRAG pattern

### Q3.1 — Graph DB choice

**Options offered:**
1. ✅ **Neo4j Community 5.24 + APOC plugin**
2. Memgraph Community Edition (in-memory, BSL license)
3. Apache AGE (Postgres extension) — deviazione STACK

**User selection:** Opzione 1. Ecosistema più maturo, LangChain `Neo4jGraph` first-class, GPLv3 acceptable per self-hosted, APOC procedures utili.

**Captured as:** D-65 (parte 1).

### Q3.2 — Graph population

**Options offered:**
1. ✅ **Deterministic da frontmatter SOP + sft-assets + taxonomy YAML**
2. Hybrid: deterministic core + LLM enrichment HITL-gated
3. Full LLM extraction at ingest (no HITL) — anti-pattern

**User selection:** Opzione 1. Deterministico, riproducibile, validabile CI, zero hallucination risk, allineato ad ARCHITECTURE.md anti-pattern (agent non scrive).

**Captured as:** D-65 (parte 2).

### Q3.3 — GraphRAG retrieval pattern

**Options offered:**
1. ✅ **Tool separato `traverse_graph` + tool `rag_search`** (composizione lato agent)
2. Unified `graphrag_search` tool (join interno graph + vector)
3. RAG only Phase 5; graph esposto solo via traversal Tool, NO join

**User selection:** Opzione 1. Composizione esplicita = audit trail chiaro, ogni tool testabile in isolamento.

**Captured as:** D-66.

---

## Area 4 — Ingest pipeline + reindex + A/B eval

### Q4.1 — Document parser scope

**Options offered:**
1. ✅ **Solo Markdown Phase 5 + interfaccia pluggable** (PDF/DOCX/HTML deferred Phase 8)
2. Markdown + Docling per PDF/DOCX/HTML
3. Markdown + unstructured.io

**User selection:** Opzione 1. Scope contenuto, copre 100% corpus attuale; ABC pluggable mantiene future-proofing.

**Note deviazione:** KNW-04 letterale dice PDF/DOCX/HTML/MD; Phase 5 chiude solo MD; PDF/DOCX/HTML scope-deviation tracked in CONTEXT.md `<scope_boundaries>` con completamento Phase 8.

**Captured as:** D-67.

### Q4.2 — Reindex trigger

**Options offered:**
1. ✅ **Git CI hook + CLI manuale `nx run ingest:run`**
2. Filesystem watcher (watchdog) + Git hook CI
3. Polling scheduler + content-hash diff (no watcher, no Git hook)

**User selection:** Opzione 1. Tutto knowledge attuale viene committato Git; KISS Phase 5; watcher daemon deferred Phase 10.

**Captured as:** D-68.

### Q4.3 — Triplo: idempotency + package layout + A/B eval

**Sub-question 4.3.a — Idempotency key per chunk:**
- Options: `sha256(source_uri+chunk_idx+text)` deterministico ✅ / `sha256(text)` puro / UUIDv4 + PG mapping
- **User selection:** sha256(source_uri+chunk_idx+text) come point.id deterministico
- **Captured as:** D-69

**Sub-question 4.3.b — Package layout:**
- Options: nuovo `packages/sft-knowledge` ✅ / estendere `packages/sft-tools`
- **User selection:** Nuovo `packages/sft-knowledge` package + service `services/knowledge-ingest`
- **Captured as:** D-70

**Sub-question 4.3.c — A/B eval test set:**
- Options: Synthetic Q-gen con Qwen2.5 + spot-check 10% ✅ / Manual labeling 100 query / Adattare MTEB
- **User selection:** Synthetic Q-gen con Qwen2.5 (3 query/SOP × 41 SOP ≈ 123 query, seed=42, types=keyword_it+natural_it+cross_lingual_en) + manual spot-check 10%
- **Captured as:** D-71

---

## Deferred ideas captured

Captured during this discussion but deferred. See `<deferred_ideas>` in CONTEXT.md for full list:

- Filesystem watcher daemon → Phase 10 UI
- REST endpoint `/v1/knowledge/search` → Phase 10
- PDF/DOCX/HTML parsers (docling/unstructured) → Phase 8 KnowledgeCurator
- LLM entity extraction HITL-gated per arricchire grafo → Phase 8
- Unified `graphrag_search` tool → Phase 7+ se necessario
- Query translation cross-lingual fallback → Phase 11 if A/B eval fails target
- Glossary-aware query expansion → Phase 11
- Multi-version SOP coexistence query → Phase 8
- Dedup detector cross-document → Phase 8 (TRN-01)
- Stale-content threshold detector → Phase 8 (TRN-01)

---

## Claude's discretion items

Items where the user did not request explicit discussion; Claude's PLAN will follow sensible defaults documented in `<claudes_discretion>` of CONTEXT.md. Key items:

- Qdrant payload indexes (`acl_level`, `lang`, `category`, `source_uri`, `version`, `asset_family`, `sop_id`)
- BGE-M3 model loading: lazy singleton, FastEmbed default + FlagEmbedding fallback
- Batch sizes: Qdrant upsert 100 points, Neo4j MERGE UNWIND 500 rows
- `RagCitation.snippet` first 200 chars
- Langfuse span hierarchy: `rag.search`, `graph.traverse`
- Frontmatter required fields enforcement
- Test fixtures: testcontainers Qdrant + Neo4j + PG
- MkDocs nav additions under "Architecture"

---

## Notes

- **No scope creep redirected:** user stuck to phase-bounded decisions; no out-of-phase capabilities suggested.
- **Discussion duration:** 4 areas, 11 sub-questions total.
- **Language:** All user-facing questions in Italiano per global instruction; technical identifiers (code, paths, libraries) remain in English.
- **Prior context applied:** Phase 4 D-59 (memory layer) directly informs Phase 5 `QdrantLongTermMemory` replacement; Phase 4 D-53 cluster `knowledge-curation` consumes Phase 5 Tools.
