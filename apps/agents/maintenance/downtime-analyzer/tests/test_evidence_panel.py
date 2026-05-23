"""MNT-05 evidence-panel declaration contract for DowntimeAnalyzer (Plan 07-11).

Asserts that ``mnt_downtime_analyzer.metadata`` exposes the four OPS-05
declaration fields — ``tool_inventory``, ``data_sources``, ``hitl_tier``,
``kpis_impacted`` — and that ``build_ops05_evidence_panel()`` returns a dict
with all five required keys (the four above + ``agent_id``).

This is the lockstep test that enforces docs ↔ code consistency (T-V7-doc-drift
mitigation): the same constants documented in
``docs/docs/agents/maintenance/downtime-analyzer.md`` are asserted here.

Key contract: DowntimeAnalyzer is a fully deterministic agent — HITL tier is
always 'none'. No LLM is invoked; tool inventory is minimal (query_timescale + log_event).

The agent itself is NOT instantiated by this test — wiring ``DowntimeAnalyzer``
requires TimescaleDB + NATS + asyncpg which are out of scope for a unit test.
"""

from __future__ import annotations

from mnt_downtime_analyzer import metadata


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
    """DowntimeAnalyzer uses query_timescale for OEE queries and ingest."""
    assert _is_non_empty_str_iterable(metadata.TOOL_INVENTORY)
    assert "query_timescale" in metadata.TOOL_INVENTORY


def test_tool_inventory_includes_log_event() -> None:
    """Tool inventory includes log_event (audit of DOWNTIME_VERDICT + OEE_REPORT)."""
    assert "log_event" in metadata.TOOL_INVENTORY


def test_tool_inventory_length() -> None:
    """DA has exactly 2 tools: query_timescale, log_event (deterministic — no LLM tools)."""
    assert len(metadata.TOOL_INVENTORY) == 2


def test_data_sources_include_nats() -> None:
    """Data sources include NATS maintenance.downtime.> (real-time ingest stream)."""
    assert _is_non_empty_str_iterable(metadata.DATA_SOURCES)
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "nats" in joined or "maintenance.downtime" in joined


def test_data_sources_include_downtime_events_table() -> None:
    """Data sources include maintenance.downtime_events hypertable (migration 08)."""
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "downtime_events" in joined or "hypertable" in joined


def test_data_sources_include_quality_verdict() -> None:
    """Data sources include cross-cluster QUALITY_VERDICT from audit.actions (D-DA-02)."""
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "quality" in joined or "audit.actions" in joined


def test_kpis_include_oee_availability() -> None:
    """KPI list includes oee_availability (core OEE component)."""
    assert _is_non_empty_str_iterable(metadata.KPIS_IMPACTED)
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "oee_availability" in joined or "availability" in joined


def test_kpis_include_oee_quality() -> None:
    """KPI list includes oee_quality (cross-cluster component)."""
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "oee_quality" in joined or "quality" in joined


def test_kpis_include_top_5_downtime_reason_codes() -> None:
    """KPI list includes top_5_downtime_reason_codes (Pareto analysis)."""
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "reason_code" in joined or "pareto" in joined or "top_5" in joined


def test_kpis_include_mtbf() -> None:
    """KPI list includes mtbf (per-asset failure frequency)."""
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "mtbf" in joined


def test_hitl_tier_default_is_none() -> None:
    """DowntimeAnalyzer is fully autonomous — HITL_TIER_DEFAULT must be 'none'."""
    assert metadata.HITL_TIER_DEFAULT == "none"


def test_agent_id_is_downtime_analyzer() -> None:
    """AGENT_ID constant matches the documented slug."""
    assert metadata.AGENT_ID == "downtime-analyzer"


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
    assert panel["agent_id"] == metadata.AGENT_ID == "downtime-analyzer"


def test_build_ops05_evidence_panel_default_hitl_tier_is_none() -> None:
    """Default hitl_tier is 'none' — DA is fully autonomous (no HITL gate)."""
    panel = metadata.build_ops05_evidence_panel()
    assert panel["hitl_tier"] == "none"


def test_build_ops05_evidence_panel_accepts_hitl_tier_override() -> None:
    """Caller can pass an override tier (used by tests, monitoring tools)."""
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
    import mnt_downtime_analyzer.metadata as mod

    assert hasattr(mod, "build_ops05_evidence_panel")
    assert hasattr(mod, "TOOL_INVENTORY")
    assert hasattr(mod, "DATA_SOURCES")
    assert hasattr(mod, "KPIS_IMPACTED")
    assert hasattr(mod, "AGENT_ID")
    assert hasattr(mod, "HITL_TIER_DEFAULT")
