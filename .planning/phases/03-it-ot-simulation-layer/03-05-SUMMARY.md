---
phase: "03"
plan: "05"
subsystem: timescaledb-migration
tags:
  - timescaledb
  - hypertable
  - compression
  - retention
  - migration
  - asyncpg
  - testcontainers
dependency_graph:
  requires:
    - "01-02: compose stack TimescaleDB service (infra/compose/core.yml)"
  provides:
    - "sensor_events hypertable DDL (idempotent SQL)"
    - "asyncpg migration runner (infra/migrations/timescale/migrate.py)"
    - "CLI wrapper (scripts/timescale-migrate.py)"
    - "make migrate-timescale target"
  affects:
    - "03-06: E2E test sim → bridge → NATS → Timescale (depends on hypertable existing)"
tech_stack:
  added:
    - asyncpg>=0.30 (TimescaleDB asyncio driver, statement_cache_size=0 mandatory)
    - testcontainers[postgres]>=4.14 (dev/test — isolated TimescaleDB containers)
    - pytest-asyncio>=0.24 (async test support)
  patterns:
    - "Idempotent SQL DDL: CREATE TABLE IF NOT EXISTS + DO block compression guard + if_not_exists params"
    - "Lazy asyncpg import: dry-run works without asyncpg installed"
    - "WORKSPACE_ROOT pattern: scripts/timescale-migrate.py follows sync-python-versions.py structure"
    - "Session-scoped testcontainers fixture for DB integration tests"
key_files:
  created:
    - "infra/migrations/timescale/001_create_sensor_events.sql (74 lines)"
    - "infra/migrations/timescale/migrate.py (131 lines)"
    - "infra/migrations/timescale/__init__.py"
    - "infra/migrations/timescale/pyproject.toml"
    - "infra/migrations/timescale/tests/__init__.py"
    - "infra/migrations/timescale/tests/conftest.py"
    - "infra/migrations/timescale/tests/test_migration_idempotent.py (214 lines)"
    - "scripts/timescale-migrate.py (93 lines)"
  modified:
    - "Makefile (added migrate-timescale + migrate-timescale-dry targets)"
decisions:
  - "D-49 honored: chunk=1d / compress=7d / drop=90d applied exactly as specified"
  - "OQ2 resolved: single hypertable sensor_events with source TEXT NOT NULL DEFAULT 'live' column"
  - "Pitfall 2 documented in SQL comment: legacy compression API, hypercore deferred to Phase 11"
  - "Pitfall 6 applied: statement_cache_size=0 in asyncpg.connect() and test connections"
  - "Lazy asyncpg import (Rule 1 fix): --dry-run works without asyncpg installed in base Python env"
  - "JSONB config parse fix (Rule 1 fix): asyncpg returns JSONB as str, json.loads() applied in tests"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-18T10:58:03Z"
  tasks_completed: 1
  tasks_pending: 1
  files_created: 8
  files_modified: 1
---

# Phase 3 Plan 05: TimescaleDB Hypertable Migration Summary

**One-liner:** Idempotent TimescaleDB hypertable `sensor_events` with compression(7d) + retention(90d) + composite indexes, asyncpg runner, and 7 testcontainers integration tests all green.

## Task Status

| Task | Name | Status | Commit |
|------|------|--------|--------|
| 1 | Migration SQL + runner + tests | COMPLETE | `5db141f` |
| 2 | [BLOCKING] schema-push to dev compose stack | PENDING — awaiting checkpoint approval | — |

## Task 1 — Migration SQL + Runner + Tests (COMPLETE)

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `infra/migrations/timescale/001_create_sensor_events.sql` | 74 | Idempotent DDL: sensor_events hypertable + compression + retention + indexes |
| `infra/migrations/timescale/migrate.py` | 131 | asyncpg runner: glob NNN_*.sql sorted, execute, exit 0/1 |
| `infra/migrations/timescale/__init__.py` | 1 | Python package marker |
| `infra/migrations/timescale/pyproject.toml` | 16 | Nx project config with asyncpg + dev test deps |
| `infra/migrations/timescale/tests/__init__.py` | 1 | Tests package marker |
| `infra/migrations/timescale/tests/conftest.py` | 37 | Session-scoped timescaledb testcontainer fixture |
| `infra/migrations/timescale/tests/test_migration_idempotent.py` | 214 | 7 idempotency + schema correctness tests |
| `scripts/timescale-migrate.py` | 93 | Top-level CLI wrapper (WORKSPACE_ROOT + argparse pattern) |

### Acceptance Criteria

All 12 acceptance criteria from the plan pass:

```
CREATE TABLE IF NOT EXISTS sensor_events .............. count: 1  PASS
create_hypertable ..................................... count: 1  PASS
add_compression_policy ................................ count: 1  PASS
add_retention_policy .................................. count: 1  PASS
if_not_exists => TRUE ................................. count: 6  PASS (>= 3 required)
source TEXT NOT NULL DEFAULT 'live' ................... count: 1  PASS (OQ2)
idx_sensor_events_asset_time .......................... count: 1  PASS
idx_sensor_events_tag_time ............................ count: 1  PASS
statement_cache_size=0 in migrate.py .................. count: 2  PASS
python3 scripts/timescale-migrate.py --dry-run ........ exit: 0   PASS
migrate-timescale: target in Makefile ................. count: 1  PASS
migrate-timescale-dry: target in Makefile ............. count: 1  PASS
```

### Dry-run Output

```
[dry-run] Migration files that would be applied:
  001_create_sensor_events.sql
Exit code: 0
```

### pytest testcontainers Output

```
platform linux -- Python 3.12.13, pytest-9.0.3
rootdir: infra/migrations/timescale
configfile: pyproject.toml
plugins: asyncio-1.3.0

collected 7 items

test_migration_idempotent.py::test_first_run                  PASSED [ 14%]
test_migration_idempotent.py::test_second_run_no_error        PASSED [ 28%]
test_migration_idempotent.py::test_retention_policy_set       PASSED [ 42%]
test_migration_idempotent.py::test_compression_policy_set     PASSED [ 57%]
test_migration_idempotent.py::test_indexes_exist              PASSED [ 71%]
test_migration_idempotent.py::test_insert_after_migration     PASSED [ 85%]
test_migration_idempotent.py::test_dry_run_no_side_effect     PASSED [100%]

======================== 7 passed in 13.54s =============================
```

TimescaleDB image used: `timescale/timescaledb:2.18.0-pg16` (matches `infra/compose/core.yml`).

## Task 2 — [BLOCKING] Schema-Push to Dev Compose Stack (PENDING)

Task 2 is a `checkpoint:human-verify` gate. The orchestrator must:

1. Start the TimescaleDB service: `docker compose -f infra/compose/core.yml up -d timescaledb`
2. Run tests with testcontainers: `uv run --with pytest --with pytest-asyncio --with 'testcontainers[postgres]' --with asyncpg -- python -m pytest infra/migrations/timescale/tests -m testcontainers -x -v`
3. Apply migration: `export TIMESCALE_DSN="postgresql://sft:sft_dev_pass@localhost:5432/sft" && python3 scripts/timescale-migrate.py`
4. Verify schema: `docker compose -f infra/compose/core.yml exec timescaledb psql -U sft -d sft -c "SELECT hypertable_name, compression_enabled FROM timescaledb_information.hypertables WHERE hypertable_name = 'sensor_events';"`
5. Verify policies: `docker compose -f infra/compose/core.yml exec timescaledb psql -U sft -d sft -c "SELECT proc_name, config FROM timescaledb_information.jobs WHERE hypertable_name = 'sensor_events';"`
6. Re-run idempotency: second `python3 scripts/timescale-migrate.py` must exit 0

Expected stdout on first apply: `OK [001_create_sensor_events.sql]: applied`
Expected schema query output: `1 row — sensor_events | t`
Expected policies: at least 2 rows (policy_compression + policy_retention)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lazy asyncpg import for dry-run compatibility**
- **Found during:** Task 1 dry-run acceptance test
- **Issue:** `import asyncpg` at module top-level caused `ModuleNotFoundError` when asyncpg was not installed in base Python env, making `--dry-run` fail before argparse ran
- **Fix:** Moved `import asyncpg` inside `migrate()` function body, after the `if dry_run: return 0` early exit. Added comment explaining the lazy import pattern.
- **Files modified:** `infra/migrations/timescale/migrate.py`
- **Impact:** `python3 scripts/timescale-migrate.py --dry-run` works without asyncpg installed; runtime connections still use asyncpg normally

**2. [Rule 1 - Bug] JSONB config column JSON parse in tests**
- **Found during:** Task 1 test run (test_retention_policy_set FAILED)
- **Issue:** `timescaledb_information.jobs.config` is a JSONB column; asyncpg returns it as a `str` (JSON-encoded string), not a Python dict. Direct subscript access `rows[0]["config"]["drop_after"]` raised `TypeError: string indices must be integers`
- **Fix:** Added `json.loads()` parse with `isinstance(raw_config, str)` guard in both `test_retention_policy_set` and `test_compression_policy_set`
- **Files modified:** `infra/migrations/timescale/tests/test_migration_idempotent.py`
- **Commit:** Included in `5db141f` (same task commit after fix)

## Known Stubs

None. All migration files are complete. Task 2 (schema-push) is a runtime operation, not a code stub.

## Threat Surface Scan

No new network endpoints, auth paths, or trust boundaries introduced beyond what the plan's threat model covers:
- `migrate.py` reads only from `_MIGRATIONS_DIR` (path-restricted, T-03-05-ddl-injection mitigated)
- `TIMESCALE_DSN` read from env only, never printed (T-03-05-dsn-leak mitigated)
- `statement_cache_size=0` applied (T-03-05-statement-cache mitigated)
- Legacy compression API comment added to SQL (T-03-05-old-compression mitigated)

## Self-Check: PASSED
