"""Tests for ``build_supply_subgraph`` — Supply/SCM cluster intra-subgraph
router (Plan 09-01, D-X-04 gateway pattern mirror of build_knowledge_subgraph).

Covers 09-RESEARCH.md Pattern 1 (clusters.py):
    - Routes by ``state["target_agent"]`` to the matching child callable.
    - Falls back to ``cost-analyzer`` (autonomous, read-only, D-SCM-AUTO) on
      missing / unknown target with a structlog warning event
      (``scm_route_unknown_target``).
    - Preserves child-returned state deltas.
    - Build-time guards: empty mapping rejected; missing fallback rejected.

Security note (T-09-06): Unknown target routes to the autonomous cost-analyzer —
no HITL, no irreversible side effects — which is the safest possible fallback
for an unknown-target elevation-of-privilege scenario.

Security note (T-09-07): Absence of cost-analyzer at build time raises ValueError
immediately (fail-fast), not at request time (DoS prevention).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
import structlog
from langgraph.graph import StateGraph

from sft_agents.runtime.clusters import _SCM_DEFAULT_AGENT, build_supply_subgraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_SCM_AGENTS = (
    "inventory-manager",
    "energy-optimizer",
    "cost-analyzer",
    "demand-forecaster",
)


def _make_mock_children() -> dict[str, AsyncMock]:
    """Return four AsyncMock children that each echo a per-agent marker.

    The marker is written to the ``thread_id`` field (declared on
    :class:`AgentState`) so LangGraph's TypedDict-keyed reducer keeps the
    value visible in the final state.
    """
    children: dict[str, AsyncMock] = {}
    for slug in _SCM_AGENTS:
        m = AsyncMock(return_value={"thread_id": f"executed-by:{slug}"})
        m.__name__ = slug.replace("-", "_")
        children[slug] = m
    return children


async def _invoke(g: StateGraph, state: dict[str, Any]) -> dict[str, Any]:
    """Compile + ainvoke helper."""
    compiled = g.compile()
    return await compiled.ainvoke(state)


# ---------------------------------------------------------------------------
# Constant
# ---------------------------------------------------------------------------


def test_scm_default_agent_constant() -> None:
    """_SCM_DEFAULT_AGENT must equal 'cost-analyzer'."""
    assert _SCM_DEFAULT_AGENT == "cost-analyzer"


# ---------------------------------------------------------------------------
# Routing behaviour — each of the 4 slugs routes to the matching child
# ---------------------------------------------------------------------------


async def test_build_supply_subgraph_routes_to_inventory_manager() -> None:
    """state['target_agent']='inventory-manager' → only InventoryManager child is called."""
    children = _make_mock_children()
    g = build_supply_subgraph(children)

    out = await _invoke(g, {"target_agent": "inventory-manager"})

    assert children["inventory-manager"].await_count == 1
    for slug in _SCM_AGENTS:
        if slug != "inventory-manager":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:inventory-manager"


async def test_build_supply_subgraph_routes_to_energy_optimizer() -> None:
    """state['target_agent']='energy-optimizer' → only EnergyOptimizer child is called."""
    children = _make_mock_children()
    g = build_supply_subgraph(children)

    out = await _invoke(g, {"target_agent": "energy-optimizer"})

    assert children["energy-optimizer"].await_count == 1
    for slug in _SCM_AGENTS:
        if slug != "energy-optimizer":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:energy-optimizer"


async def test_build_supply_subgraph_routes_to_cost_analyzer() -> None:
    """state['target_agent']='cost-analyzer' → only CostAnalyzer child is called."""
    children = _make_mock_children()
    g = build_supply_subgraph(children)

    out = await _invoke(g, {"target_agent": "cost-analyzer"})

    assert children["cost-analyzer"].await_count == 1
    for slug in _SCM_AGENTS:
        if slug != "cost-analyzer":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:cost-analyzer"


async def test_build_supply_subgraph_routes_to_demand_forecaster() -> None:
    """state['target_agent']='demand-forecaster' → only DemandForecaster child is called."""
    children = _make_mock_children()
    g = build_supply_subgraph(children)

    out = await _invoke(g, {"target_agent": "demand-forecaster"})

    assert children["demand-forecaster"].await_count == 1
    for slug in _SCM_AGENTS:
        if slug != "demand-forecaster":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:demand-forecaster"


# ---------------------------------------------------------------------------
# Fallback behaviour — unknown/missing target → cost-analyzer (D-SCM-AUTO)
# ---------------------------------------------------------------------------


async def test_build_supply_subgraph_fallback_when_target_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """target_agent absent → cost-analyzer fallback + structlog warning.

    T-09-06 mitigation: unknown target routes to the autonomous cost-analyzer
    (no irreversible action), not to a HITL/state-changing agent.
    """
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
    g = build_supply_subgraph(children)

    with caplog.at_level("WARNING"):
        out = await _invoke(g, {})  # no target_agent

    assert children["cost-analyzer"].await_count == 1
    for slug in _SCM_AGENTS:
        if slug != "cost-analyzer":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:cost-analyzer"
    joined = " ".join(rec.message for rec in caplog.records)
    assert "scm_route_unknown_target" in joined
    assert "cost-analyzer" in joined


async def test_build_supply_subgraph_fallback_when_target_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown target_agent → cost-analyzer fallback + warning.

    T-09-06 mitigation: unknown target routes to the autonomous cost-analyzer.
    """
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
    g = build_supply_subgraph(children)

    with caplog.at_level("WARNING"):
        out = await _invoke(g, {"target_agent": "rogue-scm-agent-9000"})

    assert children["cost-analyzer"].await_count == 1
    assert out["thread_id"] == "executed-by:cost-analyzer"
    joined = " ".join(rec.message for rec in caplog.records)
    assert "scm_route_unknown_target" in joined
    assert "rogue-scm-agent-9000" in joined
    assert "cost-analyzer" in joined


# ---------------------------------------------------------------------------
# State delta preservation
# ---------------------------------------------------------------------------


async def test_build_supply_subgraph_preserves_state_delta() -> None:
    """Child-returned dict keys (declared on AgentState) land on the final state."""
    children = _make_mock_children()
    # Use ``cluster`` — a declared AgentState field — so the LangGraph
    # TypedDict reducer keeps the value visible in the final state.
    children["cost-analyzer"] = AsyncMock(
        return_value={"cluster": "supply", "thread_id": "executed-by:cost-analyzer"}
    )
    children["cost-analyzer"].__name__ = "cost_analyzer"
    g = build_supply_subgraph(children)

    out = await _invoke(g, {"target_agent": "cost-analyzer"})

    assert out["cluster"] == "supply"
    assert out["thread_id"] == "executed-by:cost-analyzer"


# ---------------------------------------------------------------------------
# Build-time guards (T-09-07: fail-fast, not at request time)
# ---------------------------------------------------------------------------


def test_build_supply_subgraph_rejects_empty_mapping() -> None:
    """Empty mapping is rejected with a supply-specific message."""
    with pytest.raises(ValueError, match="supply"):
        build_supply_subgraph({})


def test_build_supply_subgraph_requires_cost_analyzer_fallback() -> None:
    """Missing cost-analyzer (the fallback) is a hard build-time error.

    T-09-07: ValueError at graph build time if cost-analyzer absent
    (fail fast, not at request time — DoS mitigation).
    """
    bad = {
        "inventory-manager": AsyncMock(return_value={}),
        "energy-optimizer": AsyncMock(return_value={}),
        "demand-forecaster": AsyncMock(return_value={}),
    }
    with pytest.raises(ValueError, match="cost-analyzer"):
        build_supply_subgraph(bad)


def test_build_supply_subgraph_minimal_only_cost_analyzer() -> None:
    """A minimal valid build needs only the fallback agent."""
    fn = AsyncMock(return_value={"thread_id": "executed-by:cost-analyzer"})
    fn.__name__ = "cost_analyzer"
    g = build_supply_subgraph({"cost-analyzer": fn})
    assert isinstance(g, StateGraph)
    compiled = g.compile()
    assert compiled is not None
