"""TRN-05 declaration metadata for ShiftHandover (Plan 08-02).

Single source of truth for the declaration constants and evidence panel builder.

D-SH-02 (resolved post-research): DATA_SOURCES lists only the two existing tables
that the aggregator actually reads (audit.actions + maintenance.downtime_events).
No new ops-layer tables are created or listed. Alert counts derive from
audit.actions WHERE action_type='ANOMALY_ALERT'; work-order presence is inferred
from DOWNTIME_VERDICT evidence_panel.work_order_id.

HITL tier is always SUPERVISOR (D-SH-03: dual sequential supervisor sign-off).
The build_trn05_evidence_panel helper always returns hitl_tier="supervisor" and
ignores any caller-supplied override that would lower the tier.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Module-level constants — keep in lockstep with MkDocs shift-handover page.
# ---------------------------------------------------------------------------

#: Agent slug.
AGENT_ID: str = "shift-handover"

#: Tool inventory for ShiftHandover (D-SH-01 + D-SH-03).
TOOL_INVENTORY: tuple[str, ...] = (
    "fetch_audit_window",
    "fetch_downtime_events",
    "escalate_to_supervisor",
)

#: Upstream stores read by the agent (D-SH-02: audit chain only, no new tables).
#: Alert counts: audit.actions WHERE action_type='ANOMALY_ALERT'.
#: Work-orders:  audit.actions DOWNTIME_VERDICT evidence_panel.work_order_id.
DATA_SOURCES: tuple[str, ...] = (
    "audit.actions (all clusters)",
    "maintenance.downtime_events",
)

#: KPIs moved by the agent (mirrors the MkDocs page).
KPIS_IMPACTED: tuple[str, ...] = (
    "shift_handover_completeness",
    "cross_shift_continuity",
)

#: D-SH-03 literal: ALWAYS supervisor — dual sequential sign-off required.
HITL_TIER_DEFAULT: str = "supervisor"


# ---------------------------------------------------------------------------
# Helper — assemble the declaration dict.
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
    """Return the TRN-05 declaration dict for ShiftHandover.

    The hitl_tier is ALWAYS 'supervisor' (D-SH-03 literal — dual sequential
    sign-off). Any caller-supplied hitl_tier in extra is silently ignored to
    prevent accidental de-escalation.

    Caller-supplied extra keys NEVER overwrite the 5 required panel keys
    (agent_id, tool_inventory, data_sources, hitl_tier, kpis_impacted).

    Args:
        input_summary:  Intent summary (<=500 chars, T-04-Checkpoint-PII).
        model_version:  LLM model identifier, e.g. "qwen2.5-7b@shift-handover".
        tool_calls:     Ordered list of tool invocation dicts.
        decision:       Audit decision string (e.g. "hitl_supervisor").
        prompt_hash:    sha256 hex of the system prompt + shift window (64 chars).
        tokens:         Token accounting dict with input, output, total keys.
        duration_ms:    End-to-end duration in milliseconds.
        extra:          Optional extra keys to merge (cannot override 5 required keys).

    Returns:
        Plain dict with at minimum agent_id, tool_inventory, data_sources,
        hitl_tier, kpis_impacted plus call-specific fields.
    """
    summary = input_summary[:500]
    panel: dict[str, Any] = {
        # Required 5 keys — cannot be overridden by caller extra.
        "agent_id": AGENT_ID,
        "tool_inventory": list(TOOL_INVENTORY),
        "data_sources": list(DATA_SOURCES),
        "hitl_tier": HITL_TIER_DEFAULT,   # ALWAYS supervisor — D-SH-03
        "kpis_impacted": list(KPIS_IMPACTED),
        # Call-specific keys.
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
        # Caller extras NEVER overwrite the 5 required keys.
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
