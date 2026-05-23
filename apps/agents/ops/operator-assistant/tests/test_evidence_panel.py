"""OPS-05 evidence-panel declaration contract for OperatorAssistant (Plan 06-14).

Asserts that ``ops_operator_assistant.metadata`` exposes the four OPS-05
declaration fields and that ``build_ops05_evidence_panel()`` returns a dict
with all five required keys (the four above + ``agent_id``).

This is the lockstep test the planner authored alongside the bilingual
MkDocs pages (T-V6-doc-drift mitigation): the same constants are documented
in ``docs/docs/agents/operations/operator-assistant.md`` and asserted here.
"""

from __future__ import annotations

import pytest

from ops_operator_assistant import metadata


_OPS05_REQUIRED_KEYS = (
    "agent_id",
    "tool_inventory",
    "data_sources",
    "hitl_tier",
    "kpis_impacted",
)


def _is_non_empty_str_iterable(value: object) -> bool:
    """True when ``value`` is a list/tuple of non-empty strings."""
    if not isinstance(value, (list, tuple)):
        return False
    if len(value) == 0:
        return False
    return all(isinstance(x, str) and len(x) > 0 for x in value)


# ----------------------------------------------------------------------
# Module-level constants
# ----------------------------------------------------------------------


def test_tool_inventory_constant_lists_all_5_tools() -> None:
    """OperatorAssistant's 5-tool toolbelt is fully declared (D-OA-02)."""
    assert _is_non_empty_str_iterable(metadata.TOOL_INVENTORY)
    expected = {
        "rag_search",
        "traverse_graph",
        "query_timescale",
        "escalate_to_supervisor",
        "log_event",
    }
    inventory = set(metadata.TOOL_INVENTORY)
    assert expected.issubset(inventory), (
        f"missing tools: {expected - inventory}"
    )


def test_data_sources_constant_includes_qdrant_neo4j_and_timescale() -> None:
    """Declared data sources match the 5-tool toolbelt back-ends."""
    assert _is_non_empty_str_iterable(metadata.DATA_SOURCES)
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "qdrant" in joined or "sop_chunks" in joined
    assert "neo4j" in joined
    assert "timescale" in joined or "sensor_events" in joined


def test_kpis_impacted_constant_includes_mttr_and_first_time_fix() -> None:
    """KPI list mirrors the bilingual MkDocs page (single source of truth)."""
    assert _is_non_empty_str_iterable(metadata.KPIS_IMPACTED)
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "mttr" in joined
    assert "first_time_fix" in joined or "first-time-fix" in joined


def test_hitl_tier_default_constant_is_none_or_supervisor() -> None:
    """OperatorAssistant's nominal interaction is read-only (none); escalation routes to SUPERVISOR."""
    assert isinstance(metadata.HITL_TIER_DEFAULT, str)
    assert metadata.HITL_TIER_DEFAULT.lower() in ("none", "supervisor")


# ----------------------------------------------------------------------
# build_ops05_evidence_panel() helper
# ----------------------------------------------------------------------


def test_build_ops05_evidence_panel_returns_dict_with_all_required_keys() -> None:
    """Helper assembles a dict containing the 5 OPS-05 declaration fields."""
    panel = metadata.build_ops05_evidence_panel()
    assert isinstance(panel, dict)
    for key in _OPS05_REQUIRED_KEYS:
        assert key in panel, f"missing OPS-05 key: {key!r}"


def test_build_ops05_evidence_panel_agent_id_is_operator_assistant() -> None:
    """The panel's agent_id must equal the documented slug."""
    panel = metadata.build_ops05_evidence_panel()
    assert panel["agent_id"] == "operator-assistant"


def test_build_ops05_evidence_panel_accepts_hitl_tier_override() -> None:
    """Caller can pass the actually-resolved tier when escalation occurred."""
    panel = metadata.build_ops05_evidence_panel(hitl_tier="supervisor")
    assert panel["hitl_tier"] == "supervisor"


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
    """`metadata` is re-exported by the package root for HTTP / docs callers."""
    import ops_operator_assistant as pkg

    assert hasattr(pkg, "metadata") or hasattr(pkg, "build_ops05_evidence_panel")
