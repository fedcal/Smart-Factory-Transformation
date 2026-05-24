"""CostAnalyzer LangGraph node — agente autonomo SCM-03 (Plan 09-04).

Design autonomo (SCM-03):
  - Pienamente autonomo: nessun meccanismo HITL (interrupt()) in questo modulo.
  - Aggrega costi da audit.actions via HistoricalCostAggregator (read-only).
  - Calcola il simulatore OEPV parametrico con OepvConfig (default o da state).
  - Scrive IMMEDIATAMENTE una riga audit Decision.AUTO (ActionType.COST_REPORT).
  - NON scrive mai su scm.* — read-only by design (fallback sicuro del supply subgraph).

Audit trail:
  - Una sola riga COST_REPORT con Decision.AUTO (SCM-03, no HITL).
  - AuditRecord passato POSIZIONALMENTE a audit_writer.write(record) (CR-02).

Security:
  - T-09-15: input ribasso/pt validati da compute_oepv (ValueError su out-of-range).
  - T-09-16: singola riga deterministica Decision.AUTO — no replay double-write.
  - T-09-17: is_anomaly_warning documentata come warning, non regola legale definitiva.

Pattern: apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/agent.py
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from sft_agents.audit.writer import AuditWriter
from sft_agents.models.audit import AuditRecord
from sft_agents.models.budget import BudgetSnapshot
from sft_agents.models.enums import ActionType, Decision
from sft_agents.models.evidence import EvidencePanel, TokenUsage, ToolCall

from scm_cost_analyzer.cost_aggregator import HistoricalCostAggregator
from scm_cost_analyzer.metadata import AGENT_ID, CLUSTER
from scm_cost_analyzer.models import CostBreakdown, OepvReport
from scm_cost_analyzer.oepv import OepvConfig, compute_oepv

_log = structlog.get_logger("agent.cost-analyzer")

# ---------------------------------------------------------------------------
# Costanti di modulo
# ---------------------------------------------------------------------------

#: Sentinel model string per agenti deterministici (no LLM).
_NO_LLM_MODEL: str = "deterministic@cost-analyzer"

#: Sentinel prompt hash (nessun prompt LLM — tutti zeri).
_NO_PROMPT_HASH: str = "0" * 64

#: Budget snapshot vuoto per agenti deterministici.
_EMPTY_BUDGET = BudgetSnapshot(
    tokens_input=0,
    tokens_output=0,
    tokens_total=0,
    cost_usd_simulated=0.0,
    duration_ms=0,
    limit_tokens=0,
    limit_cost_usd=0.0,
    limit_duration_s=0,
)

#: Finestra temporale default per l'aggregazione costi (30 giorni).
_DEFAULT_WINDOW_DAYS: int = 30


# ---------------------------------------------------------------------------
# CostAnalyzer
# ---------------------------------------------------------------------------


class CostAnalyzer:
    """Agente autonomo CostAnalyzer — LangGraph node (SCM-03, Decision.AUTO).

    Legge i costi da audit.actions, calcola il simulatore OEPV parametrico e
    scrive una riga audit Decision.AUTO (ActionType.COST_REPORT). NESSUN HITL.

    Read-only: non scrive mai su scm.* (fallback sicuro del supply subgraph).

    Parameters
    ----------
    pool:
        asyncpg.Pool per HistoricalCostAggregator (read-only su audit.actions).
    audit_writer:
        AuditWriter per la scrittura della riga COST_REPORT.
    llm:
        Non usato (LLM-free). Accettato per uniformità di interfaccia.
    """

    def __init__(
        self,
        pool: Any,
        audit_writer: AuditWriter | Any,
        llm: Any = None,
    ) -> None:
        if pool is None:
            raise ValueError("pool non deve essere None")
        if audit_writer is None:
            raise ValueError("audit_writer non deve essere None")
        self._pool = pool
        self._audit = audit_writer
        # llm ignorato — agente deterministico LLM-free (SCM-03)
        _ = llm

    # ------------------------------------------------------------------
    # LangGraph node entrypoint
    # ------------------------------------------------------------------

    async def __call__(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """LangGraph node entrypoint per l'analisi costi + simulazione OEPV.

        Legge input opzionali da state (no KeyError — CR-03):
          - ribasso_pct (float, default 10.0): ribasso percentuale OEPV.
          - pt (float, default 50.0): punteggio tecnico OEPV.
          - oepv_config (dict, default {}): override OepvConfig.
          - window_days (int, default 30): finestra aggregazione costi.

        NOTA: interrupt() NON viene mai chiamato — agente pienamente autonomo.

        Returns:
            {"cost_breakdown": dict, "oepv_report": dict}
        """
        # Leggi input con default sicuri (no KeyError — CR-03)
        ribasso_pct: float = float(state.get("ribasso_pct", 10.0))
        pt: float = float(state.get("pt", 50.0))
        oepv_config_overrides: dict[str, Any] = dict(state.get("oepv_config", {}) or {})
        window_days: int = int(state.get("window_days", _DEFAULT_WINDOW_DAYS))

        # Costruisci OepvConfig (immutabile; eventuali override da state)
        oepv_cfg = OepvConfig(**oepv_config_overrides) if oepv_config_overrides else OepvConfig()

        # Calcola finestra temporale (tz-aware)
        now = datetime.now(UTC)
        from datetime import timedelta
        window_start = now - timedelta(days=window_days)

        # Step 1: Aggregazione costi (read-only da audit.actions)
        aggregator = HistoricalCostAggregator(self._pool)
        cost_breakdown: CostBreakdown = await aggregator.aggregate(
            window_start=window_start,
            window_end=now,
        )

        # Step 2: Simulazione OEPV parametrica (pure function, LLM-free)
        oepv_result = compute_oepv(
            ribasso_pct=ribasso_pct,
            pt=pt,
            config=oepv_cfg,
        )
        oepv_report = OepvReport.from_oepv_result(oepv_result)

        # Step 3: Scrivi audit row Decision.AUTO IMMEDIATAMENTE (autonomo — nessun HITL)
        await self._write_cost_audit(
            cost_breakdown=cost_breakdown,
            oepv_report=oepv_report,
            ribasso_pct=ribasso_pct,
            pt=pt,
            ts=now,
        )

        _log.info(
            "cost_analyzer_complete",
            total_cost_eur=cost_breakdown.total_eur,
            oepv_total_score=oepv_report.total_score,
            is_anomaly_warning=oepv_report.is_anomaly_warning,
        )

        return {
            "cost_breakdown": cost_breakdown.model_dump(),
            "oepv_report": oepv_report.model_dump(),
        }

    # ------------------------------------------------------------------
    # Audit helper (Decision.AUTO — nessun interrupt)
    # ------------------------------------------------------------------

    async def _write_cost_audit(
        self,
        *,
        cost_breakdown: CostBreakdown,
        oepv_report: OepvReport,
        ribasso_pct: float,
        pt: float,
        ts: datetime,
    ) -> None:
        """Scrive la riga audit COST_REPORT con Decision.AUTO (SCM-03).

        NESSUNA chiamata a interrupt() — autonomo per design.
        AuditRecord passato POSIZIONALMENTE (CR-02).
        """
        action_id = uuid4()
        synthetic_call = ToolCall(
            name="cost_analysis",
            args={
                "ribasso_pct": ribasso_pct,
                "pt": pt,
            },
            result={
                "total_cost_eur": cost_breakdown.total_eur,
                "oepv_total_score": oepv_report.total_score,
                "is_anomaly_warning": oepv_report.is_anomaly_warning,
            },
            duration_ms=0,
            ts=ts,
        )
        evidence_panel = EvidencePanel(
            input_summary=(
                f"cost_analysis ribasso={ribasso_pct}% pt={pt} "
                f"total_cost={cost_breakdown.total_eur:.2f}eur "
                f"oepv_score={oepv_report.total_score:.4f}"
            )[:500],
            input_truncated=False,
            tool_calls=[synthetic_call],
            rag_citations=[],
            confidence=1.0,
            model=_NO_LLM_MODEL,
            prompt_hash=_NO_PROMPT_HASH,
            tokens=TokenUsage(input=0, output=0, total=0),
            duration_ms=0,
        )
        record = AuditRecord(
            id=uuid4(),
            ts=ts,
            action_id=action_id,
            agent_id=AGENT_ID,
            thread_id=f"{CLUSTER}.{AGENT_ID}.cost-report",
            cluster=CLUSTER,
            action_type=ActionType.COST_REPORT.value,
            evidence_panel=evidence_panel,
            decision=Decision.AUTO,
            decision_actor=None,
            motivation=None,
            budget_snapshot=_EMPTY_BUDGET,
            approval_id=None,
        )
        # POSIZIONALE — non kwargs (CR-02)
        await self._audit.write(record)
        _log.info(
            "cost_report_audit_written",
            action_id=str(action_id),
            total_cost_eur=cost_breakdown.total_eur,
            oepv_total_score=oepv_report.total_score,
        )


__all__ = ["CostAnalyzer"]
