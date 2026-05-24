"""
infra/migrations/timescale/tests/test_migration_011.py

Tests for migration 011_create_scm_schema.sql.

Phase 9 — Plan 09-00a (D-DATA — scm.* schema creation).

The migration creates the `scm.*` schema with five tables:
- `scm.sku_master`         — SKU reference table (category CHECK constraint)
- `scm.inventory_levels`   — TimescaleDB hypertable (partition key: ts)
- `scm.energy_readings`    — TimescaleDB hypertable (partition key: ts, process CHECK)
- `scm.historical_orders`  — relational table with timestamp
- `scm.enpi_baseline`      — ISO 50001 EnPI baseline per process

Test matrix (mirrors test_migration_010.py fixture/baseline-glob structure):
    1. test_scm_schema_exists                      — schema `scm` created by 011
    2. test_all_five_tables_exist                   — all 5 scm.* tables present in information_schema
    3. test_inventory_levels_is_hypertable          — scm.inventory_levels in timescaledb_information.hypertables
    4. test_energy_readings_is_hypertable           — scm.energy_readings in timescaledb_information.hypertables
    5. test_sku_master_category_check_rejects_invalid — invalid category raises CheckViolationError
    6. test_energy_readings_process_check_rejects_invalid — invalid process raises CheckViolationError
    7. test_idempotent_double_apply                 — re-running 011 is a no-op (does not raise)
    + test_migrate_runner_picks_up_011              — full migrate() runner globs 011 and applies it

All tests run against an isolated testcontainers Postgres+TimescaleDB function-scoped
container. Marked @pytest.mark.testcontainers AND @pytest.mark.integration so they
pick up under both CI selectors.
"""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

# Make the workspace root importable so `infra.migrations.timescale.migrate`
# resolves regardless of pytest invocation cwd. Mirrors the pattern used in
# tests/integration/test_migrations_idempotent.py (Phase 4 Plan 04-02) and
# test_migration_010.py (Phase 8 Plan 08-00a).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from infra.migrations.timescale.migrate import migrate  # noqa: E402

_MIGRATION_011 = Path(__file__).parent.parent / "011_create_scm_schema.sql"

# All five scm.* tables introduced by migration 011.
_SCM_TABLES = (
    "sku_master",
    "inventory_levels",
    "energy_readings",
    "historical_orders",
    "enpi_baseline",
)


async def _run_baseline_migrations(dsn: str) -> None:
    """Apply 001..010 (excluding 011) by reading and executing each in order.

    We deliberately bypass the migrate() runner here so that 011 is not picked
    up by the glob. This lets us exercise pre-011 state and apply 011 explicitly.
    Mirrors the pattern in test_migration_010.py._run_baseline_migrations.
    """
    migrations_dir = Path(__file__).parent.parent
    baseline_files = sorted(
        f for f in migrations_dir.glob("[0-9][0-9][0-9]_*.sql") if f.name < "011"
    )
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        for sql_file in baseline_files:
            await conn.execute(sql_file.read_text(encoding="utf-8"))
    finally:
        await conn.close()


async def _apply_011(dsn: str) -> None:
    """Apply only 011_create_scm_schema.sql against the provided DSN."""
    sql = _MIGRATION_011.read_text(encoding="utf-8")
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


async def _insert_sku(
    dsn: str,
    *,
    sku_id: str | None = None,
    category: str = "raw_yarn",
) -> None:
    """Insert a minimally-valid row into scm.sku_master.

    Raises asyncpg.CheckViolationError if the category CHECK constraint rejects the row.
    """
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        await conn.execute(
            "INSERT INTO scm.sku_master"
            " (sku_id, sku_name, category, unit, reorder_point, reorder_qty, unit_cost_eur)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7)",
            sku_id or str(uuid4()),
            "Test SKU",
            category,
            "kg",
            100.0,
            200.0,
            3.50,
        )
    finally:
        await conn.close()


async def _insert_energy_reading(
    dsn: str,
    *,
    process: str = "dyeing",
) -> None:
    """Insert a minimally-valid row into scm.energy_readings.

    Raises asyncpg.CheckViolationError if the process CHECK constraint rejects the row.
    Requires scm.energy_readings hypertable to exist (call after _apply_011).
    """
    from datetime import datetime, timezone  # noqa: PLC0415

    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        await conn.execute(
            "INSERT INTO scm.energy_readings (ts, asset_id, process, kwh)"
            " VALUES ($1, $2, $3, $4)",
            datetime.now(timezone.utc),
            "tintoria-01",
            process,
            125.50,
        )
    finally:
        await conn.close()


@pytest.fixture(scope="function")
async def fresh_dsn() -> str:
    """Yield a fresh TimescaleDB DSN per test (function-scoped, NOT shared).

    Each test must start from a clean schema because we apply different subsets
    of migrations (pre-011 vs post-011). Spawn a dedicated container per test.
    Mirrors the function-scoped fixture in test_migration_010.py.
    """
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer(
        image="timescale/timescaledb:2.18.0-pg16",
        username="sft",
        password="sft_dev_pass",
        dbname="sft",
    ) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        yield f"postgresql://sft:sft_dev_pass@{host}:{port}/sft"


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_scm_schema_exists(fresh_dsn: str) -> None:
    """After 011, schema `scm` exists in information_schema.schemata."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_011(fresh_dsn)

    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            "SELECT schema_name FROM information_schema.schemata"
            " WHERE schema_name = 'scm'"
        )
        assert row is not None, "Schema 'scm' not found after applying 011"
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("table_name", _SCM_TABLES)
async def test_all_five_tables_exist(fresh_dsn: str, table_name: str) -> None:
    """After 011, all 5 scm.* tables are present in information_schema.tables."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_011(fresh_dsn)

    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            "SELECT to_regclass($1)",
            f"scm.{table_name}",
        )
        assert row is not None and row[0] is not None, (
            f"Table scm.{table_name} not found after applying 011"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_inventory_levels_is_hypertable(fresh_dsn: str) -> None:
    """After 011, scm.inventory_levels is registered as a TimescaleDB hypertable."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_011(fresh_dsn)

    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            "SELECT hypertable_name FROM timescaledb_information.hypertables"
            " WHERE hypertable_schema = 'scm' AND hypertable_name = 'inventory_levels'"
        )
        assert row is not None, (
            "scm.inventory_levels is not a TimescaleDB hypertable after 011"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_energy_readings_is_hypertable(fresh_dsn: str) -> None:
    """After 011, scm.energy_readings is registered as a TimescaleDB hypertable."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_011(fresh_dsn)

    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            "SELECT hypertable_name FROM timescaledb_information.hypertables"
            " WHERE hypertable_schema = 'scm' AND hypertable_name = 'energy_readings'"
        )
        assert row is not None, (
            "scm.energy_readings is not a TimescaleDB hypertable after 011"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_sku_master_category_check_rejects_invalid(fresh_dsn: str) -> None:
    """The scm.sku_master.category CHECK constraint rejects values not in the allowed set."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_011(fresh_dsn)

    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await _insert_sku(fresh_dsn, category="invalid_category")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_energy_readings_process_check_rejects_invalid(fresh_dsn: str) -> None:
    """The scm.energy_readings.process CHECK constraint rejects unknown process values."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_011(fresh_dsn)

    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await _insert_energy_reading(fresh_dsn, process="invalid_process")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_idempotent_double_apply(fresh_dsn: str) -> None:
    """Re-applying migration 011 a second time must NOT raise (idempotency).

    All DDL statements use IF NOT EXISTS, so double-apply is a no-op.
    The hypertable call uses if_not_exists => TRUE.
    """
    await _run_baseline_migrations(fresh_dsn)
    await _apply_011(fresh_dsn)
    # Second apply — must be a no-op (no exception raised)
    await _apply_011(fresh_dsn)
    # Tables must still be accessible after double-apply
    await _insert_sku(fresh_dsn, category="fabric")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrate_runner_picks_up_011(fresh_dsn: str) -> None:
    """The migrate.py runner globs 011 automatically and applies it in order."""
    rc = await migrate(fresh_dsn)
    assert rc == 0

    # After the full migrate() run, all scm.* tables must be present
    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        for table_name in _SCM_TABLES:
            row = await conn.fetchrow("SELECT to_regclass($1)", f"scm.{table_name}")
            assert row is not None and row[0] is not None, (
                f"Table scm.{table_name} not found after migrate() run"
            )
    finally:
        await conn.close()
