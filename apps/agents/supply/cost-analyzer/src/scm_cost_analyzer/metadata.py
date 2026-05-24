"""Metadata per CostAnalyzer (Plan 09-04, SCM-03).

Single source of truth per i campi di dichiarazione TRN-05:
  - AGENT_ID: identificatore logico dell'agente.
  - CLUSTER: cluster di appartenenza (supply).
  - DATA_SOURCES: store letti (audit.actions, read-only).
  - KPIS_IMPACTED: KPI mossi dall'agente.
  - HITL_TIER_DEFAULT: None (agente autonomo — Decision.AUTO).

build_evidence_panel: helper per assemblare il dict di dichiarazione nelle audit row.

Pattern: apps/agents/knowledge/knowledge-curator/src/trn_knowledge_curator/metadata.py
"""

from __future__ import annotations

from typing import Any

# ----------------------------------------------------------------------
# Costanti di modulo
# ----------------------------------------------------------------------

#: Slug agente (corrisponde a audit.actions.agent_id).
AGENT_ID: str = "cost-analyzer"

#: Cluster di appartenenza (corrisponde a audit.actions.cluster).
CLUSTER: str = "supply"

#: Inventario tool / capabilities.
TOOL_INVENTORY: tuple[str, ...] = (
    "cost_aggregation",
    "oepv_simulation",
    "sensitivity_analysis",
)

#: Store letti (read-only) + scritti.
#: CostAnalyzer è read-only su audit.actions; scrive una sola riga COST_REPORT.
DATA_SOURCES: tuple[str, ...] = (
    "audit.actions (cost KPIs — downtime/scrap/energy rows, read-only)",
)

#: KPI mossi dall'agente.
KPIS_IMPACTED: tuple[str, ...] = (
    "roi_breakdown_eur",
    "oepv_total_score",
    "oepv_sensitivity_pct",
)

#: D-SCM-03: SEMPRE autonomo — nessun HITL. Non supervisor né operator.
HITL_TIER_DEFAULT: None = None


# ----------------------------------------------------------------------
# Helper — assemblare il dict di dichiarazione per le audit row.
# ----------------------------------------------------------------------


def build_evidence_panel(
    input_summary: str,
    *,
    tool_calls: list[dict[str, Any]],
    decision: str,
    duration_ms: int = 0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Restituisce il dict di dichiarazione per CostAnalyzer.

    Il campo ``hitl_tier`` è SEMPRE ``None`` (agente autonomo SCM-03).
    Eventuali chiavi ``hitl_tier`` fornite in ``extra`` vengono ignorate.

    Args:
        input_summary: Sommario dell'input (max 500 char).
        tool_calls: Lista ordinata di dict di invocazione tool.
        decision: Stringa decision dell'audit (es. "auto").
        duration_ms: Durata end-to-end in millisecondi.
        extra: Chiavi extra opzionali (non possono sovrascrivere le chiavi obbligatorie).

    Returns:
        Dict con almeno ``agent_id``, ``tool_inventory``, ``data_sources``,
        ``hitl_tier``, ``kpis_impacted`` + campi call-specific.
    """
    summary = input_summary[:500]
    panel: dict[str, Any] = {
        "agent_id": AGENT_ID,
        "cluster": CLUSTER,
        "tool_inventory": list(TOOL_INVENTORY),
        "data_sources": list(DATA_SOURCES),
        "hitl_tier": HITL_TIER_DEFAULT,  # SEMPRE None — autonomo SCM-03
        "kpis_impacted": list(KPIS_IMPACTED),
        "tool_calls": tool_calls,
        "decision": decision,
        "duration_ms": duration_ms,
        "input_summary": summary,
        "input_truncated": len(input_summary) > 500,
    }
    if extra:
        for key, value in extra.items():
            if key not in panel:
                panel[key] = value
    return panel


__all__ = [
    "AGENT_ID",
    "CLUSTER",
    "DATA_SOURCES",
    "HITL_TIER_DEFAULT",
    "KPIS_IMPACTED",
    "TOOL_INVENTORY",
    "build_evidence_panel",
]
