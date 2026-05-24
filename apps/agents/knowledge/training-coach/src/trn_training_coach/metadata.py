"""TRN-05 declaration metadata for TrainingCoach (Plan 08-05).

Single source of truth for the agent declaration fields.
Mirrors the rca-specialist metadata pattern (mnt_rca_specialist.metadata).

HITL tier is SUPERVISOR on pass — D-TC-03.
Scoring path is deterministic (no LLM) — T-08-09 mitigation documented.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Agent slug.
AGENT_ID: str = "training-coach"

#: Cluster name.
CLUSTER: str = "knowledge"

#: Tool inventory for TrainingCoach.
TOOL_INVENTORY: tuple[str, ...] = (
    "retrieval_pipeline.search",  # RAG retrieval from Qdrant training/sop collections
    "escalate_to_supervisor",     # HITL escalation on competency pass (D-TC-03)
)

#: Data sources read and written by the agent.
DATA_SOURCES: tuple[str, ...] = (
    "Qdrant training collection",    # RAG: training-specific SOP chunks
    "Qdrant sop_chunks collection",  # RAG: standard SOP chunks
    "SOP frontmatter roles",         # Persona role lookup (D-X-03)
    "audit.actions TRAINING_SESSION",   # Audit write (on pass after interrupt, on fail immediately)
    "audit.actions TRAINING_SIGNOFF",   # Audit write (on pass only, after interrupt resumes)
)

#: KPIs moved by the agent.
KPIS_IMPACTED: tuple[str, ...] = (
    "training_time",          # Time to complete a coaching session
    "competency_pass_rate",   # Fraction of sessions passing the threshold
)

#: HITL tier on competency pass (D-TC-03).
HITL_TIER_PASS: str = "supervisor"

#: Default pass threshold (D-TC-03).
DEFAULT_PASS_THRESHOLD: float = 0.80


# ---------------------------------------------------------------------------
# Helper — assemble the TRN-05 evidence panel dict.
# ---------------------------------------------------------------------------


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
    """Return the TRN-05 declaration dict for TrainingCoach.

    Mirrors build_ops05_evidence_panel from rca-specialist.

    The ``hitl_tier`` on pass is ALWAYS ``"supervisor"`` (D-TC-03).
    Any caller-supplied ``hitl_tier`` in ``extra`` is silently ignored
    to prevent accidental de-escalation.

    Args:
        input_summary:  Intent summary (<=500 chars, T-04-Checkpoint-PII).
        model_version:  LLM model identifier, e.g. ``"qwen2.5-7b@training-coach"``.
        tool_calls:     Ordered list of tool invocation dicts.
        decision:       Audit decision string (e.g. ``"hitl_supervisor"``).
        prompt_hash:    sha256 hex of the system prompt + persona_role (64 chars).
        tokens:         Token accounting dict with ``input``, ``output``, ``total`` keys.
        duration_ms:    End-to-end duration in milliseconds.
        extra:          Optional extra keys to merge (cannot override required keys).

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
        "hitl_tier": HITL_TIER_PASS,  # ALWAYS supervisor on pass — D-TC-03
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
    "CLUSTER",
    "DATA_SOURCES",
    "DEFAULT_PASS_THRESHOLD",
    "HITL_TIER_PASS",
    "KPIS_IMPACTED",
    "TOOL_INVENTORY",
    "build_trn05_evidence_panel",
]
