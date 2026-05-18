---
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
mapped_at: "2026-05-18"
files_analyzed: 38
analogs_found: 36
---

# Phase 5: Knowledge Layer (RAG + Graph) — Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 38 new/modified files
**Analogs found:** 36 / 38

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `packages/sft-knowledge/pyproject.toml` | config | — | `packages/sft-tools/pyproject.toml` | exact |
| `packages/sft-knowledge/project.json` | config | — | `packages/sft-tools/project.json` | exact |
| `packages/sft-knowledge/src/sft_knowledge/__init__.py` | config | — | `packages/sft-tools/src/sft_tools/__init__.py` | exact |
| `packages/sft-knowledge/src/sft_knowledge/parsers/base.py` | model | transform | `packages/sft-agents/src/sft_agents/sdk/memory.py` (ABC pattern) | role-match |
| `packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py` | parser | file-I/O | `scripts/validate-corpus-frontmatter.py` | role-match |
| `packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py` | service | transform | `packages/sft-tools/src/sft_tools/replay/cmapss.py` (batch CPU transform) | partial |
| `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py` | service | batch | `packages/sft-tools/src/sft_tools/replay/cmapss.py` (lazy load + lru_cache) | partial |
| `packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py` | store | CRUD | `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` | role-match |
| `packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py` | store | CRUD | `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` | role-match |
| `packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py` | service | request-response | `packages/sft-tools/src/sft_tools/timescale/query.py` (async wrapper) | partial |
| `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py` | service | request-response | `packages/sft-tools/src/sft_tools/timescale/query.py` | role-match |
| `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` | tool | request-response | `packages/sft-tools/src/sft_tools/timescale/query.py` | exact |
| `packages/sft-knowledge/src/sft_knowledge/tools/graph.py` | tool | request-response | `packages/sft-tools/src/sft_tools/timescale/query.py` | exact |
| `packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py` | memory | request-response | `packages/sft-agents/src/sft_agents/memory/long_term_stub.py` | exact |
| `packages/sft-knowledge/src/sft_knowledge/models.py` | model | — | `packages/sft-agents/src/sft_agents/models/evidence.py` | exact |
| `packages/sft-knowledge/tests/conftest.py` | test | — | `packages/sft-agents/tests/conftest.py` | exact |
| `packages/sft-knowledge/tests/test_markdown_parser.py` | test | — | `packages/sft-domain/tests/test_glossary_loader.py` | role-match |
| `packages/sft-knowledge/tests/test_semantic_chunker.py` | test | — | `packages/sft-tools/tests/test_replay_cmapss.py` | role-match |
| `packages/sft-knowledge/tests/test_qdrant_indexer.py` | test | — | `services/ot-bridge/tests/test_writer.py` | role-match |
| `packages/sft-knowledge/tests/test_neo4j_builder.py` | test | — | `services/ot-bridge/tests/test_writer.py` | role-match |
| `packages/sft-knowledge/tests/test_retrieval_e2e.py` | test | — | `packages/sft-agents/tests/test_hitl_cycle.py` | role-match |
| `services/knowledge-ingest/pyproject.toml` | config | — | `services/ot-bridge/pyproject.toml` | exact |
| `services/knowledge-ingest/project.json` | config | — | `services/ot-bridge/project.json` | exact |
| `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py` | service | batch | `services/ot-bridge/src/svc_ot_bridge/main.py` | role-match |
| `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py` | service | batch | `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` | role-match |
| `services/knowledge-ingest/src/svc_knowledge_ingest/state.py` | store | CRUD | `packages/sft-agents/src/sft_agents/audit/pg_writer.py` | role-match |
| `services/knowledge-ingest/scripts/generate_rag_testset.py` | utility | batch | `scripts/validate-corpus-frontmatter.py` | role-match |
| `services/knowledge-ingest/scripts/run_ab_eval.py` | utility | batch | `scripts/validate-corpus-frontmatter.py` | role-match |
| `services/knowledge-ingest/scripts/spot_check_testset.py` | utility | batch | `scripts/validate-corpus-frontmatter.py` | role-match |
| `packages/sft-domain/failure_modes.yaml` + loader | model | file-I/O | `packages/sft-assets/src/sft_assets/_loader.py` | exact |
| `packages/sft-agents/src/sft_agents/memory/__init__.py` (swap D-59) | config | — | `packages/sft-agents/src/sft_agents/memory/long_term_stub.py` | exact |
| `infra/compose/core.yml` (add Neo4j) | config | — | existing Qdrant service block in `infra/compose/core.yml` | exact |
| `infra/migrations/timescale/006_create_ingest_state.sql` | migration | CRUD | `infra/migrations/timescale/004_create_budget_executions.sql` | exact |
| `simulators/synthetic-corpus/**/*.md` (add `acl_level`) | utility | file-I/O | `scripts/validate-corpus-frontmatter.py` (frontmatter manipulation) | role-match |
| `.github/workflows/reindex.yml` | config | event-driven | `.github/workflows/ci.yml` | role-match |
| `scripts/qdrant-bootstrap.py` | utility | batch | `scripts/nats-bootstrap-streams.py` | exact |
| `scripts/neo4j-bootstrap.py` | utility | batch | `scripts/timescale-migrate.py` + `scripts/nats-bootstrap-streams.py` | exact |
| `scripts/migrate-sop-acl.py` | utility | file-I/O | `scripts/validate-corpus-frontmatter.py` | role-match |

---

## Pattern Assignments

### `packages/sft-knowledge/pyproject.toml` (config)

**Analog:** `packages/sft-tools/pyproject.toml`

**Full pattern** (`packages/sft-tools/pyproject.toml` lines 1-30):
```toml
[project]
name = "sft-tools"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
description = "..."
dependencies = [
  "pydantic>=2.13.4",
  "langchain-core>=1.0,<2.0",
  ...
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/sft_tools"]

[tool.uv.sources]
sft-agents = { workspace = true }
sft-domain  = { workspace = true }

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
  "integration: requires docker / testcontainers",
  "gpu: requires CUDA GPU",
]
```

**Phase 5 additions for sft-knowledge:**
- `name = "sft-knowledge"`
- Add heavy deps: `qdrant-client[fastembed]>=1.16`, `FlagEmbedding>=1.3`, `llama-index-core>=0.11`, `llama-index-embeddings-huggingface>=0.3`, `neo4j>=5.24,<7`, `python-frontmatter>=1.1`, `langchain-core>=1.0,<2.0`
- Add marker `"gpu: requires CUDA — skipped on CI CPU runner"`
- `[tool.uv.sources]` entries for `sft-agents`, `sft-domain`, `sft-assets`

---

### `packages/sft-knowledge/project.json` (config)

**Analog:** `packages/sft-tools/project.json` (lines 1-23)

```json
{
  "name": "sft-knowledge",
  "$schema": "../../node_modules/nx/schemas/project-schema.json",
  "projectType": "library",
  "sourceRoot": "packages/sft-knowledge/src",
  "targets": {
    "test": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "command": "uv run pytest packages/sft-knowledge/tests -x -v",
        "cwd": "packages/sft-knowledge"
      }
    },
    "lint": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "command": "uv run ruff check src",
        "cwd": "packages/sft-knowledge"
      }
    }
  },
  "implicitDependencies": ["sft-domain", "sft-assets", "sft-agents"]
}
```

---

### `packages/sft-knowledge/src/sft_knowledge/__init__.py` (public API)

**Analog:** `packages/sft-tools/src/sft_tools/__init__.py` (lines 1-24)

**Full pattern:**
```python
"""sft-tools: LangChain Tools cross-cutting per Phase 4+ agents.

Espone:
    REPLAY_TOOLS        — lista [ReplayCMAPSSTool(), ReplayUCITool()]
    ...
"""
from sft_tools.replay import REPLAY_TOOLS, ReplayCMAPSSTool, ReplayRecord, ReplayUCITool
from sft_tools.timescale import TIMESCALE_TOOLS, QueryTimescaleTool

__all__ = [...]
```

**Apply to sft-knowledge:** Copy module-level docstring listing public exports, then flat re-export from each sub-package. The D-70 public API is:
```python
from sft_knowledge.parsers import DocumentParser, MarkdownParser, ParsedDoc
from sft_knowledge.chunking import SemanticChunker
from sft_knowledge.embedding import BgeM3Embedder
from sft_knowledge.stores import QdrantIndexer, Neo4jGraphBuilder
from sft_knowledge.retrieval import RetrievalPipeline, BgeReranker
from sft_knowledge.tools import RagSearchTool, TraverseGraphTool
from sft_knowledge.memory import QdrantLongTermMemory

__all__ = [...]
```

---

### `packages/sft-knowledge/src/sft_knowledge/parsers/base.py` (ABC, transform)

**Analog:** `packages/sft-agents/src/sft_agents/sdk/memory.py` (lines 1-37) — ABC with `@abstractmethod`

**ABC pattern** (lines 1-37):
```python
"""Memory ABC interface (CORE-01, D-59)."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from sft_agents.models.memory_record import MemoryRecord

class Memory(ABC):
    @abstractmethod
    async def query(self, query: str, k: int = 5,
                    filters: dict[str, Any] | None = None) -> list[MemoryRecord]: ...
    @abstractmethod
    async def store(self, record: MemoryRecord) -> str: ...
```

**Apply to `parsers/base.py`:**
- Same `from __future__ import annotations` + `from abc import ABC, abstractmethod`
- Pydantic models `ParsedSection` + `ParsedDoc` with `model_config = {"frozen": True, "extra": "forbid"}` — copy from `packages/sft-agents/src/sft_agents/models/evidence.py` lines 27-35
- `DocumentParser(ABC)` with `@abstractmethod async def parse(self, path: Path) -> ParsedDoc` + `@abstractmethod def supported_extensions(self) -> set[str]`

---

### `packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py` (parser, file-I/O)

**Analog:** `scripts/validate-corpus-frontmatter.py` (lines 1-210) — frontmatter parsing + heading regex + status filter

**Imports pattern** (lines 28-36):
```python
import frontmatter
import re
import sys
from pathlib import Path
```

**Frontmatter parsing pattern** (lines 76-80):
```python
post = frontmatter.load(str(md_path))
# post.metadata is a dict — validate required keys
# post.content is the Markdown body after frontmatter block
```

**Heading regex pattern** (lines 50-52):
```python
H2_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
# For heading_path state machine: track current H2/H3 as you scan body char offsets
```

**Status filter (D-67):** Skip files where `post.metadata.get("status") != "reviewed"` — log with `structlog.get_logger(__name__).info("sop_skipped_draft", path=..., status=...)`

**ACL default fallback:** If `acl_level` missing → log WARN + default `"internal"` (never `restricted`).

**Error handling pattern** (lines 77-80):
```python
try:
    post = frontmatter.load(str(md_path))
except Exception as exc:
    errors.append(f"{rel}: ERROR parsing frontmatter: {exc}")
    return errors
```

---

### `packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py` (service, transform)

**Analog:** `packages/sft-tools/src/sft_tools/replay/cmapss.py` — batch CPU transform, lazy dependency load pattern

**Lazy import + singleton pattern** (lines 95-103 in cmapss.py):
```python
def _load_asset_list() -> list[str]:
    try:
        from sft_assets import load_assets
        assets = load_assets()
        return [a.asset_id for a in assets]
    except ImportError:
        return list(_FALLBACK_ASSET_LIST)
```

**Apply to `semantic.py`:** Wrap `SemanticSplitterNodeParser` in a lazy-initialized singleton (not `lru_cache` — splitter has state). Use `functools.lru_cache` on the `HuggingFaceEmbedding` loader:
```python
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_embed_model() -> "HuggingFaceEmbedding":
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    return HuggingFaceEmbedding(
        model_name="BAAI/bge-m3",
        device=os.environ.get("BGE_M3_DEVICE", "cpu"),
        embed_batch_size=10,
    )
```

**Async-first pattern:** `_arun` primary, `_run` raises `NotImplementedError` (copy from `packages/sft-tools/src/sft_tools/timescale/query.py` lines 72-84).

---

### `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py` (service, batch)

**Analog:** `packages/sft-assets/src/sft_assets/_loader.py` lines 22-49 — `@lru_cache(maxsize=1)` singleton + explicit error on missing dep

**Lazy singleton pattern:**
```python
from __future__ import annotations
import os
from functools import lru_cache

@lru_cache(maxsize=1)
def _get_model() -> "BGEM3FlagModel":
    try:
        from FlagEmbedding import BGEM3FlagModel
        return BGEM3FlagModel(
            "BAAI/bge-m3",
            use_fp16=True,
            device=os.environ.get("BGE_M3_DEVICE", "cpu"),
        )
    except ImportError:
        # FastEmbed fallback (D-70 discretion)
        try:
            from fastembed import TextEmbedding
            return TextEmbedding("BAAI/bge-m3")
        except ImportError:
            raise RuntimeError(
                "Neither FlagEmbedding nor fastembed available. "
                "Install sft-knowledge[gpu] or sft-knowledge[cpu]."
            )
```

**Error handling:** Re-raise with descriptive message — never silently swallow (security.md).

---

### `packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py` (store, CRUD)

**Analog:** `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` — module-constant SQL/query, asyncpg pool pattern, batch upsert

**Module-constant query pattern** (timescale_writer.py lines 28-34):
```python
# SQL parametrizzato — COSTANTE modulo, zero f-string (T-03-04-sql, T-V5-sql)
_INSERT_SQL = (
    "INSERT INTO sensor_events "
    "(asset_id, tag_id, timestamp_utc, value, unit, quality_code, source) "
    "VALUES ($1, $2, $3, $4, $5, $6, $7)"
)
```

**Apply to `qdrant.py`:** Collection names as module-level constants, no f-string in Qdrant API calls. Qdrant `query_points` calls use typed objects only (Prefetch, FusionQuery, Filter, FieldCondition, MatchAny — all constructed from typed data, never string-interpolated collection names beyond the Literal enum).

**Batch upsert pattern** (timescale_writer.py lines 92-101):
```python
async def push(self, event: SensorEvent) -> None:
    async with self._lock:
        self._buffer.append(event)
        if len(self._buffer) >= self._batch_size:
            await self._flush_locked()
```

**Apply to `qdrant.py`:** `QdrantIndexer.upsert_batch(points: list[PointStruct], batch_size: int = 100)` accumulates and flushes in batches of 100 (D-70 discretion).

**Structlog pattern** (timescale_writer.py lines 26-27):
```python
logger = structlog.get_logger(__name__)
logger.info("timescale_writer_started", dsn_prefix=self._dsn[:20])
```

**Idempotent bootstrap pattern** (RESEARCH.md §1 lines 170-178 — verified pattern):
```python
existing = {c.name for c in (await client.get_collections()).collections}
if collection_name not in existing:
    await client.create_collection(
        collection_name=collection_name,
        vectors_config={...},
        sparse_vectors_config={...},
    )
# Payload indexes: create_payload_index is idempotent — no error on re-run
await client.create_payload_index(
    collection_name=collection_name,
    field_name="acl_level",
    field_schema=PayloadSchemaType.KEYWORD,
)
```

---

### `packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py` (store, CRUD)

**Analog:** `packages/sft-agents/src/sft_agents/audit/pg_writer.py` — module-constant parameterized query, structured error handling, contextual structlog

**Module-constant Cypher pattern** (pg_writer.py lines 36-44):
```python
# SQL parameterized constant — T-V5-sql (zero f-string interpolation).
_INSERT_SQL: str = (
    "INSERT INTO audit.actions ..."
    "VALUES ($1, $2, ...)"
)
```

**Apply to `neo4j.py`:** Cypher statements as module-level constants. ONLY `$param` placeholders, never f-string for node labels beyond Literal-validated whitelist (D-65 + D-66 design):
```python
# Module-level Cypher constants — ZERO f-string interpolation
_MERGE_SOP_CYPHER = """
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
```

**Async driver pattern** (D-65):
```python
from neo4j import AsyncGraphDatabase
async with AsyncGraphDatabase.driver(uri, auth=auth) as driver:
    async with driver.session(database="neo4j") as session:
        await session.run(_MERGE_SOP_CYPHER, sop_rows=rows)
```

**Error handling** (pg_writer.py lines 87-115):
```python
try:
    async with self._pool.acquire() as conn:
        await conn.execute(_INSERT_SQL, ...)
except Exception as exc:
    logger.error("audit_pg_insert_failed", error=str(exc), ...)
    raise  # always re-raise — D-56 invariant
```

---

### `packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py` (service, request-response)

**Analog:** `packages/sft-tools/src/sft_tools/timescale/query.py` — async-only, sync wrapping with `asyncio.to_thread`

**Async-only pattern** (query.py lines 72-84):
```python
def _run(self, ...) -> pd.DataFrame:
    """Sync _run e' disabilitato — usa async _arun."""
    raise NotImplementedError(
        "QueryTimescaleTool e' async-only. "
        "Usa `await tool.ainvoke({...})` o `await tool._arun(...)` invece di _run."
    )
```

**Sync-to-async bridge for CPU-bound reranker:**
```python
async def rerank(self, query: str, hits: list[ScoredPoint]) -> list[tuple[ScoredPoint, float]]:
    pairs = [(query, h.payload["text"]) for h in hits]
    # FlagReranker.compute_score is sync — bridge via asyncio.to_thread
    scores: list[float] = await asyncio.to_thread(
        self._reranker.compute_score, pairs, True  # normalize=True
    )
    ranked = sorted(zip(hits, scores), key=lambda x: -x[1])
    return list(ranked)
```

**Lazy singleton pattern** (same as bge_m3.py):
```python
@lru_cache(maxsize=1)
def _get_reranker() -> "FlagReranker":
    from FlagEmbedding import FlagReranker
    return FlagReranker(
        "BAAI/bge-reranker-v2-m3",
        use_fp16=True,  # auto fp32 on CPU (FlagEmbedding README)
        device=os.environ.get("BGE_M3_DEVICE", "cpu"),
    )
```

---

### `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py` (service, request-response)

**Analog:** `packages/sft-tools/src/sft_tools/timescale/query.py` — env-based config, single async method, structured return

**Environment config pattern** (query.py lines 107-114):
```python
dsn = os.environ["TIMESCALE_DSN"]  # Nessun default — security.md
conn = await asyncpg.connect(dsn, statement_cache_size=0)
```

**Apply:** `QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")` — with default for dev. `NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")`.

**Return type:** `list[RagCitation]` — copy `RagCitation` model from `packages/sft-agents/src/sft_agents/models/evidence.py` lines 60-79 (Phase 4 frozen schema, Phase 5 populates).

**ACL filter construction (D-63):**
```python
ROLE_TO_ACL: dict[str, frozenset[str]] = {
    "operator":   frozenset({"public"}),
    "technician": frozenset({"public", "internal"}),
    "supervisor": frozenset({"public", "internal"}),
    "manager":    frozenset({"public", "internal", "restricted"}),
    "engineer":   frozenset({"public", "internal", "restricted"}),
    "safety":     frozenset({"public", "internal", "restricted"}),
}
# Build immutable set (coding-style.md: no mutation)
allowed = frozenset().union(*(ROLE_TO_ACL.get(r, frozenset()) for r in user_roles))
acl_filter = Filter(must=[FieldCondition(
    key="acl_level", match=MatchAny(any=list(allowed))
)])
```

---

### `packages/sft-knowledge/src/sft_knowledge/tools/rag.py` (tool, request-response)

**Analog:** `packages/sft-tools/src/sft_tools/timescale/query.py` — LangChain BaseTool, async-only, Pydantic args_schema

**Full BaseTool pattern** (query.py lines 46-143):
```python
from __future__ import annotations
import os
from datetime import datetime, timezone
from typing import Any
import asyncpg
import pandas as pd
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from sft_tools.replay.models import QueryTimescaleArgs

UTC = timezone.utc

class QueryTimescaleTool(BaseTool):
    name: str = "query_timescale"
    description: str = (
        "Query TimescaleDB sensor_events hypertable..."
    )
    args_schema: type[BaseModel] = QueryTimescaleArgs

    def _run(self, ...) -> pd.DataFrame:
        raise NotImplementedError("...async-only...")

    async def _arun(self, ...) -> pd.DataFrame:
        dsn = os.environ["TIMESCALE_DSN"]
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
        try:
            records = await conn.fetch(sql, ...)
        finally:
            await conn.close()
        return df
```

**Apply to `rag.py`:**
- `name = "rag_search"` (D-66)
- `args_schema = RagSearchInput` — Pydantic `model_config = {"frozen": True, "extra": "forbid"}` (code_context Phase 5)
- `async def _arun(self, query, user_roles, category, k, lang, sop_ids, asset_family, rerank, **kwargs) -> list[RagCitation]`
- Langfuse span: `with langfuse_callback.trace(name="rag.search"):` — copy Langfuse wiring from `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py`

**Tool 1 input schema** (D-66 CONTEXT.md lines 306-323):
```python
from typing import Literal
from pydantic import BaseModel, Field

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
```

---

### `packages/sft-knowledge/src/sft_knowledge/tools/graph.py` (tool, request-response)

**Analog:** `packages/sft-tools/src/sft_tools/timescale/query.py` — same BaseTool pattern

**Tool 2 input schema** (D-66 CONTEXT.md lines 325-339):
```python
class TraverseGraphInput(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    seed_label: Literal["Machine", "Part", "FailureMode", "SOP"]
    seed_id: str
    relation_path: list[Literal["HAS_PART", "HAS_FAILURE_MODE", "DOCUMENTED_BY"]]
    max_depth: int = Field(default=3, ge=1, le=5)
```

**Parameterized Cypher (CRITICAL — D-66):**
The label comes from a Pydantic `Literal` whitelist (injection-safe) but `seed_id` MUST be a `$param`:
```python
# seed_label is Literal-validated → safe to interpolate in f-string label slot ONLY
# seed_id MUST remain a $param (never interpolated)
cypher = (
    f"MATCH (n:{input.seed_label} {{id: $seed_id}}) "
    f"-[:{rel_pipe}]->(m) RETURN m LIMIT $limit"
)
result = await session.run(cypher, seed_id=input.seed_id, limit=input.max_depth * 10)
```

**Pattern for async Neo4j session:**
```python
async with self._driver.session(database="neo4j") as session:
    result = await session.run(cypher, ...)
    records = [r.data() for r in await result.fetch(100)]
```

---

### `packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py` (memory, request-response)

**Analog:** `packages/sft-agents/src/sft_agents/memory/long_term_stub.py` (lines 1-75) — implements `Memory` ABC, frozen config, structlog

**ABC implementation pattern** (long_term_stub.py lines 44-74):
```python
class StubLongTermMemory(Memory):
    def __init__(self, config: StubLongTermMemoryConfig | None = None) -> None:
        self._config = config or StubLongTermMemoryConfig()
        logger.info("stub_long_term_memory_instantiated", note="...")

    async def query(self, query: str, k: int = 5,
                    filters: dict[str, Any] | None = None) -> list[MemoryRecord]:
        return []

    async def store(self, record: MemoryRecord) -> str:
        raise NotImplementedError("Phase 5 supplies QdrantLongTermMemory...")
```

**Apply:** Replace stub body — same class signature `QdrantLongTermMemory(Memory)`, same `__init__(config)` pattern, config uses `model_config = ConfigDict(frozen=True, extra="forbid")`. `query()` calls `RetrievalPipeline.search()`, converts hits to `MemoryRecord`. `store()` calls `QdrantIndexer.upsert()`.

**Config pattern:**
```python
from pydantic import BaseModel, ConfigDict

class QdrantLongTermMemoryConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    qdrant_url: str = "http://localhost:6333"
    collection_name: str = "sop"
    embedding_device: str = "cpu"
```

---

### `packages/sft-knowledge/src/sft_knowledge/models.py` (model)

**Analog:** `packages/sft-agents/src/sft_agents/models/evidence.py` (lines 1-130) — frozen Pydantic, `field_validator` for tz-aware datetime

**Pydantic v2 frozen + extra=forbid pattern** (evidence.py lines 27-35):
```python
class TokenUsage(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    input: Annotated[int, Field(ge=0, description="...")]
```

**tz-aware validator pattern** (evidence.py lines 17-24):
```python
def _tz_aware(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError(
            f"Datetime field must be tz-aware, got naive: {v!r}. "
            "Use datetime.now(timezone.utc)..."
        )
    return v
```

**GraphNode model (new):**
```python
class GraphNode(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    label: Literal["Machine", "Part", "FailureMode", "SOP"]
    node_id: str
    properties: dict[str, Any] = {}
```

**RagCitation** is already defined in `packages/sft-agents/src/sft_agents/models/evidence.py` lines 60-79. Phase 5 should import it from there rather than redefine:
```python
from sft_agents.models.evidence import RagCitation  # DO NOT redefine
```

---

### `packages/sft-knowledge/tests/conftest.py` (test)

**Analog:** `packages/sft-agents/tests/conftest.py` (lines 1-170) — mock fixtures for asyncpg, NATS, LLM; `pytest_configure` markers

**Marker registration pattern** (conftest.py lines 24-35):
```python
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: marks tests requiring docker compose / testcontainers",
    )
    config.addinivalue_line(
        "markers",
        "load: marks long-running load tests",
    )
```

**Add for Phase 5:**
```python
    config.addinivalue_line("markers", "gpu: marks tests requiring CUDA GPU")
```

**Testcontainers fixtures for Qdrant + Neo4j** (extend the docker-compose `compose_stack` pattern from `tests/conftest.py` lines 88-151). Phase 5 adds per-package testcontainer fixtures:
```python
@pytest.fixture(scope="session")
async def qdrant_client():
    from testcontainers.qdrant import QdrantContainer
    with QdrantContainer("qdrant/qdrant:v1.16.1") as container:
        from qdrant_client import AsyncQdrantClient
        client = AsyncQdrantClient(url=container.get_client_url())
        yield client

@pytest.fixture(scope="session")
async def neo4j_driver():
    from testcontainers.neo4j import Neo4jContainer
    with Neo4jContainer("neo4j:5.24-community") as container:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(
            container.get_connection_url(),
            auth=("neo4j", container.NEO4J_ADMIN_PASSWORD),
        )
        yield driver
        await driver.close()
```

**Mock asyncpg conn pattern** (conftest.py lines 55-91):
```python
@pytest.fixture
def mock_pool() -> AsyncMock:
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    ...
    return pool
```

---

### `packages/sft-knowledge/tests/test_markdown_parser.py` (test)

**Analog:** `packages/sft-domain/tests/test_glossary_loader.py` — file-based unit test, real YAML/MD files, no I/O mocks

**Pattern:** Load real SOP files from `simulators/synthetic-corpus/`, assert `ParsedDoc` fields. Use `pathlib.Path(__file__).parent.parent.parent...` traversal to locate corpus — same as `_WORKSPACE_ROOT` pattern in cmapss.py line 32.

---

### `services/knowledge-ingest/pyproject.toml` (config)

**Analog:** `services/ot-bridge/pyproject.toml` (lines 1-45)

**Full pattern:**
```toml
[project]
name = "svc-knowledge-ingest"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
description = "CLI ingest pipeline: parse → chunk → embed → upsert Qdrant + Neo4j MERGE"
dependencies = [
  "sft-knowledge",
  "sft-domain",
  "sft-assets",
  "asyncpg>=0.29",
  "typer>=0.12",
  "structlog>=24.4",
  "pydantic>=2.7",
]

[project.scripts]
knowledge-ingest = "svc_knowledge_ingest.__main__:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/svc_knowledge_ingest"]

[tool.uv.sources]
sft-knowledge = { workspace = true }
sft-domain    = { workspace = true }
sft-assets    = { workspace = true }

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = ["integration: requires testcontainers Qdrant+Neo4j+PG"]
```

---

### `services/knowledge-ingest/project.json` (config)

**Analog:** `services/ot-bridge/project.json` (lines 1-27)

```json
{
  "name": "knowledge-ingest",
  "$schema": "../../node_modules/nx/schemas/project-schema.json",
  "projectType": "application",
  "sourceRoot": "services/knowledge-ingest/src",
  "targets": {
    "run": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "command": "uv run python -m svc_knowledge_ingest",
        "cwd": "services/knowledge-ingest"
      }
    },
    "bootstrap": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "command": "uv run python -m svc_knowledge_ingest --mode=bootstrap",
        "cwd": "services/knowledge-ingest"
      }
    },
    "test": {
      "executor": "@nxlv/python:run-commands",
      "options": {
        "command": "uv run pytest",
        "cwd": "services/knowledge-ingest"
      }
    }
  },
  "implicitDependencies": ["sft-knowledge", "sft-domain", "sft-assets"]
}
```

---

### `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py` (CLI, batch)

**Analog:** `services/ot-bridge/src/svc_ot_bridge/main.py` (lines 1-212) — structlog JSON config at top, `asyncio.run(main())`, env var fail-fast, structured `logger.bind(service=...)`

**Structlog JSON config pattern** (main.py lines 30-41):
```python
import structlog
import sys

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)
logger = structlog.get_logger(__name__)
```

**Env var fail-fast pattern** (main.py lines 64-69):
```python
timescale_dsn = os.environ.get("TIMESCALE_DSN")
if timescale_dsn is None:
    raise RuntimeError(
        "TIMESCALE_DSN env var e' richiesto. "
        "Usa: postgresql://user:pass@timescaledb:5432/sft"
    )
```

**CLI pattern (Typer):** Use `typer` (D-70) instead of plain `asyncio.run`. Script pattern:
```python
import typer
app = typer.Typer()

@app.command()
def run(
    paths: list[str] = typer.Option([], "--paths", help="Paths to ingest"),
    files: list[str] = typer.Option([], "--files", help="Comma-separated file list"),
    mode: str = typer.Option("incremental", "--mode", help="incremental|bootstrap"),
) -> None:
    asyncio.run(_async_main(paths, files, mode))

if __name__ == "__main__":
    app()
```

---

### `services/knowledge-ingest/src/svc_knowledge_ingest/state.py` (store, CRUD)

**Analog:** `packages/sft-agents/src/sft_agents/audit/pg_writer.py` (lines 1-124) — module-constant parameterized SQL, asyncpg pool.acquire() pattern, re-raise on error

**SQL constant pattern** (pg_writer.py lines 36-44):
```python
_INSERT_SQL: str = (
    "INSERT INTO audit.actions ..."
    "VALUES ($1, $2, ...)"
)
```

**Apply to `state.py`:**
```python
# ZERO f-string interpolation — T-V5-sql
_UPSERT_SQL: str = (
    "INSERT INTO knowledge.ingest_state "
    "(source_uri, content_hash, version, indexed_at, chunk_count, collection, acl_level) "
    "VALUES ($1, $2, $3, NOW(), $4, $5, $6) "
    "ON CONFLICT (source_uri) DO UPDATE SET "
    "content_hash = $2, version = $3, indexed_at = NOW(), "
    "chunk_count = $4, collection = $5, acl_level = $6"
)

_SELECT_SQL: str = (
    "SELECT source_uri, content_hash, version, indexed_at "
    "FROM knowledge.ingest_state WHERE source_uri = $1"
)
```

**Pool pattern:**
```python
async with self._pool.acquire() as conn:
    await conn.execute(_UPSERT_SQL, source_uri, content_hash, version, ...)
```

---

### `infra/migrations/timescale/006_create_ingest_state.sql` (migration)

**Analog:** `infra/migrations/timescale/004_create_budget_executions.sql` (lines 1-37) — `CREATE SCHEMA IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, `DO $$ ... GRANT ... $$`

**Full pattern** (budget_executions.sql lines 11-37):
```sql
CREATE SCHEMA IF NOT EXISTS budget;

CREATE TABLE IF NOT EXISTS budget.executions (
  thread_id     TEXT             NOT NULL,
  ...
  PRIMARY KEY (thread_id, agent_id)
);

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_role') THEN
    GRANT USAGE ON SCHEMA budget TO agent_role;
    GRANT INSERT, SELECT, UPDATE ON budget.executions TO agent_role;
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE '004_create_budget_executions.sql GRANT block: %', SQLERRM;
END $$;
```

**Apply to `006_create_ingest_state.sql`:**
- Replace schema: `knowledge`
- Table definition from D-68 (CONTEXT.md lines 460-470)
- Same `DO $$ IF EXISTS (agent_role) THEN GRANT` block

---

### `scripts/qdrant-bootstrap.py` (utility, batch)

**Analog:** `scripts/nats-bootstrap-streams.py` (lines 1-219) — idempotent bootstrap with `--dry-run`, `argparse`, `asyncio.run(bootstrap(...))`, `try: add → except: update` idempotency

**CLI structure pattern** (nats-bootstrap-streams.py lines 41-61):
```python
WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="...", epilog=__doc__)
    parser.add_argument("--server", default=os.environ.get("NATS_URL", "nats://localhost:4222"))
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()
```

**Idempotency pattern** (nats-bootstrap-streams.py lines 186-205):
```python
try:
    await js.add_stream(config=cfg)
    print(f"OK [{cfg.name}]: stream created")
except nats.js.errors.BadRequestError:
    try:
        await js.update_stream(config=cfg)
        print(f"OK [{cfg.name}]: stream updated (config synced)")
    except Exception as upd_exc:
        print(f"ERROR [{cfg.name}]: update_stream failed: {upd_exc}", file=sys.stderr)
        return 1
```

**Apply to `qdrant-bootstrap.py`:**
- `--qdrant-url` arg (default `QDRANT_URL` env or `http://localhost:6333`)
- `existing = {c.name for c in (await client.get_collections()).collections}`
- `if collection_name not in existing: await client.create_collection(...)` — idempotent
- Create payload indexes after collection (always idempotent per Qdrant docs)
- Same `--dry-run` → print-only exit 0

---

### `scripts/neo4j-bootstrap.py` (utility, batch)

**Analog:** `scripts/timescale-migrate.py` (lines 1-93) — WORKSPACE_ROOT derivation, argparse, `asyncio.run(migrate(...))`, env DSN

**Script structure pattern** (timescale-migrate.py lines 36-93):
```python
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

def main() -> None:
    parser = argparse.ArgumentParser(description="...")
    parser.add_argument("--dsn", default=os.environ.get("TIMESCALE_DSN"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dsn and not args.dry_run:
        print("ERROR: --dsn is required...", file=sys.stderr)
        sys.exit(1)
    sys.exit(asyncio.run(migrate(dsn, args.dry_run)))
```

**Apply to `neo4j-bootstrap.py`:**
- `--neo4j-uri` (default `NEO4J_URI` env or `bolt://localhost:7687`)
- `--neo4j-auth` (default `NEO4J_AUTH` env or `neo4j/devpassword`)
- Idempotent Cypher constraints from D-65:
```python
_CONSTRAINTS = [
    "CREATE CONSTRAINT machine_id_unique IF NOT EXISTS FOR (m:Machine) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT part_id_unique IF NOT EXISTS FOR (p:Part) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT failure_mode_id_unique IF NOT EXISTS FOR (f:FailureMode) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT sop_id_unique IF NOT EXISTS FOR (s:SOP) REQUIRE s.id IS UNIQUE",
    "CREATE INDEX sop_version IF NOT EXISTS FOR (s:SOP) ON (s.version)",
]
```

---

### `scripts/migrate-sop-acl.py` (utility, file-I/O)

**Analog:** `scripts/validate-corpus-frontmatter.py` (lines 1-209) — WORKSPACE_ROOT, argparse, `frontmatter.load()` + write back, real corpus path traversal

**Corpus traversal pattern** (validate-corpus-frontmatter.py lines 153-156):
```python
all_md = sorted(corpus_dir.rglob("*.md"))
md_files = [f for f in all_md if FILENAME_PATTERN.match(f.name)]
```

**Frontmatter add field pattern:**
```python
post = frontmatter.load(str(md_path))
if "acl_level" not in post.metadata:
    # Create new metadata dict (immutable pattern — new object, not mutation)
    new_meta = {**post.metadata, "acl_level": "internal"}  # default per D-67
    updated_post = frontmatter.Post(post.content, **new_meta)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(updated_post))
    print(f"MIGRATED: {md_path.name} → acl_level: internal")
else:
    print(f"SKIP: {md_path.name} (acl_level already set: {post.metadata['acl_level']})")
```

---

### `packages/sft-domain/failure_modes.yaml` + loader (model, file-I/O)

**Analog:** `packages/sft-assets/src/sft_assets/_loader.py` (lines 1-101) — `yaml.safe_load`, `@lru_cache(maxsize=1)`, `tuple[FailureMode, ...]` immutable return, `invalidate_cache()`

**Loader pattern** (_loader.py lines 22-49):
```python
@lru_cache(maxsize=1)
def load_assets() -> tuple[Asset, ...]:
    if not _REGISTRY_PATH.exists():
        raise FileNotFoundError(...)
    raw_text = _REGISTRY_PATH.read_text(encoding="utf-8")
    raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load, mai yaml.load (T-03-01-yaml)
    if not isinstance(raw_data, list):
        raise ValueError(...)
    return tuple(Asset.model_validate(entry) for entry in raw_data)
```

**Apply to `failure_modes` loader:**
```python
_FAILURE_MODES_PATH = pathlib.Path(__file__).parent / "failure_modes.yaml"

@lru_cache(maxsize=1)
def load_failure_modes() -> tuple[FailureMode, ...]:
    raw = yaml.safe_load(_FAILURE_MODES_PATH.read_text(encoding="utf-8"))
    return tuple(FailureMode.model_validate(entry) for entry in raw["failure_modes"])
```

**Model pattern:**
```python
class FailureMode(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    id: str
    name_it: str
    name_en: str
    asset_families: list[str]
    parts: list[str]
    severity: Literal["low", "medium", "high"] = "medium"
```

---

### `infra/compose/core.yml` — Add Neo4j service (config)

**Analog:** Existing Qdrant service block in `infra/compose/core.yml` (lines 41-55)

**Service block pattern** (qdrant block lines 41-55):
```yaml
qdrant:
  image: qdrant/qdrant:v1.16.1
  volumes:
    - qdrant-data:/qdrant/storage
  ports:
    - "${QDRANT_PORT:-6333}:6333"
    - "6334:6334"
  healthcheck:
    test: ["CMD-SHELL", "wget -qO- http://localhost:6333/healthz | grep -q ok"]
    interval: 5s
    timeout: 5s
    retries: 10
  networks:
    - sft-core
  restart: unless-stopped
```

**Neo4j addition (D-65):**
```yaml
neo4j:
  image: neo4j:5.24-community
  environment:
    NEO4J_AUTH: "${NEO4J_AUTH:-neo4j/devpassword}"
    NEO4J_PLUGINS: '["apoc"]'
  volumes:
    - neo4j-data:/data
  ports:
    - "${NEO4J_BOLT_PORT:-7687}:7687"
    - "${NEO4J_HTTP_PORT:-7474}:7474"
  healthcheck:
    test: ["CMD-SHELL", "wget -qO- http://localhost:7474 | grep -q Neo4j"]
    interval: 10s
    timeout: 5s
    retries: 10
  networks:
    - sft-core
  restart: unless-stopped
```

Also add `neo4j-data:` to `volumes:` block.

---

### `.github/workflows/reindex.yml` (CI, event-driven)

**Analog:** `.github/workflows/ci.yml` (lines 1-80) — checkout v4 + uv setup + Node.js + nx run

**CI setup steps pattern** (ci.yml lines 22-79):
```yaml
- name: Checkout
  uses: actions/checkout@v4
  with:
    fetch-depth: 0

- name: Setup Node.js
  uses: actions/setup-node@v4
  with:
    node-version: 20
    cache: 'npm'

- name: Setup Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'

- name: Install uv
  uses: astral-sh/setup-uv@v5
  with:
    version: "0.6"
    enable-cache: true
```

**D-68 pattern for reindex.yml:**
```yaml
on:
  push:
    branches: [main]
    paths:
      - 'simulators/synthetic-corpus/**'
      - 'docs/sops/**'
      - 'packages/sft-domain/failure_modes.yaml'
  workflow_dispatch:

jobs:
  reindex:
    runs-on: ubuntu-latest
    services:
      qdrant: { image: qdrant/qdrant:v1.16.1, ports: ['6333:6333'] }
      neo4j:
        image: neo4j:5.24-community
        env: { NEO4J_AUTH: 'neo4j/cipassword' }
        ports: ['7687:7687']
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Compute changed files
        run: |
          git diff --name-only ${{ github.event.before }} ${{ github.sha }} \
            -- 'simulators/synthetic-corpus/**' 'docs/sops/**' \
            > changed.txt
      - name: Install uv + deps
        # ... (copy from ci.yml)
      - run: nx run knowledge-ingest:run --files=$(paste -sd, changed.txt)
```

---

### `services/knowledge-ingest/scripts/generate_rag_testset.py` (utility, batch)

**Analog:** `scripts/validate-corpus-frontmatter.py` (lines 38-61) — `WORKSPACE_ROOT = Path(__file__).parent.parent.parent`, argparse, real corpus traversal, `sys.exit(0 if success else 1)`

**Pattern:** Same argparse structure + WORKSPACE_ROOT derivation. Use LLM adapter from Phase 4 (`packages/sft-agents/src/sft_agents/llm/factory.py`) with `LLM_BACKEND=ollama` and `Qwen2.5-7B` for Q-gen. Seed with `random.seed(42)` (D-71).

---

## Shared Patterns

### 1. Pydantic v2 frozen + extra=forbid (ALL models)

**Source:** `packages/sft-agents/src/sft_agents/models/evidence.py` lines 27-35

```python
class TokenUsage(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}

    input: Annotated[int, Field(ge=0, description="Input prompt tokens")]
    output: Annotated[int, Field(ge=0, description="Generated output tokens")]
```

**Apply to:** Every Pydantic model in `sft-knowledge` — `ParsedSection`, `ParsedDoc`, `RagSearchInput`, `TraverseGraphInput`, `QdrantLongTermMemoryConfig`, `GraphNode`, `FailureMode`.

### 2. datetime.now(UTC) mandatory (ALL datetime fields)

**Source:** `packages/sft-agents/src/sft_agents/models/evidence.py` lines 17-24 + `services/ot-bridge/src/svc_ot_bridge/main.py` line 5

```python
from datetime import datetime, timezone
UTC = timezone.utc

def _tz_aware(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError(
            f"Datetime field must be tz-aware, got naive: {v!r}. "
            "Use datetime.now(timezone.utc)..."
        )
    return v
```

**Apply to:** All models with datetime fields (`ParsedDoc`, `GraphNode`). Use `@field_validator("ts")` pattern in MemoryRecord (already in `packages/sft-agents/src/sft_agents/models/memory_record.py` lines 27-31).

### 3. Parameterized SQL (asyncpg) — zero f-string (ALL asyncpg writes/reads)

**Source:** `services/ot-bridge/src/svc_ot_bridge/timescale_writer.py` lines 28-34 + `packages/sft-tools/src/sft_tools/timescale/query.py` lines 33-41

```python
# SQL base — SEMPRE $N placeholders, MAI f-string (T-03-02-sql)
_BASE_SQL = (
    "SELECT asset_id, tag_id AS sensor_id, timestamp_utc AS timestamp, value, unit "
    "FROM sensor_events "
    "WHERE asset_id = $1 AND timestamp_utc >= $2 AND timestamp_utc <= $3"
)
```

**Apply to:** `services/knowledge-ingest/src/svc_knowledge_ingest/state.py` — every SQL in `_UPSERT_SQL`, `_SELECT_SQL`, `_DELETE_SQL` must be a module-level constant string with `$N` placeholders only.

### 4. Parameterized Cypher — zero f-string for data, Literal-only for labels (ALL Neo4j)

**Source:** D-65 + D-66 (CONTEXT.md lines 341-346)

```python
# seed_label is Literal-validated → safe for f-string label slot ONLY
# ALL data values MUST be $param (never f-string interpolated)
cypher = (
    f"MATCH (n:{input.seed_label} {{id: $seed_id}})-[:{rel_pipe}]->(m) RETURN m LIMIT $limit"
)
result = await session.run(cypher, seed_id=input.seed_id, limit=...)
```

**Apply to:** `packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py` and `tools/graph.py`.

### 5. yaml.safe_load mandatory (ALL YAML loading)

**Source:** `packages/sft-assets/src/sft_assets/_loader.py` line 41

```python
raw_data = yaml.safe_load(raw_text)  # SEMPRE safe_load, mai yaml.load (T-03-01-yaml)
```

**Apply to:** `packages/sft-domain/failure_modes.yaml` loader + any YAML parsing in markdown parser (frontmatter lib wraps YAML parsing, but any direct `yaml` calls must use `safe_load`).

### 6. structlog JSON logging (ALL services and packages)

**Source:** `services/ot-bridge/src/svc_ot_bridge/main.py` lines 30-41 + `packages/sft-agents/src/sft_agents/audit/pg_writer.py` line 33

```python
import structlog
logger = structlog.get_logger(__name__)
# In module-level code or __main__.py:
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)
```

**Apply to:** Every module in `sft-knowledge` and `svc_knowledge_ingest`. `structlog.configure()` only in `__main__.py` / CLI entrypoints (not in library code).

### 7. async-only BaseTool (_run raises NotImplementedError)

**Source:** `packages/sft-tools/src/sft_tools/timescale/query.py` lines 72-84 + `packages/sft-agents/src/sft_agents/sdk/tool.py` lines 28-37

```python
def _run(self, *args: Any, **kwargs: Any) -> Any:
    """Disabled — Tool is async-only. Use `await tool.ainvoke({...})`."""
    raise NotImplementedError(
        f"{type(self).__name__} is async-only. "
        "Use `await tool.ainvoke({...})` or `await tool._arun(...)` instead."
    )

@abstractmethod
async def _arun(self, *args: Any, **kwargs: Any) -> Any:
    """Async tool implementation — subclasses provide concrete behavior."""
```

**Apply to:** `RagSearchTool._run()` and `TraverseGraphTool._run()` must raise `NotImplementedError` with matching message.

### 8. lru_cache singleton for expensive model loads

**Source:** `packages/sft-assets/src/sft_assets/_loader.py` lines 22-27 + `packages/sft-domain/src/sft_domain/glossary/_loader.py` lines 41-44

```python
@lru_cache(maxsize=1)
def load_assets() -> tuple[Asset, ...]:
    ...
```

**Apply to:** `BgeM3Embedder._get_model()` and `BgeReranker._get_reranker()` — lazy-load heavy ML models with `@lru_cache(maxsize=1)` so the first call loads and subsequent calls return cached instance.

### 9. WORKSPACE_ROOT path derivation (ALL scripts)

**Source:** `scripts/timescale-migrate.py` line 36 + `scripts/nats-bootstrap-streams.py` line 38

```python
WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent
```

**Apply to:** All scripts in `scripts/` (`qdrant-bootstrap.py`, `neo4j-bootstrap.py`, `migrate-sop-acl.py`) and in `services/knowledge-ingest/scripts/`.

### 10. @pytest.mark.integration + @pytest.mark.gpu test markers

**Source:** `packages/sft-agents/tests/conftest.py` lines 24-34 + CONTEXT.md code_context lines 85-86

```python
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "integration: marks tests requiring docker / testcontainers")
    config.addinivalue_line("markers", "gpu: marks tests requiring CUDA GPU")
```

**Apply to:** All integration tests in `packages/sft-knowledge/tests/` — decorate with `@pytest.mark.integration` when requiring live Qdrant/Neo4j. Decorate with `@pytest.mark.gpu` for BGE-M3 GPU-only benchmarks.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `tests/data/rag_eval/testset.jsonl` | data | — | Generated file — no code analog; schema defined in D-71 (CONTEXT.md). Follow JSONL line format: `{"question": str, "reference_sop_id": str, "query_type": "keyword_it|natural_it|cross_lingual_en", "lang": "it|en"}` |
| `docs/knowledge-layer/*.md` (4 files) | doc | — | Documentation only — follow existing MkDocs pattern in `docs/docs/` with `nav:` registration in `docs/mkdocs.yml`; Phase 3 `docs/it-ot/` pages are the structural analog |

---

## Metadata

**Analog search scope:** `packages/sft-tools/`, `packages/sft-agents/`, `packages/sft-domain/`, `packages/sft-assets/`, `services/ot-bridge/`, `scripts/`, `infra/compose/`, `infra/migrations/`, `.github/workflows/`, `tests/`
**Files scanned:** 42 source files (Python, SQL, YAML, JSON, TOML)
**Pattern extraction date:** 2026-05-18

---

## PATTERN MAPPING COMPLETE
