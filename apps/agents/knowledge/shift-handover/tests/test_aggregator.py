"""Contract tests for ShiftAggregator (TRN-03 / D-SH-02).

CONTRACT: ShiftAggregator builds a structured HandoverReport from:
  - Mock asyncpg rows from audit.actions (cross-cluster audit window query)
  - Mock asyncpg rows from maintenance.downtime_events (downtime within the window)
  - Alerts DERIVED from audit.actions WHERE action_type='ANOMALY_ALERT'
    (D-SH-02 resolved: NO ops.alerts / ops.work_orders tables — audit chain only)

Implementation target: trn_shift_handover.aggregator.ShiftAggregator
(Wave 2-3 plan: 08-04)

Wave 0 scaffold: test functions fail explicitly with a message naming the
unimplemented contract. NOT module-level pytest.skip (Phase 6/7 Wave 0 decision).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Contract 1: ShiftAggregator returns a structured HandoverReport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aggregator_builds_report_from_audit_rows() -> None:
    """ShiftAggregator.compile(window, pool) returns HandoverReport with events list.

    Given a mock asyncpg pool that returns 3 audit.actions rows in the window,
    ShiftAggregator must build a HandoverReport where:
    - report.events has exactly 3 entries
    - Each entry maps to the corresponding audit row (agent_id, action_type, ts)
    - report.window_start / report.window_end match the input window

    Implementation target: trn_shift_handover.aggregator.ShiftAggregator.compile()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: ShiftAggregator.compile(window, pool) "
        "returns HandoverReport with events from audit.actions cross-cluster query. "
        "Implement in plan 08-04 (shift-handover agent). "
        "Module: trn_shift_handover.aggregator"
    )


@pytest.mark.asyncio
async def test_aggregator_derives_alerts_from_anomaly_alert_action_type() -> None:
    """Alert list in HandoverReport derives from ANOMALY_ALERT action_type rows only.

    D-SH-02 (resolved post-research): NO ops.alerts table. Alerts come from
    audit.actions WHERE action_type='ANOMALY_ALERT'. Given mock rows including
    one ANOMALY_ALERT and two other action_types, HandoverReport.alerts must
    contain exactly 1 alert entry.

    Implementation target: trn_shift_handover.aggregator.ShiftAggregator.compile()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: alerts derived from audit.actions WHERE "
        "action_type='ANOMALY_ALERT'; NO ops.alerts table (D-SH-02 resolved). "
        "Implement in plan 08-04 (shift-handover agent). "
        "Module: trn_shift_handover.aggregator"
    )


@pytest.mark.asyncio
async def test_aggregator_includes_downtime_events_from_maintenance_table() -> None:
    """HandoverReport.downtime_events populated from maintenance.downtime_events.

    Given mock asyncpg returning 2 downtime rows in the window,
    HandoverReport.downtime_events must have 2 entries with matching
    duration_min and reason_code values.

    Implementation target: trn_shift_handover.aggregator.ShiftAggregator.compile()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: downtime_events from maintenance.downtime_events "
        "hypertable within the shift window. "
        "Implement in plan 08-04 (shift-handover agent). "
        "Module: trn_shift_handover.aggregator"
    )


@pytest.mark.asyncio
async def test_aggregator_uses_datetime_objects_for_asyncpg_params() -> None:
    """asyncpg query parameters are datetime objects, never .isoformat() strings.

    WR-03 fix (Phase 7): asyncpg TIMESTAMPTZ parameters must be Python datetime
    objects. Given mock pool.fetch, verify the call was made with datetime args
    not string args (check type of args[0] and args[1]).

    Implementation target: trn_shift_handover.aggregator.ShiftAggregator.compile()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: asyncpg query parameters are datetime objects "
        "(WR-03 fix), never .isoformat() strings. "
        "Implement in plan 08-04 (shift-handover agent). "
        "Module: trn_shift_handover.aggregator"
    )
