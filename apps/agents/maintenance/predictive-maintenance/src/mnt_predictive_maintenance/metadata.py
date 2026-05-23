"""MNT-05 / OPS-05 declaration metadata for PredictiveMaintenance (Plan 07-06).

This module is the **single source of truth** for the four OPS-05
declaration fields:

    * ``TOOL_INVENTORY``   — list of tool names invoked by the agent.
    * ``DATA_SOURCES``     — list of upstream stores read / downstream
                             stores written.
    * ``KPIS_IMPACTED``    — list of business KPIs the agent moves.

The ``build_ops05_evidence_panel()`` helper assembles the declaration into
a plain ``dict`` that downstream consumers (HTTP gateway, audit dashboards,
docs build) can attach to an agent response.

Pattern: mirrors ``ops_anomaly_detector/metadata.py`` exactly, substituting
the 3 constant lists + KPI labels for the maintenance cluster (D-PM-04).
"""

from __future__ import annotations

from typing import Any

# ----------------------------------------------------------------------
# Module-level constants — keep in lockstep with the MkDocs page.
# ----------------------------------------------------------------------

#: Canonical tool inventory for PredictiveMaintenance.
TOOL_INVENTORY: list[str] = [
    "query_timescale",
    "escalate_to_supervisor",
    "log_event",
]

#: Upstream stores read + downstream stores written by the agent.
DATA_SOURCES: list[str] = [
    "TimescaleDB sensor_events",
    "sft-ml ridge-fd001-fd003-v1.0.joblib",
    "sft-assets registry",
]

#: KPIs moved by the agent (mirrors the MkDocs page).
KPIS_IMPACTED: list[str] = [
    "mtbf",
    "planned_vs_unplanned_downtime",
    "rul_accuracy_mae",
]

#: Agent slug — mirrors ``mnt_predictive_maintenance.agent.AGENT_ID``.
AGENT_ID: str = "predictive-maintenance"


# ----------------------------------------------------------------------
# Helper — assemble the declaration dict.
# ----------------------------------------------------------------------


def build_ops05_evidence_panel(
    *,
    hitl_tier: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the OPS-05 declaration dict for PredictiveMaintenance.

    Parameters
    ----------
    hitl_tier:
        Optional override for the per-decision tier actually invoked.
        Values: ``"none"`` (AUTO, health>=0.3) or ``"supervisor"`` (HITL, health<0.3).
        When ``None``, defaults to ``"none"`` (fully autonomous path).
    extra:
        Optional extra keys to merge into the returned dict. These do NOT
        replace any of the five required OPS-05 keys.

    Returns
    -------
    dict
        Plain dict with at minimum ``agent_id``, ``tool_inventory``,
        ``data_sources``, ``hitl_tier``, ``kpis_impacted``.
    """
    resolved_tier = hitl_tier if hitl_tier is not None else "none"

    panel: dict[str, Any] = {
        "agent_id": AGENT_ID,
        "tool_inventory": list(TOOL_INVENTORY),
        "data_sources": list(DATA_SOURCES),
        "hitl_tier": resolved_tier,
        "kpis_impacted": list(KPIS_IMPACTED),
    }
    if extra:
        # Caller's extras NEVER overwrite the 5 OPS-05 required keys.
        for key, value in extra.items():
            if key not in panel:
                panel[key] = value
    return panel


__all__ = [
    "AGENT_ID",
    "DATA_SOURCES",
    "KPIS_IMPACTED",
    "TOOL_INVENTORY",
    "build_ops05_evidence_panel",
]
