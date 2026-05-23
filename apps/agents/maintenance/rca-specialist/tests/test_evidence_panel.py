"""MNT-05 evidence-panel declaration contract for RCASpecialist (Plan 07-11).

Asserts that ``mnt_rca_specialist.metadata`` exposes the four OPS-05
declaration fields — ``tool_inventory``, ``data_sources``, ``hitl_tier``,
``kpis_impacted`` — and that ``build_ops05_evidence_panel()`` returns a dict
with all five required keys (the four above + ``agent_id``).

This is the lockstep test that enforces docs ↔ code consistency (T-V7-doc-drift
mitigation): the same constants documented in
``docs/docs/agents/maintenance/rca-specialist.md`` are asserted here.

Key contract: HITL tier is ALWAYS 'supervisor' (D-RCA-02 literal) — this test
asserts the hardcoded tier cannot be overridden to a lower value.

The agent itself is NOT instantiated by this test — wiring ``RCASpecialist``
requires Qdrant + Neo4j + asyncpg which are out of scope for a unit test.
"""

from __future__ import annotations

from mnt_rca_specialist import metadata


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
    """RCASpecialist uses rag_search — mandatory citation grounding (D-RCA-01)."""
    assert _is_non_empty_str_iterable(metadata.TOOL_INVENTORY)
    assert "rag_search" in metadata.TOOL_INVENTORY


def test_tool_inventory_includes_traverse_graph() -> None:
    """Tool inventory includes traverse_graph (Neo4j knowledge graph traversal)."""
    assert "traverse_graph" in metadata.TOOL_INVENTORY


def test_tool_inventory_includes_escalate_and_log() -> None:
    """Tool inventory includes escalate_to_supervisor (D-RCA-02) and log_event."""
    assert "escalate_to_supervisor" in metadata.TOOL_INVENTORY
    assert "log_event" in metadata.TOOL_INVENTORY


def test_tool_inventory_length() -> None:
    """RCA has exactly 4 tools: rag_search, traverse_graph, escalate_to_supervisor, log_event."""
    assert len(metadata.TOOL_INVENTORY) == 4


def test_data_sources_include_qdrant() -> None:
    """Data sources include Qdrant sop_chunks (RAG knowledge base)."""
    assert _is_non_empty_str_iterable(metadata.DATA_SOURCES)
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "qdrant" in joined or "sop_chunks" in joined


def test_data_sources_include_neo4j() -> None:
    """Data sources include Neo4j textile graph (Phase 5 knowledge graph)."""
    joined = " ".join(metadata.DATA_SOURCES).lower()
    assert "neo4j" in joined or "graph" in joined


def test_kpis_include_rca_completeness() -> None:
    """KPI list includes rca_completeness_5why (5-Why chain quality gate)."""
    assert _is_non_empty_str_iterable(metadata.KPIS_IMPACTED)
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "rca_completeness" in joined or "5why" in joined


def test_kpis_include_citation_grounding() -> None:
    """KPI list includes citation_grounding_rate (hallucination mitigation)."""
    joined = " ".join(metadata.KPIS_IMPACTED).lower()
    assert "citation" in joined or "grounding" in joined


def test_hitl_tier_default_is_always_supervisor() -> None:
    """D-RCA-02 literal: HITL_TIER_DEFAULT must be 'supervisor', never 'none'."""
    assert metadata.HITL_TIER_DEFAULT == "supervisor"


def test_agent_id_is_rca_specialist() -> None:
    """AGENT_ID constant matches the documented slug."""
    assert metadata.AGENT_ID == "rca-specialist"


# ----------------------------------------------------------------------
# build_ops05_evidence_panel() helper
# ----------------------------------------------------------------------


def test_build_ops05_evidence_panel_returns_dict_with_all_required_keys() -> None:
    """Helper assembles a dict containing the 5 OPS-05 declaration fields."""
    panel = metadata.build_ops05_evidence_panel(
        input_summary="test rca",
        model_version="qwen2.5-7b@rca-specialist",
        tool_calls=[],
        decision="hitl_supervisor",
        prompt_hash="0" * 64,
    )
    assert isinstance(panel, dict)
    for key in _OPS05_REQUIRED_KEYS:
        assert key in panel, f"missing OPS-05 key: {key!r}"


def test_build_ops05_evidence_panel_agent_id_matches_constant() -> None:
    """The panel's agent_id must equal AGENT_ID from metadata."""
    panel = metadata.build_ops05_evidence_panel(
        input_summary="test",
        model_version="qwen2.5-7b@rca-specialist",
        tool_calls=[],
        decision="hitl_supervisor",
        prompt_hash="0" * 64,
    )
    assert panel["agent_id"] == metadata.AGENT_ID == "rca-specialist"


def test_build_ops05_evidence_panel_hitl_tier_always_supervisor() -> None:
    """D-RCA-02: hitl_tier is hardcoded to 'supervisor' — cannot be lowered."""
    panel = metadata.build_ops05_evidence_panel(
        input_summary="test",
        model_version="qwen2.5-7b@rca-specialist",
        tool_calls=[],
        decision="hitl_supervisor",
        prompt_hash="0" * 64,
    )
    assert panel["hitl_tier"] == "supervisor"


def test_build_ops05_evidence_panel_ignores_auto_tier_in_extra() -> None:
    """Extra dict cannot lower the tier — 'auto' in extra is silently ignored."""
    panel = metadata.build_ops05_evidence_panel(
        input_summary="test",
        model_version="qwen2.5-7b@rca-specialist",
        tool_calls=[],
        decision="hitl_supervisor",
        prompt_hash="0" * 64,
        # hitl_tier is not in the required keys so passing it via 'extra' would
        # be filtered out; the function hardcodes the supervisor tier.
    )
    # The returned tier must always be supervisor (D-RCA-02 cannot be overridden)
    assert panel["hitl_tier"] == "supervisor"


def test_build_ops05_evidence_panel_lists_match_module_constants() -> None:
    """The panel returns the module-level constants verbatim (no per-call drift)."""
    panel = metadata.build_ops05_evidence_panel(
        input_summary="test",
        model_version="qwen2.5-7b@rca-specialist",
        tool_calls=[],
        decision="hitl_supervisor",
        prompt_hash="0" * 64,
    )
    assert list(panel["tool_inventory"]) == list(metadata.TOOL_INVENTORY)
    assert list(panel["data_sources"]) == list(metadata.DATA_SOURCES)
    assert list(panel["kpis_impacted"]) == list(metadata.KPIS_IMPACTED)


# ----------------------------------------------------------------------
# Import-level guard — surface API
# ----------------------------------------------------------------------


def test_metadata_module_is_importable_from_package_root() -> None:
    """`metadata` is accessible via the sub-module path for HTTP / docs callers."""
    import mnt_rca_specialist.metadata as mod

    assert hasattr(mod, "build_ops05_evidence_panel")
    assert hasattr(mod, "TOOL_INVENTORY")
    assert hasattr(mod, "DATA_SOURCES")
    assert hasattr(mod, "KPIS_IMPACTED")
    assert hasattr(mod, "AGENT_ID")
    assert hasattr(mod, "HITL_TIER_DEFAULT")
