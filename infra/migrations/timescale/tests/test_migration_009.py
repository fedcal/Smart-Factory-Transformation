"""
infra/migrations/timescale/tests/test_migration_009.py

Tests for migration 009_extend_audit_mnt.sql.

Phase 7 — Plan 07-01 (D-AE-MNT — Maintenance & Reliability cluster ActionType extension).

The migration extends the `audit.actions.action_type` CHECK constraint
(established by migration 007) to admit the 5 new Phase 7 values:
`'RUL_ESTIMATE'`, `'RCA_CHAIN'`, `'COACH_STEP'`, `'DOWNTIME_VERDICT'`,
`'OEE_REPORT'`. The Decision CHECK constraint is NOT modified (D-AE-MNT:
existing Decision values are sufficient for Phase 7).

Test matrix (mirror of test_migration_007.py — 6 tests + bonus runner test):
    1. test_pre_migration_rejects_rul_estimate            — before 009, INSERT 'RUL_ESTIMATE' raises CheckViolationError
    2. test_post_migration_admits_rul_estimate            — after 009, INSERT 'RUL_ESTIMATE' succeeds
    3. test_post_migration_admits_all_phase7_action_types — after 009, all 5 new values insert successfully
    4. test_post_migration_legacy_action_types_ok         — Phase 1-5 + Phase 6 action_types still admitted (regression)
    5. test_post_migration_decision_enum_unchanged        — sanity: Decision CHECK constraint NOT modified
    6. test_idempotent_double_apply                       — re-running 009 is a no-op (does not raise)
    + test_migrate_runner_picks_up_009                    — full migrate() runner globs 009 and applies it

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
# test_migration_007.py (Phase 6 Plan 06-01).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from infra.migrations.timescale.migrate import migrate  # noqa: E402

_MIGRATION_009 = Path(__file__).parent.parent / "009_extend_audit_mnt.sql"

# The 5 new Phase 7 ActionType values (D-AE-MNT). MUST stay in lockstep with
# the SQL CHECK constraint in 009_extend_audit_mnt.sql AND with
# packages/sft-agents/src/sft_agents/models/enums.py::ActionType.
_PHASE7_ACTION_TYPES = (
    "RUL_ESTIMATE",
    "RCA_CHAIN",
    "COACH_STEP",
    "DOWNTIME_VERDICT",
    "OEE_REPORT",
)

# Pre-Phase-7 ActionType values (Phase 1-5 baseline + Phase 6 extensions).
# These must continue to insert successfully after 009 (no regression).
_LEGACY_ACTION_TYPES = (
    # Phase 1-5 baseline
    "WRITE_PLC_SETPOINT",
    "ACTUATOR_COMMAND",
    "FIRMWARE_DEPLOY",
    "NETWORK_ACL_CHANGE",
    "GRAPH_RECURSION_REVIEW",
    "GOVERNOR_ALERT",
    # Phase 6 extensions
    "ESCALATION_REQUEST",
    "QUALITY_VERDICT",
    "SCHEDULE_DRAFT",
    "ANOMALY_ALERT",
)


async def _run_baseline_migrations(dsn: str) -> None:
    """Apply 001..008 (excluding 009) by reading and executing each in order.

    We deliberately bypass the migrate() runner here so that 009 is not picked
    up by the glob. This lets us exercise pre-009 state (test #1) and apply
    009 explicitly (tests #2-#6).
    """
    migrations_dir = Path(__file__).parent.parent
    baseline_files = sorted(
        f for f in migrations_dir.glob("[0-9][0-9][0-9]_*.sql") if f.name < "009"
    )
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        for sql_file in baseline_files:
            await conn.execute(sql_file.read_text(encoding="utf-8"))
    finally:
        await conn.close()


async def _apply_009(dsn: str) -> None:
    """Apply only 009_extend_audit_mnt.sql against the provided DSN."""
    sql = _MIGRATION_009.read_text(encoding="utf-8")
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
            "maintenance",
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
    of migrations (pre-009 vs post-009). Spawn a dedicated container per test.
    Mirrors the function-scoped fixture in test_migration_007.py L108-125.
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
async def test_pre_migration_rejects_rul_estimate(fresh_dsn: str) -> None:
    """Before 009, 'RUL_ESTIMATE' is rejected by the Phase 6 action_type CHECK constraint."""
    await _run_baseline_migrations(fresh_dsn)
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await _insert_action(fresh_dsn, action_type="RUL_ESTIMATE")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_admits_rul_estimate(fresh_dsn: str) -> None:
    """After 009, 'RUL_ESTIMATE' is admitted (D-PM-04)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_009(fresh_dsn)
    # Must not raise
    await _insert_action(fresh_dsn, action_type="RUL_ESTIMATE")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("action_type_value", _PHASE7_ACTION_TYPES)
async def test_post_migration_admits_all_phase7_action_types(
    fresh_dsn: str, action_type_value: str
) -> None:
    """After 009, every Phase 7 action_type label inserts successfully (D-AE-MNT)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_009(fresh_dsn)
    await _insert_action(fresh_dsn, decision="auto", action_type=action_type_value)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("action_type_value", _LEGACY_ACTION_TYPES)
async def test_post_migration_legacy_action_types_ok(
    fresh_dsn: str, action_type_value: str
) -> None:
    """Backward-compatibility: every Phase 1-5 + Phase 6 action_type still passes the CHECK."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_009(fresh_dsn)
    await _insert_action(fresh_dsn, decision="auto", action_type=action_type_value)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_decision_enum_unchanged(fresh_dsn: str) -> None:
    """Sanity: 009 must NOT modify the Decision CHECK constraint (D-AE-MNT explicit).

    Reads the decision CHECK constraint definition from pg_constraint after
    applying 009 and asserts it lists exactly the same values as after 007 —
    the 9 baseline decisions plus 'suppressed' and 'logged'. No Phase 7
    Decision additions are permitted.
    """
    await _run_baseline_migrations(fresh_dsn)
    await _apply_009(fresh_dsn)

    expected_values = {
        "auto",
        "hitl_operator",
        "hitl_supervisor",
        "hitl_manager",
        "interlock_reject",
        "rolled_back",
        "timed_out",
        "governor_alert",
        "escalated",
        # Phase 6
        "suppressed",
        "logged",
    }

    conn = await asyncpg.connect(
        fresh_dsn, statement_cache_size=0, command_timeout=60.0
    )
    try:
        row = await conn.fetchrow(
            "SELECT pg_get_constraintdef(oid) AS def"
            " FROM pg_constraint"
            " WHERE conrelid = 'audit.actions'::regclass"
            "   AND conname = 'audit_actions_decision_chk'"
        )
        assert row is not None, (
            "audit_actions_decision_chk constraint missing after 009 —"
            " 009 must NOT drop the decision CHECK"
        )
        check_def = row["def"]
        for v in expected_values:
            assert f"'{v}'" in check_def, (
                f"Decision value '{v}' missing from CHECK def after 009: {check_def}"
            )
        # No Phase 7-specific decision values must have leaked into the decision CHECK
        forbidden = {
            "rul_estimate",
            "rca_chain",
            "coach_step",
            "downtime_verdict",
            "oee_report",
        }
        for v in forbidden:
            assert f"'{v}'" not in check_def, (
                f"Phase 7 Decision value '{v}' must NOT be in CHECK def (D-AE-MNT): {check_def}"
            )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_idempotent_double_apply(fresh_dsn: str) -> None:
    """Re-applying migration 009 a second time must NOT raise (idempotency)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_009(fresh_dsn)
    # Second apply — must be a no-op
    await _apply_009(fresh_dsn)
    # And the new values must still be admitted
    await _insert_action(fresh_dsn, decision="auto", action_type="RUL_ESTIMATE")
    await _insert_action(fresh_dsn, decision="auto", action_type="OEE_REPORT")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrate_runner_picks_up_009(fresh_dsn: str) -> None:
    """The migrate.py runner globs 009 automatically and applies it in order."""
    rc = await migrate(fresh_dsn)
    assert rc == 0
    # After the full migrate() run, the new Phase 7 values must be admitted
    for at in _PHASE7_ACTION_TYPES:
        await _insert_action(fresh_dsn, decision="auto", action_type=at)
