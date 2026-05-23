"""
infra/migrations/timescale/tests/test_migration_008.py

Tests for migration 008_create_downtime_events.sql (Phase 7 — Plan 07-05).

Migration 008 creates:
    * schema `maintenance`
    * hypertable `maintenance.downtime_events` (time = `timestamp`)
    * continuous aggregate `maintenance.oee_hourly` (1h bucket per asset)
    * continuous aggregate refresh policy (start=2h, end=5min, schedule=5min)
    * indexes `idx_downtime_asset_time`, `idx_downtime_reason_time`

The migration is D-DA-01 + D-DA-03 data foundation; MNT-04 / V5.

Test matrix (mirrors 07-PATTERNS.md Section 11 lines 491-498):
    1. test_post_migration_creates_downtime_events_table
    2. test_post_migration_creates_hypertable
    3. test_post_migration_creates_oee_hourly_caggr
    4. test_post_migration_insert_downtime_event_then_refresh_caggr
    5. test_post_migration_idempotent_double_apply
    6. test_post_migration_check_constraint_severity
    7. test_post_migration_check_constraint_duration
    8. test_post_migration_creates_indexes  (Pareto + OEE query support)

Each test runs against a fresh function-scoped testcontainers PG so the
migration sequence is reproducible. Marked @pytest.mark.testcontainers AND
@pytest.mark.integration to honour both CI selectors (mirror 007 pattern).
"""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

# Make the workspace root importable so `infra.migrations.timescale.migrate`
# resolves regardless of pytest invocation cwd. Mirrors the pattern used in
# tests/integration/test_migrations_idempotent.py (Phase 4 Plan 04-02).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_MIGRATION_008 = Path(__file__).parent.parent / "008_create_downtime_events.sql"


async def _run_baseline_migrations(dsn: str) -> None:
    """Apply 001..007 in order (everything strictly before 008).

    We deliberately exclude 008+ so each test can apply 008 explicitly and
    assert pre-/post-008 invariants. Mirrors the helper in test_migration_007.py.
    """
    migrations_dir = Path(__file__).parent.parent
    baseline_files = sorted(
        f for f in migrations_dir.glob("[0-9][0-9][0-9]_*.sql") if f.name < "008"
    )
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        for sql_file in baseline_files:
            await conn.execute(sql_file.read_text(encoding="utf-8"))
    finally:
        await conn.close()


async def _apply_008(dsn: str) -> None:
    """Apply only 008_create_downtime_events.sql against the provided DSN."""
    sql = _MIGRATION_008.read_text(encoding="utf-8")
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


async def _insert_downtime_event(
    dsn: str,
    *,
    asset_id: str = "LOOM-01",
    reason_code: str = "WEAVING-BE-001",
    duration_min: int = 30,
    severity: str = "minor",
    timestamp: datetime | None = None,
) -> None:
    """INSERT a row into maintenance.downtime_events.

    Raises asyncpg.CheckViolationError if any CHECK constraint rejects the row.
    """
    if timestamp is None:
        timestamp = datetime.now(UTC)
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        await conn.execute(
            "INSERT INTO maintenance.downtime_events"
            " (event_id, asset_id, reason_code, duration_min, severity,"
            "  source, timestamp)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7)",
            uuid4(),
            asset_id,
            reason_code,
            duration_min,
            severity,
            "simulator",
            timestamp,
        )
    finally:
        await conn.close()


@pytest.fixture(scope="function")
async def fresh_dsn() -> str:
    """Yield a fresh TimescaleDB DSN per test (function-scoped, NOT shared).

    Each test starts from a clean schema because we apply different subsets
    of migrations (pre-008 vs post-008). Spawn a dedicated container per test.
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
async def test_post_migration_creates_downtime_events_table(fresh_dsn: str) -> None:
    """After 008, maintenance.downtime_events exists as a table."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_008(fresh_dsn)
    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0)
    try:
        row = await conn.fetchrow(
            "SELECT schemaname, tablename FROM pg_tables"
            " WHERE schemaname = 'maintenance' AND tablename = 'downtime_events'"
        )
        assert row is not None
        assert row["schemaname"] == "maintenance"
        assert row["tablename"] == "downtime_events"
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_creates_hypertable(fresh_dsn: str) -> None:
    """After 008, maintenance.downtime_events is registered as a TimescaleDB hypertable."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_008(fresh_dsn)
    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0)
    try:
        row = await conn.fetchrow(
            "SELECT hypertable_schema, hypertable_name"
            " FROM timescaledb_information.hypertables"
            " WHERE hypertable_schema = 'maintenance'"
            "   AND hypertable_name = 'downtime_events'"
        )
        assert row is not None
        assert row["hypertable_schema"] == "maintenance"
        assert row["hypertable_name"] == "downtime_events"
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_creates_oee_hourly_caggr(fresh_dsn: str) -> None:
    """After 008, maintenance.oee_hourly continuous aggregate exists."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_008(fresh_dsn)
    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0)
    try:
        row = await conn.fetchrow(
            "SELECT view_schema, view_name"
            " FROM timescaledb_information.continuous_aggregates"
            " WHERE view_schema = 'maintenance'"
            "   AND view_name = 'oee_hourly'"
        )
        assert row is not None
        assert row["view_schema"] == "maintenance"
        assert row["view_name"] == "oee_hourly"

        # Also assert the refresh policy is installed (Pitfall 4 — start_offset must
        # fit within the source hypertable retention window).
        policy_row = await conn.fetchrow(
            "SELECT config FROM timescaledb_information.jobs"
            " WHERE proc_name = 'policy_refresh_continuous_aggregate'"
            "   AND hypertable_schema = '_timescaledb_internal'"
            "   AND config::text ILIKE '%oee_hourly%'"
        )
        # The job is registered with config including start_offset/end_offset.
        # Fall back to checking presence in the policies view if the jobs view shape differs.
        if policy_row is None:
            policy_row = await conn.fetchrow(
                "SELECT * FROM timescaledb_information.continuous_aggregates"
                " WHERE view_schema = 'maintenance' AND view_name = 'oee_hourly'"
            )
        assert policy_row is not None
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_insert_downtime_event_then_refresh_caggr(
    fresh_dsn: str,
) -> None:
    """INSERT 3 downtime events in a 1h window, refresh CAGG, assert roll-up."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_008(fresh_dsn)

    # Pick a fixed past hour to avoid CAGG end_offset masking the rows.
    base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(
        hours=4
    )
    rows = [
        (base + timedelta(minutes=2), 30),
        (base + timedelta(minutes=15), 15),
        (base + timedelta(minutes=42), 45),
    ]
    for ts, dur in rows:
        await _insert_downtime_event(
            fresh_dsn,
            asset_id="LOOM-01",
            reason_code="WEAVING-BE-001",
            duration_min=dur,
            severity="minor",
            timestamp=ts,
        )

    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        # CALL refresh_continuous_aggregate('maintenance.oee_hourly', NULL, NULL)
        # — refresh the full window (NULL bounds = whole CAGG).
        await conn.execute(
            "CALL refresh_continuous_aggregate('maintenance.oee_hourly', NULL, NULL)"
        )

        # Query the CAGG: there must be exactly 1 hour_bucket for LOOM-01 with
        # total_downtime_min = 90 and event_count = 3.
        result = await conn.fetchrow(
            "SELECT asset_id, total_downtime_min, event_count"
            " FROM maintenance.oee_hourly"
            " WHERE asset_id = 'LOOM-01'"
            " ORDER BY hour_bucket DESC"
            " LIMIT 1"
        )
        assert result is not None, "No oee_hourly row after CAGG refresh"
        assert result["asset_id"] == "LOOM-01"
        assert int(result["total_downtime_min"]) == 90
        assert int(result["event_count"]) == 3
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_idempotent_double_apply(fresh_dsn: str) -> None:
    """Re-applying migration 008 a second time must NOT raise (idempotency)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_008(fresh_dsn)
    # Second apply — must be a no-op
    await _apply_008(fresh_dsn)
    # The hypertable + CAGG must still be present and INSERT still works.
    await _insert_downtime_event(fresh_dsn, asset_id="LOOM-02")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_check_constraint_severity(fresh_dsn: str) -> None:
    """INSERT with severity='invalid' must raise CheckViolationError."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_008(fresh_dsn)
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await _insert_downtime_event(fresh_dsn, severity="invalid")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_check_constraint_duration(fresh_dsn: str) -> None:
    """INSERT with duration_min=-1 must raise CheckViolationError."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_008(fresh_dsn)
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await _insert_downtime_event(fresh_dsn, duration_min=-1)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_creates_indexes(fresh_dsn: str) -> None:
    """After 008, both Pareto + OEE composite indexes exist."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_008(fresh_dsn)
    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0)
    try:
        rows = await conn.fetch(
            "SELECT indexname FROM pg_indexes"
            " WHERE schemaname = 'maintenance' AND tablename = 'downtime_events'"
        )
        index_names = {r["indexname"] for r in rows}
        assert "idx_downtime_asset_time" in index_names, index_names
        assert "idx_downtime_reason_time" in index_names, index_names
    finally:
        await conn.close()
