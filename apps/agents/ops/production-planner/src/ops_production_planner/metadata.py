"""OPS-05 declaration metadata for ProductionPlanner (Plan 06-14).

Single source of truth for the four OPS-05 declaration fields. The bilingual
MkDocs page ``docs/docs/agents/operations/production-planner.md`` restates
the same lists so reviewers can diff doc ↔ code in a single PR
(T-V6-doc-drift mitigation).
"""

from __future__ import annotations

from typing import Any

# ----------------------------------------------------------------------
# Module-level constants — keep in lockstep with the MkDocs page.
# ----------------------------------------------------------------------

#: ProductionPlanner only uses ``rag_search`` for SOP citations; the
#: scheduling heuristic is a pure function (sft_domain.scheduling.heuristic)
#: invoked directly rather than via a LangChain tool.
TOOL_INVENTORY: tuple[str, ...] = (
    "rag_search",
)

DATA_SOURCES: tuple[str, ...] = (
    "orders.yaml",
    "asset_capacity.yaml",
    "failure_modes.yaml",
    "Qdrant sop_chunks",
    "PostgreSQL audit.actions",
    "PostgreSQL approval_actions",
    "NATS JetStream hitl.approvals",
)

KPIS_IMPACTED: tuple[str, ...] = (
    "on_time_delivery_rate",
    "oee_availability",
    "schedule_stability",
)

#: ProductionPlanner ALWAYS routes through SUPERVISOR (T-V6-hitl-bypass);
#: the agent has no Decision.AUTO branch.
HITL_TIER_DEFAULT: str = "supervisor"

AGENT_ID: str = "production-planner"


def build_ops05_evidence_panel(
    *,
    hitl_tier: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the OPS-05 declaration dict for this agent.

    See :func:`ops_anomaly_detector.metadata.build_ops05_evidence_panel`
    for the contract — the shape is identical across all OPS agents
    (single OPS-05 schema).
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
