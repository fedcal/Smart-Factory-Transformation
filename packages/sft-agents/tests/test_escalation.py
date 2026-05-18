"""EscalationSupervisor scan-once tests (HITL-02, D-57).

Operator → supervisor → manager → timed_out chain via mocked asyncpg + NATS.
Real testcontainers round-trip lives in tests/integration/ (Plan 04-07 owns the
api-gateway e2e).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytest.importorskip(
    "sft_agents.runtime.escalation",
    reason="Plan 04-06 Task 03 implements EscalationSupervisor",
)

from sft_agents.hitl.approval_queue import ApprovalQueueWriter  # noqa: E402
from sft_agents.models.enums import Decision, Tier  # noqa: E402
from sft_agents.runtime.escalation import EscalationSupervisor  # noqa: E402


def _row(*, tier: str, approval_id=None) -> dict:
    return {
        "id": approval_id or uuid4(),
        "agent_id": "operator-assistant",
        "thread_id": "ops.operator-assistant.session-1",
        "tier": tier,
        "action_type": "TEST",
        "payload_json": '{"x": 1}',
    }


def _audit_mock() -> AsyncMock:
    audit = AsyncMock()
    audit.write = AsyncMock(return_value=None)
    return audit


def _nats_mock() -> AsyncMock:
    n = AsyncMock()
    n.publish_governor_alert = AsyncMock(return_value=None)
    return n


def _make_supervisor(mock_pool, audit, nats, queue) -> EscalationSupervisor:
    return EscalationSupervisor(
        pool=mock_pool,
        audit_writer=audit,
        nats_publisher=nats,
        queue_writer=queue,
        scan_interval_s=0.01,
    )


async def test_operator_to_supervisor(mock_pool: AsyncMock) -> None:
    """Operator-tier expired row → insert_escalation called with Tier.SUPERVISOR."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    seed_row = _row(tier="operator")
    conn.fetch = AsyncMock(return_value=[seed_row])

    # insert_escalation insert + update RETURNING fetchrows.
    new_escalation_id = uuid4()
    conn.fetchrow = AsyncMock(side_effect=[{"id": new_escalation_id}, {"id": new_escalation_id}])
    # Transaction context manager
    txn = AsyncMock()
    txn.__aenter__ = AsyncMock(return_value=txn)
    txn.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=txn)

    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    sup = _make_supervisor(mock_pool, audit, nats, queue)

    processed = await sup._scan_once()

    assert processed == 1
    # Two audit writes? No — only one (decision=ESCALATED).
    assert audit.write.await_count == 1
    record = audit.write.await_args.args[0]
    assert record.decision == Decision.ESCALATED
    # No governor alert (operator → supervisor is intermediate, not terminal).
    nats.publish_governor_alert.assert_not_awaited()


async def test_supervisor_to_manager(mock_pool: AsyncMock) -> None:
    """Supervisor-tier expired → escalate to manager."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetch = AsyncMock(return_value=[_row(tier="supervisor")])
    new_id = uuid4()
    conn.fetchrow = AsyncMock(side_effect=[{"id": new_id}, {"id": new_id}])
    txn = AsyncMock()
    txn.__aenter__ = AsyncMock(return_value=txn)
    txn.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=txn)

    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    sup = _make_supervisor(mock_pool, audit, nats, queue)

    await sup._scan_once()

    record = audit.write.await_args.args[0]
    assert record.decision == Decision.ESCALATED


async def test_manager_timeout(mock_pool: AsyncMock) -> None:
    """Manager-tier (terminal) → mark timed_out + governor.alert."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetch = AsyncMock(return_value=[_row(tier="manager")])

    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    sup = _make_supervisor(mock_pool, audit, nats, queue)

    await sup._scan_once()

    # 1 audit write with decision=timed_out
    audit.write.assert_awaited_once()
    record = audit.write.await_args.args[0]
    assert record.decision == Decision.TIMED_OUT
    # governor.alert published.
    nats.publish_governor_alert.assert_awaited_once()
    payload = nats.publish_governor_alert.await_args.args[0]
    assert payload["kind"] == "manager_timeout"
    assert "sla_breach_at" in payload


async def test_safety_interlock_filtered_by_query(mock_pool: AsyncMock) -> None:
    """SQL excludes tier='safety_interlock' — no rows returned, no audit."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    # SQL filter ensures safety_interlock rows are NOT in `rows`; simulate that.
    conn.fetch = AsyncMock(return_value=[])

    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    sup = _make_supervisor(mock_pool, audit, nats, queue)

    processed = await sup._scan_once()
    assert processed == 0
    audit.write.assert_not_awaited()

    # Sanity-check the SQL contains the filter.
    from sft_agents.runtime.escalation import _SCAN_SQL  # noqa: PLC0415

    assert "tier <> 'safety_interlock'" in _SCAN_SQL


async def test_run_stops_on_signal(mock_pool: AsyncMock) -> None:
    """Loop exits cleanly when stop() is called."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetch = AsyncMock(return_value=[])

    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    sup = _make_supervisor(mock_pool, audit, nats, queue)

    import asyncio

    task = asyncio.create_task(sup.run())
    await asyncio.sleep(0.005)
    await sup.stop()
    await asyncio.wait_for(task, timeout=1.0)


async def test_pool_validation() -> None:
    with pytest.raises(ValueError, match="pool must not be None"):
        EscalationSupervisor(
            pool=None,
            audit_writer=AsyncMock(),
            nats_publisher=AsyncMock(),
            queue_writer=MagicMock(),
        )
