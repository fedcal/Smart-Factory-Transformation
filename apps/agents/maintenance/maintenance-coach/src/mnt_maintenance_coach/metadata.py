"""OPS-05 / MNT-05 declaration metadata for MaintenanceCoach (Plan 07-08).

This module is the **single source of truth** for the OPS-05 declaration
fields required by the maintenance cluster:

    * ``TOOL_INVENTORY``  — list of tool names invoked by the agent.
    * ``DATA_SOURCES``    — list of upstream stores read / downstream
                            stores written.
    * ``KPIS_IMPACTED``  — list of business KPIs the agent moves.
    * ``HITL_TIER_DEFAULT`` — tier applied when no per-decision override given.

The bilingual MkDocs page ``docs/docs/agents/maintenance/maintenance-coach.md``
(IT + EN) restates the same lists so reviewers can diff doc ↔ code in a
single PR (T-V6-doc-drift mitigation).

``build_ops05_evidence_panel()`` assembles the declaration into a plain dict
that downstream consumers (07-10 HTTP gateway, audit dashboards, docs build)
can attach to an agent response. The dict shape follows the same convention as
``ops_anomaly_detector.metadata`` (Phase 6 06-14 analog).

Coach-specific note:
    ``HITL_TIER_DEFAULT`` is ``'supervisor'`` because every help-request
    escalation routes through ``HITL_SUPERVISOR`` (D-MC-02). Normal steps
    use ``Decision.AUTO`` (``hitl_tier='auto'``), but the default reflects
    the agent's escalation posture when in doubt.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Module-level constants (keep in lockstep with MkDocs page + audit registry)
# ---------------------------------------------------------------------------

#: Tools the Coach LLM can invoke (D-MC-02 + Phase 5 RAG + Phase 6 audit tools)
TOOL_INVENTORY: list[str] = [
    "rag_search",
    "request_help",
    "escalate_to_supervisor",
    "log_event",
]

#: Upstream stores read + downstream stores written by the agent.
DATA_SOURCES: list[str] = [
    "Qdrant sop_chunks",
    "Phase 5 SOP corpus",
    "langgraph_checkpoints PG (migration 005)",
]

#: KPIs moved by the agent (mirrors the MkDocs page + MNT-03/MNT-06 scope).
KPIS_IMPACTED: list[str] = [
    "mttr",
    "first_time_fix_rate",
    "intervention_completion_rate",
    "technician_help_request_rate",
]

#: Default HITL tier — 'supervisor' because request_help escalates to supervisor.
#: Per-step AUTO decisions override this to 'auto' via build_ops05_evidence_panel.
HITL_TIER_DEFAULT: str = "supervisor"

#: Agent slug — mirrors ``mnt_maintenance_coach.agent.AGENT_ID``.
AGENT_ID: str = "maintenance-coach"


# ---------------------------------------------------------------------------
# Helper — assemble the declaration dict
# ---------------------------------------------------------------------------


def build_ops05_evidence_panel(
    *,
    hitl_tier: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the OPS-05 / MNT-05 declaration dict for MaintenanceCoach.

    Parameters
    ----------
    hitl_tier:
        Optional per-decision tier override. Common values:
          - ``'auto'``: normal SOP step (Decision.AUTO)
          - ``'supervisor'``: request_help escalation (Decision.HITL_SUPERVISOR)
          - ``'technician_assignment_required'``: HITL for null technician_id
        When ``None`` (default), returns :data:`HITL_TIER_DEFAULT` = ``'supervisor'``.
    extra:
        Optional extra keys to merge (e.g. ``intervention_id``, ``step_no``,
        ``escalation_trigger``). These do NOT replace the five required OPS-05 keys.

    Returns
    -------
    dict
        Plain dict with at minimum ``agent_id``, ``tool_inventory``,
        ``data_sources``, ``hitl_tier``, ``kpis_impacted``.
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
