"""Contract tests for CostAnalyzer agent — AUTONOMOUS Decision.AUTO pattern (SCM-03).

CONTRACT: CostAnalyzer.__call__() is FULLY AUTONOMOUS — no HITL interrupt:
  - Does NOT call interrupt() at all (no HITL gating)
  - Writes audit row with Decision.AUTO (not HITL_SUPERVISOR)
  - Read-only: no writes to scm.* tables (only reads audit.actions for cost aggregation)
  - Aggregates downtime + scrap + energy cost from audit.actions
  - audit_writer.write() called with positional AuditRecord (CR-02)
  - action_type is COST_REPORT (the Phase 9 autonomous audit event type)

Phase 8 analog: KnowledgeCurator (autonomous D-KC-04 pattern)
Decision.AUTO signals: AI computed the result, no human approval required.

Implementation target: scm_cost_analyzer.agent.CostAnalyzer
(Wave 2-3 plan: 09-04)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Contract 1: interrupt() is NEVER called (autonomous agent)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_analyzer_does_not_call_interrupt(mock_audit_writer) -> None:
    """CostAnalyzer.__call__ does NOT call interrupt() — fully autonomous (SCM-03).

    CostAnalyzer is analogous to KnowledgeCurator: autonomous read-only agent
    that computes results and writes audit without human intervention.

    Implementation target: scm_cost_analyzer.agent.CostAnalyzer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-04) — contract (SCM-03 autonomous): "
        "CostAnalyzer.__call__(state) must NOT call interrupt(). "
        "Patch 'scm_cost_analyzer.agent.interrupt' with a MagicMock (or sentinel). "
        "Assert: interrupt_mock.call_count == 0 after __call__ returns."
    )


# ---------------------------------------------------------------------------
# Contract 2: Decision.AUTO in audit write
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_analyzer_writes_decision_auto_audit_row(mock_audit_writer) -> None:
    """CostAnalyzer writes AuditRecord with Decision.AUTO — no HITL (SCM-03).

    Decision.AUTO signals: AI made the decision autonomously; no human approval
    was required or solicited. This is the same pattern as KnowledgeCurator.

    Implementation target: scm_cost_analyzer.agent.CostAnalyzer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-04) — contract: after CostAnalyzer.__call__(state), "
        "audit_writer.write was called at least once. "
        "The written AuditRecord must have decision == Decision.AUTO. "
        "Verify: written_record.decision == Decision.AUTO (from sft_agents.models.enums)."
    )


# ---------------------------------------------------------------------------
# Contract 3: action_type is COST_REPORT
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_analyzer_writes_cost_report_action_type(mock_audit_writer) -> None:
    """CostAnalyzer audit row has action_type=COST_REPORT (SCM-03, Phase 9 ActionType).

    COST_REPORT was added to ActionType enum in plan 09-00a (migration 011 lockstep).
    Implementation target: scm_cost_analyzer.agent.CostAnalyzer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-04) — contract: "
        "written_record.action_type == ActionType.COST_REPORT.value. "
        "(ActionType.COST_REPORT added in 09-00a migration 011 lockstep.)"
    )


# ---------------------------------------------------------------------------
# Contract 4: Read-only — no scm.* writes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_analyzer_is_read_only_no_scm_writes(mock_pool, mock_audit_writer) -> None:
    """CostAnalyzer performs no writes to scm.* tables — read-only (SCM-03).

    CostAnalyzer only reads from audit.actions (cost KPIs). It never writes
    to scm.inventory_levels, scm.energy_readings, or scm.historical_orders.

    Implementation target: scm_cost_analyzer.agent.CostAnalyzer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-04) — contract: "
        "After CostAnalyzer.__call__(state), mock_pool connection.execute must NOT "
        "have been called with any INSERT/UPDATE/DELETE statement targeting scm.* tables. "
        "CostAnalyzer is read-only; all scm.* access is via SELECT only."
    )


# ---------------------------------------------------------------------------
# Contract 5: Aggregates downtime + scrap + energy cost from audit.actions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cost_analyzer_aggregates_downtime_scrap_energy_cost(mock_audit_writer) -> None:
    """CostAnalyzer aggregates cost breakdown: downtime + scrap + energy from audit.actions (SCM-03).

    The agent reads existing audit rows for downtime events, scrap events, and
    energy consumption, then computes a cost breakdown. The output state must
    contain a cost breakdown with at least these three components.

    Implementation target: scm_cost_analyzer.agent.CostAnalyzer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-04) — contract: "
        "CostAnalyzer result state contains a cost breakdown with keys for "
        "downtime_cost_eur, scrap_cost_eur, energy_cost_eur (or equivalent). "
        "These are aggregated from audit.actions (read-only cross-cluster query)."
    )


# ---------------------------------------------------------------------------
# Contract 6: AuditWriter.write() called with positional AuditRecord (CR-02)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_written_with_positional_audit_record(mock_audit_writer) -> None:
    """audit_writer.write() receives a positional AuditRecord — no kwargs (CR-02).

    Phase 8 critical bug: write(action_type=..., decision=...) → TypeError.
    Contract: call_args_list[0][0][0] is AuditRecord; call_args_list[0][1] == {}.

    Implementation target: scm_cost_analyzer.agent.CostAnalyzer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-04) — contract (CR-02): "
        "audit_writer.write must be called as write(record) — single positional AuditRecord. "
        "Verify: call_args_list[0][0][0] is AuditRecord instance, "
        "call_args_list[0][1] == {} (empty kwargs dict)."
    )
