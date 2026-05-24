"""
infra/migrations/timescale/tests/test_migration_010.py

Tests for migration 010_extend_audit_knw.sql.

Phase 8 — Plan 08-00a (D-X-01 — Knowledge & Training cluster ActionType extension).

The migration extends the `audit.actions.action_type` CHECK constraint
(established by migration 007, extended by 009) to admit the 7 new Phase 8 values:
`'HANDOVER_DRAFT'`, `'HANDOVER_SIGNOFF'`, `'TRAINING_SESSION'`, `'TRAINING_SIGNOFF'`,
`'KNOWLEDGE_DEDUP'`, `'STALE_FLAG'`, `'SOP_DRAFT'`. The Decision CHECK constraint
is NOT modified (D-X-01: existing Decision values are sufficient for Phase 8).

Test matrix (mirror of test_migration_009.py — 6 tests + bonus runner test):
    1. test_pre_migration_rejects_handover_draft       — before 010, INSERT 'HANDOVER_DRAFT' raises CheckViolationError
    2. test_post_migration_admits_handover_draft        — after 010, INSERT 'HANDOVER_DRAFT' succeeds
    3. test_post_migration_admits_all_phase8_action_types — after 010, all 7 new values insert successfully
    4. test_post_migration_legacy_action_types_ok       — Phase 1-7 action_types still admitted (regression)
    5. test_post_migration_decision_enum_unchanged      — sanity: Decision CHECK constraint NOT modified
    6. test_idempotent_double_apply                     — re-running 010 is a no-op (does not raise)
    + test_migrate_runner_picks_up_010                  — full migrate() runner globs 010 and applies it

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
# test_migration_009.py (Phase 7 Plan 07-01).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from infra.migrations.timescale.migrate import migrate  # noqa: E402

_MIGRATION_010 = Path(__file__).parent.parent / "010_extend_audit_knw.sql"

# The 7 new Phase 8 ActionType values (D-X-01). MUST stay in lockstep with
# the SQL CHECK constraint in 010_extend_audit_knw.sql AND with
# packages/sft-agents/src/sft_agents/models/enums.py::ActionType.
_PHASE8_ACTION_TYPES = (
    "HANDOVER_DRAFT",
    "HANDOVER_SIGNOFF",
    "TRAINING_SESSION",
    "TRAINING_SIGNOFF",
    "KNOWLEDGE_DEDUP",
    "STALE_FLAG",
    "SOP_DRAFT",
)

# Pre-Phase-8 ActionType values (Phase 1-5 baseline + Phase 6 + Phase 7 extensions).
# These must continue to insert successfully after 010 (no regression).
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
    # Phase 7 extensions
    "RUL_ESTIMATE",
    "RCA_CHAIN",
    "COACH_STEP",
    "DOWNTIME_VERDICT",
    "OEE_REPORT",
)


async def _run_baseline_migrations(dsn: str) -> None:
    """Apply 001..009 (excluding 010) by reading and executing each in order.

    We deliberately bypass the migrate() runner here so that 010 is not picked
    up by the glob. This lets us exercise pre-010 state (test #1) and apply
    010 explicitly (tests #2-#6).
    """
    migrations_dir = Path(__file__).parent.parent
    baseline_files = sorted(
        f for f in migrations_dir.glob("[0-9][0-9][0-9]_*.sql") if f.name < "010"
    )
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        for sql_file in baseline_files:
            await conn.execute(sql_file.read_text(encoding="utf-8"))
    finally:
        await conn.close()


async def _apply_010(dsn: str) -> None:
    """Apply only 010_extend_audit_knw.sql against the provided DSN."""
    sql = _MIGRATION_010.read_text(encoding="utf-8")
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
            "knowledge",
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
    of migrations (pre-010 vs post-010). Spawn a dedicated container per test.
    Mirrors the function-scoped fixture in test_migration_009.py.
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
async def test_pre_migration_rejects_handover_draft(fresh_dsn: str) -> None:
    """Before 010, 'HANDOVER_DRAFT' is rejected by the Phase 7 action_type CHECK constraint."""
    await _run_baseline_migrations(fresh_dsn)
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await _insert_action(fresh_dsn, action_type="HANDOVER_DRAFT")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_admits_handover_draft(fresh_dsn: str) -> None:
    """After 010, 'HANDOVER_DRAFT' is admitted (D-SH-01)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_010(fresh_dsn)
    # Must not raise
    await _insert_action(fresh_dsn, action_type="HANDOVER_DRAFT")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("action_type_value", _PHASE8_ACTION_TYPES)
async def test_post_migration_admits_all_phase8_action_types(
    fresh_dsn: str, action_type_value: str
) -> None:
    """After 010, every Phase 8 action_type label inserts successfully (D-X-01)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_010(fresh_dsn)
    await _insert_action(fresh_dsn, decision="auto", action_type=action_type_value)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("action_type_value", _LEGACY_ACTION_TYPES)
async def test_post_migration_legacy_action_types_ok(
    fresh_dsn: str, action_type_value: str
) -> None:
    """Backward-compatibility: every Phase 1-7 action_type still passes the CHECK."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_010(fresh_dsn)
    await _insert_action(fresh_dsn, decision="auto", action_type=action_type_value)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_decision_enum_unchanged(fresh_dsn: str) -> None:
    """Sanity: 010 must NOT modify the Decision CHECK constraint (D-X-01 explicit).

    Reads the decision CHECK constraint definition from pg_constraint after
    applying 010 and asserts it lists exactly the same values as after 009 —
    the 9 baseline decisions plus 'suppressed' and 'logged'. No Phase 8
    Decision additions are permitted.
    """
    await _run_baseline_migrations(fresh_dsn)
    await _apply_010(fresh_dsn)

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
            "audit_actions_decision_chk constraint missing after 010 —"
            " 010 must NOT drop the decision CHECK"
        )
        check_def = row["def"]
        for v in expected_values:
            assert f"'{v}'" in check_def, (
                f"Decision value '{v}' missing from CHECK def after 010: {check_def}"
            )
        # No Phase 8-specific decision values must have leaked into the decision CHECK
        forbidden = {
            "handover_draft",
            "handover_signoff",
            "training_session",
            "training_signoff",
            "knowledge_dedup",
            "stale_flag",
            "sop_draft",
        }
        for v in forbidden:
            assert f"'{v}'" not in check_def, (
                f"Phase 8 Decision value '{v}' must NOT be in CHECK def (D-X-01): {check_def}"
            )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_idempotent_double_apply(fresh_dsn: str) -> None:
    """Re-applying migration 010 a second time must NOT raise (idempotency)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_010(fresh_dsn)
    # Second apply — must be a no-op
    await _apply_010(fresh_dsn)
    # And the new values must still be admitted
    await _insert_action(fresh_dsn, decision="auto", action_type="HANDOVER_DRAFT")
    await _insert_action(fresh_dsn, decision="auto", action_type="SOP_DRAFT")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrate_runner_picks_up_010(fresh_dsn: str) -> None:
    """The migrate.py runner globs 010 automatically and applies it in order."""
    rc = await migrate(fresh_dsn)
    assert rc == 0
    # After the full migrate() run, the new Phase 8 values must be admitted
    for at in _PHASE8_ACTION_TYPES:
        await _insert_action(fresh_dsn, decision="auto", action_type=at)
