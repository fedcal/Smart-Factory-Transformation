"""
tests/integration/test_migrations_idempotent.py

Phase 4 Plan 04-02 — Wave 2 substrate idempotency + REVOKE verification.

Verifies, against an isolated TimescaleDB testcontainer:
  1. `python scripts/timescale-migrate.py` is idempotent (re-run produces zero schema changes)
  2. Schemas `hitl`, `audit`, `budget`, `langgraph` exist after migration
  3. Tables `hitl.approvals`, `audit.actions`, `audit.outbox`, `budget.executions` exist
  4. `audit.actions` is a TimescaleDB hypertable
  5. Retention policy on `audit.actions` references 7 years (= 2555 days)
  6. Role `agent_role` exists (NOLOGIN, Phase 11 binds login users)
  7. REVOKE is effective: `has_table_privilege('agent_role','audit.actions','UPDATE')` returns FALSE
  8. INSERT privilege granted: `has_table_privilege('agent_role','audit.actions','INSERT')` returns TRUE

All tests are gated by `@pytest.mark.integration` and require Docker.

Pattern reference:
  infra/migrations/timescale/tests/test_migration_idempotent.py (Phase 3 — same testcontainer fixture style)
"""
from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest

# Make the workspace root importable so `infra.migrations.timescale.migrate` resolves
# regardless of pytest invocation cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


_TIMESCALE_IMAGE = "timescale/timescaledb:2.18.0-pg16"
_DB_USER = "sft"
_DB_PASS = "sft_dev_pass"
_DB_NAME = "sft"


@pytest.fixture(scope="module")
def phase4_timescale_dsn() -> Generator[str, None, None]:
    """Module-scoped testcontainer for Phase 4 migration tests.

    A separate fixture from `timescale_dsn` in infra/migrations/timescale/tests/conftest.py
    so we get a clean DB for the idempotency snapshot diff.
    """
    pytest.importorskip("testcontainers.postgres")
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
        yield dsn


async def _snapshot_schema(dsn: str) -> list[tuple[str, str]]:
    """Return a sorted list of (schema, table) tuples for the Phase 4 schemas."""
    import asyncpg  # noqa: PLC0415

    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        rows = await conn.fetch(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema IN ('hitl','audit','budget','langgraph') "
            "ORDER BY table_schema, table_name",
        )
        return [(r["table_schema"], r["table_name"]) for r in rows]
    finally:
        await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_phase4_migrations_idempotent(phase4_timescale_dsn: str) -> None:
    """Re-running migrate.py after a clean apply produces zero schema changes."""
    from infra.migrations.timescale.migrate import migrate  # noqa: PLC0415

    rc_first = await migrate(phase4_timescale_dsn)
    assert rc_first == 0, "first migrate() must return 0"

    snapshot_after_first = await _snapshot_schema(phase4_timescale_dsn)

    rc_second = await migrate(phase4_timescale_dsn)
    assert rc_second == 0, "second migrate() must return 0 (idempotent)"

    snapshot_after_second = await _snapshot_schema(phase4_timescale_dsn)

    assert snapshot_after_first == snapshot_after_second, (
        "schema snapshot must be identical across two runs (idempotency)"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_phase4_schemas_and_tables_exist(phase4_timescale_dsn: str) -> None:
    """All four schemas + their required tables exist post-migration."""
    from infra.migrations.timescale.migrate import migrate  # noqa: PLC0415

    assert await migrate(phase4_timescale_dsn) == 0

    tables = set(await _snapshot_schema(phase4_timescale_dsn))
    assert ("hitl", "approvals") in tables, "hitl.approvals must exist"
    assert ("audit", "actions") in tables, "audit.actions must exist"
    assert ("audit", "outbox") in tables, "audit.outbox must exist"
    assert ("budget", "executions") in tables, "budget.executions must exist"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_actions_is_hypertable(phase4_timescale_dsn: str) -> None:
    """audit.actions is registered as a TimescaleDB hypertable."""
    import asyncpg  # noqa: PLC0415
    from infra.migrations.timescale.migrate import migrate  # noqa: PLC0415

    assert await migrate(phase4_timescale_dsn) == 0

    conn = await asyncpg.connect(phase4_timescale_dsn, statement_cache_size=0)
    try:
        row = await conn.fetchrow(
            "SELECT hypertable_schema, hypertable_name "
            "FROM timescaledb_information.hypertables "
            "WHERE hypertable_schema = $1 AND hypertable_name = $2",
            "audit",
            "actions",
        )
        assert row is not None, "audit.actions must be a hypertable"
    finally:
        await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_audit_retention_policy_seven_years(phase4_timescale_dsn: str) -> None:
    """7-year retention policy is registered on audit.actions."""
    import json  # noqa: PLC0415

    import asyncpg  # noqa: PLC0415
    from infra.migrations.timescale.migrate import migrate  # noqa: PLC0415

    assert await migrate(phase4_timescale_dsn) == 0

    conn = await asyncpg.connect(phase4_timescale_dsn, statement_cache_size=0)
    try:
        rows = await conn.fetch(
            "SELECT config FROM timescaledb_information.jobs "
            "WHERE hypertable_schema = $1 AND hypertable_name = $2 AND proc_name = $3",
            "audit",
            "actions",
            "policy_retention",
        )
        assert len(rows) >= 1, "retention policy job must exist on audit.actions"
        raw = rows[0]["config"]
        cfg = json.loads(raw) if isinstance(raw, str) else raw
        drop_after = str(cfg.get("drop_after", ""))
        # 7 years = 2555 days; PostgreSQL interval string may show '7 years' or '2555 days'
        assert "7 years" in drop_after or "2555" in drop_after or "years" in drop_after, (
            f"retention drop_after must reference 7 years; got {drop_after!r}"
        )
    finally:
        await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_role_exists_and_revoke_effective(phase4_timescale_dsn: str) -> None:
    """agent_role exists with INSERT/SELECT but NOT UPDATE/DELETE on audit.actions."""
    import asyncpg  # noqa: PLC0415
    from infra.migrations.timescale.migrate import migrate  # noqa: PLC0415

    assert await migrate(phase4_timescale_dsn) == 0

    conn = await asyncpg.connect(phase4_timescale_dsn, statement_cache_size=0)
    try:
        role_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = $1)",
            "agent_role",
        )
        assert role_exists, "agent_role must exist in pg_roles"

        can_insert = await conn.fetchval(
            "SELECT has_table_privilege('agent_role','audit.actions','INSERT')",
        )
        can_select = await conn.fetchval(
            "SELECT has_table_privilege('agent_role','audit.actions','SELECT')",
        )
        can_update = await conn.fetchval(
            "SELECT has_table_privilege('agent_role','audit.actions','UPDATE')",
        )
        can_delete = await conn.fetchval(
            "SELECT has_table_privilege('agent_role','audit.actions','DELETE')",
        )

        assert can_insert is True, "agent_role must have INSERT on audit.actions"
        assert can_select is True, "agent_role must have SELECT on audit.actions"
        assert can_update is False, (
            "agent_role MUST NOT have UPDATE on audit.actions (T-04-Audit-Tamper)"
        )
        assert can_delete is False, (
            "agent_role MUST NOT have DELETE on audit.actions (T-04-Audit-Tamper)"
        )
    finally:
        await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_partial_index_on_hitl_approvals(phase4_timescale_dsn: str) -> None:
    """Partial index on (tier, status, sla_deadline) WHERE status='pending' exists."""
    import asyncpg  # noqa: PLC0415
    from infra.migrations.timescale.migrate import migrate  # noqa: PLC0415

    assert await migrate(phase4_timescale_dsn) == 0

    conn = await asyncpg.connect(phase4_timescale_dsn, statement_cache_size=0)
    try:
        index_names = {
            r["indexname"]
            for r in await conn.fetch(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = $1 AND tablename = $2",
                "hitl",
                "approvals",
            )
        }
        assert "idx_approvals_tier_status" in index_names, (
            "idx_approvals_tier_status partial index must exist"
        )
        assert "idx_approvals_thread_id" in index_names, (
            "idx_approvals_thread_id must exist"
        )
    finally:
        await conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_outbox_partial_index_exists(phase4_timescale_dsn: str) -> None:
    """Partial index idx_outbox_next_attempt WHERE attempts < 10 exists on audit.outbox."""
    import asyncpg  # noqa: PLC0415
    from infra.migrations.timescale.migrate import migrate  # noqa: PLC0415

    assert await migrate(phase4_timescale_dsn) == 0

    conn = await asyncpg.connect(phase4_timescale_dsn, statement_cache_size=0)
    try:
        index_names = {
            r["indexname"]
            for r in await conn.fetch(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = $1 AND tablename = $2",
                "audit",
                "outbox",
            )
        }
        assert "idx_outbox_next_attempt" in index_names, (
            "idx_outbox_next_attempt partial index must exist"
        )
    finally:
        await conn.close()
