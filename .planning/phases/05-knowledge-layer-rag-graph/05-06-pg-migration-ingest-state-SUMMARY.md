---
phase: 5
plan: 05-06-pg-migration-ingest-state
subsystem: knowledge-layer
tags: [migration, asyncpg, ingest-state, D-68, KNW-07, TRN-01, testcontainers]
requires: []
provides:
  - "knowledge.ingest_state PG table (D-68 incremental reindex substrate)"
  - "IngestStateStore asyncpg CRUD (zero f-string SQL — T-V5-sql)"
  - "services/knowledge-ingest package scaffold (consumed by Plan 05-10)"
affects:
  - "Plan 05-10 (ingest pipeline orchestrator)"
  - "TRN-01 stale-detection scaffold (indexed_at timestamp tracking)"
tech-stack:
  added:
    - "asyncpg-backed knowledge.ingest_state CRUD"
    - "testcontainers PG integration-test fixture for knowledge-ingest service"
  patterns:
    - "Module-constant parameterized SQL (mirrors packages/sft-agents/audit/pg_writer.py)"
    - "Frozen Pydantic v2 row model + tz-aware datetime validator (Shared Pattern 1+2)"
    - "Idempotent SQL migration with conditional GRANT (mirrors 004_create_budget_executions.sql)"
key-files:
  created:
    - infra/migrations/timescale/006_create_ingest_state.sql
    - services/knowledge-ingest/pyproject.toml
    - services/knowledge-ingest/project.json
    - services/knowledge-ingest/src/svc_knowledge_ingest/__init__.py
    - services/knowledge-ingest/src/svc_knowledge_ingest/state.py
    - services/knowledge-ingest/tests/__init__.py
    - services/knowledge-ingest/tests/conftest.py
    - services/knowledge-ingest/tests/test_state.py
  modified:
    - pyproject.toml (register services/knowledge-ingest as uv workspace member)
    - uv.lock (resolved deps for svc-knowledge-ingest)
decisions:
  - "Plan 05-06 ships ONLY state.py — pipeline.py + __main__.py deferred to Plan 05-10 (per plan objective)"
  - "sft-knowledge/sft-domain/sft-assets workspace deps omitted from pyproject.toml — state.py imports none of them, and sft-knowledge does not exist yet (Wave 1 product). Plan 05-10 adds the workspace deps when wiring full pipeline."
  - "All knowledge.ingest_state SQL stored as module-level constants — zero f-string interpolation (T-V5-sql / T-05-06-01)"
  - "indexed_at always sourced from server-side NOW() in upsert (both insert and update branches) — caller cannot drift the timestamp (TRN-01 invariant)"
metrics:
  duration_minutes: ~12
  task_count: 3
  commit_count: 4
  file_count: 8
  completed_at: 2026-05-19T09:36:20Z
---

# Phase 5 Plan 05-06: PG ingest_state migration + knowledge-ingest scaffold — Summary

asyncpg-backed `knowledge.ingest_state` table (D-68 schema) with idempotent migration 006, frozen-Pydantic row model, parametrized-SQL `IngestStateStore`, and 6 green integration tests against a TimescaleDB testcontainer.

## Tasks Completed

| Task | Name                                                 | Commit  | Files                                                                                                                                                                                          |
| ---- | ---------------------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Migration 006 + runner pickup verification           | 5da91b9 | infra/migrations/timescale/006_create_ingest_state.sql                                                                                                                                         |
| 2    | Scaffold services/knowledge-ingest package           | 628325f | services/knowledge-ingest/{pyproject.toml, project.json, src/svc_knowledge_ingest/__init__.py}; pyproject.toml (workspace members); uv.lock                                                    |
| 3a   | TDD RED — failing integration tests for state.py     | aa61397 | services/knowledge-ingest/tests/{__init__.py, conftest.py, test_state.py}                                                                                                                      |
| 3b   | TDD GREEN — state.py implementation, 6 tests pass    | 0609304 | services/knowledge-ingest/src/svc_knowledge_ingest/state.py                                                                                                                                    |

## What Was Built

### Migration 006 (`infra/migrations/timescale/006_create_ingest_state.sql`)

- `CREATE SCHEMA IF NOT EXISTS knowledge`
- `CREATE TABLE IF NOT EXISTS knowledge.ingest_state` with columns per D-68 (CONTEXT.md lines 459-471): `source_uri PK, content_hash, version, indexed_at, chunk_count, collection, acl_level`
- `CREATE INDEX IF NOT EXISTS idx_ingest_state_version` (stale-detection scans, TRN-01)
- Conditional `DO $$ GRANT` block: GRANT USAGE on knowledge schema + GRANT INSERT/SELECT/UPDATE on knowledge.ingest_state to `agent_role` IFF the role exists (mirrors 004 lines 28-37)
- Picked up automatically by `scripts/timescale-migrate.py` (glob `[0-9][0-9][0-9]_*.sql` + sorted order)

Idempotency verified: re-running migrate is a no-op because every DDL uses `IF NOT EXISTS` and the GRANT block is conditional. The migration's `--dry-run` lists 006 among the targets.

### Service package scaffold (`services/knowledge-ingest/`)

- `pyproject.toml`: `svc-knowledge-ingest 0.1.0` (Python ≥3.12,<3.13), deps `asyncpg>=0.29`, `typer>=0.12`, `structlog>=24.4`, `pydantic>=2.7`, dev extra `testcontainers[postgres]>=4.14`, `[project.scripts] knowledge-ingest = "svc_knowledge_ingest.__main__:app"` (Plan 05-10 wires `app`)
- `project.json`: Nx targets `run`, `bootstrap`, `test`, `validate` (all via `@nxlv/python:run-commands`), implicit deps `[sft-knowledge, sft-domain, sft-assets]`
- `src/svc_knowledge_ingest/__init__.py`: package docstring + empty `__all__`
- Registered as uv workspace member in root `pyproject.toml`; `uv sync` is clean

### `state.py` (the headline deliverable)

- `IngestStateRow(BaseModel)` — frozen, extra=forbid, tz-aware `indexed_at` validator
- `IngestStateStore`:
  - `__init__(pool: asyncpg.Pool)` — pool reference only; caller owns lifecycle
  - `async upsert(source_uri, content_hash, version, chunk_count, collection, acl_level)` — `ON CONFLICT (source_uri) DO UPDATE` with `indexed_at = NOW()` on both branches; logs success at DEBUG, errors at ERROR, re-raises (D-56 invariant)
  - `async get(source_uri) -> IngestStateRow | None`
  - `async list_all() -> list[IngestStateRow]` — ORDER BY indexed_at DESC (TRN-01)
- SQL: `_UPSERT_SQL`, `_SELECT_SQL`, `_LIST_SQL` are module-level `str` constants — **zero f-string SQL**. Static check `test_sql_constants_have_no_fstring` is part of the regular test suite.
- All values pass through asyncpg via `$1..$6` placeholders (12 occurrences across 3 SQL constants, 6 unique).

### Tests (`services/knowledge-ingest/tests/`)

- `conftest.py`:
  - Session-scoped `timescale_dsn` fixture spinning a `timescale/timescaledb:2.18.0-pg16` container (mirror infra migration tests)
  - Session-scoped `_migrated_dsn` applying `infra.migrations.timescale.migrate` exactly once
  - Function-scoped `pg_pool` fixture creating an `asyncpg.Pool` (statement_cache_size=0), TRUNCATE-ing `knowledge.ingest_state` before each test, closing pool on teardown
  - sys.path shim so `infra.migrations.timescale.migrate` is importable from the service-tree CWD (mirror Pattern S-3 in `scripts/timescale-migrate.py`)
- `test_state.py` — 6 tests:
  1. `test_upsert_then_get` — round-trip + tz-aware assertion
  2. `test_upsert_is_idempotent` — re-upsert same key, COUNT(*) stays 1
  3. `test_upsert_updates_on_content_hash_change` — second upsert wins
  4. `test_get_returns_none_on_missing` — None, not exception
  5. `test_list_all_returns_all` — 3 inserts → 3 returned
  6. `test_sql_constants_have_no_fstring` — static source-text inspection for f-string violations

## Verification Evidence

- `grep` checks for migration 006: all PASS (table, PK, idx, agent_role, 3× `IF NOT EXISTS`)
- `uv run python scripts/timescale-migrate.py --dry-run | grep 006_create_ingest_state` → matches
- `uv sync` (after registering the workspace member) → 150 packages resolved, 51 checked, no errors
- `uv run pytest tests/test_state.py -v` (in service dir) → **6 passed in 6.36s** against live TimescaleDB testcontainer
- `grep -oE '\$[0-9]+' state.py | sort -u` → `$1 $2 $3 $4 $5 $6` (12 total occurrences) — parameterization OK
- f-string-with-SQL-values regex over `state.py` → 0 matches — T-V5-sql clean

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Omit `sft-knowledge/sft-domain/sft-assets` workspace deps from `pyproject.toml`**

- **Found during:** Task 2
- **Issue:** Plan asked for `sft-knowledge = { workspace = true }` etc. in `[tool.uv.sources]`, but `packages/sft-knowledge` does NOT yet exist (Plan 05-01 product, Wave 1, currently executing in parallel and not merged into this worktree's base `ed430316`). Declaring the workspace source would break `uv sync`.
- **Fix:** Omitted all three workspace deps from `services/knowledge-ingest/pyproject.toml`. `state.py` (the only deliverable of this plan) does not import any of them — it depends only on `asyncpg`, `structlog`, `pydantic`. The `project.json` `implicitDependencies` array still lists them (it's metadata, not a hard import). Plan 05-10 will add the deps when wiring the pipeline that actually imports `sft_knowledge`/`sft_domain`/`sft_assets`.
- **Files modified:** services/knowledge-ingest/pyproject.toml
- **Commit:** 628325f

**2. [Rule 3 — Blocking] Register `services/knowledge-ingest` in root `pyproject.toml` workspace members**

- **Found during:** Task 2
- **Issue:** Plan did not call out registering the new service in the root `[tool.uv.workspace] members` array, but without it `uv sync` would not resolve `svc-knowledge-ingest`, and the integration tests' transitive deps (testcontainers, asyncpg) would fail to install in the worktree env.
- **Fix:** Added `"services/knowledge-ingest"` between `"services/ot-bridge"` and `"simulators/sim-textile"` in root `pyproject.toml`. `uv sync` succeeded immediately afterwards.
- **Files modified:** pyproject.toml (root), uv.lock
- **Commit:** 628325f

**3. [Rule 3 — Blocking] sys.path shim in `services/knowledge-ingest/tests/conftest.py`**

- **Found during:** Task 3 RED phase
- **Issue:** `from infra.migrations.timescale.migrate import migrate` fails with `ModuleNotFoundError: No module named 'infra'` when pytest runs with cwd inside the service tree, because `infra/` is a script tree (not a pip-installable workspace member).
- **Fix:** Prepend the workspace root to `sys.path` at conftest top (mirrors `scripts/timescale-migrate.py` Pattern S-3 documented in 05-PATTERNS.md). Comment explains the rationale.
- **Files modified:** services/knowledge-ingest/tests/conftest.py
- **Commit:** aa61397

**4. [Rule 2 — Critical functionality] Replace plan-suggested `markers` with explicit `pytest_configure` registration**

- **Found during:** Task 3 RED phase
- **Issue:** Although `[tool.pytest.ini_options] markers = ["integration: ..."]` is declared in `services/knowledge-ingest/pyproject.toml`, registering it again in `conftest.py` via `pytest_configure` mirrors the existing Phase 4 convention (`packages/sft-agents/tests/conftest.py`) and protects future `--strict-markers` runs from breaking when pytest config is overridden in CI.
- **Fix:** Added `def pytest_configure(config)` registering the `integration` marker.
- **Files modified:** services/knowledge-ingest/tests/conftest.py
- **Commit:** aa61397

### Out-of-scope items observed (not fixed)

None — no pre-existing failures touched.

## Threat Model Compliance

| Threat ID | Mitigation Plan | Implementation evidence |
|-----------|-----------------|--------------------------|
| T-05-06-01 | Module constants + `$N` only | `_UPSERT_SQL`, `_SELECT_SQL`, `_LIST_SQL` are str constants; 12 `$N` occurrences across 6 unique placeholders; `test_sql_constants_have_no_fstring` enforces statically |
| T-05-06-02 | Idempotent migration | `IF NOT EXISTS` × 3 + `DO $$ EXCEPTION` GRANT block; `migrate()` returns 0 on first and subsequent runs |
| T-05-06-03 | Conditional `agent_role` GRANT | `DO $$ IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'agent_role')` |
| T-05-06-04 | content_hash + acl_level acceptance | Hashes non-reversible; acl_level enforcement deferred to retrieval layer (Plan 05-09) |
| T-05-06-SC | Supply chain | All deps (`asyncpg`, `typer`, `structlog`, `pydantic`, `testcontainers[postgres]`) already present in workspace transitive closure; no new top-level libraries introduced |

## TDD Gate Compliance

- RED gate: `aa61397 test(05-06-pg-migration-ingest-state): add failing integration tests for state.py` (collection-time ImportError, confirmed before GREEN)
- GREEN gate: `0609304 feat(05-06-pg-migration-ingest-state): add state.py with IngestStateStore + integration tests` (6/6 tests pass)
- REFACTOR gate: not needed — state.py shipped clean on first GREEN.

## Known Stubs

None — `state.py` is fully wired. `__init__.py` exports nothing (`__all__ = []`) by design; Plan 05-10 expands.

## Authentication Gates

None.

## Success Criteria Met

- [x] 3 atomic commits feat(05-06-pg-migration-ingest-state): × 3 (plus one TDD-RED test commit = 4 total)
- [x] KNW-07 foundation (state tracking) — `knowledge.ingest_state` exists, upsert/get/list_all green
- [x] TRN-01 foundation (indexed_at) — server-side NOW() timestamping, ORDER BY indexed_at DESC list_all
- [x] Migration 006 idempotent and discovered by existing runner
- [x] state.py SQL is 100% parametrized (zero f-string SQL gate enforced via static test)
- [x] Service package scaffold ready for Plan 05-10

## Self-Check: PASSED

- File `infra/migrations/timescale/006_create_ingest_state.sql` exists
- File `services/knowledge-ingest/pyproject.toml` exists
- File `services/knowledge-ingest/project.json` exists
- File `services/knowledge-ingest/src/svc_knowledge_ingest/__init__.py` exists
- File `services/knowledge-ingest/src/svc_knowledge_ingest/state.py` exists
- File `services/knowledge-ingest/tests/conftest.py` exists
- File `services/knowledge-ingest/tests/test_state.py` exists
- Commit 5da91b9 in `git log --all`
- Commit 628325f in `git log --all`
- Commit aa61397 in `git log --all`
- Commit 0609304 in `git log --all`
