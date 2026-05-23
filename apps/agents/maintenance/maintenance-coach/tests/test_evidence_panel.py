"""MNT-05 evidence-panel declaration contract for MaintenanceCoach (Plan 07-11).

Asserts that ``mnt_maintenance_coach.metadata`` exposes the four OPS-05
declaration fields — ``tool_inventory``, ``data_sources``, ``hitl_tier``,
``kpis_impacted`` — and that ``build_ops05_evidence_panel()`` returns a dict
with all five required keys (the four above + ``agent_id``).

This is the lockstep test that enforces docs ↔ code consistency (T-V7-doc-drift
mitigation): the same constants documented in
``docs/docs/agents/maintenance/maintenance-coach.md`` are asserted here.

Key contract: HITL has two paths — AUTO for normal SOP steps, SUPERVISOR when
``request_help`` is invoked (D-MC-02). The HITL_TIER_DEFAULT is 'supervisor'
reflecting the escalation posture.

The agent itself is NOT instantiated by this test — wiring ``MaintenanceCoach``
requires Qdrant + langgraph_checkpoints (PG) which are out of scope for a unit test.
"""

from __future__ import annotations

from mnt_maintenance_coach import metadata


_OPS05_REQUIRED_KEYS = (
    "agent_id",
    "tool_inventory",
    "data_sources",
    "hitl_tier",
    "kpis_impacted",
)


def _is_non_empty_str_iterable(value: object) -> bool:
    """True when ``value`` is a list/tuple of non-empty strings (no dicts)."""
    if not isinstance(value, (list, tuple)):
        return False
    if len(value) == 0:
        return False
    return all(isinstance(x, str) and len(x) > 0 for x in value)


# ----------------------------------------------------------------------
# Module-level constants — lockstep with MkDocs page
# ----------------------------------------------------------------------


def test_tool_inventory_includes_rag_search() -> None:
    """MaintenanceCoach uses rag_search to retrieve SOP steps from Qdrant."""
    assert _is_non_empty_str_iterable(metadata.TOOL_INVENTORY)
    assert "rag_search" in metadata.TOOL_INVENTORY


def test_tool_inventory_includes_request_help() -> None:
    """Tool inventory includes request_help (D-MC-02 technician escalation tool)."""
    assert "request_help" in metadata.TOOL_INVENTORY


def test_tool_inventory_includes_escalate_and_log() -> None:
    """Tool inventory includes escalate_to_supervisor and log_event."""
    assert "escalate_to_supervisor" in metadata.TOOL_INVENTORY
    assert "log_event" in metadata.TOOL_INVENTORY


def test_tool_inventory_length() -> None:
    """Coach has exactly 4 tools: rag_search, request_help, escalate_to_supervisor, log_event."""
    assert len(metadata.TOOL_INVENTORY) == 4


def test_data_sources_include_qdrant_sop_chunks() -> None:
    """Data sources include Qdrant sop_chunks (Phase 5 SOP corpus)."""
    assert _is_non_empty_str_iterable(metadata.DATA_SOURCES)
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "qdrant" in joined or "sop_chunks" in joined


def test_data_sources_include_langgraph_checkpoints() -> None:
    """Data sources include langgraph_checkpoints PG (cross-shift persistence)."""
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "langgraph" in joined or "checkpoint" in joined


def test_kpis_include_mttr() -> None:
    """KPI list includes mttr — primary maintenance timing KPI."""
    assert _is_non_empty_str_iterable(metadata.KPIS_IMPACTED)
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "mttr" in joined


def test_kpis_include_first_time_fix_rate() -> None:
    """KPI list includes first_time_fix_rate (procedural coaching effectiveness)."""
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "first_time_fix" in joined or "first-time-fix" in joined


def test_kpis_include_help_request_rate() -> None:
    """KPI list includes technician_help_request_rate (SOP quality signal)."""
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "help_request" in joined or "help-request" in joined


def test_hitl_tier_default_is_supervisor() -> None:
    """HITL_TIER_DEFAULT is 'supervisor' (request_help escalation posture D-MC-02)."""
    assert metadata.HITL_TIER_DEFAULT == "supervisor"


def test_agent_id_is_maintenance_coach() -> None:
    """AGENT_ID constant matches the documented slug."""
    assert metadata.AGENT_ID == "maintenance-coach"


# ----------------------------------------------------------------------
# build_ops05_evidence_panel() helper
# ----------------------------------------------------------------------


def test_build_ops05_evidence_panel_returns_dict_with_all_required_keys() -> None:
    """Helper assembles a dict containing the 5 OPS-05 declaration fields."""
    panel = metadata.build_ops05_evidence_panel()
    assert isinstance(panel, dict)
    for key in _OPS05_REQUIRED_KEYS:
        assert key in panel, f"missing OPS-05 key: {key!r}"


def test_build_ops05_evidence_panel_default_tier_is_supervisor() -> None:
    """Default tier is 'supervisor' matching HITL_TIER_DEFAULT (escalation posture)."""
    panel = metadata.build_ops05_evidence_panel()
    assert panel["hitl_tier"] == "supervisor"


def test_build_ops05_evidence_panel_accepts_auto_tier_for_normal_step() -> None:
    """Caller can override to 'auto' for normal SOP steps (Decision.AUTO path)."""
    panel = metadata.build_ops05_evidence_panel(hitl_tier="auto")
    assert panel["hitl_tier"] == "auto"


def test_build_ops05_evidence_panel_accepts_supervisor_tier_for_help_step() -> None:
    """Caller can explicitly set 'supervisor' for request_help escalation steps."""
    panel = metadata.build_ops05_evidence_panel(hitl_tier="supervisor")
    assert panel["hitl_tier"] == "supervisor"


def test_build_ops05_evidence_panel_agent_id_matches_constant() -> None:
    """The panel's agent_id must equal AGENT_ID from metadata."""
    panel = metadata.build_ops05_evidence_panel()
    assert panel["agent_id"] == metadata.AGENT_ID == "maintenance-coach"


def test_build_ops05_evidence_panel_lists_match_module_constants() -> None:
    """The panel returns the module-level constants verbatim (no per-call drift)."""
    panel = metadata.build_ops05_evidence_panel()
    assert list(panel["tool_inventory"]) == list(metadata.TOOL_INVENTORY)
    assert list(panel["data_sources"]) == list(metadata.DATA_SOURCES)
    assert list(panel["kpis_impacted"]) == list(metadata.KPIS_IMPACTED)


# ----------------------------------------------------------------------
# Import-level guard — surface API
# ----------------------------------------------------------------------


def test_metadata_module_is_importable_from_package_root() -> None:
    """`metadata` is accessible via the sub-module path for HTTP / docs callers."""
    import mnt_maintenance_coach.metadata as mod

    assert hasattr(mod, "build_ops05_evidence_panel")
    assert hasattr(mod, "TOOL_INVENTORY")
    assert hasattr(mod, "DATA_SOURCES")
    assert hasattr(mod, "KPIS_IMPACTED")
    assert hasattr(mod, "AGENT_ID")
    assert hasattr(mod, "HITL_TIER_DEFAULT")
