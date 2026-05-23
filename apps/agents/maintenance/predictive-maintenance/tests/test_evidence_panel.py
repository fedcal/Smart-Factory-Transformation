"""MNT-05 evidence-panel declaration contract for PredictiveMaintenance (Plan 07-11).

Asserts that ``mnt_predictive_maintenance.metadata`` exposes the four OPS-05
declaration fields — ``tool_inventory``, ``data_sources``, ``hitl_tier``,
``kpis_impacted`` — and that ``build_ops05_evidence_panel()`` returns a dict
with all five required keys (the four above + ``agent_id``).

This is the lockstep test that enforces docs ↔ code consistency (T-V7-doc-drift
mitigation): the same constants documented in
``docs/docs/agents/maintenance/predictive-maintenance.md`` are asserted here.

The agent itself is NOT instantiated by this test — wiring ``PredictiveMaintenance``
requires TimescaleDB + asyncpg which are out of scope for a unit test. The
declaration constants are module-level and importable without runtime dependencies.
"""

from __future__ import annotations

from mnt_predictive_maintenance import metadata


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


def test_tool_inventory_includes_query_timescale() -> None:
    """PredictiveMaintenance tool inventory includes query_timescale (D-PM-04)."""
    assert _is_non_empty_str_iterable(metadata.TOOL_INVENTORY)
    assert "query_timescale" in metadata.TOOL_INVENTORY


def test_tool_inventory_includes_escalate_and_log() -> None:
    """Tool inventory includes escalate_to_supervisor and log_event (HITL + audit)."""
    assert "escalate_to_supervisor" in metadata.TOOL_INVENTORY
    assert "log_event" in metadata.TOOL_INVENTORY


def test_tool_inventory_length() -> None:
    """PM has exactly 3 tools: query_timescale, escalate_to_supervisor, log_event."""
    assert len(metadata.TOOL_INVENTORY) == 3


def test_data_sources_include_timescale() -> None:
    """Data sources include TimescaleDB sensor_events (primary input store)."""
    assert _is_non_empty_str_iterable(metadata.DATA_SOURCES)
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "timescale" in joined or "sensor_events" in joined


def test_data_sources_include_ml_model() -> None:
    """Data sources include the sft-ml Ridge model artefact (NASA C-MAPSS)."""
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "sft-ml" in joined or "ridge" in joined or "joblib" in joined


def test_kpis_include_mtbf() -> None:
    """KPI list includes MTBF — primary maintenance cluster KPI."""
    assert _is_non_empty_str_iterable(metadata.KPIS_IMPACTED)
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "mtbf" in joined


def test_kpis_include_planned_vs_unplanned() -> None:
    """KPI list includes planned_vs_unplanned_downtime ratio."""
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "planned" in joined and "unplanned" in joined


def test_kpis_include_rul_accuracy() -> None:
    """KPI list includes rul_accuracy_mae (model quality monitoring)."""
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "rul_accuracy" in joined or "mae" in joined


def test_agent_id_is_predictive_maintenance() -> None:
    """AGENT_ID constant matches the documented slug."""
    assert metadata.AGENT_ID == "predictive-maintenance"


# ----------------------------------------------------------------------
# build_ops05_evidence_panel() helper
# ----------------------------------------------------------------------


def test_build_ops05_evidence_panel_returns_dict_with_all_required_keys() -> None:
    """Helper assembles a dict containing the 5 OPS-05 declaration fields."""
    panel = metadata.build_ops05_evidence_panel()
    assert isinstance(panel, dict)
    for key in _OPS05_REQUIRED_KEYS:
        assert key in panel, f"missing OPS-05 key: {key!r}"


def test_build_ops05_evidence_panel_agent_id_matches_constant() -> None:
    """The panel's agent_id must equal AGENT_ID from metadata."""
    panel = metadata.build_ops05_evidence_panel()
    assert panel["agent_id"] == metadata.AGENT_ID == "predictive-maintenance"


def test_build_ops05_evidence_panel_default_hitl_tier_is_none() -> None:
    """Default hitl_tier is 'none' — PM runs AUTO for health_index >= 0.3."""
    panel = metadata.build_ops05_evidence_panel()
    assert panel["hitl_tier"] == "none"


def test_build_ops05_evidence_panel_accepts_supervisor_tier() -> None:
    """Caller can override tier to 'supervisor' for health_index < 0.3 path."""
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
    """`metadata` is accessible via the sub-module path for HTTP / docs callers."""
    import mnt_predictive_maintenance.metadata as mod

    assert hasattr(mod, "build_ops05_evidence_panel")
    assert hasattr(mod, "TOOL_INVENTORY")
    assert hasattr(mod, "DATA_SOURCES")
    assert hasattr(mod, "KPIS_IMPACTED")
    assert hasattr(mod, "AGENT_ID")
