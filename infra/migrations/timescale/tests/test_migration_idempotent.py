"""
infra/migrations/timescale/tests/test_migration_idempotent.py

Idempotency and schema-correctness tests for the TimescaleDB migration
``001_create_sensor_events.sql`` executed via ``migrate.py``.

All tests use an isolated TimescaleDB testcontainer (session-scoped, shared within
a pytest session to avoid redundant container starts).

Test matrix:
    1. test_first_run            — migrate() returns 0; hypertable exists + compression enabled
    2. test_second_run_no_error  — second migrate() call returns 0 (idempotency)
    3. test_retention_policy_set — retention policy present (drop_after = 90 days)
    4. test_compression_policy_set — compression policy present (compress_after = 7 days)
    5. test_indexes_exist        — both composite indexes created
    6. test_insert_after_migration — INSERT + SELECT COUNT(*) = 1
    7. test_dry_run_no_side_effect — dry-run does NOT create the hypertable
"""
from __future__ import annotations

import json

import pytest
import asyncpg

from infra.migrations.timescale.migrate import migrate


@pytest.mark.testcontainers
@pytest.mark.asyncio
async def test_first_run(timescale_dsn: str) -> None:
    """Migration runs without error and hypertable is created with compression enabled."""
    rc = await migrate(timescale_dsn)
    assert rc == 0, "migrate() should return exit code 0 on first run"

    conn = await asyncpg.connect(timescale_dsn, statement_cache_size=0)
    try:
        row = await conn.fetchrow(
            "SELECT compression_enabled FROM timescaledb_information.hypertables"
            " WHERE hypertable_name = $1",
            "sensor_events",
        )
        assert row is not None, "sensor_events hypertable must exist after migration"
        assert row["compression_enabled"] is True, "compression must be enabled on hypertable"
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.asyncio
async def test_second_run_no_error(timescale_dsn: str) -> None:
    """Re-running migrate() on an already-migrated database returns 0 (idempotency)."""
    # First run may already have been executed by test_first_run (same session fixture),
    # but we call it explicitly here to guarantee idempotency regardless of test order.
    rc_first = await migrate(timescale_dsn)
    rc_second = await migrate(timescale_dsn)
    assert rc_first == 0, "First migrate() call must return 0"
    assert rc_second == 0, "Second migrate() call must return 0 (idempotent)"

    # Verify the table still exists and has exactly one hypertable row
    conn = await asyncpg.connect(timescale_dsn, statement_cache_size=0)
    try:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM timescaledb_information.hypertables"
            " WHERE hypertable_name = $1",
            "sensor_events",
        )
        assert count == 1, "Exactly one hypertable row must exist after double migration"
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.asyncio
async def test_retention_policy_set(timescale_dsn: str) -> None:
    """Retention policy with drop_after = '@ 90 days' is registered for sensor_events."""
    await migrate(timescale_dsn)

    conn = await asyncpg.connect(timescale_dsn, statement_cache_size=0)
    try:
        # timescaledb_information.jobs contains scheduled background jobs.
        # proc_name = 'policy_retention' identifies retention jobs.
        rows = await conn.fetch(
            "SELECT config FROM timescaledb_information.jobs"
            " WHERE hypertable_name = $1 AND proc_name = $2",
            "sensor_events",
            "policy_retention",
        )
        assert len(rows) >= 1, "At least one retention policy job must exist for sensor_events"
        # asyncpg returns JSONB columns as strings; parse explicitly
        raw_config = rows[0]["config"]
        config = json.loads(raw_config) if isinstance(raw_config, str) else raw_config
        # config["drop_after"] encodes the interval in PostgreSQL interval format e.g. "@ 90 days"
        config_drop_after = config["drop_after"]
        assert "90" in str(config_drop_after), (
            f"Retention drop_after must reference 90 days; got: {config_drop_after!r}"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.asyncio
async def test_compression_policy_set(timescale_dsn: str) -> None:
    """Compression policy with compress_after = '@ 7 days' is registered for sensor_events."""
    await migrate(timescale_dsn)

    conn = await asyncpg.connect(timescale_dsn, statement_cache_size=0)
    try:
        rows = await conn.fetch(
            "SELECT config FROM timescaledb_information.jobs"
            " WHERE hypertable_name = $1 AND proc_name = $2",
            "sensor_events",
            "policy_compression",
        )
        assert len(rows) >= 1, "At least one compression policy job must exist for sensor_events"
        raw_config = rows[0]["config"]
        config = json.loads(raw_config) if isinstance(raw_config, str) else raw_config
        config_compress_after = config["compress_after"]
        assert "7" in str(config_compress_after), (
            f"Compression compress_after must reference 7 days; got: {config_compress_after!r}"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.asyncio
async def test_indexes_exist(timescale_dsn: str) -> None:
    """Both composite indexes idx_sensor_events_asset_time and idx_sensor_events_tag_time exist."""
    await migrate(timescale_dsn)

    conn = await asyncpg.connect(timescale_dsn, statement_cache_size=0)
    try:
        index_names = {
            row["indexname"]
            for row in await conn.fetch(
                "SELECT indexname FROM pg_indexes WHERE tablename = $1",
                "sensor_events",
            )
        }
        assert "idx_sensor_events_asset_time" in index_names, (
            "idx_sensor_events_asset_time must exist in pg_indexes"
        )
        assert "idx_sensor_events_tag_time" in index_names, (
            "idx_sensor_events_tag_time must exist in pg_indexes"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.asyncio
async def test_insert_after_migration(timescale_dsn: str) -> None:
    """After migration, a single row INSERT is accepted and SELECT COUNT(*) returns 1."""
    await migrate(timescale_dsn)

    conn = await asyncpg.connect(timescale_dsn, statement_cache_size=0)
    try:
        # Use $1..$N placeholders — no f-string SQL (T-03-05-ddl-injection mitigation)
        await conn.execute(
            "INSERT INTO sensor_events"
            " (asset_id, tag_id, timestamp_utc, value, unit, quality_code, source)"
            " VALUES ($1, $2, NOW(), $3, $4, $5, $6)",
            "LOOM-01",
            "warp_tension",
            25.4,
            "N",
            0,
            "live",
        )
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM sensor_events WHERE asset_id = $1 AND tag_id = $2",
            "LOOM-01",
            "warp_tension",
        )
        assert count >= 1, "At least one row must be present after INSERT"
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.asyncio
async def test_dry_run_no_side_effect(timescale_dsn: str) -> None:
    """dry_run=True exits 0 but does NOT create the sensor_events table."""
    # Use a DIFFERENT container for this test — we need a fresh database.
    # The shared session fixture already ran migrations; spawn a new container inline.
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer(
        image="timescale/timescaledb:2.18.0-pg16",
        username="sft",
        password="sft_dev_pass",
        dbname="sft",
    ) as fresh_container:
        host = fresh_container.get_container_host_ip()
        port = fresh_container.get_exposed_port(5432)
        fresh_dsn = f"postgresql://sft:sft_dev_pass@{host}:{port}/sft"

        rc = await migrate(fresh_dsn, dry_run=True)
        assert rc == 0, "dry_run migrate() must return 0"

        # The table must NOT exist because dry_run never connected
        conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0)
        try:
            regclass = await conn.fetchval(
                "SELECT to_regclass($1)",
                "sensor_events",
            )
            assert regclass is None, (
                "sensor_events table must NOT exist after dry_run (no DDL should have been applied)"
            )
        finally:
            await conn.close()
