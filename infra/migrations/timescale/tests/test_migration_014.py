"""
infra/migrations/timescale/tests/test_migration_014.py

Tests for migration 014_extend_audit_phase11.sql.

Phase 11 — Plan 11-00 (SEC-07 — audit log di ogni accesso a documenti restricted).

The migration extends the `audit.actions.action_type` CHECK constraint
(established by migration 007, extended by 009, 010, 012) to admit the new
Phase 11 value: `'RESTRICTED_DOC_ACCESS'`. The Decision CHECK constraint is
NOT modified (D-X-01 pattern explicit).

Test matrix (mirror of test_migration_012.py — 6 tests + runner test):
    1. test_pre_migration_rejects_restricted_doc_access   — before 014, INSERT raises CheckViolationError
    2. test_post_migration_admits_restricted_doc_access   — after 014, INSERT succeeds
    3. test_post_migration_admits_all_phase11_action_types — after 014, new Phase 11 value inserts ok
    4. test_post_migration_legacy_action_types_ok          — Phase 1-9 action_types still admitted (regression)
    5. test_post_migration_decision_enum_unchanged         — sanity: Decision CHECK NOT modified
    6. test_idempotent_double_apply                        — re-running 014 is a no-op
    + test_migrate_runner_picks_up_014                    — full migrate() runner applies 014

All tests run against an isolated testcontainers Postgres+TimescaleDB function-scoped
container. Marked @pytest.mark.testcontainers AND @pytest.mark.integration.
"""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from infra.migrations.timescale.migrate import migrate  # noqa: E402

_MIGRATION_014 = Path(__file__).parent.parent / "014_extend_audit_phase11.sql"

# The new Phase 11 ActionType value (SEC-07).
# MUST stay in lockstep with the SQL CHECK constraint in 014_extend_audit_phase11.sql
# AND with packages/sft-agents/src/sft_agents/models/enums.py::ActionType (added in Plan 11-03).
_PHASE11_ACTION_TYPES = (
    "RESTRICTED_DOC_ACCESS",
)

# Pre-Phase-11 ActionType values (Phase 1-9). Must continue to insert after 014.
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
    # Phase 8 extensions
    "HANDOVER_DRAFT",
    "HANDOVER_SIGNOFF",
    "TRAINING_SESSION",
    "TRAINING_SIGNOFF",
    "KNOWLEDGE_DEDUP",
    "STALE_FLAG",
    "SOP_DRAFT",
    # Phase 9 extensions
    "REORDER_ALERT",
    "PURCHASE_RECOMMENDATION_DRAFT",
    "PURCHASE_SIGNOFF",
    "ENERGY_PROPOSAL",
    "ENERGY_SIGNOFF",
    "DEMAND_PLAN_DRAFT",
    "DEMAND_PLAN_SIGNOFF",
    "COST_REPORT",
)


async def _run_baseline_migrations(dsn: str) -> None:
    """Apply 001..013 (excluding 014) by reading and executing each in order."""
    migrations_dir = Path(__file__).parent.parent
    baseline_files = sorted(
        f for f in migrations_dir.glob("[0-9][0-9][0-9]_*.sql") if f.name < "014"
    )
    conn = await asyncpg.connect(dsn, statement_cache_size=0, command_timeout=60.0)
    try:
        for sql_file in baseline_files:
            await conn.execute(sql_file.read_text(encoding="utf-8"))
    finally:
        await conn.close()


async def _apply_014(dsn: str) -> None:
    """Apply only 014_extend_audit_phase11.sql against the provided DSN."""
    sql = _MIGRATION_014.read_text(encoding="utf-8")
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
    """Attempt to INSERT a minimally-valid row into audit.actions."""
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
            "obs-security",
            action_type,
            "{}",
            decision,
        )
    finally:
        await conn.close()


@pytest.fixture(scope="function")
async def fresh_dsn() -> str:
    """Yield a fresh TimescaleDB DSN per test (function-scoped, NOT shared)."""
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
async def test_pre_migration_rejects_restricted_doc_access(fresh_dsn: str) -> None:
    """Before 014, 'RESTRICTED_DOC_ACCESS' is rejected by the Phase 9 CHECK constraint."""
    await _run_baseline_migrations(fresh_dsn)
    with pytest.raises(asyncpg.exceptions.CheckViolationError):
        await _insert_action(fresh_dsn, action_type="RESTRICTED_DOC_ACCESS")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_admits_restricted_doc_access(fresh_dsn: str) -> None:
    """After 014, 'RESTRICTED_DOC_ACCESS' is admitted (SEC-07)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_014(fresh_dsn)
    # Must not raise
    await _insert_action(fresh_dsn, action_type="RESTRICTED_DOC_ACCESS")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("action_type_value", _PHASE11_ACTION_TYPES)
async def test_post_migration_admits_all_phase11_action_types(
    fresh_dsn: str, action_type_value: str
) -> None:
    """After 014, every Phase 11 action_type label inserts successfully (SEC-07)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_014(fresh_dsn)
    await _insert_action(fresh_dsn, decision="auto", action_type=action_type_value)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("action_type_value", _LEGACY_ACTION_TYPES)
async def test_post_migration_legacy_action_types_ok(
    fresh_dsn: str, action_type_value: str
) -> None:
    """Backward-compatibility: every Phase 1-9 action_type still passes the CHECK."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_014(fresh_dsn)
    await _insert_action(fresh_dsn, decision="auto", action_type=action_type_value)


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_migration_decision_enum_unchanged(fresh_dsn: str) -> None:
    """Sanity: 014 must NOT modify the Decision CHECK constraint (D-X-01 explicit)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_014(fresh_dsn)

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
            "audit_actions_decision_chk constraint missing after 014 —"
            " 014 must NOT drop the decision CHECK"
        )
        check_def = row["def"]
        for v in expected_values:
            assert f"'{v}'" in check_def, (
                f"Decision value '{v}' missing from CHECK def after 014: {check_def}"
            )
        # Phase 11 action_type value must NOT leak into the decision CHECK
        assert "'restricted_doc_access'" not in check_def.lower(), (
            "Phase 11 action_type value must NOT be in the Decision CHECK def"
        )
    finally:
        await conn.close()


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_idempotent_double_apply(fresh_dsn: str) -> None:
    """Re-applying migration 014 a second time must NOT raise (idempotency)."""
    await _run_baseline_migrations(fresh_dsn)
    await _apply_014(fresh_dsn)
    # Second apply — must be a no-op
    await _apply_014(fresh_dsn)
    # And the new Phase 11 value must still be admitted
    await _insert_action(fresh_dsn, decision="auto", action_type="RESTRICTED_DOC_ACCESS")


@pytest.mark.testcontainers
@pytest.mark.integration
@pytest.mark.asyncio
async def test_migrate_runner_picks_up_014(fresh_dsn: str) -> None:
    """The migrate.py runner globs 014 automatically and applies it in order."""
    rc = await migrate(fresh_dsn)
    assert rc == 0
    # After the full migrate() run, the new Phase 11 value must be admitted
    for at in _PHASE11_ACTION_TYPES:
        await _insert_action(fresh_dsn, decision="auto", action_type=at)
