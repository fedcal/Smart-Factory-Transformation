"""
infra/migrations/timescale/tests/test_migration_007.py

Tests for migration 007_extend_audit_decisions.sql.

Phase 6 — Plan 06-01 (D-AD-03 suppressed + D-OA-02 logged + escalation/quality/schedule/anomaly action types).

The migration extends the `audit.actions.decision` CHECK constraint to admit
the new values `'suppressed'` and `'logged'`, and adds a NEW named CHECK
constraint on `audit.actions.action_type` admitting the Phase 6 action-type
labels (no action_type CHECK existed before this migration — verified against
003_create_audit_actions.sql line 30).

Test matrix:
    1. test_pre_migration_rejects_suppressed     — before 007, INSERT 'suppressed' raises CheckViolationError
    2. test_post_migration_admits_suppressed     — after 007, INSERT 'suppressed' succeeds
    3. test_post_migration_admits_logged         — after 007, INSERT 'logged' succeeds
    4. test_post_migration_legacy_decisions_ok   — existing decisions still admitted
    5. test_post_migration_admits_new_action_types — new action_type values admitted
    6. test_idempotent_double_apply              — re-running 007 is a no-op (does not raise)

All tests run against an isolated testcontainers Postgres+TimescaleDB session-scoped
container (see conftest.py). Marked @pytest.mark.testcontainers AND
@pytest.mark.integration so they pick up under both CI selectors.
"""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

from infra.migrations.timescale.migrate import migrate

_MIGRATION_007 = Path(__file__).parent.parent / "007_extend_audit_decisions.sql"


async def _run_baseline_migrations(dsn: str) -> None:
    """Apply 001..006 via the migration runner (skips 007 if not yet present).

    The runner globs `[0-9][0-9][0-9]_*.sql`. We rely on it to apply all
    migrations sorted by filename. For tests that exercise pre-007 state, we
    temporarily rename 007 out of the glob path? No — instead we apply 001..006
    by reading and executing them directly, in order, so 007 is not picked up.
    """
    migrations_dir = Path(__file__).parent.parent
    baseline_files = sorted(
        f for f in migrations_dir.glob("[0-9][0-9][0-9]_*.sql") if f.name < "007"
    )
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        for sql_file in baseline_files:
            await conn.execute(sql_file.read_text(encoding="utf-8"))
    finally:
        await conn.close()


async def _apply_007(dsn: str) -> None:
    """Apply only 007_extend_audit_decisions.sql against the provided DSN."""
    sql = _MIGRATION_007.read_text(encoding="utf-8")
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        await conn.execute(sql)
    finally:
        await conn.close()


async def _insert_action(
    dsn: str,
    *,
    decision: str = "auto",
    action_type: str = "WRITE_PLC_SETPOINT",
) -> None:
    """Attempt to INSERT a minimally-valid row into audit.actions.

    Raises asyncpg.CheckViolationError if any CHECK constraint rejects the row.
    Decision='auto' satisfies the audit_actions_hitl_motivation_chk constraint
    (no motivation/approval_id required).
    """
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        await conn.execute(
            "INSERT INTO audit.actions"
            " (action_id, agent_id, thread_id, cluster, action_type,"
            "  evidence_panel, decision)"
            " VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)",
            uuid4(),
            "test-agent",
            "test-thread",
            "ops",
            action_type,
            "{}",
            decision,
        )
    finally:
        await conn.close()


@pytest.fixture(scope="function")
async def fresh_dsn() -> str:
    """Yield a fresh TimescaleDB DSN per test (function-scoped, NOT shared).

    Each test must start from a clean schema because we apply different subsets
    of migrations (pre-007 vs post-007). Spawn a dedicated container per test.
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
async def test_pre_migration_rejects_suppressed(fresh_dsn: str) -> None:
    """Before 007, 'suppressed' is rejected by the original decision CHECK constraint."""
    await _run_baseline_migrations(fresh_dsn)
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await _insert_action(fresh_dsn, decision="suppressed")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_admits_suppressed(fresh_dsn: str) -> None:
    """After 007, 'suppressed' is admitted (D-AD-03)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_007(fresh_dsn)
    # Must not raise
    await _insert_action(fresh_dsn, decision="suppressed")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_admits_logged(fresh_dsn: str) -> None:
    """After 007, 'logged' is admitted (D-OA-02)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_007(fresh_dsn)
    await _insert_action(fresh_dsn, decision="logged")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "decision_value",
    [
        "auto",
        "hitl_operator",
        "hitl_supervisor",
        "hitl_manager",
        "interlock_reject",
        "rolled_back",
        "timed_out",
        "governor_alert",
        "escalated",
    ],
)
async def test_post_migration_legacy_decisions_still_admitted(
    fresh_dsn: str, decision_value: str
) -> None:
    """Backward-compatibility: every pre-Phase-6 decision still passes the CHECK."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_007(fresh_dsn)
    if decision_value.startswith("hitl_"):
        # hitl_* requires motivation + approval_id — out of scope for this test,
        # which only verifies the decision CHECK enum membership. Skip insertion
        # and instead verify constraint admits the value by issuing a check via
        # an explicit cast-roundtrip query against pg_constraint.
        conn = await asyncpg.connect(
            fresh_dsn, statement_cache_size=0, command_timeout=60.0
        )
        try:
            row = await conn.fetchrow(
                "SELECT pg_get_constraintdef(oid) AS def"
                " FROM pg_constraint"
                " WHERE conrelid = 'audit.actions'::regclass"
                "   AND pg_get_constraintdef(oid) ILIKE '%decision%'"
                "   AND pg_get_constraintdef(oid) NOT ILIKE '%motivation%'",
            )
            assert row is not None
            assert f"'{decision_value}'" in row["def"], (
                f"Expected '{decision_value}' in CHECK def: {row['def']}"
            )
        finally:
            await conn.close()
    else:
        await _insert_action(fresh_dsn, decision=decision_value)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action_type_value",
    ["ESCALATION_REQUEST", "QUALITY_VERDICT", "SCHEDULE_DRAFT", "ANOMALY_ALERT"],
)
async def test_post_migration_admits_new_action_types(
    fresh_dsn: str, action_type_value: str
) -> None:
    """After 007, new Phase 6 action_type labels insert successfully."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_007(fresh_dsn)
    await _insert_action(fresh_dsn, decision="auto", action_type=action_type_value)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_idempotent_double_apply(fresh_dsn: str) -> None:
    """Re-applying migration 007 a second time must NOT raise (idempotency)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_007(fresh_dsn)
    # Second apply — must be a no-op
    await _apply_007(fresh_dsn)
    # And the new values must still be admitted
    await _insert_action(fresh_dsn, decision="suppressed")
    await _insert_action(
        fresh_dsn, decision="auto", action_type="ESCALATION_REQUEST"
    )


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrate_runner_picks_up_007(fresh_dsn: str) -> None:
    """The migrate.py runner globs 007 automatically and applies it in order."""
    rc = await migrate(fresh_dsn)
    assert rc == 0
    # After the full migrate() run, the new values must be admitted
    await _insert_action(fresh_dsn, decision="suppressed")
    await _insert_action(fresh_dsn, decision="logged")
    await _insert_action(
        fresh_dsn, decision="auto", action_type="ANOMALY_ALERT"
    )
