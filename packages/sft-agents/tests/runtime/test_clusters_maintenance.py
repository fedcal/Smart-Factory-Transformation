"""Tests for ``build_maintenance_subgraph`` — Maintenance cluster intra-subgraph
router (Plan 07-04, D-X OPS routing pattern mirror).

Covers RESEARCH §Pattern 9 + 07-PATTERNS Section 1:
    - Routes by ``state["target_agent"]`` to the matching child callable.
    - Falls back to ``rca-specialist`` (planner decision: always-HITL fallback,
      D-RCA-02) on missing / unknown target with a structlog warning event
      (``mnt_route_unknown_target``).
    - Preserves child-returned state deltas.
    - Build-time guards: empty mapping rejected; missing fallback rejected.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
import structlog
from langgraph.graph import StateGraph

from sft_agents.runtime import build_maintenance_subgraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_MNT_AGENTS = (
    "predictive-maintenance",
    "rca-specialist",
    "maintenance-coach",
    "downtime-analyzer",
)


def _make_mock_children() -> dict[str, AsyncMock]:
    """Return four AsyncMock children that each echo a per-agent marker.

    The marker is written to the ``thread_id`` field (declared on
    :class:`AgentState`) so LangGraph's TypedDict-keyed reducer keeps the
    value visible in the final state.
    """
    children: dict[str, AsyncMock] = {}
    for slug in _MNT_AGENTS:
        m = AsyncMock(return_value={"thread_id": f"executed-by:{slug}"})
        m.__name__ = slug.replace("-", "_")
        children[slug] = m
    return children


async def _invoke(g: StateGraph, state: dict[str, Any]) -> dict[str, Any]:
    """Compile + ainvoke helper."""
    compiled = g.compile()
    return await compiled.ainvoke(state)


# ---------------------------------------------------------------------------
# Routing behaviour
# ---------------------------------------------------------------------------


async def test_build_maintenance_subgraph_routes_to_target_agent() -> None:
    """state['target_agent']='predictive-maintenance' → only PM child is called."""
    children = _make_mock_children()
    g = build_maintenance_subgraph(children)

    out = await _invoke(g, {"target_agent": "predictive-maintenance"})

    assert children["predictive-maintenance"].await_count == 1
    for slug in _MNT_AGENTS:
        if slug != "predictive-maintenance":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:predictive-maintenance"


async def test_build_maintenance_subgraph_routes_to_rca_specialist() -> None:
    """state['target_agent']='rca-specialist' → only RCA child is called."""
    children = _make_mock_children()
    g = build_maintenance_subgraph(children)

    out = await _invoke(g, {"target_agent": "rca-specialist"})

    assert children["rca-specialist"].await_count == 1
    for slug in _MNT_AGENTS:
        if slug != "rca-specialist":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:rca-specialist"


async def test_build_maintenance_subgraph_fallback_when_target_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """target_agent absent → rca-specialist fallback + structlog warning."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    children = _make_mock_children()
    g = build_maintenance_subgraph(children)

    with caplog.at_level("WARNING"):
        out = await _invoke(g, {})  # no target_agent

    assert children["rca-specialist"].await_count == 1
    for slug in _MNT_AGENTS:
        if slug != "rca-specialist":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:rca-specialist"
    joined = " ".join(rec.message for rec in caplog.records)
    assert "mnt_route_unknown_target" in joined
    assert "rca-specialist" in joined


async def test_build_maintenance_subgraph_fallback_when_target_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown target_agent → rca-specialist fallback + warning."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    children = _make_mock_children()
    g = build_maintenance_subgraph(children)

    with caplog.at_level("WARNING"):
        out = await _invoke(g, {"target_agent": "rogue-mnt-agent-9000"})

    assert children["rca-specialist"].await_count == 1
    assert out["thread_id"] == "executed-by:rca-specialist"
    joined = " ".join(rec.message for rec in caplog.records)
    assert "mnt_route_unknown_target" in joined
    assert "rogue-mnt-agent-9000" in joined
    assert "rca-specialist" in joined


async def test_build_maintenance_subgraph_preserves_state_delta() -> None:
    """Child-returned dict keys (declared on AgentState) land on the final state."""
    children = _make_mock_children()
    # Use ``cluster`` — a declared AgentState field — so the LangGraph
    # TypedDict reducer keeps the value visible in the final state.
    children["downtime-analyzer"] = AsyncMock(
        return_value={"cluster": "maintenance", "thread_id": "executed-by:downtime-analyzer"}
    )
    children["downtime-analyzer"].__name__ = "downtime_analyzer"
    g = build_maintenance_subgraph(children)

    out = await _invoke(g, {"target_agent": "downtime-analyzer"})

    assert out["cluster"] == "maintenance"
    assert out["thread_id"] == "executed-by:downtime-analyzer"


# ---------------------------------------------------------------------------
# Build-time guards
# ---------------------------------------------------------------------------


def test_build_maintenance_subgraph_rejects_empty_mapping() -> None:
    """Empty mapping is rejected with a maintenance-specific message."""
    with pytest.raises(ValueError, match="maintenance"):
        build_maintenance_subgraph({})


def test_build_maintenance_subgraph_requires_rca_specialist_fallback() -> None:
    """Missing rca-specialist (the fallback) is a hard build-time error."""
    bad = {
        "predictive-maintenance": AsyncMock(return_value={}),
        "maintenance-coach": AsyncMock(return_value={}),
        "downtime-analyzer": AsyncMock(return_value={}),
    }
    with pytest.raises(ValueError, match="rca-specialist"):
        build_maintenance_subgraph(bad)


def test_build_maintenance_subgraph_minimal_only_rca_specialist() -> None:
    """A minimal valid build needs only the fallback agent."""
    fn = AsyncMock(return_value={"thread_id": "executed-by:rca-specialist"})
    fn.__name__ = "rca_specialist"
    g = build_maintenance_subgraph({"rca-specialist": fn})
    assert isinstance(g, StateGraph)
    compiled = g.compile()
    assert compiled is not None
