"""SCM-02 declaration metadata for EnergyOptimizer (Plan 09-03).

Single source of truth for the agent declaration constants and evidence panel builder.
Mirrors the pattern from apps/agents/supply/inventory-manager/src/scm_inventory_manager/metadata.py.

Data sources: scm.energy_readings + scm.enpi_baseline (the two tables EnergyOptimizer reads).
HITL tier: always supervisor (energy schedule proposals require sign-off before shift dispatch).

The build_evidence_panel helper enforces the 5 required declaration keys and prevents
caller-supplied overrides from lowering the HITL tier.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Module-level constants — keep in lockstep with MkDocs supply/energy-optimizer page.
# ---------------------------------------------------------------------------

#: Agent slug.
AGENT_ID: str = "energy-optimizer"

#: Cluster identifier.
CLUSTER: str = "supply"

#: Tool inventory for EnergyOptimizer (SCM-02).
TOOL_INVENTORY: tuple[str, ...] = (
    "fetch_energy_readings",
    "compute_enpi",
    "propose_off_peak_schedule",
    "escalate_to_energy_supervisor",
)

#: Upstream stores read by the agent (SCM-02: only scm.* tables).
DATA_SOURCES: tuple[str, ...] = (
    "scm.energy_readings",
    "scm.enpi_baseline",
)

#: KPIs moved by the agent.
KPIS_IMPACTED: tuple[str, ...] = (
    "enpi_kwh_per_kg",
    "off_peak_kwh_pct",
    "energy_deviation_pct",
    "peak_hour_cost_eur",
)

#: HITL tier is always SUPERVISOR for energy schedule proposals (SCM-02).
HITL_TIER_DEFAULT: str = "supervisor"


# ---------------------------------------------------------------------------
# Helper — assemble the declaration evidence panel dict.
# ---------------------------------------------------------------------------


def build_evidence_panel(
    input_summary: str,
    *,
    model_version: str = "llm-free@energy-optimizer",
    tool_calls: list[dict[str, Any]] | None = None,
    decision: str = "hitl_supervisor",
    prompt_hash: str = "0" * 64,
    tokens: dict[str, int] | None = None,
    duration_ms: int = 0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the evidence panel dict for EnergyOptimizer audit rows.

    The hitl_tier is ALWAYS 'supervisor' (SCM-02 energy schedule sign-off).
    Caller-supplied extra keys NEVER overwrite the 5 required panel keys
    (agent_id, tool_inventory, data_sources, hitl_tier, kpis_impacted).

    Args:
        input_summary:  Intent summary (<=500 chars, T-04-Checkpoint-PII).
        model_version:  LLM model identifier (default llm-free since EnPI is LLM-free).
        tool_calls:     Ordered list of tool invocation dicts (default empty).
        decision:       Audit decision string (default "hitl_supervisor").
        prompt_hash:    sha256 hex of the system prompt (default all-zeros for LLM-free).
        tokens:         Token accounting dict (default zeros for LLM-free path).
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
        "hitl_tier": HITL_TIER_DEFAULT,   # ALWAYS supervisor — SCM-02
        "kpis_impacted": list(KPIS_IMPACTED),
        # Call-specific keys.
        "model": model_version,
        "tool_calls": tool_calls or [],
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
    "CLUSTER",
    "DATA_SOURCES",
    "HITL_TIER_DEFAULT",
    "KPIS_IMPACTED",
    "TOOL_INVENTORY",
    "build_evidence_panel",
]
