---
plan_id: 05-06-pg-migration-ingest-state
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 2
depends_on: []
requirements: [KNW-07, TRN-01]
files_modified:
  - infra/migrations/timescale/006_create_ingest_state.sql
  - services/knowledge-ingest/pyproject.toml
  - services/knowledge-ingest/project.json
  - services/knowledge-ingest/src/svc_knowledge_ingest/__init__.py
  - services/knowledge-ingest/src/svc_knowledge_ingest/state.py
  - services/knowledge-ingest/tests/conftest.py
  - services/knowledge-ingest/tests/test_state.py
  - scripts/timescale-migrate.py
autonomous: true
estimated_atomic_commits: 3
must_haves:
  truths:
    - "knowledge.ingest_state table exists with PK source_uri, content_hash, version, indexed_at, chunk_count, collection, acl_level columns"
    - "Migration 006_create_ingest_state.sql is idempotent (CREATE TABLE IF NOT EXISTS + DO $$ GRANT block)"
    - "scripts/timescale-migrate.py picks up 006 automatically (numeric ordering)"
    - "asyncpg state.py module: upsert_state() + get_state() use parametrized $N placeholders only (zero f-string SQL)"
    - "test_state_upsert_get + test_state_idempotent_upsert pass via testcontainer PG"
  artifacts:
    - path: infra/migrations/timescale/006_create_ingest_state.sql
      provides: PG migration creating knowledge.ingest_state hypertable-adjacent table
    - path: services/knowledge-ingest/src/svc_knowledge_ingest/state.py
      provides: asyncpg reader/writer with parametrized SQL constants
    - path: services/knowledge-ingest/pyproject.toml
      provides: knowledge-ingest service package scaffold (full implementation in 05-10)
  key_links:
    - from: services/knowledge-ingest/src/svc_knowledge_ingest/state.py
      to: PG knowledge.ingest_state
      via: asyncpg pool.acquire + parametrized $1..$N
      pattern: "knowledge\\.ingest_state"
    - from: scripts/timescale-migrate.py
      to: infra/migrations/timescale/006_create_ingest_state.sql
      via: numeric ordering pickup
      pattern: "006_create_ingest_state"
---

<objective>
Create the PG `knowledge.ingest_state` table via idempotent migration 006, scaffold the `services/knowledge-ingest` service package (pyproject + project.json + `state.py` module only — full ingest pipeline in Plan 05-10), and validate via testcontainer PG.

Purpose: foundation for D-68 incremental reindex idempotency (content_hash gate, early-exit on unchanged file) and TRN-01 stale-detection scaffold (indexed_at timestamp tracking). Plan 05-10 pipeline orchestrator consumes this state module.

Output: a runnable migration + a tested state module + service package scaffold ready for Plan 05-10 to fill in pipeline + CLI.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md
@.planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md
@.planning/phases/03-it-ot-simulation-layer/03-CONTEXT.md
@infra/migrations/timescale/004_create_budget_executions.sql
@infra/migrations/timescale/005_create_langgraph_checkpoints.sql
@scripts/timescale-migrate.py
@packages/sft-agents/src/sft_agents/audit/pg_writer.py
@services/ot-bridge/pyproject.toml
@services/ot-bridge/project.json
</context>

<interfaces>
Schema (D-68 LOCKED — CONTEXT.md lines 459-471):

```
CREATE SCHEMA IF NOT EXISTS knowledge;

CREATE TABLE IF NOT EXISTS knowledge.ingest_state (
  source_uri    TEXT PRIMARY KEY,
  content_hash  TEXT NOT NULL,
  version       TEXT NOT NULL,
  indexed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  chunk_count   INT NOT NULL,
  collection    TEXT NOT NULL,
  acl_level     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ingest_state_version ON knowledge.ingest_state (version);
```

Asyncpg conventions (Phase 3+4 established + 05-PATTERNS.md state.py section + Shared Pattern 3):
- SQL stored as module-level CONSTANTS (zero f-string)
- All values via `$N` placeholders (T-V5-sql threat mitigation)
- Pool pattern: `async with self._pool.acquire() as conn: await conn.execute(_UPSERT_SQL, ...)`
- Re-raise on error (D-56 invariant from audit/pg_writer.py)

State module API (Plan 05-10 contract — define here, consume there):
- `class IngestStateRow` (frozen Pydantic): mirrors table columns + tz-aware datetime
- `class IngestStateStore`:
  - `def __init__(self, pool: asyncpg.Pool)`: store pool reference
  - `async def upsert(self, source_uri: str, content_hash: str, version: str, chunk_count: int, collection: str, acl_level: str) -> None`: ON CONFLICT (source_uri) DO UPDATE
  - `async def get(self, source_uri: str) -> IngestStateRow | None`
  - `async def list_all() -> list[IngestStateRow]` (used by Plan 05-10 stale-detection scaffold)

GRANT block (mirror migration 004 lines 28-37): conditional GRANT INSERT/SELECT/UPDATE on knowledge schema/table to `agent_role` IF role exists.

Service package layout (D-70):
```
services/knowledge-ingest/
├── pyproject.toml
├── project.json
└── src/svc_knowledge_ingest/
    ├── __init__.py
    └── state.py
```

Plan 05-10 fills in `__main__.py` (Typer CLI) + `pipeline.py` (orchestrator). This plan only ships `state.py`.
</interfaces>

<tasks>

<task id="05-06-01" type="auto">
  <name>Task 1: Migration 006_create_ingest_state.sql + timescale-migrate.py pickup verification</name>
  <files>
    infra/migrations/timescale/006_create_ingest_state.sql,
    scripts/timescale-migrate.py
  </files>
  <read_first>
    infra/migrations/timescale/004_create_budget_executions.sql (full pattern lines 1-37 — CREATE SCHEMA IF NOT EXISTS + DO $$ GRANT block),
    infra/migrations/timescale/005_create_langgraph_checkpoints.sql (most recent migration for naming consistency),
    scripts/timescale-migrate.py (file iteration logic — confirm numeric ordering picks up 006 automatically),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-68 schema lines 459-471),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (infra/migrations section lines 891-920)
  </read_first>
  <action>
    Create `infra/migrations/timescale/006_create_ingest_state.sql`:

    Header comment: `-- Migration 006: knowledge.ingest_state — track ingest state per source_uri for incremental reindex (D-68, KNW-07, TRN-01 scaffold)`

    Body:
    1. `CREATE SCHEMA IF NOT EXISTS knowledge;`
    2. `CREATE TABLE IF NOT EXISTS knowledge.ingest_state (...)` with columns exactly as in `<interfaces>` schema block above.
    3. `CREATE INDEX IF NOT EXISTS idx_ingest_state_version ON knowledge.ingest_state (version);`
    4. `DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_role') THEN GRANT USAGE ON SCHEMA knowledge TO agent_role; GRANT INSERT, SELECT, UPDATE ON knowledge.ingest_state TO agent_role; END IF; EXCEPTION WHEN OTHERS THEN RAISE NOTICE '006_create_ingest_state.sql GRANT block: %', SQLERRM; END $$;` (mirror analog 004 lines 28-37 exactly).

    Inspect `scripts/timescale-migrate.py`: confirm migration discovery uses numeric sort on filenames matching `^[0-9]+_*.sql` glob — `006_create_ingest_state.sql` MUST be picked up automatically (no edit required if pattern matches). If discovery requires explicit allow-list, add `"006_create_ingest_state.sql"` to the list.

    Verify locally against a fresh PG container OR existing dev PG: `uv run python scripts/timescale-migrate.py --dry-run` should list 006 among the migrations to apply. If a clean PG is available: `uv run python scripts/timescale-migrate.py` should apply and re-runs should be no-ops (verify with second invocation).

    NOTE: There is NO `[BLOCKING]` schema-push task in Phase 5 (Phase 5 is Python-only, no ORM schema sync). The migration is applied by the standard `scripts/timescale-migrate.py` runner; Plan 05-10 ingest service depends on this migration being run as part of `nx run knowledge-ingest:bootstrap`.

    Commit: `feat(05-06-pg-migration-ingest-state): add migration 006 for knowledge.ingest_state table`.
  </action>
  <acceptance_criteria>
    - `infra/migrations/timescale/006_create_ingest_state.sql` exists
    - `grep -q 'CREATE TABLE IF NOT EXISTS knowledge.ingest_state' infra/migrations/timescale/006_create_ingest_state.sql`
    - `grep -q 'source_uri.*PRIMARY KEY' infra/migrations/timescale/006_create_ingest_state.sql`
    - `grep -q 'idx_ingest_state_version' infra/migrations/timescale/006_create_ingest_state.sql`
    - `grep -q 'agent_role' infra/migrations/timescale/006_create_ingest_state.sql` (GRANT block)
    - `grep -c 'IF NOT EXISTS' infra/migrations/timescale/006_create_ingest_state.sql` returns ≥3 (idempotent CREATE SCHEMA + TABLE + INDEX)
    - `uv run python scripts/timescale-migrate.py --dry-run 2>&1 | grep -q '006_create_ingest_state'`
  </acceptance_criteria>
  <verify>
    <automated>uv run python scripts/timescale-migrate.py --dry-run 2&gt;&amp;1 | grep -q '006_create_ingest_state' &amp;&amp; grep -q 'CREATE TABLE IF NOT EXISTS knowledge.ingest_state' infra/migrations/timescale/006_create_ingest_state.sql</automated>
  </verify>
  <done>Migration 006 created with idempotent CREATE + GRANT pattern; runner picks it up.</done>
</task>

<task id="05-06-02" type="auto">
  <name>Task 2: Scaffold services/knowledge-ingest package (pyproject + project.json + __init__)</name>
  <files>
    services/knowledge-ingest/pyproject.toml,
    services/knowledge-ingest/project.json,
    services/knowledge-ingest/src/svc_knowledge_ingest/__init__.py
  </files>
  <read_first>
    services/ot-bridge/pyproject.toml (full pattern lines 1-45),
    services/ot-bridge/project.json (lines 1-27),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-70 service layout lines 562-573),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (services/knowledge-ingest sections lines 720-799)
  </read_first>
  <action>
    Create `services/knowledge-ingest/pyproject.toml` mirroring `services/ot-bridge/pyproject.toml`:
    - `name = "svc-knowledge-ingest"`, `version = "0.1.0"`, `requires-python = ">=3.12,<3.13"`
    - description: "CLI ingest pipeline: parse → chunk → embed → upsert Qdrant + Neo4j MERGE (Phase 5)"
    - dependencies: `sft-knowledge`, `sft-domain`, `sft-assets`, `asyncpg>=0.29`, `typer>=0.12`, `structlog>=24.4`, `pydantic>=2.7`
    - `[project.scripts] knowledge-ingest = "svc_knowledge_ingest.__main__:app"` (NOTE: Plan 05-10 will create `__main__.py` and the `app` Typer instance; declaring the script here in Plan 05-06 is intentional so the Nx target wiring is already in place)
    - `[tool.hatch.build.targets.wheel] packages = ["src/svc_knowledge_ingest"]`
    - `[tool.uv.sources] sft-knowledge = { workspace = true }` + sft-domain + sft-assets
    - `[tool.pytest.ini_options] asyncio_mode = "auto"`, `testpaths = ["tests"]`, `markers = ["integration: requires testcontainers Qdrant+Neo4j+PG"]`

    Create `services/knowledge-ingest/project.json` mirroring `services/ot-bridge/project.json`:
    - `"name": "knowledge-ingest"`, `"projectType": "application"`, `"sourceRoot": "services/knowledge-ingest/src"`
    - Targets:
      - `run`: executor `@nxlv/python:run-commands`, command `uv run python -m svc_knowledge_ingest`, cwd `services/knowledge-ingest`
      - `bootstrap`: same executor, command `uv run python -m svc_knowledge_ingest --mode=bootstrap`, cwd same
      - `test`: same executor, command `uv run pytest`, cwd same
      - `validate`: same executor, command `uv run python -m svc_knowledge_ingest --mode=validate`, cwd same
    - `"implicitDependencies": ["sft-knowledge", "sft-domain", "sft-assets"]`

    Create `services/knowledge-ingest/src/svc_knowledge_ingest/__init__.py` with module docstring and empty `__all__ = []` (Plan 05-10 expands).

    Run `nx run knowledge-ingest:test --args="--collect-only"` to confirm Nx target discovers pytest config (collection is allowed to find zero tests at this stage — Task 3 adds tests).

    Commit: `feat(05-06-pg-migration-ingest-state): scaffold services/knowledge-ingest package`.
  </action>
  <acceptance_criteria>
    - `services/knowledge-ingest/pyproject.toml` exists
    - `grep -q 'name = "svc-knowledge-ingest"' services/knowledge-ingest/pyproject.toml`
    - `grep -q 'asyncpg' services/knowledge-ingest/pyproject.toml`
    - `services/knowledge-ingest/project.json` exists with targets `run`, `bootstrap`, `test`, `validate`
    - `grep -q '"knowledge-ingest"' services/knowledge-ingest/project.json`
    - `grep -q '"run":' services/knowledge-ingest/project.json` and `grep -q '"bootstrap":' services/knowledge-ingest/project.json`
    - `nx run knowledge-ingest:test --args="--collect-only" 2>&1` does not error on Nx target resolution (pytest may report 0 collected — that's fine; Task 3 adds tests)
  </acceptance_criteria>
  <verify>
    <automated>grep -q 'name = "svc-knowledge-ingest"' services/knowledge-ingest/pyproject.toml &amp;&amp; grep -q '"bootstrap":' services/knowledge-ingest/project.json</automated>
  </verify>
  <done>Service package scaffold + Nx targets exist; ready for Plan 05-10 to fill pipeline + CLI.</done>
</task>

<task id="05-06-03" type="auto" tdd="true">
  <name>Task 3: state.py asyncpg reader/writer + integration test via testcontainer PG</name>
  <files>
    services/knowledge-ingest/src/svc_knowledge_ingest/state.py,
    services/knowledge-ingest/tests/conftest.py,
    services/knowledge-ingest/tests/test_state.py
  </files>
  <read_first>
    packages/sft-agents/src/sft_agents/audit/pg_writer.py (module-constant SQL pattern lines 36-44; asyncpg pool acquire lines 87-115; re-raise on error),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-68 schema + idempotent UPSERT semantics),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (services/knowledge-ingest/state.py section lines 852-887 + Shared Pattern 3 parametrized SQL),
    .planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md (TRN-01 + KNW-07 test row pointing at test_ingest_pipeline.py — note: that's Plan 05-10; this plan only tests state.py)
  </read_first>
  <behavior>
    - `IngestStateRow` is frozen Pydantic v2 model: source_uri, content_hash, version, indexed_at (tz-aware datetime), chunk_count, collection, acl_level
    - `IngestStateStore.upsert(source_uri, content_hash, version, chunk_count, collection, acl_level) -> None`: ON CONFLICT (source_uri) DO UPDATE SET all fields including indexed_at = NOW()
    - `IngestStateStore.get(source_uri) -> IngestStateRow | None`: returns row or None
    - `IngestStateStore.list_all() -> list[IngestStateRow]`: returns all rows (for stale-detection scaffold per TRN-01)
    - All SQL stored as module-level CONSTANTS (no f-string interpolation)
    - All values via `$N` placeholders
    - structlog logging on insert/update with `source_uri` + counts
    - On asyncpg error: log and re-raise (no silent swallow)
    - test_upsert_then_get: upsert row, get returns IngestStateRow with same values + indexed_at tz-aware
    - test_upsert_is_idempotent: upsert same source_uri twice with same content_hash → second upsert updates indexed_at but no row count change
    - test_upsert_updates_on_content_hash_change: upsert source_uri with hash1, then upsert same source_uri with hash2 → get returns hash2
    - test_get_returns_none_on_missing: get unknown source_uri → None
    - test_list_all_returns_all: insert 3 rows → list_all returns 3
    - test_sql_constants_have_no_fstring: import state module + verify `_UPSERT_SQL`, `_SELECT_SQL`, `_LIST_SQL` are str constants containing `$1` placeholder (regex/grep check) — also assert they do NOT contain Python f-string `{var}` interpolation markers around source_uri/content_hash/etc.
  </behavior>
  <action>
    Create `services/knowledge-ingest/src/svc_knowledge_ingest/state.py`:

    - `from __future__ import annotations`, `import asyncpg`, `import structlog`, `from datetime import datetime`, `from typing import Annotated`, `from pydantic import BaseModel, Field, field_validator`

    - Define `IngestStateRow(BaseModel)` with `model_config = {"frozen": True, "extra": "forbid"}`:
      - source_uri: str
      - content_hash: str
      - version: str
      - indexed_at: datetime (with tz-aware validator from Shared Pattern 2)
      - chunk_count: Annotated[int, Field(ge=0)]
      - collection: str
      - acl_level: str
      - Validator: `@field_validator("indexed_at") def _ensure_tz(cls, v): if v.tzinfo is None: raise ValueError(...); return v`

    - Module-level SQL constants (mirror PATTERNS.md state.py section verbatim):
      ```
      _UPSERT_SQL: str = (
          "INSERT INTO knowledge.ingest_state "
          "(source_uri, content_hash, version, indexed_at, chunk_count, collection, acl_level) "
          "VALUES ($1, $2, $3, NOW(), $4, $5, $6) "
          "ON CONFLICT (source_uri) DO UPDATE SET "
          "content_hash = $2, version = $3, indexed_at = NOW(), "
          "chunk_count = $4, collection = $5, acl_level = $6"
      )
      _SELECT_SQL: str = (
          "SELECT source_uri, content_hash, version, indexed_at, "
          "chunk_count, collection, acl_level "
          "FROM knowledge.ingest_state WHERE source_uri = $1"
      )
      _LIST_SQL: str = (
          "SELECT source_uri, content_hash, version, indexed_at, "
          "chunk_count, collection, acl_level "
          "FROM knowledge.ingest_state ORDER BY indexed_at DESC"
      )
      ```

    - `class IngestStateStore`:
      - `def __init__(self, pool: asyncpg.Pool) -> None: self._pool = pool; self._logger = structlog.get_logger(__name__)`
      - `async def upsert(self, source_uri, content_hash, version, chunk_count, collection, acl_level) -> None`: try/acquire/execute/log; on exception log + re-raise.
      - `async def get(self, source_uri: str) -> IngestStateRow | None`: fetchrow → if None return None; else build IngestStateRow via model_validate({...}).
      - `async def list_all(self) -> list[IngestStateRow]`: fetch → list comprehension.
      - All methods use `async with self._pool.acquire() as conn:` pattern from pg_writer.py.

    Create `services/knowledge-ingest/tests/conftest.py`:
    - `pg_pool` session-scoped fixture using `testcontainers.postgres.PostgresContainer` (image `timescale/timescaledb:latest-pg16` per Phase 3 convention — verify image tag against Phase 3 if it differs).
    - Inside: run migrations against the testcontainer via `scripts/timescale-migrate.py` subprocess call (passing the testcontainer DSN), then yield an asyncpg pool.
    - Marker registration `integration` (mirror Plan 05-01 conftest).

    Create `services/knowledge-ingest/tests/test_state.py`:
    - All tests marked `@pytest.mark.integration`.
    - Implement the 6 tests from `<behavior>`.
    - Each test uses the `pg_pool` fixture; create `IngestStateStore(pg_pool)` per test (or use a function-scoped fixture).
    - Cleanup: `TRUNCATE knowledge.ingest_state` between tests (function-scoped fixture or autouse cleanup fixture).

    Commit: `feat(05-06-pg-migration-ingest-state): add state.py with IngestStateStore + integration tests`.
  </action>
  <acceptance_criteria>
    - `grep -q 'class IngestStateRow(BaseModel):' services/knowledge-ingest/src/svc_knowledge_ingest/state.py`
    - `grep -q 'class IngestStateStore:' services/knowledge-ingest/src/svc_knowledge_ingest/state.py`
    - `grep -q '_UPSERT_SQL:' services/knowledge-ingest/src/svc_knowledge_ingest/state.py`
    - `grep -q 'ON CONFLICT (source_uri)' services/knowledge-ingest/src/svc_knowledge_ingest/state.py`
    - `grep -v '^#' services/knowledge-ingest/src/svc_knowledge_ingest/state.py | grep -E 'f"[^"]*\\{(source_uri|content_hash|version|collection|acl_level)\\}' | wc -l` returns 0 (no f-string SQL — coding-style.md immutability + Phase 3 T-V5-sql threat)
    - `nx run knowledge-ingest:test --args="-m integration -v"` exits 0 (all 6 tests pass)
  </acceptance_criteria>
  <verify>
    <automated>nx run knowledge-ingest:test --args="-m integration -v"</automated>
  </verify>
  <done>state.py committed with 6 integration tests green; zero f-string SQL; SQL constants verified; ready for Plan 05-10 pipeline orchestrator.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| state.py → PG knowledge.ingest_state | asyncpg writes pass through parametrized $N placeholders only; no user input crosses unchecked |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-06-01 | Tampering (SQL injection) | state.py SQL | mitigate | Module-level constants + $N placeholders only (T-V5-sql inherited from Phase 3); zero f-string SQL test gate |
| T-05-06-02 | Tampering | migration 006 idempotency | mitigate | CREATE SCHEMA/TABLE/INDEX IF NOT EXISTS; DO $$ EXCEPTION block; verified by re-running migrate script |
| T-05-06-03 | Elevation of Privilege | agent_role GRANTs | mitigate | GRANT block is conditional on role existing; runs at migration time only; Phase 11 reviews role boundaries |
| T-05-06-04 | Information Disclosure | content_hash + acl_level in PG | accept | Hashes are non-reversible; acl_level is the column being protected at retrieval layer (Plan 05-09), not in this table |
| T-05-06-SC | Tampering | npm/pip install | mitigate | asyncpg + typer + structlog already in workspace from Phase 3/4; testcontainers[postgres] available via plan 05-01 dev dep declaration |
</threat_model>

<verification>
- `uv run python scripts/timescale-migrate.py --dry-run` lists `006_create_ingest_state` in plan output
- `nx run knowledge-ingest:test --args="-m integration -v"` exits 0 (6 tests pass)
- `grep -c '\$[0-9]' services/knowledge-ingest/src/svc_knowledge_ingest/state.py` returns ≥6 (parametrized placeholders)
- Zero f-string SQL: grep test in Task 3 acceptance criteria returns 0
- Migration idempotency: second run leaves DB unchanged (table still exists with same schema)
</verification>

<success_criteria>
- 3 atomic commits: `feat(05-06-pg-migration-ingest-state):` × 3
- KNW-07 foundation (state tracking) + TRN-01 foundation (indexed_at timestamp) closed
- Migration 006 idempotent and discovered by existing runner
- state.py SQL is 100% parametrized (zero f-string SQL gate)
- Service package scaffold ready for Plan 05-10
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-06-pg-migration-ingest-state-SUMMARY.md` when done with: migration applied confirmation, 6 integration tests green, service package scaffold + Nx targets list.
</output>
