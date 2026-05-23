"""MNT-05 declaration metadata for RCASpecialist (Plan 07-07).

Single source of truth for the four OPS-05 / MNT-05 declaration fields.
The bilingual MkDocs page ``docs/docs/agents/maintenance/rca-specialist.md``
restates the same lists (T-V7-doc-drift mitigation).

HITL tier is always SUPERVISOR — literal D-RCA-02. There is no per-severity
branching; the ``build_ops05_evidence_panel`` helper always returns
``hitl_tier="supervisor"`` and ignores any override that would lower the tier.
"""

from __future__ import annotations

from typing import Any

# ----------------------------------------------------------------------
# Module-level constants — keep in lockstep with the MkDocs page.
# ----------------------------------------------------------------------

#: Tool inventory for RCASpecialist (D-RCA-01 + D-RCA-02).
#: Order matches the ReAct loop tool registration.
TOOL_INVENTORY: tuple[str, ...] = (
    "rag_search",
    "traverse_graph",
    "escalate_to_supervisor",
    "log_event",
)

#: Upstream stores read + downstream stores written by the agent.
DATA_SOURCES: tuple[str, ...] = (
    "Qdrant sop_chunks",
    "Neo4j textile graph",
    "PG documents",
    "maintenance.downtime_events (08)",
)

#: KPIs moved by the agent (mirrors the MkDocs page).
KPIS_IMPACTED: tuple[str, ...] = (
    "rca_completeness_5why",
    "citation_grounding_rate",
    "mttr_root_cause_to_fix",
)

#: D-RCA-02 literal: ALWAYS supervisor — no severity branching.
HITL_TIER_DEFAULT: str = "supervisor"

#: Agent slug.
AGENT_ID: str = "rca-specialist"


# ----------------------------------------------------------------------
# Helper — assemble the declaration dict.
# ----------------------------------------------------------------------


def build_ops05_evidence_panel(
    input_summary: str,
    *,
    model_version: str,
    tool_calls: list[dict[str, Any]],
    decision: str,
    prompt_hash: str,
    tokens: dict[str, int] | None = None,
    duration_ms: int = 0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the MNT-05 declaration dict for RCASpecialist.

    The ``hitl_tier`` is ALWAYS ``"supervisor"`` (D-RCA-02 literal).
    Any caller-supplied ``hitl_tier`` in ``extra`` is silently ignored
    to prevent accidental de-escalation.

    Args:
        input_summary:  Intent summary (≤500 chars, T-04-Checkpoint-PII).
        model_version:  LLM model identifier, e.g. ``"qwen2.5-7b@rca-specialist"``.
        tool_calls:     Ordered list of tool invocation dicts (name, args, result, duration_ms, ts).
        decision:       Audit decision string (e.g. ``"hitl_supervisor"``).
        prompt_hash:    sha256 hex of the system prompt + problem statement (64 chars).
        tokens:         Token accounting dict with ``input``, ``output``, ``total`` keys.
        duration_ms:    End-to-end duration in milliseconds.
        extra:          Optional extra keys to merge (cannot override the 5 required keys).

    Returns:
        Plain dict with at minimum ``agent_id``, ``tool_inventory``,
        ``data_sources``, ``hitl_tier``, ``kpis_impacted`` + call-specific fields.
    """
    summary = input_summary[:500]
    panel: dict[str, Any] = {
        "agent_id": AGENT_ID,
        "tool_inventory": list(TOOL_INVENTORY),
        "data_sources": list(DATA_SOURCES),
        "hitl_tier": HITL_TIER_DEFAULT,  # ALWAYS supervisor — D-RCA-02
        "kpis_impacted": list(KPIS_IMPACTED),
        "model": model_version,
        "tool_calls": tool_calls,
        "decision": decision,
        "prompt_hash": prompt_hash,
        "tokens": tokens or {"input": 0, "output": 0, "total": 0},
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
    "DATA_SOURCES",
    "HITL_TIER_DEFAULT",
    "KPIS_IMPACTED",
    "TOOL_INVENTORY",
    "build_ops05_evidence_panel",
]
