"""
infra/migrations/timescale/tests/test_scm_mantis_seed.py

Seed smoke tests for scm_mantis_seed.sql.

Phase 9 — Plan 09-01 (SCM-05: Mantis synthetic dataset).

The seed file (infra/migrations/timescale/seed/scm_mantis_seed.sql) is a
NON-NUMBERED file (not matching [0-9][0-9][0-9]_*.sql) and is dev/test-only.
It populates all 5 scm.* tables with realistic SYNTHETIC data for the Mantis
Textile Group demonstration.

Test matrix:
    1. test_sku_master_non_empty            — all 6 SKUs inserted
    2. test_enpi_baseline_dyeing_finishing   — both processes present with correct values
    3. test_inventory_levels_non_empty       — inventory snapshot present
    4. test_inventory_below_reorder_point    — at least 1 SKU below its reorder_point
    5. test_energy_readings_non_empty        — energy data for dyeing + finishing present
    6. test_energy_readings_both_processes   — both dyeing and finishing processes present
    7. test_historical_orders_two_sku_groups — jersey and twill sku_groups present
    8. test_historical_orders_18_monthly_buckets_jersey — >=18 monthly buckets for jersey
    9. test_historical_orders_18_monthly_buckets_twill  — >=18 monthly buckets for twill
    10. test_seed_idempotent_double_apply    — re-applying seed is a no-op (ON CONFLICT)
    11. test_seed_file_non_numbered          — static check: filename not matching migration glob

All DB tests run against an isolated testcontainers Postgres+TimescaleDB
function-scoped container. Marked @pytest.mark.testcontainers AND
@pytest.mark.integration so they pick up under both CI selectors.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import asyncpg
import pytest

# Make the workspace root importable so `infra.migrations.timescale.migrate`
# resolves regardless of pytest invocation cwd. Mirrors the pattern used in
# test_migration_011.py.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from infra.migrations.timescale.migrate import migrate  # noqa: E402

_SEED_FILE = Path(__file__).parent.parent / "seed" / "scm_mantis_seed.sql"


# ---------------------------------------------------------------------------
# Static test — no database needed
# ---------------------------------------------------------------------------


def test_seed_file_non_numbered() -> None:
    """Seed filename must NOT match the migration glob [0-9][0-9][0-9]_*.sql.

    Non-numbered file ensures numbered migrations stay idempotent.
    The seed file lives under seed/ (separate dir) and is labeled SYNTHETIC.
    """
    assert _SEED_FILE.exists(), f"Seed file not found: {_SEED_FILE}"
    # Filename must not start with three digits followed by underscore
    assert not re.match(r"[0-9]{3}_", _SEED_FILE.name), (
        f"Seed file name '{_SEED_FILE.name}' must NOT match migration glob [0-9][0-9][0-9]_*.sql"
    )
    # Seed file must contain the SYNTHETIC label (IT or EN, uppercase check)
    seed_text_upper = _SEED_FILE.read_text(encoding="utf-8").upper()
    assert "SYNTHETIC" in seed_text_upper, (
        "Seed file must contain the SYNTHETIC label (IT+EN requirement SCM-05 / T-09-08)"
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def seeded_dsn() -> str:
    """Yield a fresh TimescaleDB DSN with all migrations + seed applied.

    Each test gets an isolated function-scoped container. Mirrors the
    fixture pattern from test_migration_011.py.
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
        dsn = f"postgresql://sft:sft_dev_pass@{host}:{port}/sft"

        # Apply all migrations (001..012) via the migrate() runner
        rc = await migrate(dsn)
        assert rc == 0, f"migrate() failed with rc={rc}"

        # Apply the seed file
        seed_sql = _SEED_FILE.read_text(encoding="utf-8")
        conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=120.0)
        try:
            await conn.execute(seed_sql)
        finally:
            await conn.close()

        yield dsn


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


async def _count(dsn: str, table: str) -> int:
    """Return row count for a fully-qualified table."""
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(f"SELECT COUNT(*) AS n FROM {table}")
        return int(row["n"])
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Seed smoke tests (require Docker)
# ---------------------------------------------------------------------------


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_sku_master_non_empty(seeded_dsn: str) -> None:
    """All 6 SKUs from Pattern 11 are present in scm.sku_master after seed."""
    conn = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        rows = await conn.fetch("SELECT sku_id FROM scm.sku_master ORDER BY sku_id")
        sku_ids = {r["sku_id"] for r in rows}
    finally:
        await conn.close()

    expected = {
        "SKU-YARN-NE20-BLU",
        "SKU-YARN-NE30-BIA",
        "SKU-DYE-REACT-BLU",
        "SKU-SPARE-NEEDLE-L",
        "SKU-FAB-JERSEY-BLU",
        "SKU-FAB-TWILL-GRY",
    }
    assert expected.issubset(sku_ids), (
        f"Missing SKUs after seed: {expected - sku_ids}"
    )


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_enpi_baseline_dyeing_finishing(seeded_dsn: str) -> None:
    """Both dyeing and finishing EnPI baselines are present with expected values.

    dyeing:    target=3.80, ytd=4.12 (8% above — EnergyOptimizer alert case)
    finishing: target=2.20, ytd=2.18 (within baseline)
    """
    conn = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        rows = await conn.fetch(
            "SELECT process, kwh_per_kg_target, kwh_per_kg_actual_ytd "
            "FROM scm.enpi_baseline WHERE process IN ('dyeing', 'finishing') "
            "ORDER BY process"
        )
    finally:
        await conn.close()

    assert len(rows) == 2, f"Expected 2 EnPI baseline rows, got {len(rows)}"
    by_process = {r["process"]: r for r in rows}

    assert "dyeing" in by_process, "dyeing EnPI baseline missing"
    assert float(by_process["dyeing"]["kwh_per_kg_target"]) == pytest.approx(3.80, abs=0.01)
    assert float(by_process["dyeing"]["kwh_per_kg_actual_ytd"]) == pytest.approx(4.12, abs=0.01)

    assert "finishing" in by_process, "finishing EnPI baseline missing"
    assert float(by_process["finishing"]["kwh_per_kg_target"]) == pytest.approx(2.20, abs=0.01)
    assert float(by_process["finishing"]["kwh_per_kg_actual_ytd"]) == pytest.approx(2.18, abs=0.01)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_inventory_levels_non_empty(seeded_dsn: str) -> None:
    """scm.inventory_levels is non-empty after seed."""
    n = await _count(seeded_dsn, "scm.inventory_levels")
    assert n > 0, "scm.inventory_levels is empty after seed"


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_inventory_below_reorder_point(seeded_dsn: str) -> None:
    """At least one inventory row is below its SKU's reorder_point.

    SCM-01 live reorder case: SKU-FAB-JERSEY-BLU (qty=310 < reorder_point=500)
    and SKU-SPARE-NEEDLE-L (qty=150 < reorder_point=200) must be present.
    """
    conn = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            """
            SELECT COUNT(*) AS n
            FROM (
                SELECT DISTINCT ON (il.sku_id) il.sku_id, il.quantity, sm.reorder_point
                FROM scm.inventory_levels il
                JOIN scm.sku_master sm USING (sku_id)
                ORDER BY il.sku_id, il.ts DESC
            ) latest
            WHERE quantity < reorder_point
            """
        )
    finally:
        await conn.close()

    assert int(row["n"]) >= 1, (
        "No inventory row is below its reorder_point — InventoryManager has no reorder case to detect"
    )


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_energy_readings_non_empty(seeded_dsn: str) -> None:
    """scm.energy_readings is non-empty after seed."""
    n = await _count(seeded_dsn, "scm.energy_readings")
    assert n > 0, "scm.energy_readings is empty after seed"


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_energy_readings_both_processes(seeded_dsn: str) -> None:
    """Both 'dyeing' and 'finishing' process values are present in energy readings."""
    conn = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        rows = await conn.fetch(
            "SELECT DISTINCT process FROM scm.energy_readings "
            "WHERE process IN ('dyeing', 'finishing')"
        )
    finally:
        await conn.close()

    processes = {r["process"] for r in rows}
    assert "dyeing" in processes, "No dyeing readings in scm.energy_readings after seed"
    assert "finishing" in processes, "No finishing readings in scm.energy_readings after seed"


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_historical_orders_two_sku_groups(seeded_dsn: str) -> None:
    """At least 2 distinct sku_group values in scm.historical_orders (jersey + twill)."""
    conn = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        rows = await conn.fetch(
            "SELECT DISTINCT sku_group FROM scm.historical_orders "
            "WHERE sku_group IN ('jersey', 'twill')"
        )
    finally:
        await conn.close()

    groups = {r["sku_group"] for r in rows}
    assert "jersey" in groups, "sku_group 'jersey' missing from historical_orders"
    assert "twill" in groups, "sku_group 'twill' missing from historical_orders"


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_historical_orders_18_monthly_buckets_jersey(seeded_dsn: str) -> None:
    """jersey sku_group has >=18 distinct monthly buckets in historical_orders."""
    conn = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            """
            SELECT COUNT(DISTINCT DATE_TRUNC('month', order_date)) AS buckets
            FROM scm.historical_orders
            WHERE sku_group = 'jersey'
            """
        )
    finally:
        await conn.close()

    assert int(row["buckets"]) >= 18, (
        f"Expected >=18 monthly buckets for jersey, got {row['buckets']}"
    )


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_historical_orders_18_monthly_buckets_twill(seeded_dsn: str) -> None:
    """twill sku_group has >=18 distinct monthly buckets in historical_orders."""
    conn = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            """
            SELECT COUNT(DISTINCT DATE_TRUNC('month', order_date)) AS buckets
            FROM scm.historical_orders
            WHERE sku_group = 'twill'
            """
        )
    finally:
        await conn.close()

    assert int(row["buckets"]) >= 18, (
        f"Expected >=18 monthly buckets for twill, got {row['buckets']}"
    )


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_seed_idempotent_double_apply(seeded_dsn: str) -> None:
    """Re-applying the seed is a no-op for tables with PRIMARY KEY.

    scm.sku_master, scm.enpi_baseline, and scm.historical_orders have a
    PRIMARY KEY and use ON CONFLICT DO NOTHING — their row counts must not
    change on re-apply.

    scm.inventory_levels and scm.energy_readings are TimescaleDB hypertables
    without a PRIMARY KEY (time-series by design). Their inserts use relative
    timestamps (NOW()) and accumulate on re-run; this is expected and correct
    for append-only time-series tables. Their idempotency is out of scope for
    this test.
    """
    # Tables with PRIMARY KEY — must be idempotent
    pk_tables = ("sku_master", "enpi_baseline", "historical_orders")

    conn = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        before = {
            tbl: await conn.fetchval(f"SELECT COUNT(*) FROM scm.{tbl}")
            for tbl in pk_tables
        }
    finally:
        await conn.close()

    # Second application
    seed_sql = _SEED_FILE.read_text(encoding="utf-8")
    conn2 = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=120.0)
    try:
        await conn2.execute(seed_sql)
    finally:
        await conn2.close()

    conn3 = await asyncpg.connect(seeded_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        after = {
            tbl: await conn3.fetchval(f"SELECT COUNT(*) FROM scm.{tbl}")
            for tbl in pk_tables
        }
    finally:
        await conn3.close()

    assert before == after, (
        f"Row counts changed on re-apply for PK tables — ON CONFLICT not working: "
        f"before={before}, after={after}"
    )
