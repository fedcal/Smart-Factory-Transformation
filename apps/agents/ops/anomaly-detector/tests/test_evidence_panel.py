"""OPS-05 evidence-panel declaration contract for AnomalyDetector (Plan 06-14).

Asserts that ``ops_anomaly_detector.metadata`` exposes the four OPS-05
declaration fields — ``tool_inventory``, ``data_sources``, ``hitl_tier``,
``kpis_impacted`` — and that ``build_ops05_evidence_panel()`` returns a dict
with all five required keys (the four above + ``agent_id``).

This is the lockstep test the planner authored alongside the bilingual
MkDocs pages (T-V6-doc-drift mitigation): the same constants are documented
in ``docs/docs/agents/operations/anomaly-detector.md`` and asserted here.

The agent itself (``AnomalyDetector.__call__``) is NOT instantiated by this
test — wiring the agent requires a TimescaleDB + asyncpg pool which is out
of scope for a unit test. The declaration constants live module-level so
external consumers (HTTP gateway, docs build, audit consumers) can read
them without touching the agent's runtime collaborators.
"""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from ops_anomaly_detector import AGENT_ID, metadata


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
# Module-level constants
# ----------------------------------------------------------------------


def test_tool_inventory_constant_lists_query_timescale() -> None:
    """AnomalyDetector uses exactly one tool: query_timescale (Plan 06-06)."""
    assert _is_non_empty_str_iterable(metadata.TOOL_INVENTORY)
    assert "query_timescale" in metadata.TOOL_INVENTORY


def test_data_sources_constant_includes_timescale_and_baselines_yaml() -> None:
    """Declared data sources match the agent.py imports + YAML loader."""
    assert _is_non_empty_str_iterable(metadata.DATA_SOURCES)
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "timescale" in joined or "sensor_events" in joined
    assert "anomaly_baselines" in joined or "yaml" in joined


def test_kpis_impacted_constant_includes_mtbf_and_alert_fatigue() -> None:
    """KPI list mirrors the bilingual MkDocs page (single source of truth)."""
    assert _is_non_empty_str_iterable(metadata.KPIS_IMPACTED)
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "mtbf" in joined
    assert "alert_fatigue" in joined or "alert-fatigue" in joined


def test_hitl_tier_default_constant_is_none_string() -> None:
    """AnomalyDetector is fully autonomous → default tier == 'none'."""
    assert isinstance(metadata.HITL_TIER_DEFAULT, str)
    assert metadata.HITL_TIER_DEFAULT.lower() == "none"


# ----------------------------------------------------------------------
# build_ops05_evidence_panel() helper
# ----------------------------------------------------------------------


def test_build_ops05_evidence_panel_returns_dict_with_all_required_keys() -> None:
    """Helper assembles a dict containing the 5 OPS-05 declaration fields."""
    panel = metadata.build_ops05_evidence_panel()
    assert isinstance(panel, dict)
    for key in _OPS05_REQUIRED_KEYS:
        assert key in panel, f"missing OPS-05 key: {key!r}"


def test_build_ops05_evidence_panel_agent_id_matches_agent_module() -> None:
    """The panel's agent_id must equal the AGENT_ID constant from agent.py."""
    panel = metadata.build_ops05_evidence_panel()
    assert panel["agent_id"] == AGENT_ID == "anomaly-detector"


def test_build_ops05_evidence_panel_accepts_hitl_tier_override() -> None:
    """A caller can pass the actually-invoked tier (e.g. 'suppressed' for rate-cap)."""
    panel = metadata.build_ops05_evidence_panel(hitl_tier="suppressed")
    assert panel["hitl_tier"] == "suppressed"


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
    import ops_anomaly_detector as pkg

    assert hasattr(pkg, "metadata") or hasattr(pkg, "build_ops05_evidence_panel")
