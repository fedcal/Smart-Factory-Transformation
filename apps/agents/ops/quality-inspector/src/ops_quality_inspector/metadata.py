"""OPS-05 declaration metadata for QualityInspector (Plan 06-14).

Single source of truth for the four OPS-05 declaration fields. The bilingual
MkDocs page ``docs/docs/agents/operations/quality-inspector.md`` restates
the same lists so reviewers can diff doc ↔ code in a single PR
(T-V6-doc-drift mitigation).
"""

from __future__ import annotations

from typing import Any

# ----------------------------------------------------------------------
# Module-level constants — keep in lockstep with the MkDocs page.
# ----------------------------------------------------------------------

#: QualityInspector exposes only ``rag_search`` as a LangChain tool; the
#: LLM grader is invoked directly as a pure function (not as a tool).
TOOL_INVENTORY: tuple[str, ...] = (
    "rag_search",
)

DATA_SOURCES: tuple[str, ...] = (
    "NATS JetStream quality.events",
    "PostgreSQL audit.actions",
    "PostgreSQL approval_actions",
    "Qdrant sop_chunks",
    "failure_modes.yaml",
)

KPIS_IMPACTED: tuple[str, ...] = (
    "defect_rate_4pt",
    "scrap_rate",
    "dye_lot_deviation",
)

#: Default tier is SUPERVISOR — the modal severity-band lands on
#: ``major`` (the ``minor`` auto-log branch and the ``critical``
#: manager+safety branch are reported per-decision via the override arg).
HITL_TIER_DEFAULT: str = "supervisor"

AGENT_ID: str = "quality-inspector"


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
