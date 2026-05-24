"""TRN-05 declaration metadata for KnowledgeCurator (Plan 08-06).

Single source of truth for the four TRN-05 declaration fields:
  - AGENT_ID: logical agent identifier.
  - TOOL_INVENTORY: ordered list of tools/capabilities.
  - DATA_SOURCES: upstream stores read + downstream stores written.
  - KPIS_IMPACTED: KPIs moved by the agent.
  - HITL_TIER_DEFAULT: always "none" (D-KC-04 autonomous).

build_trn05_evidence_panel: assemble the declaration dict for audit rows.

Pattern reference: mnt_rca_specialist/metadata.py (07-07).
"""

from __future__ import annotations

from typing import Any

# ----------------------------------------------------------------------
# Module-level constants
# ----------------------------------------------------------------------

#: Agent slug (matches audit.actions.agent_id).
AGENT_ID: str = "knowledge-curator"

#: Cluster the agent belongs to (matches audit.actions.cluster).
CLUSTER: str = "knowledge"

#: Tool inventory (D-KC-01/02/03 capabilities).
TOOL_INVENTORY: tuple[str, ...] = (
    "dedup_check",
    "staleness_check",
    "reuse_rate",
)

#: Upstream stores read + downstream stores written.
DATA_SOURCES: tuple[str, ...] = (
    "Qdrant sop collection (near-dup cosine query)",
    "audit.actions evidence_panel rag_citations (reuse-rate source_uri)",
    "documents table (total indexed count)",
    "ingest_state table (document metadata)",
)

#: KPIs moved by the agent.
KPIS_IMPACTED: tuple[str, ...] = (
    "knowledge_reuse_rate",
    "duplicate_rate",
    "stale_doc_count",
)

#: D-KC-04: ALWAYS autonomous — no HITL. Never "supervisor" or "operator".
HITL_TIER_DEFAULT: str = "none"


# ----------------------------------------------------------------------
# Helper — assemble the declaration dict for audit rows.
# ----------------------------------------------------------------------


def build_trn05_evidence_panel(
    input_summary: str,
    *,
    tool_calls: list[dict[str, Any]],
    decision: str,
    duration_ms: int = 0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the TRN-05 declaration dict for KnowledgeCurator.

    The ``hitl_tier`` is ALWAYS ``"none"`` (D-KC-04 — autonomous agent).
    Any caller-supplied ``hitl_tier`` in ``extra`` is silently ignored.

    Args:
        input_summary: Intent summary (≤500 chars).
        tool_calls: Ordered list of tool invocation dicts.
        decision: Audit decision string (e.g. "auto").
        duration_ms: End-to-end duration in milliseconds.
        extra: Optional extra keys to merge (cannot override required keys).

    Returns:
        Plain dict with at minimum ``agent_id``, ``tool_inventory``,
        ``data_sources``, ``hitl_tier``, ``kpis_impacted`` + call-specific fields.
    """
    summary = input_summary[:500]
    panel: dict[str, Any] = {
        "agent_id": AGENT_ID,
        "cluster": CLUSTER,
        "tool_inventory": list(TOOL_INVENTORY),
        "data_sources": list(DATA_SOURCES),
        "hitl_tier": HITL_TIER_DEFAULT,  # ALWAYS "none" — D-KC-04 autonomous
        "kpis_impacted": list(KPIS_IMPACTED),
        "tool_calls": tool_calls,
        "decision": decision,
        "duration_ms": duration_ms,
        "input_summary": summary,
        "input_truncated": len(input_summary) > 500,
    }
    if extra:
        # Caller's extras NEVER overwrite the required keys.
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
    "build_trn05_evidence_panel",
]
