---
plan_id: 05-09-retrieval-pipeline-tools-memory
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 4
depends_on: [05-04-qdrant-bootstrap, 05-05-neo4j-compose-bootstrap, 05-07-embedding-chunking, 05-08-indexer-graph-builder]
requirements: [KNW-06, KNW-09]
files_modified:
  - packages/sft-knowledge/src/sft_knowledge/retrieval/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py
  - packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py
  - packages/sft-knowledge/src/sft_knowledge/tools/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/tools/rag.py
  - packages/sft-knowledge/src/sft_knowledge/tools/graph.py
  - packages/sft-knowledge/src/sft_knowledge/memory/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py
  - packages/sft-knowledge/src/sft_knowledge/__init__.py
  - packages/sft-agents/src/sft_agents/memory/__init__.py
  - packages/sft-knowledge/tests/test_retrieval_pipeline.py
  - packages/sft-knowledge/tests/test_acl_enforcement.py
  - packages/sft-knowledge/tests/test_crosslingual_e2e.py
autonomous: true
estimated_atomic_commits: 4
must_haves:
  truths:
    - "BgeReranker.rerank(query, hits) returns sorted list[tuple[hit, score]] with scores in [0,1] (normalize=True)"
    - "RetrievalPipeline.search(query, user_roles) executes embed → Qdrant Query API (Prefetch dense+sparse → Fusion RRF top-20) → BGE-reranker → top-k"
    - "ACL pre-filter applied at Qdrant engine level via ROLE_TO_ACL constant + Filter(must=[FieldCondition(acl_level)])"
    - "RagSearchTool exposes async-only BaseTool with frozen+forbid args_schema RagSearchInput"
    - "TraverseGraphTool uses Literal whitelist for seed_label + relation_path; $param for seed_id (D-66 injection-safe)"
    - "QdrantLongTermMemory implements Memory ABC; replaces StubLongTermMemory in sft-agents/memory/__init__.py"
    - "test_operator_cannot_see_restricted (KNW-06 SC#2) passes: operator role retrieves zero restricted chunks"
    - "test_it_query_returns_en_sop (SC#1 cross-lingual) passes: IT query retrieves ≥1 EN SOP chunk"
    - "test_hybrid_retrieval_returns_ranked (KNW-09) passes: scores monotonically decreasing in [0,1]"
  artifacts:
    - path: packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py
      provides: RetrievalPipeline with single-shot Qdrant query_points + Prefetch + Fusion RRF + rerank
    - path: packages/sft-knowledge/src/sft_knowledge/tools/rag.py
      provides: RagSearchTool LangChain BaseTool with ACL pre-filter + sop_ids composition
    - path: packages/sft-knowledge/src/sft_knowledge/tools/graph.py
      provides: TraverseGraphTool with injection-safe parametrized Cypher
    - path: packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py
      provides: QdrantLongTermMemory(Memory) — replaces D-59 stub
  key_links:
    - from: packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py
      to: BgeM3Embedder + QdrantIndexer
      via: query_points Prefetch dense+sparse + FusionQuery(RRF)
      pattern: "Prefetch.*FusionQuery"
    - from: packages/sft-knowledge/src/sft_knowledge/tools/rag.py
      to: ROLE_TO_ACL
      via: Filter(must=[FieldCondition(acl_level)])
      pattern: "ROLE_TO_ACL|acl_level"
    - from: packages/sft-agents/src/sft_agents/memory/__init__.py
      to: packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py
      via: import swap (D-59 stub → real)
      pattern: "QdrantLongTermMemory"
---

<objective>
Implement the retrieval tier: `BgeReranker` (BGE-reranker-v2-m3 cross-encoder, FlagReranker wrapper, async bridge), `RetrievalPipeline` (orchestrates embed → Qdrant query_points single-shot Prefetch+RRF → rerank → top-k), the two LangChain `BaseTool` exposures (`RagSearchTool` + `TraverseGraphTool`), and `QdrantLongTermMemory` replacing the Phase 4 D-59 stub.

Purpose: this plan closes the user-facing surface of Phase 5 knowledge layer. KNW-06 (ACL enforcement SC#2), KNW-09 (hybrid retrieval), and Phase 5 SC#1 (cross-lingual E2E) close here.

Output: complete retrieval pipeline + 2 tools + memory backend swap, with 3 critical integration tests green (ACL non-leak, hybrid retrieval ranked, cross-lingual E2E).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md
@.planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md
@.planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md
@.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md
@packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py
@packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py
@packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py
@packages/sft-knowledge/src/sft_knowledge/models.py
@packages/sft-agents/src/sft_agents/memory/__init__.py
@packages/sft-agents/src/sft_agents/memory/long_term_stub.py
@packages/sft-agents/src/sft_agents/sdk/memory.py
@packages/sft-agents/src/sft_agents/models/memory_record.py
@packages/sft-tools/src/sft_tools/timescale/query.py
</context>

<interfaces>
BgeReranker (D-63 + RESEARCH §3 + PATTERNS.md reranker.py section):
```
class BgeReranker:
    def __init__(self, device: str | None = None):
        # lazy singleton via @lru_cache
        ...

    async def rerank(self, query: str, hits: list[ScoredPoint]) -> list[tuple[ScoredPoint, float]]:
        # pairs = [(query, hit.payload["text"]) for hit in hits]
        # FlagReranker.compute_score is sync — bridge via asyncio.to_thread
        # scores = await asyncio.to_thread(reranker.compute_score, pairs, True)
        # return sorted(zip(hits, scores), key=lambda x: -x[1])
```

RetrievalPipeline (D-63 LOCKED):
```
ROLE_TO_ACL: dict[str, frozenset[str]] = {
    "operator":   frozenset({"public"}),
    "technician": frozenset({"public", "internal"}),
    "supervisor": frozenset({"public", "internal"}),
    "manager":    frozenset({"public", "internal", "restricted"}),
    "engineer":   frozenset({"public", "internal", "restricted"}),
    "safety":     frozenset({"public", "internal", "restricted"}),
}

def build_acl_filter(user_roles: list[str]) -> Filter:
    allowed = frozenset().union(*(ROLE_TO_ACL.get(r, frozenset()) for r in user_roles))
    if not allowed:
        raise ValueError(f"No ACL levels resolved for roles: {user_roles}")
    return Filter(must=[FieldCondition(key="acl_level", match=MatchAny(any=sorted(allowed)))])

class RetrievalPipeline:
    def __init__(self, qdrant_client, embedder: BgeM3Embedder, reranker: BgeReranker | None = None):
        ...

    async def search(self, query: str, user_roles: list[str], category: str = "sop",
                     k: int = 5, lang: str | None = None, sop_ids: list[str] | None = None,
                     asset_family: str | None = None, rerank: bool = True) -> list[RagCitation]:
        # 1. embed query → dense_vec + sparse_vec
        # 2. build acl_filter + optional lang/sop_ids/asset_family filter conditions
        # 3. await client.query_points(collection=category, prefetch=[
        #      Prefetch(query=dense_vec, using="dense", limit=20, query_filter=composite_filter),
        #      Prefetch(query=sparse_vec, using="sparse", limit=20, query_filter=composite_filter),
        #    ], query=FusionQuery(fusion=Fusion.RRF), limit=20, with_payload=True)
        # 4. if rerank: await self._reranker.rerank(query, fused_hits) → top k
        # 5. else: fused_hits[:k]
        # 6. Return list[RagCitation(source_uri, snippet=text[:200], score, retrieved_at=datetime.now(UTC))]
```

RagSearchTool (D-66 LOCKED — args_schema schema is non-negotiable per CONTEXT.md):
```
class RagSearchInput(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    query: str
    user_roles: list[str]
    category: Literal["sop", "manuals", "troubleshooting", "training"] = "sop"
    k: int = Field(default=5, ge=1, le=20)
    lang: Literal["it", "en"] | None = None
    sop_ids: list[str] | None = None
    asset_family: str | None = None
    rerank: bool = True

class RagSearchTool(BaseTool):
    name: str = "rag_search"
    description: str = "Search knowledge base chunks with hybrid retrieval (dense+sparse+rerank). Returns RagCitation list."
    args_schema = RagSearchInput

    def _run(self, **kwargs) -> list[RagCitation]:
        raise NotImplementedError("RagSearchTool is async-only. Use `await tool.ainvoke({...})`.")

    async def _arun(self, **kwargs) -> list[RagCitation]:
        return await self._pipeline.search(**kwargs)
```

TraverseGraphTool (D-66 LOCKED + RESEARCH §5 injection defense):
```
class TraverseGraphInput(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    seed_label: Literal["Machine", "Part", "FailureMode", "SOP"]
    seed_id: str
    relation_path: list[Literal["HAS_PART", "HAS_FAILURE_MODE", "DOCUMENTED_BY"]]
    max_depth: int = Field(default=3, ge=1, le=5)

class TraverseGraphTool(BaseTool):
    name: str = "traverse_graph"
    description: str = "Navigate entity graph (Machine→Part→FailureMode→SOP) along relation_path. Returns list[GraphNode]."
    args_schema = TraverseGraphInput

    async def _arun(self, **kwargs) -> list[GraphNode]:
        # seed_label is Literal-validated → safe for label slot in f-string
        # seed_id MUST remain a $param (RESEARCH §5)
        # relation_path → build "[:REL1|REL2|...]" string (Literal-validated)
        # cypher = f"MATCH (n:{seed_label} {{id: $seed_id}})-[:{rel_pipe}*1..{max_depth}]->(m) RETURN DISTINCT m LIMIT 100"
        # async with self._driver.session() as session: result = await session.run(cypher, seed_id=seed_id)
        # return [GraphNode(label=record["m"].labels.first, node_id=record["m"]["id"], properties={...})]
```

QdrantLongTermMemory (D-70 + PATTERNS.md memory/qdrant_long_term.py):
```
from sft_agents.sdk.memory import Memory
from sft_agents.models.memory_record import MemoryRecord

class QdrantLongTermMemoryConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "sop"
    embedding_device: str = "cpu"

class QdrantLongTermMemory(Memory):
    def __init__(self, config: QdrantLongTermMemoryConfig | None = None) -> None:
        ...

    async def query(self, query: str, k: int = 5, filters: dict[str, Any] | None = None) -> list[MemoryRecord]:
        # 1. Build user_roles from filters.get("user_roles", []) or default ["operator"]
        # 2. Call RetrievalPipeline.search(query, user_roles, k=k)
        # 3. Convert RagCitation → MemoryRecord (mirror Phase 4 MemoryRecord schema)

    async def store(self, record: MemoryRecord) -> str:
        # Phase 5: agents don't write directly to knowledge stores (ARCHITECTURE.md anti-pattern)
        # → raise NotImplementedError("Agents must not write directly to knowledge stores. Use services/knowledge-ingest pipeline.")
```

Memory ABC swap in sft-agents:
```
# packages/sft-agents/src/sft_agents/memory/__init__.py BEFORE:
from sft_agents.memory.long_term_stub import StubLongTermMemory
LongTermMemory = StubLongTermMemory  # D-59 Phase 4

# AFTER (Plan 05-09 task 4):
try:
    from sft_knowledge.memory import QdrantLongTermMemory
    LongTermMemory = QdrantLongTermMemory
except ImportError:
    # graceful fallback for environments where sft-knowledge not installed
    from sft_agents.memory.long_term_stub import StubLongTermMemory
    LongTermMemory = StubLongTermMemory
```

Preserve `LongTermMemory` export name so Phase 4 agent imports continue to resolve.

Phase 4 MemoryRecord schema (per packages/sft-agents/src/sft_agents/models/memory_record.py — executor must read to confirm exact field names): typically `agent_id, content, ts (tz-aware), metadata` or similar. Map RagCitation → MemoryRecord field-by-field.
</interfaces>

<tasks>

<task id="05-09-01" type="auto" tdd="true">
  <name>Task 1: BgeReranker + RetrievalPipeline (embed → query_points + RRF → rerank → top-k)</name>
  <files>
    packages/sft-knowledge/src/sft_knowledge/retrieval/__init__.py,
    packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py,
    packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py,
    packages/sft-knowledge/src/sft_knowledge/__init__.py,
    packages/sft-knowledge/tests/test_retrieval_pipeline.py
  </files>
  <read_first>
    packages/sft-tools/src/sft_tools/timescale/query.py (async-only pattern lines 72-84, env-based config lines 107-114),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-63 retrieval pipeline lines 164-212; ROLE_TO_ACL constant),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §1 + §3 (Qdrant query_points API + FlagReranker compute_score + asyncio.to_thread bridge),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (retrieval/reranker.py + retrieval/pipeline.py sections lines 410-479),
    packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py (BgeM3Embedder API from Plan 05-07)
  </read_first>
  <behavior>
    - `_get_reranker()` is `@lru_cache(maxsize=1)`; imports FlagReranker inside; uses BGE_M3_DEVICE env; use_fp16=True (auto fp32 on CPU)
    - `BgeReranker.rerank(query, hits)` returns sorted list[tuple[hit, score]] descending by score; scores in [0,1] (normalize=True per D-63); uses `asyncio.to_thread(compute_score, pairs, True)` bridge
    - `RetrievalPipeline.search()`:
      - Always builds ACL filter via build_acl_filter (raises ValueError if no roles match)
      - Combines acl_filter + optional lang, sop_ids, asset_family filters into single Filter via `must=[...]`
      - Calls `await client.query_points(...)` with both dense+sparse Prefetch + FusionQuery(RRF)
      - If rerank=True: await reranker.rerank(query, fused.points) → top-k tuples → convert to RagCitation
      - If rerank=False: take fused.points[:k] → convert to RagCitation (score = fused.points[i].score)
      - RagCitation.snippet = text[:200] (claudes_discretion lines 788)
      - RagCitation.retrieved_at = datetime.now(UTC)
    - test_acl_filter_raises_on_empty_roles: build_acl_filter([]) → ValueError
    - test_acl_filter_allowed_set: build_acl_filter(["operator"]) → Filter contains MatchAny(any=["public"])
    - test_acl_filter_multi_role_union: build_acl_filter(["technician", "manager"]) → Filter contains union {public, internal, restricted}
    - test_pipeline_search_returns_rag_citations (integration, testcontainer): full pipeline returns list[RagCitation] with snippet ≤200 chars, score in [0,1], retrieved_at tz-aware
    - test_hybrid_retrieval_returns_ranked (integration, KNW-09 SC): index ≥10 chunks; query; assert scores monotonically descending; assert all scores in [0,1]; assert all citations have valid source_uri
    - test_rerank_disabled_uses_fusion_score (integration): same query with rerank=False returns hits with fusion RRF scores (different from rerank scores)
  </behavior>
  <action>
    Create `packages/sft-knowledge/src/sft_knowledge/retrieval/__init__.py` re-exporting `BgeReranker, RetrievalPipeline, ROLE_TO_ACL, build_acl_filter`.

    Create `packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py`:
    - lazy `_get_reranker()` per PATTERNS.md retrieval/reranker.py section lines 437-446.
    - `class BgeReranker`:
      - `def __init__(self, device: str | None = None) -> None`: optional device override (sets env if provided), store self._device.
      - `async def rerank(self, query: str, hits: list) -> list[tuple]`: build pairs, await asyncio.to_thread, return sorted tuples. Handle empty hits → return [].

    Create `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`:
    - Module constants `ROLE_TO_ACL` per D-63 (exact mapping).
    - Function `build_acl_filter(user_roles: list[str]) -> Filter` per CONTEXT.md D-63 lines 192-204. Lazy-import qdrant_client.http.models inside function. Raises ValueError if allowed set is empty.
    - `class RetrievalPipeline`:
      - `def __init__(self, qdrant_client, embedder, reranker: BgeReranker | None = None) -> None`: store, default reranker = BgeReranker() if None.
      - `async def search(self, query, user_roles, category="sop", k=5, lang=None, sop_ids=None, asset_family=None, rerank=True) -> list[RagCitation]`:
        1. `output = self._embedder.encode([query], return_dense=True, return_sparse=True)`; `dense_vec = output.dense_vecs[0].tolist()`; sparse via `self._embedder.to_qdrant_sparse(output.sparse_weights[0])`.
        2. acl = build_acl_filter(user_roles); must_conditions = list(acl.must).
        3. Append optional FieldCondition for lang, sop_ids (MatchAny), asset_family.
        4. composite_filter = Filter(must=must_conditions).
        5. result = await client.query_points(collection_name=category, prefetch=[Prefetch(query=dense_vec, using="dense", limit=20, filter=composite_filter), Prefetch(query=sparse, using="sparse", limit=20, filter=composite_filter)], query=FusionQuery(fusion=Fusion.RRF), limit=20, with_payload=True).
        6. fused_hits = result.points.
        7. if rerank and len(fused_hits) > 0: ranked = await self._reranker.rerank(query, fused_hits); take [:k].
        8. else: ranked = [(h, h.score) for h in fused_hits[:k]].
        9. Convert to RagCitation: `RagCitation(source_uri=hit.payload["source_uri"], snippet=hit.payload["text"][:200], score=float(score), retrieved_at=datetime.now(UTC))`.
        10. Return list.
      - Wrap all in try/except with structlog logger; re-raise.

    Update `packages/sft-knowledge/src/sft_knowledge/__init__.py` to re-export `RetrievalPipeline, BgeReranker, ROLE_TO_ACL, build_acl_filter`.

    Update `packages/sft-knowledge/tests/test_retrieval_pipeline.py` (remove Plan 05-01 stub skip):
    - 3 unit tests for build_acl_filter (no marker).
    - 3 integration tests (`@pytest.mark.integration`) using `qdrant_client` + indexed sample data. To avoid running real BGE-M3 in CI, MOCK the BgeM3Embedder by injecting a stub returning deterministic dense+sparse vectors. The BgeReranker similarly stubbed for CI; if `@pytest.mark.gpu` available the real path is exercised.

    Commit: `feat(05-09-retrieval-pipeline-tools-memory): add BgeReranker + RetrievalPipeline with hybrid query + ACL pre-filter`.
  </action>
  <acceptance_criteria>
    - `grep -q 'class RetrievalPipeline' packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`
    - `grep -q 'ROLE_TO_ACL' packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`
    - `grep -q 'def build_acl_filter' packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`
    - `grep -q 'FusionQuery' packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`
    - `grep -q 'Prefetch' packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`
    - `grep -q 'asyncio.to_thread' packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py`
    - `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k 'acl_filter or build_acl' -v"` exits 0
    - `nx run sft-knowledge:test --args="-m integration -k 'test_hybrid_retrieval_returns_ranked' -v"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m integration -k 'test_hybrid_retrieval_returns_ranked' -v"</automated>
  </verify>
  <done>RetrievalPipeline + BgeReranker committed; KNW-09 hybrid retrieval verified; ACL filter constructed at engine level.</done>
</task>

<task id="05-09-02" type="auto" tdd="true">
  <name>Task 2: RagSearchTool + TraverseGraphTool (LangChain BaseTool, async-only, injection-safe)</name>
  <files>
    packages/sft-knowledge/src/sft_knowledge/tools/__init__.py,
    packages/sft-knowledge/src/sft_knowledge/tools/rag.py,
    packages/sft-knowledge/src/sft_knowledge/tools/graph.py,
    packages/sft-knowledge/src/sft_knowledge/__init__.py,
    packages/sft-knowledge/tests/test_acl_enforcement.py
  </files>
  <read_first>
    packages/sft-tools/src/sft_tools/timescale/query.py (BaseTool async-only pattern lines 46-143),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-66 RagSearchTool + TraverseGraphTool full spec lines 302-362),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §5 (Cypher injection defense — labels safe from Literal, $param for data) + §6 (GraphRAG patterns),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (tools/rag.py + tools/graph.py sections lines 483-577 + Shared Patterns 4 + 7),
    .planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md (KNW-06 SC#2 test row),
    packages/sft-knowledge/src/sft_knowledge/models.py (GraphNode)
  </read_first>
  <behavior>
    - RagSearchTool args_schema is frozen+forbid; extra args rejected by Pydantic
    - RagSearchTool._run raises NotImplementedError per Shared Pattern 7
    - RagSearchTool._arun calls RetrievalPipeline.search with all args; returns list[RagCitation]
    - TraverseGraphTool args_schema: seed_label is Literal whitelist, relation_path is list[Literal[...]]; Pydantic rejects unknown labels/relations
    - TraverseGraphTool builds Cypher using f-string ONLY for label slot (Literal-validated) and relation pipe (Literal-validated); seed_id and max_depth pass as $param
    - test_rag_tool_rejects_unknown_args (unit): RagSearchInput(query="x", user_roles=["operator"], extra_field="y") raises ValidationError
    - test_rag_tool_async_only (unit): RagSearchTool()._run() raises NotImplementedError
    - test_traverse_tool_rejects_invalid_label (unit): TraverseGraphInput(seed_label="DROP TABLE") raises ValidationError
    - test_traverse_tool_rejects_invalid_relation (unit): TraverseGraphInput(relation_path=["DROP_TABLE"]) raises ValidationError
    - test_traverse_tool_uses_param_for_seed_id (unit, source scan): grep tools/graph.py source; assert seed_id appears as `$seed_id` in cypher AND as kwarg to session.run; NOT as f-string interpolation
    - test_operator_cannot_see_restricted (KNW-06 SC#2, integration): index 1 SOP with acl_level="restricted" + 1 SOP with acl_level="public"; operator role queries; result contains zero restricted chunks
    - test_technician_can_see_internal: technician role queries → can retrieve internal chunks but not restricted
    - test_manager_can_see_restricted: manager role can retrieve restricted chunks
  </behavior>
  <action>
    Create `packages/sft-knowledge/src/sft_knowledge/tools/__init__.py` re-exporting `RagSearchTool, RagSearchInput, TraverseGraphTool, TraverseGraphInput`.

    Create `packages/sft-knowledge/src/sft_knowledge/tools/rag.py`:
    - Import from langchain_core.tools BaseTool, pydantic BaseModel, Field, Literal.
    - Define `RagSearchInput` per D-66 (verbatim schema from <interfaces>).
    - `class RagSearchTool(BaseTool)`:
      - `name: str = "rag_search"`, descriptive `description` string covering D-66 (D-66 line 318-321).
      - `args_schema: type[BaseModel] = RagSearchInput`.
      - `_pipeline: RetrievalPipeline | None = None` (pydantic-allowed since BaseTool uses pydantic v1/v2 compat; use `model_config = ConfigDict(arbitrary_types_allowed=True)` if needed).
      - Alternative: take pipeline via `__init__` and use Tool subclass pattern — verify what langchain-core>=0.3 supports; PATTERNS.md tools/rag.py keeps pipeline as instance attribute set via setter or init.
      - `def _run(self, *args, **kwargs)` raises NotImplementedError per Shared Pattern 7.
      - `async def _arun(self, query, user_roles, category="sop", k=5, lang=None, sop_ids=None, asset_family=None, rerank=True, **kwargs) -> list[RagCitation]`:
        - return await `self._pipeline.search(query=query, user_roles=user_roles, category=category, k=k, lang=lang, sop_ids=sop_ids, asset_family=asset_family, rerank=rerank)`.

    Create `packages/sft-knowledge/src/sft_knowledge/tools/graph.py`:
    - `TraverseGraphInput` per D-66 (verbatim schema).
    - `class TraverseGraphTool(BaseTool)`:
      - name, description, args_schema set.
      - `_driver` attribute (Neo4j AsyncDriver) set via init.
      - `def _run`: raises NotImplementedError.
      - `async def _arun(self, seed_label, seed_id, relation_path, max_depth=3) -> list[GraphNode]`:
        - `rel_pipe = "|".join(relation_path)` (Literal-validated values, safe to f-string)
        - `cypher = f"MATCH (n:{seed_label} {{id: $seed_id}})-[:{rel_pipe}*1..{max_depth}]->(m) RETURN DISTINCT m LIMIT 100"` (seed_label and rel_pipe from Literal whitelist; max_depth is Pydantic-validated int with ge=1, le=5 so safe to interpolate; seed_id is $param)
        - `async with self._driver.session(database="neo4j") as session: result = await session.run(cypher, seed_id=seed_id); records = await result.data()`
        - For each record m: build GraphNode(label=infer from labels, node_id=m["id"], properties={k:v for k,v in m.items()}).
        - Return list.

    Update `packages/sft-knowledge/src/sft_knowledge/__init__.py` to re-export `RagSearchTool, TraverseGraphTool, RagSearchInput, TraverseGraphInput`.

    Update `packages/sft-knowledge/tests/test_acl_enforcement.py` (remove Plan 05-01 stub skip):
    - Implement 3 integration tests (KNW-06 SC#2 + technician + manager) and 3 unit tests (frozen args, async-only _run, label/relation Literal validation).
    - For integration tests: index 2 SOP fixtures (one public, one restricted) using mocked embeddings (deterministic dense + sparse zero/one vectors). Verify ACL pre-filter blocks the restricted hit.
    - Add `test_traverse_tool_uses_param_for_seed_id` as a source-scan unit test: `grep -E "f\".*\\{seed_id\\}" packages/sft-knowledge/src/sft_knowledge/tools/graph.py` returns 0.

    Commit: `feat(05-09-retrieval-pipeline-tools-memory): add RagSearchTool + TraverseGraphTool with injection-safe Cypher`.
  </action>
  <acceptance_criteria>
    - `grep -q 'class RagSearchTool(BaseTool):' packages/sft-knowledge/src/sft_knowledge/tools/rag.py`
    - `grep -q 'class TraverseGraphTool(BaseTool):' packages/sft-knowledge/src/sft_knowledge/tools/graph.py`
    - `grep -q 'name: str = "rag_search"' packages/sft-knowledge/src/sft_knowledge/tools/rag.py`
    - `grep -q 'NotImplementedError' packages/sft-knowledge/src/sft_knowledge/tools/rag.py` (Shared Pattern 7)
    - `grep -q 'NotImplementedError' packages/sft-knowledge/src/sft_knowledge/tools/graph.py`
    - `grep -q '\\$seed_id' packages/sft-knowledge/src/sft_knowledge/tools/graph.py` (param placeholder used)
    - `grep -E 'f".*\\{seed_id\\}' packages/sft-knowledge/src/sft_knowledge/tools/graph.py | wc -l` returns 0 (seed_id never interpolated)
    - `nx run sft-knowledge:test --args="-m integration -k test_operator_cannot_see_restricted -v"` exits 0 (KNW-06 SC#2)
    - `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k 'test_traverse_tool or test_rag_tool' -v"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m integration -k 'test_operator_cannot_see_restricted or test_technician_can_see_internal or test_manager_can_see_restricted' -v"</automated>
  </verify>
  <done>Both tools committed with frozen+forbid args + injection-safe Cypher + Shared Pattern 7 async-only; KNW-06 SC#2 ACL non-leak verified.</done>
</task>

<task id="05-09-03" type="auto" tdd="true">
  <name>Task 3: Cross-lingual E2E integration test (Phase 5 SC#1)</name>
  <files>
    packages/sft-knowledge/tests/test_crosslingual_e2e.py
  </files>
  <read_first>
    packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py (just from Task 1),
    packages/sft-knowledge/src/sft_knowledge/tools/rag.py (just from Task 2),
    .planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md (SC#1 test row + Cross-Lingual E2E Test Detail section lines 929-940),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-64 cross-lingual approach lines 215-225 + acceptance threshold ≥0.70),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §7 (cross-lingual eval methodology)
  </read_first>
  <behavior>
    - test_it_query_returns_en_sop (Phase 5 SC#1):
      1. Index ≥2 EN SOPs related to a common textile topic (e.g., warp thread break repair) using REAL BgeM3Embedder (this test requires real model — mark @pytest.mark.integration AND @pytest.mark.gpu since real embedding on CPU is slow but tolerable for 2-3 SOPs)
      2. Italian query "come riparare rottura filo ordito" (per VALIDATION.md SC#1 detail) via RagSearchTool with user_roles=["technician"], k=10
      3. Assert len(results) ≥ 1 AND at least one result has source_uri containing "/en/" — proves cross-lingual retrieval works without query translation
      4. Soft assertion: log all returned source_uris + scores; final A/B eval in Plan 05-10 validates the ≥0.70 threshold rigorously
    - Test is best-effort on CPU (acceptable if it takes 30-60s for 2-3 SOPs); marked GPU-recommended but should run on CPU CI when @pytest.mark.gpu is opted in
  </behavior>
  <action>
    Update `packages/sft-knowledge/tests/test_crosslingual_e2e.py` (remove Plan 05-01 stub skip).

    Implement `test_it_query_returns_en_sop`:
    - Decorate with `@pytest.mark.integration` and `@pytest.mark.gpu` (matching CONTEXT.md SC#1 + VALIDATION.md test detail).
    - Use `qdrant_client` fixture + `neo4j_driver` (not needed for this test but conftest provides anyway).
    - Setup phase: parse 2-3 EN SOPs from `simulators/synthetic-corpus/en/loom/` (focus on warp/loom topic), chunk via SemanticChunker, embed via real BgeM3Embedder, upsert via QdrantIndexer.
    - Run RagSearchTool with query="come riparare rottura filo ordito" (IT), user_roles=["technician"], k=10, lang=None (cross-lingual default per D-64).
    - Assert ≥1 result with `"/en/" in citation.source_uri`.
    - Print citations to log for debugging.
    - Note in docstring that the rigorous A/B Recall@10 ≥ 0.70 acceptance gate is validated by Plan 05-10's `run_ab_eval.py`; this test is the binary "at least one EN SOP retrieved from IT query" gate.

    Commit: `test(05-09-retrieval-pipeline-tools-memory): add cross-lingual E2E test (Phase 5 SC#1)`.
  </action>
  <acceptance_criteria>
    - `grep -q 'def test_it_query_returns_en_sop' packages/sft-knowledge/tests/test_crosslingual_e2e.py`
    - `grep -q '@pytest.mark.integration' packages/sft-knowledge/tests/test_crosslingual_e2e.py`
    - `grep -q '@pytest.mark.gpu' packages/sft-knowledge/tests/test_crosslingual_e2e.py`
    - Either: test passes on GPU runner: `nx run sft-knowledge:test --args="-m 'integration and gpu' -k test_it_query_returns_en_sop -v"` exits 0
    - OR: test is collectible and skips on CPU CI: `nx run sft-knowledge:test --args="--collect-only -k test_it_query_returns_en_sop"` exits 0 and shows the test
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="--collect-only -k test_it_query_returns_en_sop" 2&gt;&amp;1 | grep -q 'test_it_query_returns_en_sop'</automated>
  </verify>
  <done>SC#1 cross-lingual E2E test exists, collectible, runs green when @pytest.mark.gpu is active.</done>
</task>

<task id="05-09-04" type="auto" tdd="true">
  <name>Task 4: QdrantLongTermMemory + swap D-59 stub in sft-agents/memory/__init__.py</name>
  <files>
    packages/sft-knowledge/src/sft_knowledge/memory/__init__.py,
    packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py,
    packages/sft-knowledge/src/sft_knowledge/__init__.py,
    packages/sft-agents/src/sft_agents/memory/__init__.py
  </files>
  <read_first>
    packages/sft-agents/src/sft_agents/memory/long_term_stub.py (StubLongTermMemory implementation lines 1-75 — exact class signature to mirror),
    packages/sft-agents/src/sft_agents/sdk/memory.py (Memory ABC lines 1-37),
    packages/sft-agents/src/sft_agents/models/memory_record.py (MemoryRecord schema — needed to map RagCitation → MemoryRecord),
    packages/sft-agents/src/sft_agents/memory/__init__.py (current D-59 wiring — exact import + alias to swap),
    .planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md (D-59 memory layer split — Phase 5 replaces stub),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (memory/qdrant_long_term.py section lines 581-611)
  </read_first>
  <behavior>
    - `QdrantLongTermMemoryConfig` is frozen+forbid Pydantic (qdrant_url, collection_name, embedding_device defaults)
    - `QdrantLongTermMemory(Memory)` implements Memory ABC: async query() + async store()
    - `query(query: str, k: int = 5, filters: dict | None = None) -> list[MemoryRecord]`:
      - Extract user_roles from filters.get("user_roles", ["operator"]) (default operator = most restrictive)
      - Build RetrievalPipeline lazily on first call (lazy-loaded shared instance per process)
      - Call pipeline.search → list[RagCitation]
      - Map each RagCitation → MemoryRecord (use the EXACT field names from packages/sft-agents/src/sft_agents/models/memory_record.py; executor MUST read that file)
    - `store(record: MemoryRecord) -> str`:
      - Raises NotImplementedError per ARCHITECTURE.md anti-pattern ("agents must not write directly to knowledge stores") with message pointing to services/knowledge-ingest
    - Memory wiring swap in sft-agents:
      - Try import QdrantLongTermMemory from sft_knowledge.memory
      - On ImportError: graceful fallback to StubLongTermMemory (covers test environments without sft-knowledge)
      - `LongTermMemory` name is preserved as module-level alias so Phase 4 agent imports unchanged
    - test_qdrant_long_term_memory_query_returns_memory_records (integration): index sample chunks; call memory.query("test", k=3, filters={"user_roles": ["technician"]}); assert returns list[MemoryRecord] with len ≤ 3
    - test_store_raises_not_implemented (unit): memory.store(record) → NotImplementedError
    - test_default_role_is_operator (unit, source scan or behavior): if filters missing user_roles, defaults to ["operator"] (most restrictive)
    - test_sft_agents_memory_swap_preserves_alias: `from sft_agents.memory import LongTermMemory; assert LongTermMemory.__name__ == "QdrantLongTermMemory"` (or graceful fallback to StubLongTermMemory if sft-knowledge unavailable in test env)
  </behavior>
  <action>
    Create `packages/sft-knowledge/src/sft_knowledge/memory/__init__.py` re-exporting `QdrantLongTermMemory, QdrantLongTermMemoryConfig`.

    Create `packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py`:
    - Mirror `packages/sft-agents/src/sft_agents/memory/long_term_stub.py` class signature (Memory implementation, config-based init, logger).
    - `class QdrantLongTermMemoryConfig(BaseModel)` with `model_config = ConfigDict(frozen=True, extra="forbid")`, fields per `<interfaces>`.
    - `class QdrantLongTermMemory(Memory)`:
      - `def __init__(self, config: QdrantLongTermMemoryConfig | None = None) -> None`: store config (default = QdrantLongTermMemoryConfig()), logger via structlog.
      - Lazy-build pipeline: `_get_pipeline()` private method that on first call instantiates AsyncQdrantClient + BgeM3Embedder + BgeReranker + RetrievalPipeline.
      - `async def query(self, query, k=5, filters=None) -> list[MemoryRecord]`:
        - user_roles = (filters or {}).get("user_roles") or ["operator"]
        - citations = await pipeline.search(query=query, user_roles=user_roles, k=k)
        - Map citations to MemoryRecord per the schema in packages/sft-agents/src/sft_agents/models/memory_record.py (READ that file to confirm exact field names — e.g., if MemoryRecord has fields {agent_id, content, ts, metadata}, build accordingly).
      - `async def store(self, record: MemoryRecord) -> str`:
        - Log "qdrant_long_term_memory_store_rejected" + raise NotImplementedError with message: "Agents must not write directly to knowledge stores per ARCHITECTURE.md. Use services/knowledge-ingest pipeline."

    Update `packages/sft-knowledge/src/sft_knowledge/__init__.py` to re-export `QdrantLongTermMemory, QdrantLongTermMemoryConfig`.

    Update `packages/sft-agents/src/sft_agents/memory/__init__.py`:
    - Read current content first to confirm what's exported (StubLongTermMemory or LongTermMemory alias).
    - Add the conditional import block at top:
      ```
      try:
          from sft_knowledge.memory import QdrantLongTermMemory
          LongTermMemory = QdrantLongTermMemory
      except ImportError:
          from sft_agents.memory.long_term_stub import StubLongTermMemory
          LongTermMemory = StubLongTermMemory
      ```
    - Preserve any other exports (e.g., EpisodicMemory if present).
    - Do NOT remove the long_term_stub.py file — it's the fallback (and Phase 4 test fixtures may still reference it directly).

    Add tests to `packages/sft-knowledge/tests/test_qdrant_long_term_memory.py` (NEW file):
    - Implement 4 tests from `<behavior>`. test_sft_agents_memory_swap_preserves_alias verifies the conditional import path.

    Commit: `feat(05-09-retrieval-pipeline-tools-memory): add QdrantLongTermMemory + swap D-59 stub in sft-agents`.
  </action>
  <acceptance_criteria>
    - `grep -q 'class QdrantLongTermMemory(Memory):' packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py`
    - `grep -q 'NotImplementedError' packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py` (store method)
    - `grep -q 'class QdrantLongTermMemoryConfig' packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py`
    - `grep -q 'from sft_knowledge.memory import QdrantLongTermMemory' packages/sft-agents/src/sft_agents/memory/__init__.py`
    - `grep -q 'LongTermMemory =' packages/sft-agents/src/sft_agents/memory/__init__.py`
    - `python -c "from sft_agents.memory import LongTermMemory; print(LongTermMemory.__name__)"` prints either "QdrantLongTermMemory" or "StubLongTermMemory" (no exception)
    - `nx run sft-knowledge:test --args="-k 'test_qdrant_long_term_memory or test_store_raises_not_implemented or test_default_role_is_operator or test_sft_agents_memory_swap' -v"` exits 0
    - `nx run sft-agents:test` still exits 0 (Phase 4 tests not broken by the import swap)
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-k test_qdrant_long_term_memory -v" &amp;&amp; nx run sft-agents:test --args="-x -q"</automated>
  </verify>
  <done>QdrantLongTermMemory ships, D-59 stub swap committed with graceful ImportError fallback, Phase 4 sft-agents tests still green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| RagSearchTool → user_roles input | user_roles is provided by caller (agent); ROLE_TO_ACL is constant in code; pre-filter applied at Qdrant engine — no Python post-filter |
| TraverseGraphTool → seed_id input | seed_id is user-provided; passed as $param to Cypher (never interpolated); seed_label restricted to Literal whitelist |
| QdrantLongTermMemory.store | Explicitly raises NotImplementedError — enforces ARCHITECTURE.md anti-pattern (agents never write to knowledge stores) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-09-01 | Information Disclosure (ACL bypass) | RetrievalPipeline | mitigate | Pre-filter at Qdrant engine; test_operator_cannot_see_restricted (KNW-06 SC#2) verifies zero leak; build_acl_filter raises ValueError if no role match (fail-closed) |
| T-05-09-02 | Tampering (Cypher injection) | TraverseGraphTool | mitigate | Pydantic Literal whitelist for label + relations; $param for seed_id; source-scan test test_traverse_tool_uses_param_for_seed_id blocks f-string data interpolation |
| T-05-09-03 | Elevation of Privilege (write to knowledge) | QdrantLongTermMemory.store | mitigate | store() raises NotImplementedError; agent code that tries to write fails loudly with clear error pointing at services/knowledge-ingest |
| T-05-09-04 | Tampering (RagSearchInput extra args) | RagSearchTool | mitigate | Pydantic frozen+extra=forbid rejects unknown args; type checks reject wrong-type args |
| T-05-09-05 | Denial of Service | RetrievalPipeline | mitigate | k ≤ 20 (Pydantic Field ge=1, le=20); rerank fp16 capped batch; query_points limit=20 prefetch |
| T-05-09-SC | Tampering | npm/pip install | mitigate | All deps already declared in Plan 05-01 pyproject; Approved per RESEARCH legitimacy audit |
</threat_model>

<verification>
- `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -v"` exits 0 (all unit tests)
- `nx run sft-knowledge:test --args="-m integration -k 'test_operator_cannot_see_restricted or test_hybrid_retrieval_returns_ranked' -v"` exits 0 (SC#2 + KNW-09)
- `nx run sft-knowledge:test --args="--collect-only -k test_it_query_returns_en_sop"` collects the SC#1 cross-lingual test
- `nx run sft-agents:test` exits 0 (Phase 4 unaffected by memory swap)
- KNW-06 SC#2 + KNW-09 + Phase 5 SC#1 critical-path gates closed
- D-59 stub swap atomic: Phase 4 imports of `LongTermMemory` continue to work; agents now hit real RAG when sft-knowledge is installed
</verification>

<success_criteria>
- 4 atomic commits: `feat(05-09-...):` × 3 + `test(05-09-...):` × 1
- KNW-06 + KNW-09 requirements closed
- Phase 5 SC#1 (cross-lingual E2E) test exists and passes on GPU runners
- Phase 5 SC#2 (ACL non-leak) test exists and passes
- Phase 4 D-59 memory stub replaced by real QdrantLongTermMemory with graceful fallback
- Public API surface (`__init__.py`) now complete for Phase 5: parsers, chunking, embedding, stores, retrieval, tools, memory
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-09-retrieval-pipeline-tools-memory-SUMMARY.md` when done with: SC#1 + SC#2 test results, ROLE_TO_ACL mapping, RagSearchInput/TraverseGraphInput schemas, D-59 memory swap confirmation.
</output>
