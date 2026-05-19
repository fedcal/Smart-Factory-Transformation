"""Shared pytest fixtures for svc-knowledge-ingest test suite (Phase 5, Plan 05-06).

Provides:
    timescale_dsn   — session-scoped TimescaleDB testcontainer (mirrors
                      infra/migrations/timescale/tests/conftest.py).
    pg_pool         — function-scoped asyncpg.Pool, migrations applied,
                      knowledge.ingest_state truncated between tests.

All integration tests are marked ``@pytest.mark.integration``; Docker must be
available. The container image matches infra/compose/core.yml convention.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

# Make ``infra.migrations.timescale.migrate`` importable without requiring the
# infra/ tree to be installed as a workspace package (it is a script tree, not
# a pip-installable package). Mirrors scripts/timescale-migrate.py pattern S-3.
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

from infra.migrations.timescale.migrate import migrate  # noqa: E402

_TIMESCALE_IMAGE = "timescale/timescaledb:2.18.0-pg16"
_DB_USER = "sft"
_DB_PASS = "sft_dev_pass"
_DB_NAME = "sft"


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers locally so ``--strict-markers`` (if enabled) passes."""
    config.addinivalue_line(
        "markers",
        "integration: requires testcontainers Qdrant+Neo4j+PG",
    )


@pytest.fixture(scope="session")
def timescale_dsn() -> Generator[str, None, None]:
    """Yield a DSN for a fresh session-scoped TimescaleDB testcontainer."""
    with PostgresContainer(
        image=_TIMESCALE_IMAGE,
        username=_DB_USER,
        password=_DB_PASS,
        dbname=_DB_NAME,
    ) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        dsn = f"postgresql://{_DB_USER}:{_DB_PASS}@{host}:{port}/{_DB_NAME}"
        yield dsn


@pytest_asyncio.fixture(scope="session")
async def _migrated_dsn(timescale_dsn: str) -> AsyncGenerator[str, None]:
    """Apply all migrations once per session; subsequent tests reuse the schema."""
    rc = await migrate(timescale_dsn)
    if rc != 0:
        raise RuntimeError(f"timescale migrate() failed with rc={rc}")
    yield timescale_dsn


@pytest_asyncio.fixture
async def pg_pool(_migrated_dsn: str) -> AsyncGenerator[asyncpg.Pool, None]:
    """Provide an asyncpg pool against a migrated testcontainer.

    Truncates ``knowledge.ingest_state`` before yielding so each test sees an
    empty table (deterministic seed — Pattern S-2).
    ``statement_cache_size=0`` is required for TimescaleDB DDL compatibility
    (Pitfall 6 — also applies to plain PG when sharing the image).
    """
    pool = await asyncpg.create_pool(
        _migrated_dsn,
        min_size=1,
        max_size=4,
        statement_cache_size=0,
        command_timeout=30.0,
    )
    assert pool is not None
    try:
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE knowledge.ingest_state")
        yield pool
    finally:
        await pool.close()
