"""
infra/migrations/timescale/tests/test_migration_013.py

Tests for migration 013_create_auth_users.sql.

Phase 10 — Plan 10-03 (dev-mode persona seeding).

The migration creates an `auth.auth_users` reference table and seeds 5 persona rows
(operator@mantis.it, supervisor@mantis.it, technician@mantis.it, cio@mantis.it,
admin@mantis.it) using INSERT ... ON CONFLICT DO NOTHING.

Test matrix (mirrors test_migration_012.py pattern):
    1. test_post_migration_creates_auth_schema        — after 013, auth schema exists
    2. test_post_migration_creates_auth_users_table   — after 013, auth.auth_users table exists
    3. test_post_migration_seeds_5_persona_rows       — exactly 5 rows seeded
    4. test_post_migration_seeded_row_emails          — all 5 expected email values present
    5. test_idempotent_double_apply                   — re-running 013 is a no-op (does not raise)
    6. test_migrate_runner_picks_up_013               — full migrate() runner applies 013

All tests run against isolated testcontainers Postgres+TimescaleDB (function-scoped).
Marked @pytest.mark.testcontainers AND @pytest.mark.integration.
"""
from __future__ import annotations

import sys
from pathlib import Path

import asyncpg
import pytest

# Make the workspace root importable (mirrors test_migration_012.py pattern).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from infra.migrations.timescale.migrate import migrate  # noqa: E402

_MIGRATION_013 = Path(__file__).parent.parent / "013_create_auth_users.sql"

# The 5 seeded persona emails (10-UI-SPEC Dev-Mode JWT table, jwt.py SEEDED_USERS).
_SEEDED_EMAILS = (
    "operator@mantis.it",
    "supervisor@mantis.it",
    "technician@mantis.it",
    "cio@mantis.it",
    "admin@mantis.it",
)


async def _run_baseline_migrations(dsn: str) -> None:
    """Apply migrations 001..012 (excluding 013) against the given DSN.

    Bypasses the migrate() runner so 013 is not picked up by the glob.
    Mirrors the pattern in test_migration_012.py._run_baseline_migrations.
    """
    migrations_dir = Path(__file__).parent.parent
    baseline_files = sorted(
        f for f in migrations_dir.glob("[0-9][0-9][0-9]_*.sql") if f.name < "013"
    )
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        for sql_file in baseline_files:
            await conn.execute(sql_file.read_text(encoding="utf-8"))
    finally:
        await conn.close()


async def _apply_013(dsn: str) -> None:
    """Apply only 013_create_auth_users.sql against the provided DSN."""
    sql = _MIGRATION_013.read_text(encoding="utf-8")
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


@pytest.fixture(scope="function")
async def fresh_dsn() -> str:
    """Yield a fresh TimescaleDB DSN per test (function-scoped, NOT shared).

    Mirrors the function-scoped fixture in test_migration_012.py.
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
async def test_post_migration_creates_auth_schema(fresh_dsn: str) -> None:
    """After 013, the `auth` schema exists in the database."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_013(fresh_dsn)

    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            "SELECT schema_name FROM information_schema.schemata"
            " WHERE schema_name = 'auth'"
        )
        assert row is not None, "auth schema must exist after migration 013"
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_creates_auth_users_table(fresh_dsn: str) -> None:
    """After 013, the `auth.auth_users` table exists with the expected columns."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_013(fresh_dsn)

    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = 'auth' AND table_name = 'auth_users'"
        )
        assert row is not None, "auth.auth_users table must exist after migration 013"

        # Verify expected columns are present
        cols = await conn.fetch(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema = 'auth' AND table_name = 'auth_users'"
        )
        col_names = {r["column_name"] for r in cols}
        expected_cols = {"email", "role", "display_name", "created_at"}
        assert expected_cols.issubset(col_names), (
            f"Missing columns in auth.auth_users: {expected_cols - col_names}"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_seeds_5_persona_rows(fresh_dsn: str) -> None:
    """After 013, exactly 5 persona rows are seeded in auth.auth_users."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_013(fresh_dsn)

    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM auth.auth_users")
        assert row is not None
        count = int(row["cnt"])
        assert count == 5, (
            f"Expected 5 seeded rows in auth.auth_users, got {count}"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("email", _SEEDED_EMAILS)
async def test_post_migration_seeded_row_emails(fresh_dsn: str, email: str) -> None:
    """After 013, each of the 5 persona email addresses is present in auth.auth_users."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_013(fresh_dsn)

    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow(
            "SELECT email, role, display_name FROM auth.auth_users WHERE email = $1",
            email,
        )
        assert row is not None, f"Expected seeded row for email={email!r} but found none"
        assert row["role"] is not None, f"role must not be null for {email!r}"
        assert row["display_name"] is not None, f"display_name must not be null for {email!r}"
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_idempotent_double_apply(fresh_dsn: str) -> None:
    """Re-applying migration 013 a second time must NOT raise (idempotency).

    ON CONFLICT DO NOTHING ensures re-seeding is a no-op.
    CREATE TABLE IF NOT EXISTS / CREATE SCHEMA IF NOT EXISTS guard schema/table.
    """
    await _run_baseline_migrations(fresh_dsn)
    await _apply_013(fresh_dsn)
    # Second apply — must be a no-op
    await _apply_013(fresh_dsn)

    # After double-apply, still exactly 5 rows (no duplicates)
    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM auth.auth_users")
        assert row is not None
        count = int(row["cnt"])
        assert count == 5, (
            f"Double-apply must not duplicate rows; expected 5, got {count}"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrate_runner_picks_up_013(fresh_dsn: str) -> None:
    """The migrate.py runner globs 013 automatically and applies it in order."""
    rc = await migrate(fresh_dsn)
    assert rc == 0

    # After the full migrate() run, auth.auth_users must have the 5 seeded rows
    conn = await asyncpg.connect(fresh_dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM auth.auth_users")
        assert row is not None
        count = int(row["cnt"])
        assert count == 5, (
            f"Full migrate() must seed 5 auth_users rows; got {count}"
        )
        # Verify operator@mantis.it is present (documented in plan artifacts)
        op_row = await conn.fetchrow(
            "SELECT email FROM auth.auth_users WHERE email = 'operator@mantis.it'"
        )
        assert op_row is not None, "operator@mantis.it must be seeded by migration 013"
    finally:
        await conn.close()
