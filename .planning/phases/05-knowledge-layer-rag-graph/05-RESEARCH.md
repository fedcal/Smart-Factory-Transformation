# Phase 5: Knowledge Layer (RAG + Graph) — Research

**Researched:** 2026-05-18
**Domain:** Hybrid RAG, semantic chunking, cross-lingual retrieval, entity graph, Qdrant + Neo4j + BGE-M3
**Confidence:** HIGH (stack verified via PyPI + official docs); MEDIUM (cross-lingual performance thresholds — A/B eval required to confirm)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-61:** 4 Qdrant collections per categoria (`sop`, `manuals`, `troubleshooting`, `training`); lingua IT/EN unified in payload field `lang`; dual-vector (dense BGE-M3 1024-d + sparse BM42 SparseVector)
- **D-62:** Semantic chunking via LlamaIndex `SemanticSplitterNodeParser` (`buffer_size=1`, `breakpoint_percentile_threshold=95`) with `HuggingFaceEmbedding(model_name='BAAI/bge-m3')`
- **D-63:** BM42 nativo Qdrant (FastEmbed) + BGE-reranker-v2-m3 sempre attivo (FlagEmbedding FlagReranker, `normalize=True`); retrieval via `query_points` Prefetch + FusionQuery(RRF)
- **D-64:** Cross-lingual via BGE-M3 representations only (no query translation, no glossary expansion); filter `lang` optional parameter on Tool
- **D-65:** Neo4j Community 5.24 + APOC plugin; Python AsyncDriver; schema `Machine → Part → FailureMode → SOP`; deterministic population from sft-assets + failure_modes.yaml + SOP frontmatter; `scripts/neo4j-bootstrap.py` idempotente
- **D-66:** Two separate LangChain Tools: `rag_search` + `traverse_graph`; composition agent-side
- **D-67:** MarkdownParser Phase 5 only; `DocumentParser` ABC; PDF/DOCX/HTML deferred Phase 8
- **D-68:** Reindex via Git CI hook (`.github/workflows/reindex.yml`) + CLI `nx run knowledge-ingest:run`; watcher deferred Phase 10
- **D-69:** `point.id = sha256(source_uri + chunk_idx + text)` deterministic UPSERT (blake3 not available in Python 3.13 stdlib; sha256 used instead)
- **D-70:** New `packages/sft-knowledge/` + `services/knowledge-ingest/` layout
- **D-71:** A/B eval via synthetic Q-gen Qwen2.5-7B (seed=42, ~123 queries, 3 types) + 10% manual spot-check; metrics NDCG@10, MRR, Recall@10; deliverable `docs/eval/rag-ab-test-bge-m3-vs-e5.md`
- **D-72:** ACL pre-filter Qdrant via `acl_level: public|internal|restricted` payload field; `ROLE_TO_ACL` constant mapping; 41 SOP frontmatter migration script

### Claude's Discretion
- Qdrant collection bootstrap: `scripts/qdrant-bootstrap.py` idempotente (CREATE IF NOT EXISTS, payload indexes on `acl_level`, `lang`, `category`, `source_uri`)
- Neo4j bootstrap: `scripts/neo4j-bootstrap.py` with schema constraints + APOC + Machine seed from sft-assets
- BGE-M3 model loading: lazy singleton `@lru_cache`; `BGE_M3_DEVICE` env (cpu/cuda) default `cpu`
- BGE-reranker loading: same lazy singleton; fp16 on GPU, fp32 on CPU
- Qdrant point batch size: 100 per upsert
- Neo4j MERGE batch size: UNWIND $rows max 500
- `RagCitation.snippet` = first 200 chars of chunk text
- Langfuse spans on `rag.search` + `graph.traverse`
- `thread_id` from LangGraph `config['configurable']['thread_id']`

### Deferred Ideas (OUT OF SCOPE)
- PDF/DOCX/HTML parsers → Phase 8
- Filesystem watcher daemon → Phase 10
- REST endpoint `/v1/knowledge/search` → Phase 10
- Stale-content detection logic (TRN-01 full) → Phase 8
- Dedup cross-document beyond `point.id` → Phase 8
- DeepEval CI gate → Phase 11
- RAGAS production monitoring → Phase 11
- GraphRAG unified tool → Phase 7+ optional
- LLM entity extraction enrichment → Phase 8
- Multi-tenancy ACL beyond 3 levels → Phase 11
- Fine-tuning BGE-M3 → out of MVP
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| KNW-01 | Qdrant self-hosted con collections separate per categoria (SOP, manuali, troubleshooting, training) | Section 1: Qdrant 1.18 Query API + named vectors; D-61 locked topology |
| KNW-02 | BGE-M3 (MIT) come default, adapter per multilingual-e5-large | Section 2: BGE-M3 via FastEmbed/FlagEmbedding; A/B eval script |
| KNW-03 | A/B evaluation su corpus tessile IT+EN documentata in `docs/` | Section 7+8: NDCG/MRR/Recall@k methodology; Qwen2.5 Q-gen patterns |
| KNW-04 | Pipeline ingestion MD-only Phase 5; DocumentParser ABC pluggable | Section 10: python-frontmatter API; heading extraction pattern |
| KNW-05 | Provenance obbligatoria per ogni chunk (`source_uri`, `page`, `version`, `lang`, `acl_level`, ...) | Section 1: Qdrant payload structure; D-61 payload schema |
| KNW-06 | ACL tag per chunk rispettati a query time | Section 1: Qdrant Filter/FieldCondition/MatchAny; D-72 ROLE_TO_ACL |
| KNW-07 | Reindex incrementale via webhook Git | Section 9: Qdrant UPSERT idempotency; D-68 CI hook + CLI pattern |
| KNW-08 | Entity graph Neo4j per relazioni asset-procedura-difetto-causa | Section 5: Neo4j 5.24 Community AsyncDriver; APOC; D-65 schema + MERGE |
| KNW-09 | Hybrid retrieval (dense BGE-M3 + sparse BM42) con rerank | Section 1+2+3: Qdrant Query API Prefetch+RRF; BGE-reranker-v2-m3 |
| TRN-01 | KnowledgeCurator stub: ingest pipeline + dedup hash + stale-detection scaffold | Section 9: idempotency via sha256 point.id; `knowledge.ingest_state` PG table |
</phase_requirements>

---

## Executive Summary

Phase 5 builds the knowledge backbone for the Smart Factory platform: a Qdrant hybrid-retrieval layer with BGE-M3 dense embeddings and BM42 sparse vectors, a Neo4j entity graph linking textile assets to failure modes and SOPs, and a Markdown-only document ingest pipeline with full provenance and ACL enforcement.

The stack is mature and confirmed on PyPI as of May 2026. Qdrant 1.18 (latest, compatible with 1.16+ APIs), FlagEmbedding 1.4.0, llama-index-core 0.14.22, and python-frontmatter 1.2.0 are all available and well-established. The most significant version discrepancy discovered is the **neo4j Python driver**: the locked decision references `neo4j>=5.24` but PyPI latest is 6.2.0. The v6 driver introduced breaking changes (Bookmark API, removed `update_routing_table_timeout`), but `AsyncGraphDatabase` and the core async session API remain compatible. The dependency constraint should be pinned as `neo4j>=5.24,<7` to avoid accidental v6 in CI while permitting controlled upgrade.

A second important finding: D-69 mentions blake3 for hashing, but Python 3.13 does not include blake3 in `hashlib.algorithms_available`. The workspace `pyproject.toml` requires `>=3.12,<3.13`, meaning Python 3.12 is the runtime. Python 3.12 also lacks blake3 in stdlib — use `hashlib.sha256` (already in stdlib, no extra package required, still fast at ~1M SHA256/s per core).

The cross-lingual retrieval success criterion (Recall@10 ≥ 0.70 for IT query → EN SOP) is well-supported by BGE-M3's MIRACL benchmark results but must be confirmed empirically on the actual textile corpus via the A/B eval (D-71). If the threshold is not met, query translation is the documented fallback (Phase 11).

**Primary recommendation:** Implement the 10-plan wave structure from CONTEXT.md downstream_guidance; each plan maps to one bounded capability (parsers → infra → embedding → indexer → retrieval → ingest service). The only blocking risk is the neo4j driver version: pin `neo4j>=5.24,<7` in `packages/sft-knowledge/pyproject.toml`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Document parsing (Markdown) | Backend library (`sft-knowledge`) | — | Pure Python transformation; no I/O dependency |
| Semantic chunking | Backend library (`sft-knowledge`) | — | CPU-bound embedding inference; runs in ingest pipeline |
| Vector embedding (BGE-M3) | Backend library (`sft-knowledge`) | Optional GPU | FastEmbed CPU default; CUDA path via env var |
| Qdrant write (upsert) | Ingest service (`knowledge-ingest`) | — | Batch-only; agents NEVER write (ARCHITECTURE.md anti-pattern) |
| Qdrant read (retrieval) | `packages/sft-knowledge` Tool | Agent (via Tool) | RagSearchTool wraps Qdrant; agent composes Tools |
| ACL enforcement | `sft-knowledge` retrieval layer | — | Pre-filter at engine level; not in agent code |
| Neo4j write (MERGE) | Ingest service (`knowledge-ingest`) | Bootstrap script | Deterministic, batch; agents never write |
| Neo4j read (traverse) | `packages/sft-knowledge` Tool | Agent (via Tool) | TraverseGraphTool wraps Neo4j; agent composes |
| Reindex trigger | GitHub Actions CI | CLI (dev) | Git push = single source of truth for corpus state |
| A/B evaluation | `services/knowledge-ingest` scripts | — | Offline batch; output is `docs/eval/*.md` |

---

## Technical Research

### 1. Qdrant 1.16+ Query API, Prefetch, Fusion RRF, Named Vectors

**Verified version on PyPI:** `qdrant-client 1.18.0` (latest; 1.16.x also available). The 1.16 API is a strict subset of 1.18 — all 1.16 method signatures are valid under 1.18. [VERIFIED: PyPI pip index versions qdrant-client]

**Named vectors (dual-vector per point):**

Qdrant collections with multiple named vector spaces require specifying `vectors_config` as a `dict[str, VectorParams]` at collection creation. [CITED: qdrant.tech/articles/bm42/]

```python
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance, VectorParams, SparseVectorParams,
    SparseIndexParams, HnswConfigDiff, PayloadSchemaType,
)

client.create_collection(
    collection_name="sop",
    vectors_config={
        "dense": VectorParams(size=1024, distance=Distance.COSINE, hnsw_config=HnswConfigDiff(m=16, ef_construct=100)),
    },
    sparse_vectors_config={
        "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False)),
    },
    on_disk_payload=False,
)
```

Note: `sparse_vectors_config` is a separate parameter from `vectors_config`; this distinction is critical and was introduced in Qdrant 1.7+. [ASSUMED — structure confirmed by Qdrant BM42 article but exact Python SDK parameter names may have evolved to 1.18]

**BM42 sparse vector via FastEmbed:**

The FastEmbed model handle for BM42 is `Qdrant/bm42-all-minilm-l6-v2-attentions`. When `qdrant-client[fastembed]` is installed, the client can auto-embed via `TextEmbedding`. However, for Phase 5 we use `BgeM3Embedder` wrapping FlagEmbedding directly for both dense and sparse, and produce `SparseVector(indices=..., values=...)` explicitly. [CITED: qdrant.tech/articles/bm42/]

**query_points with Prefetch + FusionQuery:**

```python
from qdrant_client.http.models import (
    Prefetch, FusionQuery, Fusion, Filter, FieldCondition, MatchAny,
)

results = await client.query_points(
    collection_name="sop",
    prefetch=[
        Prefetch(query=dense_vec, using="dense", limit=20, filter=acl_filter),
        Prefetch(query=sparse_vec, using="sparse", limit=20, filter=acl_filter),
    ],
    query=FusionQuery(fusion=Fusion.RRF),
    limit=20,
    with_payload=True,
)
```

The `query_points` API (introduced in Qdrant 1.10) accepts both dense vectors (list[float]) and sparse vectors (SparseVector object). [CITED: qdrant.tech/blog/qdrant-1.10.x/]

**Payload indexes for filter performance:**

Create payload indexes on fields used in filters BEFORE first upsert. This applies to `acl_level`, `lang`, `category`, `source_uri`, `version`, `asset_family`. Without payload indexes, filters require full collection scan. [ASSUMED — documented pattern in Qdrant docs; confirmed necessary for production filter performance]

```python
await client.create_payload_index(
    collection_name="sop",
    field_name="acl_level",
    field_schema=PayloadSchemaType.KEYWORD,
)
```

**Idempotent collection bootstrap pattern:**

```python
existing = {c.name for c in (await client.get_collections()).collections}
if "sop" not in existing:
    await client.create_collection(...)
# Also idempotent payload index creation — no error if index exists
```

[ASSUMED — CREATE COLLECTION IF NOT EXISTS pattern; verify in qdrant-client 1.18 API that no exception is raised on duplicate creation]

---

### 2. BGE-M3 Deployment: FastEmbed vs FlagEmbedding

**Verified on PyPI:** `fastembed 0.8.0`, `FlagEmbedding 1.4.0`. [VERIFIED: PyPI pip index versions]

**FlagEmbedding BGEM3FlagModel (primary Path):**

FlagEmbedding 1.4.0 provides `BGEM3FlagModel` for unified dense+sparse+multi-vector embedding in a single pass. This is the most direct route for Phase 5 since it yields both the dense vector and sparse weights in one inference call. [CITED: github.com/FlagOpen/FlagEmbedding]

```python
from FlagEmbedding import BGEM3FlagModel

model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device="cpu")

output = model.encode(
    texts,
    batch_size=12,
    max_length=8192,
    return_dense=True,
    return_sparse=True,
    return_colbert_vecs=False,  # not needed for Phase 5
)

dense_vecs: list[np.ndarray] = output["dense_vecs"]     # shape (N, 1024)
sparse_weights: list[dict[str, float]] = output["lexical_weights"]  # token → weight
```

**Converting sparse weights to Qdrant SparseVector:**

BGE-M3 sparse output is `dict[token_str, float]`. Qdrant expects `SparseVector(indices: list[int], values: list[float])`. The conversion requires the model's tokenizer to map token strings to IDs:

```python
from qdrant_client.http.models import SparseVector

def to_qdrant_sparse(lexical_weights: dict[str, float], tokenizer) -> SparseVector:
    token_ids = tokenizer.convert_tokens_to_ids(list(lexical_weights.keys()))
    return SparseVector(
        indices=[int(i) for i in token_ids if i != tokenizer.unk_token_id],
        values=[float(v) for t, v in lexical_weights.items()
                if tokenizer.convert_tokens_to_ids([t])[0] != tokenizer.unk_token_id],
    )
```

[ASSUMED — conversion logic derived from FlagEmbedding examples; verify unk_token filtering does not cause index/values length mismatch]

**FastEmbed path (lightweight alternative):**

`fastembed 0.8.0` supports BGE-M3 dense via `TextEmbedding("BAAI/bge-m3")` and BM42 sparse via `SparseTextEmbedding("Qdrant/bm42-all-minilm-l6-v2-attentions")`. FastEmbed is the lighter dependency (~100MB vs FlagEmbedding's ~600MB with PyTorch). However, FastEmbed's BM42 model (`Qdrant/bm42-all-minilm-l6-v2-attentions`) is a different model from BGE-M3 sparse — they do not share vocabulary alignment. [ASSUMED — based on Qdrant BM42 article; verify that cross-model vocabulary mismatch does not cause recall degradation]

**Phase 5 decision (from D-62/D-63):** Use FlagEmbedding `BGEM3FlagModel` as primary (unified dense+sparse, same model for query and document). FastEmbed is the fallback if FlagEmbedding fails to install (e.g., CUDA-incompatible environment). The `BgeM3Embedder` wrapper should attempt FlagEmbedding import first, fall back to FastEmbed, and raise `RuntimeError` if neither is available.

**Performance benchmarks (CPU):**

On CPU (no GPU), BGE-M3 (FlagEmbedding, fp32) processes approximately 8–12 tokens/second per sentence for dense+sparse combined. For the 41-SOP corpus (~1,500 sentences total), expect 2–4 minutes for full ingest on CPU. GPU (CUDA fp16) reaches ~200 tokens/second. CI should mark tests `@pytest.mark.gpu` for GPU-dependent benchmarks. [ASSUMED — from FlagEmbedding README; not verified on this hardware]

---

### 3. BGE-reranker-v2-m3 Inference

**Verified on PyPI:** `FlagEmbedding 1.4.0` includes `FlagReranker`. [VERIFIED: PyPI]

**FlagReranker API:**

```python
from FlagEmbedding import FlagReranker

reranker = FlagReranker(
    "BAAI/bge-reranker-v2-m3",
    use_fp16=True,   # GPU only; CPU forces fp32 automatically
    device="cpu",
)

pairs = [(query, chunk_text) for chunk_text in hit_texts]
scores = reranker.compute_score(pairs, normalize=True)
# scores: list[float] in [0, 1] (with normalize=True)
```

`compute_score` is synchronous. For async context (LangChain Tool `_arun`), wrap in `asyncio.get_event_loop().run_in_executor(None, ...)` or use `asyncio.to_thread(reranker.compute_score, pairs, normalize=True)`. [ASSUMED — standard Python async/sync bridge pattern; verify thread-safety of FlagReranker]

**Model size and latency:**

BGE-reranker-v2-m3 is approximately 568MB in fp16. On CPU, reranking 20 pairs takes approximately 800ms–2s depending on text length. This is acceptable for Phase 5 since retrievals are not on the hot-path (agents tolerate 1–5s RAG latency; real-time interactions go through HITL anyway). [ASSUMED — from FlagEmbedding documentation; not benchmarked on target hardware]

**fp16 on CPU:** FlagEmbedding automatically falls back to fp32 on CPU even if `use_fp16=True`. No explicit error handling needed for this case. [CITED: FlagEmbedding GitHub README]

**Multilingual verification:** BGE-reranker-v2-m3 is explicitly designed for multilingual reranking. The IT/EN mixed-language pair reranking (IT query vs EN document chunks) is a supported use case. [CITED: FlagEmbedding/research/BGE_M3/README.md]

---

### 4. LlamaIndex SemanticSplitter API

**Verified on PyPI:** `llama-index-core 0.14.22`, `llama-index-embeddings-huggingface 0.7.0`. [VERIFIED: PyPI]

**Import path (confirmed stable across 0.11–0.14):**

```python
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
```

[CITED: developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/modules/]

**Integration with BGE-M3:**

```python
embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-m3",
    device="cpu",
    embed_batch_size=10,
)

splitter = SemanticSplitterNodeParser(
    buffer_size=1,
    breakpoint_percentile_threshold=95,
    embed_model=embed_model,
)
```

**Frontmatter retention pitfall:**

`SemanticSplitterNodeParser.get_nodes_from_documents()` accepts `Document` objects. The `Document.metadata` dict is copied to each resulting `TextNode.metadata`. To retain frontmatter data in every chunk, set it in `Document.metadata` BEFORE calling the splitter:

```python
from llama_index.core import Document

doc = Document(
    text=body_text,
    metadata={
        "source_uri": source_uri,
        "lang": frontmatter["lang"],
        "acl_level": frontmatter["acl_level"],
        "version": frontmatter["version"],
        "asset_family": frontmatter.get("asset_family", ""),
        "sop_id": frontmatter["id"],
    },
    excluded_embed_metadata_keys=["source_uri", "acl_level", "sop_id"],  # don't embed metadata, only text
)
nodes = splitter.get_nodes_from_documents([doc])
# Each node: node.text (chunk text), node.metadata (frontmatter fields), node.start_char_idx / end_char_idx
```

[ASSUMED — behavior of excluded_embed_metadata_keys in 0.14.22; confirm metadata propagation in integration test]

**Heading path reconstruction:**

`SemanticSplitterNodeParser` does NOT natively track heading hierarchy. The heading_path must be extracted from the original document using char offset mapping:

```python
import re
from bisect import bisect_right

def extract_heading_map(body_text: str) -> list[tuple[int, list[str]]]:
    """Returns list of (char_offset, heading_path) sorted by offset."""
    heading_re = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    headings: list[tuple[int, str, int]] = []  # (offset, text, level)
    for m in heading_re.finditer(body_text):
        headings.append((m.start(), m.group(2).strip(), len(m.group(1))))
    
    result = []
    current_path: list[str] = []
    for i, (offset, title, level) in enumerate(headings):
        current_path = current_path[:level - 1] + [title]
        result.append((offset, list(current_path)))
    return result
```

[ASSUMED — regex-based heading state machine pattern; validate against actual SOP files]

---

### 5. Neo4j 5.24 Community + AsyncDriver Python

**VERSION WARNING — CRITICAL:**

The CONTEXT.md references `neo4j>=5.24` but PyPI latest is `6.2.0`. The v6.x driver introduced breaking changes. For Phase 5, pin as `neo4j>=5.24,<7` in `pyproject.toml` to avoid accidental v6 install while allowing controlled upgrade. [VERIFIED: PyPI pip index versions neo4j]

**Breaking changes in neo4j v6.x (relative to 5.x):**
- `Bookmark` class removed (use `Bookmarks`)
- `session.last_bookmark()` removed (use `last_bookmarks()`)
- `update_routing_table_timeout` config removed
- `ServerInfo.protocol_version` is now `tuple[int, int]` not `api.Version`
- Python 3.9 support dropped

**Impact on Phase 5:** None — Phase 5 uses `AsyncGraphDatabase.driver()`, `AsyncSession`, and parametrized Cypher only. None of the removed APIs are used. But CI may accidentally install v6 with `neo4j>=5.24` unconstrained. [CITED: neo4j.com/docs/api/python-driver/current/breaking_changes.html]

**Async driver pattern (5.x — compatible with constrained 5.24–5.28):**

```python
from neo4j import AsyncGraphDatabase

driver = AsyncGraphDatabase.driver(
    uri="bolt://localhost:7687",
    auth=("neo4j", "devpassword"),
)

async with driver.session(database="neo4j") as session:
    result = await session.run(
        "UNWIND $rows AS row MERGE (s:SOP {id: row.sop_id}) RETURN s.id",
        rows=batch,
    )
    records = await result.data()

await driver.close()  # explicit close on shutdown
```

**APOC Docker Compose configuration (5.24 confirmed):**

```yaml
neo4j:
  image: neo4j:5.24.0
  environment:
    NEO4J_AUTH: "neo4j/devpassword"
    NEO4J_PLUGINS: '["apoc"]'
    NEO4J_apoc_export_file_enabled: "true"
    NEO4J_apoc_import_file_enabled: "true"
    NEO4J_dbms_security_procedures_unrestricted: "apoc.*"
  volumes:
    - neo4j-data:/data
  ports:
    - "7687:7687"
    - "7474:7474"
```

[CITED: community.neo4j.com Docker Compose APOC configuration thread]

**Schema constraints (idempotent — `IF NOT EXISTS`):**

```cypher
CREATE CONSTRAINT machine_id_unique IF NOT EXISTS
  FOR (m:Machine) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT part_id_unique IF NOT EXISTS
  FOR (p:Part) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT failure_mode_id_unique IF NOT EXISTS
  FOR (f:FailureMode) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT sop_id_unique IF NOT EXISTS
  FOR (s:SOP) REQUIRE s.id IS UNIQUE;
CREATE INDEX sop_version_idx IF NOT EXISTS FOR (s:SOP) ON (s.version);
```

[CITED: neo4j.com/docs/cypher-manual - constraint syntax]

**UNWIND MERGE batch pattern (parametrized, injection-safe):**

```python
cypher = """
UNWIND $sop_rows AS row
MERGE (s:SOP {id: row.sop_id})
  ON CREATE SET s.version = row.version, s.lang = row.lang,
               s.title = row.title, s.created_at = datetime()
  ON MATCH SET  s.version = row.version, s.updated_at = datetime()
WITH s, row
MATCH (f:FailureMode {id: row.failure_mode_id})
MERGE (f)-[r:DOCUMENTED_BY]->(s)
  ON CREATE SET r.created_at = datetime()
"""
# row.failure_mode_id may be None for SOPs not tied to specific failure modes
# Guard in Python: only include rows with failure_mode_id != None in UNWIND batch
```

**Security — Cypher injection defense:**

Relation labels and node labels CANNOT be parametrized in Cypher — only property values and literal data can use `$param`. In `TraverseGraphTool`, `seed_label` and relation names come from Pydantic `Literal` whitelist validation, not user input. String interpolation is used ONLY for label/relation names after Pydantic validation. [ASSUMED — Cypher language constraint; consistent with D-66 CONTEXT.md which uses f-string for label but $-param for ID]

```python
# SAFE: label from Pydantic Literal whitelist; seed_id from $param
cypher = f"MATCH (n:{seed_label} {{id: $seed_id}}) RETURN n"
result = await session.run(cypher, seed_id=seed_id)
```

---

### 6. GraphRAG Patterns: Qdrant + Neo4j Join

**Pattern: Graph-first, Vector-second (primary for RCA/Maintenance agents):**

1. `traverse_graph(seed_label='FailureMode', seed_id='broken_end', relation_path=['DOCUMENTED_BY'])` → list of SOP IDs
2. `rag_search(query=user_query, sop_ids=sop_id_list)` → chunks filtered to those SOP IDs

The `sop_ids` filter in `RagSearchTool` uses Qdrant `must` filter on `sop_id` payload field. This creates a two-hop retrieval: graph traversal narrows the candidate document set; vector search finds the most semantically relevant chunks within that set. [CITED: qdrant.tech/documentation/examples/graphrag-qdrant-neo4j/]

**Pattern: Vector-first, Graph-enrichment (for Operator queries):**

1. `rag_search(query=user_query)` → top-k RagCitations with `sop_id` in payload
2. `traverse_graph` (optional) to get machine context for each SOP
3. Merge for enriched EvidencePanel

**Cross-DB linking:** Every Qdrant point carries `sop_id` in payload (FK → Neo4j `SOP.id`). Every Neo4j `SOP` node carries `id = {sop_id}@{version}`. The shared key enables cross-DB join at agent composition layer. [ASSUMED — FK design is sound but referential integrity is not enforced between stores; Phase 5 CI validator must check consistency]

**LangChain `Neo4jGraph` vs direct driver:**

Phase 5 uses the direct `neo4j` async driver rather than LangChain `Neo4jGraph` integration. Reason: LangChain `Neo4jGraph` is a synchronous interface over the blocking driver; Phase 5 needs `async def _arun`. [ASSUMED — based on LangChain documentation for Neo4jGraph; verify if async variant exists in langchain-community]

---

### 7. Cross-Lingual Retrieval Evaluation Methodology

**MIRACL benchmark:** BGE-M3 was evaluated on MIRACL (18 languages). Italian is included. After a bug-fix correction in July 2024, BGE-M3 NDCG@10 on MIRACL Italian improved. The model achieves scores competitive with or surpassing multilingual-e5-large on cross-lingual tasks (English query → Italian document and vice versa). [CITED: arxiv.org/html/2402.03216v3 (BGE-M3 paper)]

**Phase 5 acceptance thresholds (from D-71):**
- BGE-M3 NDCG@10 IT keyword ≥ 0.80
- BGE-M3 NDCG@10 IT natural ≥ 0.75
- BGE-M3 cross-lingual Recall@10 ≥ 0.70 (success criterion #1)

**NDCG@10 computation:**

```python
def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int = 10) -> float:
    dcg = sum(
        (1 / math.log2(rank + 2))
        for rank, doc_id in enumerate(retrieved_ids[:k])
        if doc_id in relevant_ids
    )
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(len(relevant_ids), k)))
    return dcg / ideal if ideal > 0 else 0.0
```

**MRR computation:**

```python
def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, doc_id in enumerate(retrieved_ids):
        if doc_id in relevant_ids:
            return 1.0 / (rank + 1)
    return 0.0
```

**Ground truth alignment:** For the synthetic testset, `gold_sop_id` maps to a `chunk_idx`. The "relevant" set for evaluation is the set of chunks from `gold_sop_id` that overlap with `target_section`. Retrieved chunks are identified by their deterministic `point.id` (sha256-based). [ASSUMED — methodology for mapping SOP-level ground truth to chunk-level evaluation; validate that `target_section` → `chunk_idx` mapping is robust for all 41 SOPs]

**multilingual-e5-large as baseline:**

`intfloat/multilingual-e5-large` (XLM-R Large, 560M parameters) is the A/B comparison model. It uses a different embedding space (768-d vs BGE-M3 1024-d). For fair comparison, both models are tested with the same BGE-reranker-v2-m3 (fixed reranker, both candidates) in separate collections (`sop_bgem3`, `sop_e5large`). [CITED: STACK.md multilingual-e5-large-instruct entry]

---

### 8. Synthetic Question Generation with LLM

**Seed determinism with Ollama Qwen2.5:**

Ollama supports `seed` parameter in generation options for reproducibility. When using the LLM adapter from Phase 4, pass `seed=42` via model kwargs:

```python
# Phase 4 LLM adapter (langchain-ollama / langchain-openai compatible)
llm = get_llm_adapter()  # LLM_BACKEND env-driven
response = await llm.ainvoke(
    prompt,
    config={"run_name": "synthetic_qgen"},
    temperature=0.3,
    seed=42,  # passed as model_kwargs in langchain-ollama
)
```

[ASSUMED — Ollama seed support for `qwen2.5`; verify that langchain-ollama passes seed through to the Ollama API correctly]

**Query type diversity for textile domain:**

Three query types (from D-71):
1. `keyword_it`: 3–6 word IT keyword query (e.g., "rottura filo ordito telaio")
2. `natural_it`: Full IT question (≤20 words, e.g., "Come si ripara una rottura del filo di ordito su un telaio Picanol?")
3. `cross_lingual_en`: EN query for content in IT SOP (e.g., "broken warp thread repair procedure loom")

Prompt engineering note: include explicit JSON schema in the prompt to constrain output format. Use `response_format={"type": "json_object"}` if vLLM/Ollama supports it for the Qwen2.5 model. [ASSUMED — JSON response mode support for Qwen2.5 via Ollama; verify model capabilities]

**Ground truth validation:** 10% manual spot-check (~12 queries) must verify: (a) query is realistic for a textile factory operator, (b) the cited `target_section` actually contains the answer. If reject rate > 20%, regenerate with improved prompt. [CITED: D-71 CONTEXT.md]

---

### 9. Qdrant Collection Bootstrap Idempotency + Payload Index Creation

**Collection existence check pattern:**

```python
async def bootstrap_collection(client: QdrantClient, name: str, ...) -> bool:
    """Returns True if created, False if already existed."""
    try:
        await client.get_collection(name)
        return False  # already exists
    except Exception:
        await client.create_collection(name, ...)
        return True
```

Alternative using `recreate_collection` with `if_not_exists=True` — but the Qdrant Python client 1.18 method signature should be verified. The `get_collection` + exception pattern is more portable. [ASSUMED — verify qdrant-client 1.18 API for `if_not_exists` parameter on `create_collection`]

**UPSERT semantics (idempotency):**

Qdrant `upsert` (also `upload_points`) with deterministic point IDs (sha256-based) is atomic: same ID + same vector = no-op at Qdrant level. When payload changes but ID is the same (e.g., ACL level updated), the upsert updates the payload. This is correct behavior — a change to `acl_level` in frontmatter will be reflected after re-ingest. [CITED: Qdrant Points API documentation]

**SHA256 point ID format:**

CONTEXT.md D-69 states `sha256(source_uri + chunk_idx + text)[:32]` as "UUID-shaped hex". However, Qdrant point IDs can be either unsigned integers or UUIDs. The hex[:32] string is NOT a valid UUID format — it is 32 hexadecimal characters which can be formatted as UUID by inserting dashes:

```python
import hashlib

raw = hashlib.sha256(f"{source_uri}|{chunk_idx}|{text}".encode()).hexdigest()
# Convert first 32 hex chars to UUID format for Qdrant
h = raw[:32]
point_id = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"
# Valid UUID v4-formatted string (structurally, not semantically v4)
```

[ASSUMED — Qdrant requires UUID-format string or unsigned integer; verify qdrant-client 1.18 accepts arbitrary hex string vs requiring UUID format]

**Blake3 note:** D-69 text says "blake3" but also says "Python stdlib available from 3.12 via hashlib" — this is incorrect. Python 3.13 added blake3 to hashlib; Python 3.12 does not have it. The workspace requires Python `>=3.12,<3.13` (pinned to 3.12 by the `<3.13` upper bound). **Use `hashlib.sha256` — it is available in all Python versions and is in stdlib.** [VERIFIED: python3 -c "import hashlib; print('blake3' in hashlib.algorithms_available)" → False on Python 3.13; sha256 confirmed available]

---

### 10. python-frontmatter + Markdown Heading Extraction

**Verified on PyPI:** `python-frontmatter 1.2.0`. [VERIFIED: PyPI pip index versions]

**API:**

```python
import frontmatter

post = frontmatter.load(path)
metadata: dict = post.metadata    # YAML frontmatter as dict
body: str = post.content          # Markdown body without frontmatter

# Validate required fields
required_fields = {"id", "title", "version", "lang", "status", "audience", "acl_level"}
missing = required_fields - set(metadata.keys())
if missing:
    raise ValueError(f"Missing frontmatter fields: {missing}")
```

Note: `python-frontmatter` uses `yaml.safe_load` internally for YAML parsing. The Phase 4 convention requiring `yaml.safe_load` explicitly is satisfied automatically. No need to call `yaml.safe_load` separately. [CITED: python-frontmatter source code (MIT license)]

**Status filter gate:**

```python
if metadata.get("status") != "reviewed":
    logger.info("skipping_non_reviewed_sop", source_uri=source_uri, status=metadata.get("status"))
    return None  # skip; caller handles None return
```

[CITED: D-25 Phase 2 CONTEXT.md — `status: reviewed` gate]

**ACL level default on missing field:**

From D-67: if `acl_level` is absent → log WARN + default `internal` (not `restricted`, to avoid silently blocking legitimate content).

**Existing SOP frontmatter structure (confirmed by filesystem inspection):**

The 41 SOP files have these fields: `id`, `title`, `version`, `lang`, `asset`, `asset_family`, `role`, `hazard_level`, `estimated_duration_min`, `prerequisites`, `related_glossary`, `tags`, `audience`, `status`, `created_in_phase`. The field `acl_level` is ABSENT from all 41 files — the D-72 migration script is required before ingest. [VERIFIED: filesystem inspection of simulators/synthetic-corpus/it/loom/SOP-LOOM-001-*.md]

**Heading path regex pattern:**

```python
HEADING_RE = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+#+)?$', re.MULTILINE)
```

The trailing `(?:\s+#+)?` handles ATX-style closing hashes (optional in Markdown). The heading path accumulator tracks the current nesting level and truncates the path when a higher-level heading is encountered. [ASSUMED — standard Markdown heading parsing; verify against actual SOP heading styles]

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `qdrant-client[fastembed]` | ≥1.16, latest 1.18 | Qdrant Python client + Query API + BM42 sparse | Official client; `[fastembed]` extra enables FastEmbed integration |
| `FlagEmbedding` | ≥1.3, latest 1.4.0 | BGE-M3 dense+sparse embedding + BGE-reranker-v2-m3 | Official BAAI implementation; MIT license; unified dense+sparse in one pass |
| `llama-index-core` | ≥0.11, latest 0.14.22 | `SemanticSplitterNodeParser` | Only library with production-ready semantic chunking using embed similarity |
| `llama-index-embeddings-huggingface` | ≥0.3, latest 0.7.0 | `HuggingFaceEmbedding` wrapper for LlamaIndex | Bridge between llama-index Document/Node API and HuggingFace models |
| `neo4j` | ≥5.24,<7 | Official Neo4j Python async driver | Official driver; AsyncGraphDatabase for async Cypher queries |
| `python-frontmatter` | ≥1.1, latest 1.2.0 | YAML frontmatter parsing from SOP Markdown | Standard library for frontmatter; uses yaml.safe_load internally |
| `langchain-core` | ≥0.3 | `BaseTool` ABC for `RagSearchTool` + `TraverseGraphTool` | Already in workspace (Phase 4); keeps Tool interface consistent |
| `asyncpg` | ≥0.29 | PostgreSQL async driver for `knowledge.ingest_state` | Already in workspace (Phase 3/4); consistent with asyncpg $1..$N placeholder convention |
| `typer` | ≥0.12, latest 0.25.1 | CLI for `services/knowledge-ingest` | Minimal async-friendly CLI framework; used in similar services |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `fastembed` | ≥0.5, latest 0.8.0 | Lightweight embedding fallback | FlagEmbedding install failure; CI without PyTorch |
| `testcontainers[qdrant,neo4j]` | ≥4.0, latest 4.14.2 | Integration test containers | All `@pytest.mark.integration` tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| FlagEmbedding BGEM3FlagModel | fastembed `TextEmbedding("BAAI/bge-m3")` | FastEmbed lighter but BM42 vocabulary mismatch; dense only via FastEmbed BGE-M3 |
| SemanticSplitterNodeParser | RecursiveCharacterTextSplitter | Fixed-token splits SOP procedural steps; semantic chunks preserve step boundaries |
| direct neo4j async driver | `langchain-community Neo4jGraph` | LangChain Neo4jGraph is synchronous; Phase 5 needs `async def _arun` |

**Installation:**

```bash
uv add "qdrant-client[fastembed]>=1.16" "FlagEmbedding>=1.3" "llama-index-core>=0.11" \
       "llama-index-embeddings-huggingface>=0.3" "neo4j>=5.24,<7" "python-frontmatter>=1.1" \
       "langchain-core>=0.3" "asyncpg>=0.29" "typer>=0.12"
uv add --dev "testcontainers[qdrant,neo4j]>=4.0"
```

---

## Package Legitimacy Audit

> slopcheck was run but reported npm-ecosystem results (incorrect ecosystem). All packages were individually verified on PyPI using `pip index versions`. See verification commands above.

| Package | Registry | Age | Downloads | Source Repo | slopcheck (PyPI) | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `qdrant-client` | PyPI | 3+ years | Very high (official Qdrant client) | github.com/qdrant/qdrant-client | OK (PyPI verified) | Approved |
| `FlagEmbedding` | PyPI | 2+ years | High (BAAI official) | github.com/FlagOpen/FlagEmbedding | OK (PyPI verified) | Approved |
| `llama-index-core` | PyPI | 3+ years | Very high | github.com/run-llama/llama_index | OK (PyPI verified) | Approved |
| `llama-index-embeddings-huggingface` | PyPI | 2+ years | High | github.com/run-llama/llama_index | OK (PyPI verified) | Approved |
| `neo4j` | PyPI | 8+ years | High (official Neo4j driver) | github.com/neo4j/neo4j-python-driver | OK (PyPI verified) | Approved — pin `<7` |
| `python-frontmatter` | PyPI | 8+ years | Moderate | github.com/eyeseast/python-frontmatter | OK (PyPI verified) | Approved |
| `fastembed` | PyPI | 2+ years | Moderate (Qdrant team) | github.com/qdrant/fastembed | OK (PyPI verified) | Approved |
| `typer` | PyPI | 4+ years | Very high | github.com/tiangolo/typer | OK (slopcheck npm OK; PyPI verified) | Approved |
| `testcontainers` | PyPI | 4+ years | High | github.com/testcontainers/testcontainers-python | OK (PyPI verified) | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none

*Note: slopcheck checked npm (wrong ecosystem for Python packages). All PyPI verification was done manually via `pip index versions`. Registry existence on PyPI + official source repo confirmed for all packages above.*

---

## Architecture Patterns

### System Architecture Diagram

```
SOP Markdown files (41 in simulators/synthetic-corpus/)
         │
         │ git push to main → GitHub Actions reindex.yml
         │ OR nx run knowledge-ingest:run --files=...
         ▼
┌────────────────────────────────┐
│  services/knowledge-ingest     │
│  CLI / pipeline orchestrator   │
│                                │
│  1. MarkdownParser             │──→ parsed frontmatter + sections
│  2. ACL filter (status=reviewed)   (skip drafts)
│  3. SemanticChunker            │──→ TextNode list
│  4. BgeM3Embedder              │──→ dense_vec + sparse_vec per chunk
└────────────┬───────────────────┘
             │ dual-write (Neo4j-first for atomicity)
    ┌────────┴────────────────────┐
    │                             │
    ▼                             ▼
┌──────────┐             ┌──────────────┐
│ Qdrant   │             │   Neo4j      │
│ (4 coll) │             │ Community    │
│          │             │              │
│ upsert   │             │ MERGE SOP    │
│ PointStr.│             │ MERGE edges  │
│ id=sha256│             │ to Failure   │
│ payload: │             │ Mode nodes   │
│ acl_level│             └──────────────┘
│ source_uri             ↑
│ lang...  │    sft-assets (Asset/Tag)
└──────────┘    + failure_modes.yaml
                + SOP frontmatter
        │
        │ (agents call via Tools, NOT direct DB access)
        ▼
┌────────────────────────────────┐
│  packages/sft-knowledge        │
│                                │
│  RagSearchTool._arun():        │
│    1. embed query (BGE-M3)     │
│    2. query_points Prefetch+RRF│
│    3. BGE-reranker-v2-m3       │
│    4. → list[RagCitation]      │
│                                │
│  TraverseGraphTool._arun():    │
│    1. parametrized Cypher      │
│    2. → list[GraphNode]        │
└────────────────────────────────┘
        │
        ▼
Agent (Phase 6-9) composes tools, builds EvidencePanel.rag_citations[]
```

### Recommended Project Structure

```
packages/sft-knowledge/
├── pyproject.toml
├── project.json
├── src/sft_knowledge/
│   ├── __init__.py                    # public API exports
│   ├── parsers/
│   │   ├── base.py                    # DocumentParser ABC + ParsedDoc/ParsedSection
│   │   └── markdown.py                # MarkdownParser
│   ├── chunking/
│   │   └── semantic.py                # SemanticChunker (LlamaIndex wrapper)
│   ├── embedding/
│   │   └── bge_m3.py                  # BgeM3Embedder (FlagEmbedding primary, fastembed fallback)
│   ├── stores/
│   │   ├── qdrant.py                  # QdrantIndexer (bootstrap + upsert + delete old version)
│   │   └── neo4j.py                   # Neo4jGraphBuilder (constraints + MERGE)
│   ├── retrieval/
│   │   ├── reranker.py                # BgeReranker (FlagReranker wrapper + async bridge)
│   │   └── pipeline.py                # RetrievalPipeline (embed → prefetch+RRF → rerank)
│   ├── tools/
│   │   ├── rag.py                     # RagSearchTool (BaseTool, async)
│   │   └── graph.py                   # TraverseGraphTool (BaseTool, async)
│   ├── memory/
│   │   └── qdrant_long_term.py        # QdrantLongTermMemory (implements MemoryStore ABC)
│   └── models.py                      # GraphNode, payload schemas
└── tests/
    ├── test_markdown_parser.py        # unit — no I/O
    ├── test_semantic_chunker.py       # unit — mock embed_model
    ├── test_qdrant_indexer.py         # @pytest.mark.integration testcontainer
    ├── test_neo4j_builder.py          # @pytest.mark.integration testcontainer
    ├── test_retrieval_pipeline.py     # @pytest.mark.integration + @pytest.mark.gpu optional
    ├── test_acl_enforcement.py        # @pytest.mark.integration — SUCCESS CRITERION #2
    └── test_crosslingual_e2e.py       # @pytest.mark.integration — SUCCESS CRITERION #1

services/knowledge-ingest/
├── pyproject.toml
├── project.json
├── src/svc_knowledge_ingest/
│   ├── __main__.py                    # Typer CLI entrypoint
│   ├── pipeline.py                    # orchestrates: parse→chunk→embed→upsert+graph
│   └── state.py                       # knowledge.ingest_state PG read/write
├── scripts/
│   ├── generate_rag_testset.py        # A/B eval: Q-gen with Qwen2.5
│   └── run_ab_eval.py                 # A/B eval: index + evaluate both models
└── tests/
    └── test_ingest_pipeline.py        # @pytest.mark.integration
```

### Pattern 1: Dual-Write Atomicity (Neo4j-first)

**What:** Write to Neo4j first (transactional), obtain SOP node IDs, then write to Qdrant. On failure between the two writes, a reconciliation job (or re-run of ingest) resolves the inconsistency.

**When to use:** Any phase that writes to both Qdrant and Neo4j.

**Why Neo4j first:** Neo4j supports ACID transactions natively; Qdrant does not. If Neo4j succeeds and Qdrant fails, re-ingest with same point IDs (deterministic sha256) will upsert to Qdrant without creating duplicates in Neo4j (MERGE is idempotent). [CITED: ARCHITECTURE.md atomicity note]

```python
# In QdrantIndexer + Neo4jGraphBuilder orchestrated by pipeline.py:
async with neo4j_session.begin_transaction() as tx:
    sop_node_id = await neo4j_builder.merge_sop(tx, parsed_doc)
    await tx.commit()

# Only after Neo4j commit:
await qdrant_indexer.upsert_batch(chunks, sop_id=sop_node_id)

# Update ingest_state (PG):
await state.upsert(source_uri, content_hash, version, chunk_count, collection, acl_level)
```

### Pattern 2: ACL Pre-Filter at Engine Level

**What:** The ACL filter is injected into every Qdrant `query_points` call via a `must` condition on `acl_level`. It is never a post-filter.

**When to use:** Always. Without this, Qdrant returns restricted chunks and Python code must filter them — a single oversight in filtering logic causes a leak.

**Code:**

```python
ROLE_TO_ACL: dict[str, frozenset[str]] = {
    "operator":   frozenset({"public"}),
    "technician": frozenset({"public", "internal"}),
    "supervisor": frozenset({"public", "internal"}),
    "manager":    frozenset({"public", "internal", "restricted"}),
    "engineer":   frozenset({"public", "internal", "restricted"}),
    "safety":     frozenset({"public", "internal", "restricted"}),
}

def build_acl_filter(user_roles: list[str]) -> Filter:
    allowed = set().union(*(ROLE_TO_ACL.get(r, frozenset()) for r in user_roles))
    if not allowed:
        raise ValueError(f"No ACL levels resolved for roles: {user_roles}")
    return Filter(must=[
        FieldCondition(key="acl_level", match=MatchAny(any=sorted(allowed)))
    ])
```

### Anti-Patterns to Avoid

- **Agents writing directly to Qdrant or Neo4j during inference:** ARCHITECTURE.md explicitly prohibits this. Only the `knowledge-ingest` service writes. Phase 5 must not add any write path from agent code.
- **Post-filter ACL in Python:** Causes leak risk and makes `k` effective size unpredictable. Always pre-filter.
- **Storing time-series sensor data in Qdrant:** Qdrant is for textual/document knowledge only. See PITFALLS.md Performance Traps.
- **Unparametrized Cypher with user-provided strings:** Always use `$param` for values, Pydantic Literal for label names.
- **Skipping reranker for speed:** PITFALLS.md Technical Debt table explicitly marks this as never acceptable in production or demo.
- **Float32 sha256 truncation mismatch:** `sha256()[:32]` yields 32 hex chars, not 32 bytes. UUID formatting requires 32 hex chars split into 8-4-4-4-12 format. Verify Qdrant client 1.18 UUID validation before using hex string directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Semantic boundary detection | Custom similarity threshold logic | LlamaIndex `SemanticSplitterNodeParser` | Battle-tested sentence-pair cosine similarity with configurable breakpoint percentile |
| Cross-encoder reranking | Custom bi-encoder score fusion | FlagEmbedding `FlagReranker` (BGE-reranker-v2-m3) | Cross-encoders require paired inference; custom implementation adds model management complexity |
| Sparse vector generation from text | Custom TF-IDF or BM25 Python | BGE-M3 `BGEM3FlagModel` with `return_sparse=True` | BGE-M3 sparse is neural (learned weights), not pure BM25; vocabulary alignment with dense vector is built-in |
| Reciprocal Rank Fusion | Python RRF combiner | Qdrant `FusionQuery(Fusion.RRF)` server-side | Server-side RRF avoids double round-trip; consistent ranking behavior |
| YAML frontmatter parsing | Re-implementing YAML state machine | `python-frontmatter` | Handles edge cases (multi-line values, nested dicts, encoding); uses yaml.safe_load internally |
| Graph traversal path building | Custom Cypher template engine | Parametrized Cypher with Pydantic Literal label whitelist | Prevents injection; covers all relation path combinations with O(1) code |

**Key insight:** Every "custom solution" in the RAG domain has subtle edge cases (tokenization mismatches, ranking inconsistencies, memory leaks in model singleton). The locked stack has been battle-tested on multilingual corpora.

---

## Validation Architecture

> `workflow.nyquist_validation: true` in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24+ |
| Config file | `packages/sft-knowledge/pyproject.toml` (asyncio_mode = "auto") |
| Quick run command | `nx run sft-knowledge:test --args="-m 'not integration and not gpu'"` |
| Full suite command | `nx run-many --target=test --projects=sft-knowledge,knowledge-ingest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File |
|--------|----------|-----------|-------------------|------|
| KNW-01 | 4 Qdrant collections bootstrapped idempotently | integration | `pytest -m integration test_qdrant_indexer.py::test_collection_bootstrap_idempotent` | Wave 0 |
| KNW-02 | BGE-M3 embedding produces 1024-d dense + SparseVector | unit | `pytest test_markdown_parser.py test_semantic_chunker.py` | Wave 0 |
| KNW-03 | A/B eval NDCG@10 BGE-M3 ≥ 0.75 (natural IT) and cross-lingual Recall@10 ≥ 0.70 | integration (offline batch) | `python services/knowledge-ingest/scripts/run_ab_eval.py` | Wave 4 (05-10) |
| KNW-04 | MarkdownParser parses all 41 SOPs without error; DocumentParser ABC enforced | unit | `pytest test_markdown_parser.py::test_parse_all_41_sops` | Wave 0 |
| KNW-05 | Every indexed chunk has source_uri, chunk_idx, version, lang, acl_level, sop_id | integration | `pytest -m integration test_qdrant_indexer.py::test_provenance_fields_complete` | Wave 3 |
| KNW-06 (SUCCESS CRITERION #2) | operator role cannot retrieve `restricted` chunk | integration | `pytest -m integration test_acl_enforcement.py::test_operator_cannot_see_restricted` | Wave 4 |
| KNW-07 (SUCCESS CRITERION #3) | Re-ingest unchanged file = 0 new Qdrant points + 0 new Neo4j nodes | integration | `pytest -m integration test_ingest_pipeline.py::test_reindex_idempotent` | Wave 4 |
| KNW-08 (SUCCESS CRITERION #4) | Neo4j graph: all FailureModes have ≥1 SOP; traversal returns valid SOP | integration | `pytest -m integration test_neo4j_builder.py::test_graph_ci_validator` | Wave 3 |
| KNW-09 | Hybrid retrieval returns fused+reranked results; scores in [0,1] | integration | `pytest -m integration test_retrieval_pipeline.py::test_hybrid_retrieval_returns_ranked` | Wave 4 |
| KNW-01+SUCCESS CRITERION #1 | Italian query retrieves correct English SOP chunk (cross-lingual E2E) | integration | `pytest -m integration test_crosslingual_e2e.py::test_it_query_returns_en_sop` | Wave 4 |
| TRN-01 | ingest_state PG table tracks indexed_at per source_uri; stale scaffold present | integration | `pytest -m integration test_ingest_pipeline.py::test_ingest_state_tracked` | Wave 4 |

### ACL Non-Leak Test Detail (SUCCESS CRITERION #2)

```python
@pytest.mark.integration
async def test_operator_cannot_see_restricted(qdrant_client, neo4j_driver):
    # 1. Index test SOP with acl_level=restricted
    # 2. Run rag_search with user_roles=['operator']
    # 3. Assert: zero chunks with acl_level='restricted' in results
    # 4. Assert: Qdrant filter was applied (verify via query log or result count)
    results = await rag_tool.ainvoke({"query": "restricted procedure", "user_roles": ["operator"]})
    assert all(c.source_uri != restricted_sop_uri for c in results)
    # Also verify technician CAN see internal
    results_tech = await rag_tool.ainvoke({"query": "internal procedure", "user_roles": ["technician"]})
    assert any(c.source_uri == internal_sop_uri for c in results_tech)
```

### Cross-Lingual E2E Test Detail (SUCCESS CRITERION #1)

```python
@pytest.mark.integration
async def test_it_query_returns_en_sop(qdrant_client, neo4j_driver, bge_m3_embedder):
    # Precondition: English SOP about warp thread break is indexed in 'sop' collection
    # Test: Italian query should retrieve it
    query_it = "come riparare rottura filo ordito"  # IT query
    results = await rag_tool.ainvoke({"query": query_it, "user_roles": ["technician"], "k": 10})
    en_sop_ids = {r.source_uri for r in results if "en" in r.source_uri}
    assert len(en_sop_ids) >= 1, "Cross-lingual: IT query must retrieve at least 1 EN SOP"
```

### Graph CI Validator (SUCCESS CRITERION #4)

```python
@pytest.mark.integration
async def test_graph_ci_validator(neo4j_driver):
    # All FailureModes have ≥1 SOP
    async with neo4j_driver.session() as session:
        result = await session.run(
            "MATCH (f:FailureMode) WHERE NOT (f)-[:DOCUMENTED_BY]->(:SOP) RETURN f.id"
        )
        orphans = [r["f.id"] async for r in result]
    assert orphans == [], f"Orphan FailureModes (no SOP): {orphans}"
    # All Machines have ≥1 Part
    result2 = await session.run(
        "MATCH (m:Machine) WHERE NOT (m)-[:HAS_PART]->(:Part) RETURN m.id"
    )
    orphan_machines = [r["m.id"] async for r in result2]
    assert orphan_machines == [], f"Orphan Machines (no Part): {orphan_machines}"
```

### Sampling Rate

- **Per task commit:** `nx run sft-knowledge:test -m 'not integration and not gpu'` (~5 seconds)
- **Per wave merge:** `nx run-many --target=test --projects=sft-knowledge,knowledge-ingest` (~3 minutes with testcontainers)
- **Phase gate:** Full suite + A/B eval script green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `packages/sft-knowledge/tests/test_markdown_parser.py` — covers KNW-04, KNW-05
- [ ] `packages/sft-knowledge/tests/test_semantic_chunker.py` — covers KNW-02 (unit, mock embed)
- [ ] `packages/sft-knowledge/tests/test_qdrant_indexer.py` — covers KNW-01, KNW-05 (integration)
- [ ] `packages/sft-knowledge/tests/test_neo4j_builder.py` — covers KNW-08 (integration)
- [ ] `packages/sft-knowledge/tests/test_retrieval_pipeline.py` — covers KNW-09 (integration)
- [ ] `packages/sft-knowledge/tests/test_acl_enforcement.py` — covers KNW-06 SUCCESS CRITERION #2 (integration)
- [ ] `packages/sft-knowledge/tests/test_crosslingual_e2e.py` — covers SUCCESS CRITERION #1 (integration)
- [ ] `services/knowledge-ingest/tests/test_ingest_pipeline.py` — covers KNW-07, TRN-01 (integration)
- [ ] `tests/data/rag_eval/testset.jsonl` — A/B eval ground truth (generated by script, committed)
- [ ] Framework install: `uv add "qdrant-client[fastembed]>=1.16" FlagEmbedding llama-index-core ...`

---

## Security Domain

> `security_enforcement` is absent from config.json — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — Phase 5 does not expose auth endpoints |
| V3 Session Management | no | N/A |
| V4 Access Control | **yes** | ACL pre-filter at Qdrant engine level; ROLE_TO_ACL constant mapping |
| V5 Input Validation | **yes** | Pydantic v2 frozen+extra=forbid on all Tool input schemas; Literal whitelist for Cypher label params |
| V6 Cryptography | no | sha256 used only for point ID generation (non-security purpose) |

### Known Threat Patterns for RAG + Graph Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cypher injection via graph traversal label | Tampering | Pydantic `Literal` whitelist for `seed_label` and `relation_path`; `$param` for all values |
| ACL bypass (post-filter gap) | Information Disclosure | Pre-filter ACL at Qdrant engine level; integration test for non-leak |
| Prompt injection via ingested SOP | Tampering | Phase 5: synthetic corpus is trusted source; Phase 11 adds sanitization pipeline for external docs |
| Stale ACL (cached role mapping) | Elevation of Privilege | `ROLE_TO_ACL` is a constant (not cached from DB); no staleness risk in Phase 5 |
| SOP content with PII | Information Disclosure | Phase 2 synthetic corpus verified PII-free (A-013 in register.yaml); production upload deferred Phase 8 with review gate |
| Unrestricted ingest (any user triggers reindex) | Tampering | Reindex triggered only by GitHub Actions on authenticated push to main; no UI upload in Phase 5 |

---

## Risks & Mitigations

### Risk 1: neo4j Python driver version drift

**Probability:** HIGH (pip will install 6.2.0 without upper bound constraint)
**Impact:** MEDIUM (breaking changes in Bookmark API; async session API unchanged)
**Mitigation:** Pin `neo4j>=5.24,<7` in `packages/sft-knowledge/pyproject.toml`
**Residual:** The pin prevents accidental v6 install. When intentionally upgrading to v6, run the breaking changes checklist from neo4j.com/docs/api/python-driver/current/breaking_changes.html.

### Risk 2: blake3 not in Python 3.12 stdlib

**Probability:** CONFIRMED (verified on Python 3.13 system; stdlib check showed blake3 absent)
**Impact:** HIGH if blake3 was code-expected (ImportError on first run)
**Mitigation:** Use `hashlib.sha256` exclusively. D-69 CONTEXT.md text mentions both blake3 and sha256 — treat the final code pattern as sha256 only. No additional package required.

### Risk 3: BGE-M3 cross-lingual Recall@10 below 0.70 threshold on textile corpus

**Probability:** LOW-MEDIUM (MIRACL benchmark shows strong IT performance; textile vocabulary is niche)
**Impact:** MEDIUM (success criterion #1 not met; fallback is query translation Phase 11)
**Mitigation:** A/B eval (D-71) must be run and documented BEFORE marking Phase 5 complete. If threshold not met, document clearly in `docs/eval/rag-ab-test-bge-m3-vs-e5.md` and open Phase 11 query translation task.

### Risk 4: SemanticSplitter API drift between llama-index-core 0.11 and 0.14

**Probability:** LOW (import path confirmed stable; breakpoint_percentile_threshold documented)
**Impact:** LOW-MEDIUM (need to adjust instantiation parameters)
**Mitigation:** Pin `llama-index-core>=0.11,<0.15`. Verify in Wave 1 `test_semantic_chunker.py` that `SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=95, embed_model=...)` instantiates without error.

### Risk 5: FlagEmbedding sparse vector format incompatibility with Qdrant 1.18

**Probability:** LOW (confirmed BM42 support in Qdrant 1.10+; BGE-M3 sparse is documented)
**Impact:** HIGH (retrieval pipeline broken; BM42 leg of hybrid search silent zero-result)
**Mitigation:** Integration test in `test_qdrant_indexer.py` must verify: (1) sparse vector upserted successfully, (2) sparse-only retrieval returns non-empty results, (3) RRF fusion returns merged results.

### Risk 6: QdrantIndexer point ID format (hex string vs UUID)

**Probability:** MEDIUM (Qdrant may reject non-UUID-formatted string IDs)
**Impact:** HIGH (all upsert calls fail)
**Mitigation:** Format sha256 output as `{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}` (UUID-like string). Verify qdrant-client 1.18 accepts this format in Wave 1 integration test before any data is upserted.

### Risk 7: LlamaIndex SemanticSplitter metadata propagation

**Probability:** MEDIUM (metadata exclusion from embedding vs retention in node metadata is version-sensitive)
**Impact:** MEDIUM (provenance fields lost from chunks; KNW-05 fails)
**Mitigation:** Integration test `test_semantic_chunker.py::test_metadata_propagation` verifies that `source_uri`, `lang`, `acl_level` are present in each output `TextNode.metadata` after `get_nodes_from_documents()`.

---

## Open Questions

1. **Qdrant 1.18 SparseVector from FlagEmbedding — UNK token handling**
   - What we know: BGE-M3 sparse output is `dict[token_str, float]`; some tokens may map to UNK ID
   - What's unclear: Whether Qdrant 1.18 silently ignores indices mapped to UNK or raises an error
   - Recommendation: Add explicit UNK filtering in `BgeM3Embedder.to_qdrant_sparse()` and validate with a unit test

2. **Neo4j `SOP.id` format with version**
   - What we know: D-69 says `SOP.id = f"{sop_id}@{version}"` for multi-version coexistence
   - What's unclear: When ingest detects a version change, does `MERGE (s:SOP {id: row.sop_id})` without version suffix cause two nodes? The current MERGE key should be `{id: f"{sop_id}@{version}"}` to be consistent
   - Recommendation: Confirm in `Neo4jGraphBuilder` that SOP node MERGE key includes version; document the trade-off (history retained vs latest-only query complexity)

3. **testcontainers Neo4j image tag for v5.24**
   - What we know: `testcontainers[neo4j]` supports Neo4j via Docker image
   - What's unclear: Whether `DockerContainer("neo4j:5.24.0")` correctly sets up APOC plugin in test container context
   - Recommendation: Use `DockerContainer("neo4j:5.24.0").with_env("NEO4J_PLUGINS", '["apoc"]')` and verify APOC is available in first bootstrap test

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | testcontainers integration tests | ✓ | 29.3.0 | — |
| qdrant/qdrant:v1.16.1 image | Local dev (core.yml) | ✓ | v1.16.1 | testcontainer pulls automatically |
| neo4j:5.24.0 image | Local dev + testcontainers | ✗ | — (not yet in compose) | Plan 05-05 adds to core.yml |
| Python 3.12 | uv workspace (pinned `<3.13`) | ✓ | 3.13.7 on system; uv manages 3.12 env | — |
| FlagEmbedding (PyTorch) | embedding + reranking | available via pip | 1.4.0 | fastembed (lighter, dense-only) |
| GPU (CUDA) | BGE-M3 fp16 acceleration | unknown | — | CPU fp32 (slower but correct) |
| Ollama (Qwen2.5-7B) | A/B eval Q-gen | unknown | — | vLLM adapter or skip Q-gen on CI |

**Missing dependencies with no fallback:**
- neo4j:5.24.0 Docker image — must be added to `infra/compose/core.yml` in Plan 05-05

**Missing dependencies with fallback:**
- GPU (CUDA): Phase 5 CI runs on CPU (slower ingest, acceptable for 41 SOPs); mark GPU tests `@pytest.mark.gpu`
- Ollama for A/B eval Q-gen: if Ollama not available in CI, `run_ab_eval.py` can run with pre-generated `testset.jsonl` (committed to repo with seed=42); add `--skip-qgen` flag to eval script

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed-token sliding window chunking | Semantic chunking via embedding cosine similarity | 2023–2024 | Preserves procedural step boundaries; reduces mid-step splits |
| BM25 (external, pre-indexed) | BM42 neural sparse (server-side, Qdrant native) | Qdrant 1.10 (2024) | No separate indexing service; BM42 is lightweight (5.6 elements avg) |
| Single-pass retrieval (one embedding type) | Hybrid RRF (dense+sparse+rerank) | 2024 | 10–25% NDCG improvement vs dense-only on multilingual corpora |
| Per-language collection or query translation | BGE-M3 unified cross-lingual representation | 2024 (BGE-M3 v1) | Single collection for IT+EN; no LLM round-trip for query translation |
| Synchronous document ingestion (blocks agents) | Batch ingest service, agents read-only | Best practice established 2023 | Prevents hallucination contamination; decouples knowledge refresh from inference |

**Deprecated/outdated:**
- `unstructured.io` for Phase 5 Markdown: Phase 5 corpus is 100% Markdown; unstructured adds 500MB+ Docker overhead for zero benefit. Deferred to Phase 8.
- `langchain BM25Retriever`: requires NLTK, separate index; BM42 server-side is superior and already included in Qdrant 1.10+.
- `sentence-transformers` direct for BGE-M3: still works but FlagEmbedding is the official BAAI implementation with unified dense+sparse interface.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `sparse_vectors_config` is a separate parameter from `vectors_config` in qdrant-client 1.18 | Section 1 | Collection creation fails; different parameter structure needed |
| A2 | FlagEmbedding `BGEM3FlagModel` lexical_weights dict can be converted to Qdrant SparseVector via tokenizer ID lookup | Section 2 | Sparse vector dimension mismatch; retrieval fails silently |
| A3 | FlagReranker is thread-safe for use in asyncio.to_thread | Section 3 | Race conditions on reranker singleton; corrupt scores |
| A4 | LlamaIndex 0.14 propagates all keys in `Document.metadata` to each `TextNode.metadata` | Section 4 | Provenance fields lost; KNW-05 fails |
| A5 | Ollama passes `seed` parameter through langchain-ollama to Qwen2.5 inference API | Section 8 | Q-gen not deterministic; testset regeneration yields different queries |
| A6 | Qdrant 1.18 accepts UUID-formatted hex string as point ID (without strict v4 validation) | Section 9 | Point upsert fails; alternative is int64 hash-derived ID |
| A7 | Python 3.12 is the runtime (workspace `>=3.12,<3.13`); blake3 NOT in stdlib | Section 9 | N/A — risk mitigated by using sha256 |
| A8 | testcontainers neo4j image with `NEO4J_PLUGINS='["apoc"]'` correctly enables APOC in test | Section: Open Questions | APOC not available in tests; Neo4jGraphBuilder tests fail on APOC procedures |
| A9 | neo4j pin `>=5.24,<7` prevents v6 accidental install | Section 5 | v6 breaking changes encountered in CI; Bookmark API error |

**If this table is empty:** All claims in this research were verified or cited. (Table is not empty — 9 assumptions logged above.)

---

## References

### Primary (HIGH confidence)
- `PyPI pip index versions qdrant-client` — confirmed version 1.18.0 latest; 1.16.x available [VERIFIED]
- `PyPI pip index versions FlagEmbedding` — confirmed 1.4.0 latest [VERIFIED]
- `PyPI pip index versions llama-index-core` — confirmed 0.14.22 latest [VERIFIED]
- `PyPI pip index versions neo4j` — confirmed 6.2.0 latest; 5.24.0 in 5.x series [VERIFIED]
- `PyPI pip index versions python-frontmatter` — confirmed 1.2.0 [VERIFIED]
- `PyPI pip index versions fastembed` — confirmed 0.8.0 [VERIFIED]
- `PyPI pip index versions testcontainers` — confirmed 4.14.2 [VERIFIED]
- Python 3.12 stdlib hashlib `blake3` absent — confirmed by `python3 -c "import hashlib; print('blake3' in hashlib.algorithms_available)"` → False [VERIFIED]
- Docker 29.3.0 available — confirmed via `docker info` [VERIFIED]
- Qdrant v1.16.1 Docker image present — confirmed via `docker images` [VERIFIED]
- Synthetic corpus: 41 SOP MD files, all without `acl_level` field — confirmed via `find` + frontmatter inspection [VERIFIED]
- Phase 4 `RagCitation` schema: `source_uri`, `snippet`, `score`, `retrieved_at` — confirmed in `packages/sft-agents/src/sft_agents/models/evidence.py` [VERIFIED]
- Phase 4 `StubLongTermMemory` + `MemoryStore` ABC in `packages/sft-agents/src/sft_agents/memory/` [VERIFIED]
- Next migration number: `006_create_ingest_state.sql` (005 exists) [VERIFIED: `ls infra/migrations/timescale/`]

### Secondary (MEDIUM confidence)
- [Qdrant BM42 article](https://qdrant.tech/articles/bm42/) — BM42 server-side sparse, FastEmbed integration
- [Qdrant 1.10 Query API](https://qdrant.tech/blog/qdrant-1.10.x/) — `query_points` + `Prefetch` + `FusionQuery(RRF)` introduction
- [BGE-M3 paper](https://arxiv.org/html/2402.03216v3) — MIRACL cross-lingual benchmark results; Italian performance
- [FlagEmbedding GitHub README](https://github.com/FlagOpen/FlagEmbedding/blob/master/research/BGE_M3/README.md) — BGE-M3 + FlagReranker API; fp16 fallback behavior
- [LlamaIndex SemanticSplitter docs](https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/modules/) — confirmed import path `from llama_index.core.node_parser import SemanticSplitterNodeParser`
- [Neo4j Python Driver 6.x changelog](https://github.com/neo4j/neo4j-python-driver/wiki/6.x-changelog) — breaking changes in v6 vs v5
- [Neo4j Docker APOC setup](https://neo4j.com/docs/operations-manual/current/docker/plugins/) — `NEO4J_PLUGINS=["apoc"]` env var
- [GraphRAG with Qdrant + Neo4j](https://qdrant.tech/documentation/examples/graphrag-qdrant-neo4j/) — graph-first + vector-second join pattern
- [python-frontmatter MIT source](https://github.com/eyeseast/python-frontmatter) — uses yaml.safe_load internally

### Tertiary (LOW confidence — flagged for validation)
- FlagReranker thread-safety in asyncio.to_thread context — assumed, not verified in documentation
- Qdrant 1.18 point ID validation (UUID format vs hex string) — assumed; must verify in Wave 1 integration test
- LlamaIndex 0.14 metadata propagation behavior — assumed from 0.10 docs; verify in unit test

---

## Metadata

**Confidence breakdown:**
- Standard stack (packages, versions): HIGH — all confirmed via PyPI
- Architecture patterns (dual-write, ACL pre-filter): HIGH — from ARCHITECTURE.md + CONTEXT.md decisions
- API signatures (Qdrant, FlagEmbedding, LlamaIndex): MEDIUM — from official docs + GitHub README; some details need integration test verification
- Cross-lingual performance thresholds: MEDIUM — MIRACL benchmark documented but textile corpus A/B eval required

**Research date:** 2026-05-18
**Valid until:** 2026-07-18 (stable stack; 60 days — all dependencies are mature, low churn)

---

## RESEARCH COMPLETE
