"""OPS-05 declaration metadata for OperatorAssistant (Plan 06-14).

Single source of truth for the four OPS-05 declaration fields. The bilingual
MkDocs page ``docs/docs/agents/operations/operator-assistant.md`` restates
the same lists so reviewers can diff doc ↔ code in a single PR
(T-V6-doc-drift mitigation).
"""

from __future__ import annotations

from typing import Any

# ----------------------------------------------------------------------
# Module-level constants — keep in lockstep with the MkDocs page.
# ----------------------------------------------------------------------

#: Full 5-tool toolbelt (D-OA-02). Order matches ``agent._build_tools``.
TOOL_INVENTORY: tuple[str, ...] = (
    "rag_search",
    "traverse_graph",
    "query_timescale",
    "escalate_to_supervisor",
    "log_event",
)

DATA_SOURCES: tuple[str, ...] = (
    "Qdrant sop_chunks",
    "Neo4j textile entity graph",
    "TimescaleDB sensor_events",
    "PostgreSQL audit.actions",
    "PostgreSQL approval_actions",
    "NATS JetStream hitl.approvals",
)

KPIS_IMPACTED: tuple[str, ...] = (
    "mttr",
    "first_time_fix_rate",
    "knowledge_reuse_rate",
)

#: Nominal interaction is read-only (operator Q&A) — no HITL.
#: Escalation paths report the actual tier via the override arg.
HITL_TIER_DEFAULT: str = "none"

AGENT_ID: str = "operator-assistant"


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
