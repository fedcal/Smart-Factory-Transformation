---
phase: 5
plan: 05-09
subsystem: knowledge-layer
tags: [retrieval, rag, langchain, memory, acl, cross-lingual]
requires:
  - 05-04-qdrant-bootstrap
  - 05-05-neo4j-compose-bootstrap
  - 05-07-embedding-chunking
  - 05-08-indexer-graph-builder
provides:
  - BgeReranker
  - RetrievalPipeline
  - ROLE_TO_ACL
  - build_acl_filter
  - RagSearchTool
  - RagSearchInput
  - TraverseGraphTool
  - TraverseGraphInput
  - QdrantLongTermMemory
  - QdrantLongTermMemoryConfig
affects:
  - sft_agents.memory.LongTermMemory (alias swap D-59 → D-70)
tech-stack:
  added:
    - FlagEmbedding.FlagReranker (BAAI/bge-reranker-v2-m3)
    - langchain_core.tools.BaseTool (already in sft-knowledge deps)
  patterns:
    - lazy_singleton_lru_cache (reranker model)
    - async_only_basetool (Shared Pattern 7)
    - acl_pre_filter_engine_level (T-05-09-01 fail-closed)
    - parametrized_cypher_with_literal_whitelist (T-05-09-02)
    - graceful_import_fallback (sft_agents.memory)
key-files:
  created:
    - packages/sft-knowledge/src/sft_knowledge/retrieval/__init__.py
    - packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py
    - packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py
    - packages/sft-knowledge/src/sft_knowledge/tools/__init__.py
    - packages/sft-knowledge/src/sft_knowledge/tools/rag.py
    - packages/sft-knowledge/src/sft_knowledge/tools/graph.py
    - packages/sft-knowledge/src/sft_knowledge/memory/__init__.py
    - packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py
    - packages/sft-knowledge/tests/test_qdrant_long_term_memory.py
  modified:
    - packages/sft-knowledge/src/sft_knowledge/__init__.py
    - packages/sft-knowledge/tests/test_retrieval_pipeline.py
    - packages/sft-knowledge/tests/test_acl_enforcement.py
    - packages/sft-knowledge/tests/test_crosslingual_e2e.py
    - packages/sft-agents/src/sft_agents/memory/__init__.py
    - packages/sft-agents/tests/test_long_term_stub.py
decisions:
  - "D-63 LOCKED ROLE_TO_ACL constant inlined in retrieval/pipeline.py; build_acl_filter raises ValueError on empty roles (fail-closed T-05-09-01)"
  - "D-66 LOCKED args_schema (RagSearchInput, TraverseGraphInput) with frozen+forbid; Literal whitelists for category, lang, seed_label, relation_path"
  - "Pipeline/driver injected via PrivateAttr to satisfy BaseTool's pydantic v2 strict field model"
  - "TraverseGraphTool builds Cypher with seed_label and rel_pipe via f-string (Literal-validated → safe) but seed_id ALWAYS as $param (T-05-09-02)"
  - "QdrantLongTermMemory.store() raises NotImplementedError pointing to services/knowledge-ingest (T-05-09-03 ARCHITECTURE.md anti-pattern)"
  - "sft_agents.memory.__init__ swap uses try/except ImportError graceful fallback to preserve Phase 4 test fixtures running without sft-knowledge"
metrics:
  duration_minutes: ~25
  tasks_completed: 4
  files_created: 9
  files_modified: 6
  commits: 4
  unit_tests_added: 25
  integration_tests_added: 6
  gpu_tests_added: 1
  completed_date: "2026-05-19"
---

# Phase 5 Plan 09: Retrieval Pipeline + Tools + Memory Summary

JWT-style closing-plan del knowledge layer: BgeReranker + RetrievalPipeline (single-shot Qdrant Prefetch+RRF) + due LangChain BaseTool (RagSearchTool, TraverseGraphTool) + QdrantLongTermMemory che rimpiazza il D-59 stub Phase 4.

## Tasks Executed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | BgeReranker + RetrievalPipeline + ACL pre-filter | `f256210` | done |
| 2 | RagSearchTool + TraverseGraphTool (injection-safe Cypher) | `e599afe` | done |
| 3 | Cross-lingual E2E test (SC#1) | `44d939f` | done |
| 4 | QdrantLongTermMemory + D-59 stub swap | `6d549fd` | done |

## Acceptance Gates Closed

- **KNW-06 SC#2 (ACL non-leak)**: `test_operator_cannot_see_restricted` + `test_technician_can_see_internal` + `test_manager_can_see_restricted` (integration, marked) — pre-filter applicato a livello engine Qdrant tramite `Filter(must=[FieldCondition(acl_level, MatchAny(any=[...]))])`.
- **KNW-09 (hybrid retrieval ranked + scores ∈ [0,1])**: `test_hybrid_retrieval_returns_ranked` integration test verifica monotonic descending scores + range [0,1].
- **Phase 5 SC#1 (cross-lingual E2E)**: `test_it_query_returns_en_sop` collected, marked `integration` + `gpu`. Gate binario "≥1 EN SOP" — rigorous A/B Recall@10 ≥ 0.70 lives in Plan 05-10.

## Public API Surface (sft-knowledge)

```python
from sft_knowledge import (
    # retrieval
    BgeReranker, RetrievalPipeline, ROLE_TO_ACL, build_acl_filter,
    # tools
    RagSearchTool, RagSearchInput, TraverseGraphTool, TraverseGraphInput,
    # memory
    QdrantLongTermMemory, QdrantLongTermMemoryConfig,
    # already present
    DocumentParser, MarkdownParser, ParsedDoc, ParsedSection,
    GraphNode, RagCitation, BgeM3Embedder, EncodeOutput,
    SemanticChunker, Chunk, QdrantIndexer, point_id, Neo4jGraphBuilder,
)
```

## D-63 LOCKED ROLE_TO_ACL Mapping

```python
ROLE_TO_ACL = {
    "operator":   frozenset({"public"}),
    "technician": frozenset({"public", "internal"}),
    "supervisor": frozenset({"public", "internal"}),
    "manager":    frozenset({"public", "internal", "restricted"}),
    "engineer":   frozenset({"public", "internal", "restricted"}),
    "safety":     frozenset({"public", "internal", "restricted"}),
}
```

`build_acl_filter([])` → `ValueError` (fail-closed). `build_acl_filter(["NOT_A_ROLE"])` → `ValueError`.

## D-66 LOCKED Tool Schemas

### `RagSearchInput` (frozen + extra=forbid)
- `query: str`
- `user_roles: list[str]`
- `category: Literal["sop","manuals","troubleshooting","training"]` (default "sop")
- `k: int = Field(ge=1, le=20)` (default 5)
- `lang: Literal["it","en"] | None` (default None — cross-lingual)
- `sop_ids: list[str] | None`
- `asset_family: str | None`
- `rerank: bool = True`

### `TraverseGraphInput` (frozen + extra=forbid)
- `seed_label: Literal["Machine","Part","FailureMode","SOP"]`
- `seed_id: str` — passato come `$seed_id` parametro Cypher (mai f-string)
- `relation_path: list[Literal["HAS_PART","HAS_FAILURE_MODE","DOCUMENTED_BY"]]`
- `max_depth: int = Field(ge=1, le=5)` (default 3)

## D-59 Memory Swap Confirmation

```python
# packages/sft-agents/src/sft_agents/memory/__init__.py — Phase 5 swap
try:
    from sft_knowledge.memory import QdrantLongTermMemory
    LongTermMemory = QdrantLongTermMemory
except ImportError:
    from sft_agents.memory.long_term_stub import StubLongTermMemory
    LongTermMemory = StubLongTermMemory
```

Verifica end-to-end: `python -c "from sft_agents.memory import LongTermMemory; print(LongTermMemory.__name__)"` → `QdrantLongTermMemory` (con sft-knowledge installato).

## Test Results

```
sft-knowledge unit tests:     62 passed (markers: not integration and not gpu)
sft-agents test suite:        301 passed, 2 skipped
cross-lingual e2e:            1 collected (skip outside GPU runner)
ACL integration (KNW-06 #2):  3 collected (require Qdrant testcontainer)
hybrid retrieval (KNW-09):    3 collected (require Qdrant testcontainer)
```

## Threat Flags

Nessuna nuova superficie di minaccia oltre quelle già registrate nel `<threat_model>` del plan (T-05-09-01..05 mitigate). Le scrivibilità su Qdrant sono mantenute esclusivamente nel ingest path (Plan 05-10), mai negli agenti.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Update Phase 4 test_long_term_memory_alias_points_to_stub**
- **Found during:** Task 4 verification (sft-agents test suite)
- **Issue:** Phase 4 test asserted `LongTermMemory is StubLongTermMemory` — questo conflitto è **intenzionalmente prodotto** dal task 4 swap (D-70 replaces D-59).
- **Fix:** Renamed test → `test_long_term_memory_alias_resolves_to_swap_target`. Ora accetta sia `StubLongTermMemory` (env senza sft-knowledge) sia `QdrantLongTermMemory` (env Phase 5).
- **Files modified:** `packages/sft-agents/tests/test_long_term_stub.py`
- **Commit:** `6d549fd` (incluso nello stesso commit del Task 4)

**2. [Rule 3 - Blocking] pytest-asyncio missing on first run**
- **Found during:** Task 1 test invocation
- **Issue:** `uv run pytest` su sft-knowledge mancava `pytest_asyncio` (estensione "dev" non sincronizzata).
- **Fix:** `uv sync --extra dev` installa pytest + pytest-asyncio + testcontainers + docker. Nessun side-effect sul codice sorgente — solo virtualenv populated.
- **Files modified:** none (operazione di env, non committed)

### Notes su scelte implementative

- `BaseTool` di langchain-core 1.4 è ancora un `RunnableSerializable` pydantic v2; gli attributi non-tool (pipeline, driver) richiedono `PrivateAttr` per non finire nell'args_schema. Soluzione implementata in entrambi i tool.
- `relation_path` vuoto in `TraverseGraphTool._arun` → ritorna `[]` invece di costruire una Cypher invalida.
- Lo stub `_FastEmbedAdapter` di Plan 05-07 non espone `tokenizer` → `RetrievalPipeline` cade in degraded-mode dense-only (warning loggato) invece di crashare. Ammesso esplicitamente nei test integration via `_StubEmbedder` che lascia `sparse_weights=[{}]` → la pipeline costruisce solo il Prefetch dense.

## Auth Gates

Nessuno. Tutti i task autonomi, nessun blocco di autenticazione richiesto.

## Known Stubs

Nessuno stub in questo plan. Tutto il codice produttivo wired end-to-end. Il `_StubEmbedder` / `_StubReranker` / `_StubPipeline` sono **test doubles** isolati in `tests/`, non finiscono nel runtime.

## Self-Check: PASSED

**Files verified to exist:**
- `packages/sft-knowledge/src/sft_knowledge/retrieval/__init__.py` — FOUND
- `packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py` — FOUND
- `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py` — FOUND
- `packages/sft-knowledge/src/sft_knowledge/tools/__init__.py` — FOUND
- `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` — FOUND
- `packages/sft-knowledge/src/sft_knowledge/tools/graph.py` — FOUND
- `packages/sft-knowledge/src/sft_knowledge/memory/__init__.py` — FOUND
- `packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py` — FOUND
- `packages/sft-knowledge/tests/test_qdrant_long_term_memory.py` — FOUND

**Commits verified in git log:**
- `f256210` — FOUND (feat 05-09 retrieval + reranker + ACL)
- `e599afe` — FOUND (feat 05-09 tools rag + graph)
- `44d939f` — FOUND (test 05-09 cross-lingual e2e)
- `6d549fd` — FOUND (feat 05-09 memory + sft-agents swap)
