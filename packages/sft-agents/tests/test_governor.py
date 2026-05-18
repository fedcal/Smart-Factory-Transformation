"""Governor scan-once tests (HITL-09, D-58).

Tests cover threshold gating, min-sample, cooldown, and top-agents query shape.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

pytest.importorskip(
    "sft_agents.runtime.governor",
    reason="Plan 04-06 Task 04 implements Governor",
)

from sft_agents.hitl.approval_queue import ApprovalQueueWriter  # noqa: E402
from sft_agents.models.enums import Decision  # noqa: E402
from sft_agents.runtime.governor import (  # noqa: E402
    _COOLDOWN_SQL,
    _GOVERNOR_SCAN_SQL,
    _TOP_AGENTS_SQL,
    Governor,
)


def _audit_mock() -> AsyncMock:
    audit = AsyncMock()
    audit.write = AsyncMock(return_value=None)
    return audit


def _nats_mock() -> AsyncMock:
    n = AsyncMock()
    n.publish_governor_alert = AsyncMock(return_value=None)
    return n


def _make_governor(mock_pool, audit, nats, queue, **kwargs) -> Governor:
    return Governor(
        pool=mock_pool,
        audit_writer=audit,
        nats_publisher=nats,
        queue_writer=queue,
        scan_interval_s=0.01,
        **kwargs,
    )


def _configure_fetchrow_sequence(conn, *, cooldown, scan_row):
    """Set up fetchrow to return cooldown probe then scan_row + INSERT result."""

    seq = [cooldown, scan_row]

    async def _fr(sql, *args, **kw):
        return seq.pop(0) if seq else None

    conn.fetchrow = AsyncMock(side_effect=_fr)


async def test_governor_alert_fires(mock_pool: AsyncMock) -> None:
    """25 auto rows + 0 cooldown → emit alert (audit + NATS + approval)."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    _configure_fetchrow_sequence(
        conn,
        cooldown=None,  # no recent governor alert
        scan_row={"auto_count": 25, "total": 25},
    )
    conn.fetch = AsyncMock(
        return_value=[
            {"agent_id": "agent-a", "cnt": 10},
            {"agent_id": "agent-b", "cnt": 8},
            {"agent_id": "agent-c", "cnt": 7},
        ]
    )

    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    # Approval insert path uses fetchrow too — we need an extra fake row.
    # Wrap to add one more queued response.
    orig_side_effect = conn.fetchrow.side_effect
    extra = [{"id": uuid4()}]

    async def _fr_extended(sql, *args, **kw):
        # cooldown + scan rows consumed; subsequent calls (approval INSERT) get the extra.
        try:
            return await orig_side_effect(sql, *args, **kw)
        except IndexError:
            return extra.pop(0) if extra else None

    conn.fetchrow = AsyncMock(side_effect=_fr_extended)
    gov = _make_governor(mock_pool, audit, nats, queue)

    fired = await gov._scan_once()

    assert fired is True
    audit.write.assert_awaited_once()
    record = audit.write.await_args.args[0]
    assert record.decision == Decision.GOVERNOR_ALERT

    nats.publish_governor_alert.assert_awaited_once()
    payload = nats.publish_governor_alert.await_args.args[0]
    assert payload["auto_rate"] == 1.0
    assert payload["sample_size"] == 25
    assert len(payload["top_agents"]) <= 5


async def test_below_threshold_no_alert(mock_pool: AsyncMock) -> None:
    """auto_count/total = 0.625 (≤0.80) → no alert."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    _configure_fetchrow_sequence(
        conn, cooldown=None, scan_row={"auto_count": 25, "total": 40}
    )
    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    gov = _make_governor(mock_pool, audit, nats, queue)

    fired = await gov._scan_once()
    assert fired is False
    audit.write.assert_not_awaited()
    nats.publish_governor_alert.assert_not_awaited()


async def test_below_min_sample(mock_pool: AsyncMock) -> None:
    """total=10 < min_sample=20 → no alert."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    _configure_fetchrow_sequence(
        conn, cooldown=None, scan_row={"auto_count": 10, "total": 10}
    )
    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    gov = _make_governor(mock_pool, audit, nats, queue)

    fired = await gov._scan_once()
    assert fired is False


async def test_cooldown_prevents_thrash(mock_pool: AsyncMock) -> None:
    """If a governor_alert exists in last 5min → scan returns False immediately."""
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    _configure_fetchrow_sequence(
        conn,
        cooldown={"?column?": 1},  # recent alert exists
        scan_row=None,
    )
    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    gov = _make_governor(mock_pool, audit, nats, queue)

    fired = await gov._scan_once()
    assert fired is False
    audit.write.assert_not_awaited()


async def test_top_agents_query_constants() -> None:
    """SQL constants used (no f-strings); 1h window + 5m cooldown."""
    assert "INTERVAL '1 hour'" in _GOVERNOR_SCAN_SQL
    assert "INTERVAL '1 hour'" in _TOP_AGENTS_SQL
    assert "INTERVAL '5 minutes'" in _COOLDOWN_SQL
    assert "LIMIT 5" in _TOP_AGENTS_SQL


async def test_governor_rejects_none_pool() -> None:
    with pytest.raises(ValueError, match="pool must not be None"):
        Governor(
            pool=None,
            audit_writer=AsyncMock(),
            nats_publisher=AsyncMock(),
            queue_writer=MagicMock(),
        )


async def test_governor_run_stops_on_signal(mock_pool: AsyncMock) -> None:
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetchrow = AsyncMock(return_value=None)
    audit = _audit_mock()
    nats = _nats_mock()
    queue = ApprovalQueueWriter(mock_pool)
    gov = _make_governor(mock_pool, audit, nats, queue)

    import asyncio

    task = asyncio.create_task(gov.run())
    await asyncio.sleep(0.005)
    await gov.stop()
    await asyncio.wait_for(task, timeout=1.0)
