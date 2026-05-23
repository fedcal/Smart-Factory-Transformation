"""Integration tests for `RateLimiter` (D-AD-03, Phase 6 Plan 06-02).

The PG-backed sliding-window rate limiter (12 alerts/h per agent) enforces the
threshold by COUNTing rows in `audit.actions` rather than holding per-process
state. This file exercises the 7 invariants from Plan 06-02:

  1. Under-limit count → ``(True, n)``.
  2. Exactly at limit → ``(False, limit)``.
  3. Above limit → ``(False, n)``.
  4. Sliding window: rows older than ``window_minutes`` are excluded.
  5. Per-agent isolation: rows for a different ``agent_id`` are not counted.
  6. Per-action-type isolation: rows for a different ``action_type`` are not
     counted.
  7. Restart resilience: a fresh ``RateLimiter`` instance over the same pool
     reads the same count (state lives in PG, not in the limiter).

Reference: Plan 06-02, Pattern 8 (06-PATTERNS.md lines 195-246), Pitfall 7
(`datetime.now(timezone.utc)` mandatory — never naive).

Every test:
  * is marked ``@pytest.mark.integration`` (gated behind docker / testcontainers);
  * spins up a fresh TimescaleDB container with the production migration set
    (001..007) applied so ``audit.actions`` exists with the Phase 6 CHECK
    constraint admitting ``Decision.SUPPRESSED``;
  * truncates ``audit.actions`` between cases to guarantee isolation.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

# Make repo root importable so `infra.migrations.timescale.migrate` resolves
# regardless of the pytest invocation cwd. Mirrors the pattern used by
# `infra/migrations/timescale/tests/test_migration_007.py`.
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ---------------------------------------------------------------------------
# Testcontainer + migration helpers
# ---------------------------------------------------------------------------

_TIMESCALE_IMAGE = "timescale/timescaledb:2.18.0-pg16"
_DB_USER = "sft"
_DB_PASS = "sft_dev_pass"
_DB_NAME = "sft"
_TARGET_AGENT = "anomaly-detector"
_TARGET_ACTION = "ANOMALY_ALERT"


@pytest.fixture(scope="module")
def _pg_dsn() -> Any:
    """Module-scoped TimescaleDB container with full migration set applied.

    Pre-applies migrations 001..007 so ``audit.actions`` exists with the
    Phase 6 CHECK constraint admitting ``'suppressed'``. The container is
    reused across tests in this module; isolation is enforced by the
    ``_truncate_audit_actions`` fixture (function-scoped).
    """
    pytest.importorskip("testcontainers.postgres")
    pytest.importorskip("asyncpg")
    from testcontainers.postgres import PostgresContainer  # noqa: PLC0415

    with PostgresContainer(
        image=_TIMESCALE_IMAGE,
        username=_DB_USER,
        password=_DB_PASS,
        dbname=_DB_NAME,
    ) as container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        dsn = f"postgresql://{_DB_USER}:{_DB_PASS}@{host}:{port}/{_DB_NAME}"

        import asyncio  # noqa: PLC0415

        from infra.migrations.timescale.migrate import migrate  # noqa: PLC0415

        # Use a dedicated event loop for fixture setup so the sync fixture body
        # does not collide with the running pytest-asyncio loop. pytest-asyncio
        # in "auto" mode owns the per-test loop; a fresh loop here keeps the
        # one-shot migration apply isolated.
        loop = asyncio.new_event_loop()
        try:
            rc = loop.run_until_complete(migrate(dsn))
        finally:
            loop.close()
        if rc != 0:
            raise RuntimeError("baseline migrations failed during fixture setup")
        yield dsn


@pytest.fixture
async def pg_pool(_pg_dsn: str) -> AsyncGenerator[Any, None]:
    """Function-scoped asyncpg.Pool against the module testcontainer.

    Truncates ``audit.actions`` on setup so every test starts from a clean
    slate (testcontainer is module-scoped — isolation lives here).
    """
    import asyncpg  # noqa: PLC0415

    pool = await asyncpg.create_pool(
        _pg_dsn, min_size=1, max_size=4, statement_cache_size=0
    )
    try:
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE audit.actions")
        yield pool
    finally:
        await pool.close()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

# Module-level SQL constant — T-V5-sql convention (NO f-string interpolation).
_SEED_SQL: str = (
    "INSERT INTO audit.actions "
    "(action_id, agent_id, thread_id, cluster, action_type, "
    " evidence_panel, decision, ts) "
    "VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)"
)


async def _seed_rows(
    pool: Any,
    *,
    count: int,
    agent_id: str = _TARGET_AGENT,
    action_type: str = _TARGET_ACTION,
    ts: datetime | None = None,
) -> None:
    """Insert ``count`` minimally-valid audit.actions rows.

    ``decision='auto'`` keeps us decoupled from migration 007 — these tests
    care about the COUNT path, not the SUPPRESSED enum (which Plan 06-06 wires
    via the caller of the limiter).
    """
    if ts is None:
        ts = datetime.now(UTC)
    async with pool.acquire() as conn:
        for _ in range(count):
            await conn.execute(
                _SEED_SQL,
                uuid4(),
                agent_id,
                "test-thread",
                "ops",
                action_type,
                "{}",
                "auto",
                ts,
            )


# ---------------------------------------------------------------------------
# Tests — 7 behaviours from Plan 06-02 Task 1 <behavior>.
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    ("seed_count", "expected_allowed", "expected_count"),
    [
        (5, True, 5),    # under limit
        (12, False, 12), # exactly at limit
        (15, False, 15), # above limit
    ],
)
async def test_check_and_emit_threshold_boundary(
    pg_pool: Any,
    seed_count: int,
    expected_allowed: bool,
    expected_count: int,
) -> None:
    """Tests 1-3: boundary behaviour at and around the 12/h limit."""
    from sft_agents.runtime.rate_limit import RateLimiter  # noqa: PLC0415

    await _seed_rows(pg_pool, count=seed_count)

    limiter = RateLimiter(pool=pg_pool, agent_id=_TARGET_AGENT)
    allowed, current = await limiter.check_and_emit(_TARGET_ACTION)

    assert allowed is expected_allowed
    assert current == expected_count


@pytest.mark.integration
async def test_sliding_window_excludes_old_rows(pg_pool: Any) -> None:
    """Test 4: rows older than ``window_minutes`` are excluded from the count."""
    from sft_agents.runtime.rate_limit import RateLimiter  # noqa: PLC0415

    now = datetime.now(UTC)
    # 12 rows 2h ago — outside the 60min window.
    await _seed_rows(pg_pool, count=12, ts=now - timedelta(hours=2))
    # 3 rows just now — inside the window.
    await _seed_rows(pg_pool, count=3, ts=now)

    limiter = RateLimiter(pool=pg_pool, agent_id=_TARGET_AGENT)
    allowed, current = await limiter.check_and_emit(_TARGET_ACTION)

    assert allowed is True
    assert current == 3


@pytest.mark.integration
async def test_per_agent_isolation(pg_pool: Any) -> None:
    """Test 5: rows for a different agent_id are not counted."""
    from sft_agents.runtime.rate_limit import RateLimiter  # noqa: PLC0415

    await _seed_rows(pg_pool, count=12, agent_id="other-agent")

    limiter = RateLimiter(pool=pg_pool, agent_id=_TARGET_AGENT)
    allowed, current = await limiter.check_and_emit(_TARGET_ACTION)

    assert allowed is True
    assert current == 0


@pytest.mark.integration
async def test_per_action_type_isolation(pg_pool: Any) -> None:
    """Test 6: rows for a different action_type are not counted."""
    from sft_agents.runtime.rate_limit import RateLimiter  # noqa: PLC0415

    await _seed_rows(pg_pool, count=12, action_type=_TARGET_ACTION)

    limiter = RateLimiter(pool=pg_pool, agent_id=_TARGET_AGENT)
    allowed, current = await limiter.check_and_emit("WRITE_PLC_SETPOINT")

    assert allowed is True
    assert current == 0


@pytest.mark.integration
async def test_restart_resilience(pg_pool: Any) -> None:
    """Test 7: a fresh ``RateLimiter`` instance reads the same count from PG.

    The limiter holds no per-process state; the source of truth is
    ``audit.actions`` (D-AD-03). A new instance with the same pool must see
    the same count as the previous instance — simulating container restart.
    """
    from sft_agents.runtime.rate_limit import RateLimiter  # noqa: PLC0415

    await _seed_rows(pg_pool, count=7)

    first = RateLimiter(pool=pg_pool, agent_id=_TARGET_AGENT)
    allowed_first, count_first = await first.check_and_emit(_TARGET_ACTION)
    assert allowed_first is True
    assert count_first == 7

    # Discard the first instance; "restart" by constructing a new one.
    del first
    second = RateLimiter(pool=pg_pool, agent_id=_TARGET_AGENT)
    allowed_second, count_second = await second.check_and_emit(_TARGET_ACTION)

    assert allowed_second is True
    assert count_second == 7
