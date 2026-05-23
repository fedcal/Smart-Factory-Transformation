"""OPS-05 declaration metadata for AnomalyDetector (Plan 06-14).

This module is the **single source of truth** for the four OPS-05
declaration fields:

    * ``TOOL_INVENTORY``      — list of tool names invoked by the agent.
    * ``DATA_SOURCES``        — list of upstream stores read / downstream
                                 stores written.
    * ``KPIS_IMPACTED``       — list of business KPIs the agent moves.
    * ``HITL_TIER_DEFAULT``   — string tier label applied when no
                                 per-decision override is supplied.

The bilingual MkDocs page ``docs/docs/agents/operations/anomaly-detector.md``
(IT + EN) restates the same lists so reviewers can diff doc ↔ code in a
single PR (T-V6-doc-drift mitigation).

The ``build_ops05_evidence_panel()`` helper assembles the declaration into
a plain ``dict`` that downstream consumers (HTTP gateway, audit dashboards,
docs build) can attach to an agent response without modifying the strict
``sft_agents.models.evidence.EvidencePanel`` schema (which has
``extra='forbid'``).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

# ----------------------------------------------------------------------
# Module-level constants — keep in lockstep with the MkDocs page.
# ----------------------------------------------------------------------

#: Canonical tool inventory — AnomalyDetector is deterministic and only
#: consumes the TimescaleDB query tool (Plan 06-06).
TOOL_INVENTORY: tuple[str, ...] = (
    "query_timescale",
)

#: Upstream stores read + downstream stores written by the agent.
DATA_SOURCES: tuple[str, ...] = (
    "TimescaleDB sensor_events",
    "PostgreSQL audit.actions",
    "PostgreSQL rate_limit_state",
    "anomaly_baselines.yaml",
    "sft_assets registry",
)

#: KPIs moved by the agent (mirrors the MkDocs page).
KPIS_IMPACTED: tuple[str, ...] = (
    "mtbf",
    "alert_fatigue_rate",
    "sensor_coverage",
)

#: Default HITL tier — fully autonomous; emissions are ``Decision.AUTO``.
HITL_TIER_DEFAULT: str = "none"

#: Agent slug — mirrors ``ops_anomaly_detector.agent.AGENT_ID``.
AGENT_ID: str = "anomaly-detector"


# ----------------------------------------------------------------------
# Helper — assemble the declaration dict.
# ----------------------------------------------------------------------


def build_ops05_evidence_panel(
    *,
    hitl_tier: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the OPS-05 declaration dict for this agent.

    Parameters
    ----------
    hitl_tier:
        Optional override for the per-decision tier actually invoked (e.g.
        ``"suppressed"`` when the rate limiter dropped the alert). When
        ``None`` (default), returns :data:`HITL_TIER_DEFAULT`.
    extra:
        Optional extra keys to merge into the returned dict (e.g. the
        actual ``severity`` of the anomaly). These do NOT replace any of
        the five required OPS-05 keys.

    Returns
    -------
    dict
        Plain dict with at minimum ``agent_id``, ``tool_inventory``,
        ``data_sources``, ``hitl_tier``, ``kpis_impacted``. Lists are
        returned as ``list`` (not tuple) for JSON serialisation parity.
    """
    panel: dict[str, Any] = {
        "agent_id": AGENT_ID,
        "tool_inventory": list(TOOL_INVENTORY),
        "data_sources": list(DATA_SOURCES),
        "hitl_tier": hitl_tier if hitl_tier is not None else HITL_TIER_DEFAULT,
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
    "HITL_TIER_DEFAULT",
    "KPIS_IMPACTED",
    "TOOL_INVENTORY",
    "build_ops05_evidence_panel",
]
