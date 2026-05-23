"""Tests for ``build_ops_subgraph`` — OPS cluster intra-subgraph router (Plan 06-05).

Covers RESEARCH §Pattern 9 + D-X OPS routing:
    - Routes by ``state["target_agent"]`` to the matching child callable.
    - Falls back to ``operator-assistant`` on missing / unknown target with a
      structlog warning event (``ops_route_unknown_target``).
    - Preserves child-returned state deltas.
    - Build-time guard: requires ``operator-assistant`` in child_callables
      (otherwise the fallback would silently fail).
    - Existing ``build_cluster_subgraph`` (linear placeholder) is untouched.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
import structlog
from langgraph.graph import StateGraph

from sft_agents.runtime import build_ops_subgraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_OPS_AGENTS = (
    "operator-assistant",
    "production-planner",
    "quality-inspector",
    "anomaly-detector",
)


def _make_mock_children() -> dict[str, AsyncMock]:
    """Return four AsyncMock children that each echo a per-agent marker.

    The marker is written to the ``thread_id`` field (declared on
    :class:`AgentState`) so LangGraph's TypedDict-keyed reducer keeps the
    value in the final state — useful for routing assertions.
    """
    children: dict[str, AsyncMock] = {}
    for slug in _OPS_AGENTS:
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


async def test_build_ops_subgraph_routes_to_target_agent() -> None:
    """state['target_agent']='quality-inspector' → only QI child is called."""
    children = _make_mock_children()
    g = build_ops_subgraph(children)

    out = await _invoke(g, {"target_agent": "quality-inspector"})

    assert children["quality-inspector"].await_count == 1
    for slug in _OPS_AGENTS:
        if slug != "quality-inspector":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:quality-inspector"


async def test_build_ops_subgraph_fallback_to_operator_assistant_when_target_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """target_agent absent → operator-assistant fallback + structlog warning."""
    # Configure structlog to use the stdlib logging pipeline so caplog catches it.
    structlog.configure(
        processors=[structlog.stdlib.add_log_level, structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    children = _make_mock_children()
    g = build_ops_subgraph(children)

    with caplog.at_level("WARNING"):
        out = await _invoke(g, {})  # no target_agent

    assert children["operator-assistant"].await_count == 1
    for slug in _OPS_AGENTS:
        if slug != "operator-assistant":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:operator-assistant"
    # Warning surfaces the fallback for observability.
    joined = " ".join(rec.message for rec in caplog.records)
    assert "ops_route_unknown_target" in joined
    assert "operator-assistant" in joined


async def test_build_ops_subgraph_fallback_when_target_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown target_agent → operator-assistant fallback + warning."""
    structlog.configure(
        processors=[structlog.stdlib.add_log_level, structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    children = _make_mock_children()
    g = build_ops_subgraph(children)

    with caplog.at_level("WARNING"):
        out = await _invoke(g, {"target_agent": "rogue-agent-9000"})

    assert children["operator-assistant"].await_count == 1
    assert out["thread_id"] == "executed-by:operator-assistant"
    joined = " ".join(rec.message for rec in caplog.records)
    assert "ops_route_unknown_target" in joined
    assert "rogue-agent-9000" in joined


async def test_build_ops_subgraph_preserves_state_delta() -> None:
    """Child-returned dict keys (declared on AgentState) land on the final state."""
    children = _make_mock_children()
    # Use ``cluster`` — a declared AgentState field — so the LangGraph
    # TypedDict reducer keeps the value visible in the final state.
    children["anomaly-detector"] = AsyncMock(
        return_value={"cluster": "ops", "thread_id": "executed-by:anomaly-detector"}
    )
    children["anomaly-detector"].__name__ = "anomaly_detector"
    g = build_ops_subgraph(children)

    out = await _invoke(g, {"target_agent": "anomaly-detector"})

    assert out["cluster"] == "ops"
    assert out["thread_id"] == "executed-by:anomaly-detector"


# ---------------------------------------------------------------------------
# Build-time guards
# ---------------------------------------------------------------------------


def test_build_ops_subgraph_requires_operator_assistant() -> None:
    """Missing operator-assistant is a hard build-time error (no silent fallback)."""
    bad = {
        "production-planner": AsyncMock(return_value={}),
        "quality-inspector": AsyncMock(return_value={}),
    }
    with pytest.raises(ValueError, match="operator-assistant"):
        build_ops_subgraph(bad)


def test_build_ops_subgraph_rejects_empty_mapping() -> None:
    """Empty mapping is rejected."""
    with pytest.raises(ValueError):
        build_ops_subgraph({})


# ---------------------------------------------------------------------------
# Regression — existing build_cluster_subgraph keeps working
# ---------------------------------------------------------------------------


def test_existing_build_cluster_subgraph_still_works() -> None:
    """build_cluster_subgraph (linear placeholder) is untouched by Plan 06-05."""
    from sft_agents.runtime import build_cluster_subgraph

    sg = build_cluster_subgraph("maintenance", ["predictive-maintenance", "rca-specialist"])
    assert isinstance(sg, StateGraph)
    compiled = sg.compile()
    assert compiled is not None
