"""Contract tests for ShiftAggregator (TRN-03 / D-SH-02).

CONTRACT: ShiftAggregator builds a structured HandoverReport from:
  - Mock asyncpg rows from audit.actions (cross-cluster audit window query)
  - Mock asyncpg rows from maintenance.downtime_events (downtime within the window)
  - Alerts DERIVED from audit.actions WHERE action_type='ANOMALY_ALERT'
    (D-SH-02 resolved: NO ops.alerts / ops.work_orders tables — audit chain only)

Implementation: trn_shift_handover.aggregator.ShiftAggregator
(Implemented in plan 08-02. Extended with HITL in plan 08-04.)
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers — build mock asyncpg rows
# ---------------------------------------------------------------------------


def _make_audit_row(
    *,
    ts: datetime | None = None,
    agent_id: str = "test-agent",
    cluster: str = "ops",
    action_type: str = "ANOMALY_ALERT",
    thread_id: str = "thread-1",
    evidence_panel: dict | None = None,
    decision: str = "auto",
) -> dict:
    """Build a mock audit.actions row dict."""
    if ts is None:
        ts = datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
    return {
        "ts": ts,
        "agent_id": agent_id,
        "cluster": cluster,
        "action_type": action_type,
        "thread_id": thread_id,
        "evidence_panel": evidence_panel or {},
        "decision": decision,
    }


def _make_downtime_row(
    *,
    event_id: str = "evt-1",
    asset_id: str = "loom-01",
    reason_code: str = "SPINDLE_BREAK",
    duration_min: int = 30,
    severity: str = "medium",
    work_order_id: str | None = None,
    timestamp: datetime | None = None,
) -> dict:
    """Build a mock maintenance.downtime_events row dict."""
    if timestamp is None:
        timestamp = datetime(2024, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    return {
        "event_id": event_id,
        "asset_id": asset_id,
        "reason_code": reason_code,
        "duration_min": duration_min,
        "severity": severity,
        "work_order_id": work_order_id,
        "timestamp": timestamp,
    }


def _make_mock_pool(audit_rows: list[dict], downtime_rows: list[dict]) -> MagicMock:
    """Build mock asyncpg pool that returns given rows on conn.fetch() calls."""
    pool = MagicMock()
    conn = AsyncMock()
    # First call returns audit_rows, second call returns downtime_rows
    conn.fetch = AsyncMock(side_effect=[audit_rows, downtime_rows])
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    return pool


# ---------------------------------------------------------------------------
# Contract 1: ShiftAggregator returns a structured HandoverReport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aggregator_builds_report_from_audit_rows() -> None:
    """ShiftAggregator.compile(window, pool) returns HandoverReport with events list.

    Given a mock asyncpg pool that returns 3 audit.actions rows in the window,
    ShiftAggregator must build a HandoverReport where:
    - report.source_events has exactly 3 entries
    - report.window_start / report.window_end match the input window

    Implementation: trn_shift_handover.aggregator.ShiftAggregator.compile()
    """
    from trn_shift_handover.aggregator import ShiftAggregator
    from trn_shift_handover.models import HandoverReport, ShiftWindow

    shift_start = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
    shift_end = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    audit_rows = [
        _make_audit_row(agent_id="agent-a", action_type="ANOMALY_ALERT"),
        _make_audit_row(agent_id="agent-b", action_type="QUALITY_VERDICT"),
        _make_audit_row(agent_id="agent-c", action_type="DOWNTIME_VERDICT"),
    ]
    downtime_rows: list[dict] = []

    pool = _make_mock_pool(audit_rows, downtime_rows)
    window = ShiftWindow(
        shift_start=shift_start,
        shift_end=shift_end,
        boundary_label="06:00-14:00",
    )

    agg = ShiftAggregator(pool=pool)
    report = await agg.compile(window)

    assert isinstance(report, HandoverReport)
    assert len(report.source_events) == 3
    assert report.shift_start == shift_start
    assert report.shift_end == shift_end


@pytest.mark.asyncio
async def test_aggregator_derives_alerts_from_anomaly_alert_action_type() -> None:
    """Alert list in HandoverReport derives from ANOMALY_ALERT action_type rows only.

    D-SH-02 (resolved post-research): NO ops.alerts table. Alerts come from
    audit.actions WHERE action_type='ANOMALY_ALERT'. Given mock rows including
    one ANOMALY_ALERT and two other action_types, HandoverReport.open_alerts must
    be exactly 1.
    """
    from trn_shift_handover.aggregator import ShiftAggregator
    from trn_shift_handover.models import ShiftWindow

    shift_start = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
    shift_end = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    audit_rows = [
        _make_audit_row(action_type="ANOMALY_ALERT"),      # 1 alert
        _make_audit_row(action_type="QUALITY_VERDICT"),    # not an alert
        _make_audit_row(action_type="DOWNTIME_VERDICT"),   # not an alert
    ]
    downtime_rows: list[dict] = []

    pool = _make_mock_pool(audit_rows, downtime_rows)
    window = ShiftWindow(
        shift_start=shift_start,
        shift_end=shift_end,
        boundary_label="06:00-14:00",
    )

    agg = ShiftAggregator(pool=pool)
    report = await agg.compile(window)

    assert report.open_alerts == 1, (
        f"Expected 1 open_alert (from ANOMALY_ALERT rows only), got {report.open_alerts}. "
        "D-SH-02: alerts derive from audit.actions action_type='ANOMALY_ALERT'."
    )


@pytest.mark.asyncio
async def test_aggregator_includes_downtime_events_from_maintenance_table() -> None:
    """HandoverReport.downtime_events populated from maintenance.downtime_events.

    Given mock asyncpg returning 2 downtime rows in the window,
    HandoverReport.downtime_events must be 2.
    """
    from trn_shift_handover.aggregator import ShiftAggregator
    from trn_shift_handover.models import ShiftWindow

    shift_start = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
    shift_end = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    audit_rows: list[dict] = []
    downtime_rows = [
        _make_downtime_row(event_id="evt-1", duration_min=30, reason_code="SPINDLE_BREAK"),
        _make_downtime_row(event_id="evt-2", duration_min=15, reason_code="WARP_BREAK"),
    ]

    pool = _make_mock_pool(audit_rows, downtime_rows)
    window = ShiftWindow(
        shift_start=shift_start,
        shift_end=shift_end,
        boundary_label="06:00-14:00",
    )

    agg = ShiftAggregator(pool=pool)
    report = await agg.compile(window)

    assert report.downtime_events == 2, (
        f"Expected 2 downtime_events from maintenance.downtime_events, "
        f"got {report.downtime_events}."
    )


@pytest.mark.asyncio
async def test_aggregator_uses_datetime_objects_for_asyncpg_params() -> None:
    """asyncpg query parameters are datetime objects, never .isoformat() strings.

    WR-03 fix (Phase 7): asyncpg TIMESTAMPTZ parameters must be Python datetime
    objects. Verify the conn.fetch() calls receive datetime args, not strings.
    """
    from trn_shift_handover.aggregator import ShiftAggregator
    from trn_shift_handover.models import ShiftWindow

    shift_start = datetime(2024, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
    shift_end = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

    pool = MagicMock()
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )

    window = ShiftWindow(
        shift_start=shift_start,
        shift_end=shift_end,
        boundary_label="06:00-14:00",
    )

    agg = ShiftAggregator(pool=pool)
    await agg.compile(window)

    # Verify conn.fetch was called at least once
    assert conn.fetch.called, "conn.fetch was never called"

    # Verify all call args are datetime objects (WR-03: never strings)
    for call in conn.fetch.call_args_list:
        # call.args[0] is the SQL string; args[1] and [2] are the datetime params
        positional_args = call.args
        for arg in positional_args[1:]:  # skip the SQL string
            assert isinstance(arg, datetime), (
                f"asyncpg parameter must be datetime object (WR-03 fix), "
                f"got {type(arg).__name__!r}: {arg!r}. "
                "Never call .isoformat() before passing to conn.fetch()."
            )
