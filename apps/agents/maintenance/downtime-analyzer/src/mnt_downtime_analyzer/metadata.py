"""OPS-05 declaration metadata for DowntimeAnalyzer (plan 07-09, D-DA-03).

This module is the single source of truth for the OPS-05 declaration fields.
Full implementation in Task 4 (agent.py). This stub satisfies imports during
Tasks 2-3.
"""

from __future__ import annotations

from typing import Any

#: Tool inventory — DA is deterministic (no LLM tools).
TOOL_INVENTORY: tuple[str, ...] = (
    "query_timescale",
    "log_event",
)

#: Data sources for DowntimeAnalyzer (D-DA-01/02/03).
DATA_SOURCES: tuple[str, ...] = (
    "NATS maintenance.downtime.>",
    "PG maintenance.downtime_events hypertable (08)",
    "PG audit.actions cross-cluster QUALITY_VERDICT (Phase 6 06-01)",
    "sim-textile production_state.py (06-09)",
    "sft-assets registry",
)

#: KPIs impacted by the agent.
KPIS_IMPACTED: tuple[str, ...] = (
    "oee_availability",
    "oee_performance",
    "oee_quality",
    "mtbf",
    "top_5_downtime_reason_codes",
)

#: Default HITL tier — fully autonomous (no HITL for analytics reports).
HITL_TIER_DEFAULT: str = "none"

#: Agent slug — mirrors agent.AGENT_ID.
AGENT_ID: str = "downtime-analyzer"


def build_ops05_evidence_panel(
    *,
    hitl_tier: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the OPS-05 declaration dict for DowntimeAnalyzer.

    Parameters
    ----------
    hitl_tier:
        Optional per-decision tier override. Default: HITL_TIER_DEFAULT ("none").
    extra:
        Optional extra keys to merge. Does NOT replace the 5 required OPS-05 keys.

    Returns
    -------
    dict
        Plain dict with agent_id, tool_inventory, data_sources, hitl_tier, kpis_impacted.
    """
    panel: dict[str, Any] = {
        "agent_id": AGENT_ID,
        "tool_inventory": list(TOOL_INVENTORY),
        "data_sources": list(DATA_SOURCES),
        "hitl_tier": hitl_tier if hitl_tier is not None else HITL_TIER_DEFAULT,
        "kpis_impacted": list(KPIS_IMPACTED),
    }
    if extra:
        for key, value in extra.items():
            if key not in panel:
                panel[key] = value
    return panel


__all__ = [
    "AGENT_ID",
    "DATA_SOURCES",
    "HITL_TIER_DEFAULT",
    "KPIS_IMPACTED",
    "TOOL_INVENTORY",
    "build_ops05_evidence_panel",
]
