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

from sft_agents.models.audit import AuditRecord
from sft_agents.models.enums import ActionType, Decision

from scm_cost_analyzer.agent import CostAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agent(mock_pool, mock_audit_writer):
    """Costruisce CostAnalyzer con pool e audit_writer mock."""
    return CostAnalyzer(
        pool=mock_pool,
        audit_writer=mock_audit_writer,
    )


async def _invoke(agent, state=None):
    """Invoca l'agente con state opzionale."""
    return await agent(state or {})


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
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    # Mock fetchrow restituisce None (zero costi — valido per CostBreakdown)
    conn.fetchrow = AsyncMock(return_value=None)

    agent = _make_agent(pool, mock_audit_writer)

    with patch("scm_cost_analyzer.agent.interrupt", create=True) as interrupt_mock:
        await _invoke(agent)
        assert interrupt_mock.call_count == 0, (
            f"interrupt() non deve essere chiamato da CostAnalyzer (autonomo SCM-03). "
            f"Chiamate trovate: {interrupt_mock.call_count}"
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
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    conn.fetchrow = AsyncMock(return_value=None)

    agent = _make_agent(pool, mock_audit_writer)
    await _invoke(agent)

    assert mock_audit_writer.write.call_count >= 1, (
        "audit_writer.write deve essere chiamato almeno una volta."
    )
    written_record = mock_audit_writer.write.call_args_list[0][0][0]
    assert written_record.decision == Decision.AUTO, (
        f"Decision deve essere Decision.AUTO, trovata: {written_record.decision}"
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
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    conn.fetchrow = AsyncMock(return_value=None)

    agent = _make_agent(pool, mock_audit_writer)
    await _invoke(agent)

    assert mock_audit_writer.write.call_count >= 1
    written_record = mock_audit_writer.write.call_args_list[0][0][0]
    assert written_record.action_type == ActionType.COST_REPORT.value, (
        f"action_type deve essere COST_REPORT, trovato: {written_record.action_type!r}"
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
    agent = _make_agent(mock_pool, mock_audit_writer)
    await _invoke(agent)

    # Raccoglie tutte le chiamate a conn.execute
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    for call in conn.execute.call_args_list:
        sql = (call[0][0] if call[0] else "").upper()
        # Nessuna INSERT/UPDATE/DELETE su tabelle scm.*
        assert "INSERT INTO SCM." not in sql, f"CostAnalyzer non deve scrivere su scm.*: {sql}"
        assert "UPDATE SCM." not in sql, f"CostAnalyzer non deve aggiornare scm.*: {sql}"
        assert "DELETE FROM SCM." not in sql, f"CostAnalyzer non deve cancellare da scm.*: {sql}"


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
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    conn.fetchrow = AsyncMock(return_value=None)

    agent = _make_agent(pool, mock_audit_writer)
    result = await _invoke(agent)

    assert "cost_breakdown" in result, "Il risultato deve contenere 'cost_breakdown'."
    cb = result["cost_breakdown"]
    assert "downtime_cost_eur" in cb, "cost_breakdown deve avere 'downtime_cost_eur'."
    assert "scrap_cost_eur" in cb, "cost_breakdown deve avere 'scrap_cost_eur'."
    assert "energy_cost_eur" in cb, "cost_breakdown deve avere 'energy_cost_eur'."


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
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    conn.fetchrow = AsyncMock(return_value=None)

    agent = _make_agent(pool, mock_audit_writer)
    await _invoke(agent)

    assert mock_audit_writer.write.call_count >= 1, (
        "audit_writer.write deve essere chiamato almeno una volta."
    )

    first_call = mock_audit_writer.write.call_args_list[0]
    positional_args = first_call[0]  # tuple di argomenti posizionali
    keyword_args = first_call[1]     # dict di argomenti keyword

    assert len(positional_args) == 1, (
        f"write() deve ricevere esattamente 1 argomento posizionale (AuditRecord). "
        f"Trovati: {len(positional_args)} posizionali."
    )
    assert isinstance(positional_args[0], AuditRecord), (
        f"Il primo argomento posizionale deve essere AuditRecord, "
        f"trovato: {type(positional_args[0])!r}"
    )
    assert keyword_args == {}, (
        f"write() non deve ricevere kwargs (CR-02). Trovati: {keyword_args!r}"
    )
