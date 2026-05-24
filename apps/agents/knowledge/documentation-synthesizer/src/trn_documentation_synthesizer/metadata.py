"""TRN-05 declaration metadata for DocumentationSynthesizer (Plan 08-07).

Single source of truth for the four TRN-05 declaration fields.
HITL tier is always SUPERVISOR — literal D-DS-03.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Agent slug (kebab-case, Pattern I)
AGENT_ID: str = "documentation-synthesizer"

#: Tool inventory for DocumentationSynthesizer (D-DS-01/02/03).
TOOL_INVENTORY: tuple[str, ...] = (
    "retrieval_pipeline_search",
    "historical_event_aggregator",
    "sop_builder",
    "sop_translator",
    "sop_citation_validator",
    "qdrant_indexer",
)

#: Upstream stores read + downstream stores written by the agent.
DATA_SOURCES: tuple[str, ...] = (
    "audit.actions (RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT rows)",
    "Qdrant sop collection (read for RAG grounding)",
    "Qdrant sop collection (write after HITL approval)",
)

#: KPIs moved by the agent.
KPIS_IMPACTED: tuple[str, ...] = (
    "sop_coverage",
    "doc_authoring_time",
)

#: D-DS-03 literal: ALWAYS supervisor — no severity branching.
HITL_TIER_DEFAULT: str = "supervisor"


def build_trn05_evidence_panel(
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
    """Return the TRN-05 declaration dict for DocumentationSynthesizer.

    The ``hitl_tier`` is ALWAYS ``"supervisor"`` (D-DS-03 literal).
    Any caller-supplied ``hitl_tier`` in ``extra`` is silently ignored.

    Args:
        input_summary:  Intent summary (<=500 chars, T-04-Checkpoint-PII).
        model_version:  LLM model identifier, e.g. ``"qwen2.5-7b@documentation-synthesizer"``.
        tool_calls:     Ordered list of tool invocation dicts.
        decision:       Audit decision string (e.g. ``"hitl_supervisor"``).
        prompt_hash:    sha256 hex of the system prompt + failure_mode (64 chars).
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
        "hitl_tier": HITL_TIER_DEFAULT,  # ALWAYS supervisor — D-DS-03
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
    "build_trn05_evidence_panel",
]
