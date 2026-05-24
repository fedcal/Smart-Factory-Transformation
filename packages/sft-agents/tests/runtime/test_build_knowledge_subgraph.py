"""Tests for ``build_knowledge_subgraph`` — Knowledge cluster intra-subgraph
router (Plan 08-01, D-X-04 gateway pattern mirror of build_maintenance_subgraph).

Covers 08-PATTERNS.md section "clusters.py" (lines 174-247):
    - Routes by ``state["target_agent"]`` to the matching child callable.
    - Falls back to ``knowledge-curator`` (autonomous, D-KC-04) on missing /
      unknown target with a structlog warning event (``knw_route_unknown_target``).
    - Preserves child-returned state deltas.
    - Build-time guards: empty mapping rejected; missing fallback rejected.

Security note (T-08-03): Unknown target routes to the autonomous curator —
no HITL, no irreversible side effects — which is the safest possible fallback
for an unknown-target elevation-of-privilege scenario.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest
import structlog
from langgraph.graph import StateGraph

from sft_agents.runtime.clusters import build_knowledge_subgraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_KNW_AGENTS = (
    "shift-handover",
    "training-coach",
    "knowledge-curator",
    "documentation-synthesizer",
)


def _make_mock_children() -> dict[str, AsyncMock]:
    """Return four AsyncMock children that each echo a per-agent marker.

    The marker is written to the ``thread_id`` field (declared on
    :class:`AgentState`) so LangGraph's TypedDict-keyed reducer keeps the
    value visible in the final state.
    """
    children: dict[str, AsyncMock] = {}
    for slug in _KNW_AGENTS:
        m = AsyncMock(return_value={"thread_id": f"executed-by:{slug}"})
        m.__name__ = slug.replace("-", "_")
        children[slug] = m
    return children


async def _invoke(g: StateGraph, state: dict[str, Any]) -> dict[str, Any]:
    """Compile + ainvoke helper."""
    compiled = g.compile()
    return await compiled.ainvoke(state)


# ---------------------------------------------------------------------------
# Routing behaviour — each of the 4 slugs routes to the matching child
# ---------------------------------------------------------------------------


async def test_build_knowledge_subgraph_routes_to_shift_handover() -> None:
    """state['target_agent']='shift-handover' → only ShiftHandover child is called."""
    children = _make_mock_children()
    g = build_knowledge_subgraph(children)

    out = await _invoke(g, {"target_agent": "shift-handover"})

    assert children["shift-handover"].await_count == 1
    for slug in _KNW_AGENTS:
        if slug != "shift-handover":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:shift-handover"


async def test_build_knowledge_subgraph_routes_to_training_coach() -> None:
    """state['target_agent']='training-coach' → only TrainingCoach child is called."""
    children = _make_mock_children()
    g = build_knowledge_subgraph(children)

    out = await _invoke(g, {"target_agent": "training-coach"})

    assert children["training-coach"].await_count == 1
    for slug in _KNW_AGENTS:
        if slug != "training-coach":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:training-coach"


async def test_build_knowledge_subgraph_routes_to_knowledge_curator() -> None:
    """state['target_agent']='knowledge-curator' → only KnowledgeCurator child is called."""
    children = _make_mock_children()
    g = build_knowledge_subgraph(children)

    out = await _invoke(g, {"target_agent": "knowledge-curator"})

    assert children["knowledge-curator"].await_count == 1
    for slug in _KNW_AGENTS:
        if slug != "knowledge-curator":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:knowledge-curator"


async def test_build_knowledge_subgraph_routes_to_documentation_synthesizer() -> None:
    """state['target_agent']='documentation-synthesizer' → only DocSynthesizer child is called."""
    children = _make_mock_children()
    g = build_knowledge_subgraph(children)

    out = await _invoke(g, {"target_agent": "documentation-synthesizer"})

    assert children["documentation-synthesizer"].await_count == 1
    for slug in _KNW_AGENTS:
        if slug != "documentation-synthesizer":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:documentation-synthesizer"


# ---------------------------------------------------------------------------
# Fallback behaviour — unknown/missing target → knowledge-curator (D-KC-04)
# ---------------------------------------------------------------------------


async def test_build_knowledge_subgraph_fallback_when_target_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """target_agent absent → knowledge-curator fallback + structlog warning.

    T-08-03 mitigation: unknown target routes to the autonomous curator
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
    g = build_knowledge_subgraph(children)

    with caplog.at_level("WARNING"):
        out = await _invoke(g, {})  # no target_agent

    assert children["knowledge-curator"].await_count == 1
    for slug in _KNW_AGENTS:
        if slug != "knowledge-curator":
            assert children[slug].await_count == 0
    assert out["thread_id"] == "executed-by:knowledge-curator"
    joined = " ".join(rec.message for rec in caplog.records)
    assert "knw_route_unknown_target" in joined
    assert "knowledge-curator" in joined


async def test_build_knowledge_subgraph_fallback_when_target_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown target_agent → knowledge-curator fallback + warning.

    T-08-03 mitigation: unknown target routes to the autonomous curator.
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
    g = build_knowledge_subgraph(children)

    with caplog.at_level("WARNING"):
        out = await _invoke(g, {"target_agent": "rogue-knw-agent-9000"})

    assert children["knowledge-curator"].await_count == 1
    assert out["thread_id"] == "executed-by:knowledge-curator"
    joined = " ".join(rec.message for rec in caplog.records)
    assert "knw_route_unknown_target" in joined
    assert "rogue-knw-agent-9000" in joined
    assert "knowledge-curator" in joined


# ---------------------------------------------------------------------------
# State delta preservation
# ---------------------------------------------------------------------------


async def test_build_knowledge_subgraph_preserves_state_delta() -> None:
    """Child-returned dict keys (declared on AgentState) land on the final state."""
    children = _make_mock_children()
    # Use ``cluster`` — a declared AgentState field — so the LangGraph
    # TypedDict reducer keeps the value visible in the final state.
    children["knowledge-curator"] = AsyncMock(
        return_value={"cluster": "knowledge", "thread_id": "executed-by:knowledge-curator"}
    )
    children["knowledge-curator"].__name__ = "knowledge_curator"
    g = build_knowledge_subgraph(children)

    out = await _invoke(g, {"target_agent": "knowledge-curator"})

    assert out["cluster"] == "knowledge"
    assert out["thread_id"] == "executed-by:knowledge-curator"


# ---------------------------------------------------------------------------
# Build-time guards
# ---------------------------------------------------------------------------


def test_build_knowledge_subgraph_rejects_empty_mapping() -> None:
    """Empty mapping is rejected with a knowledge-specific message."""
    with pytest.raises(ValueError, match="knowledge"):
        build_knowledge_subgraph({})


def test_build_knowledge_subgraph_requires_knowledge_curator_fallback() -> None:
    """Missing knowledge-curator (the fallback) is a hard build-time error."""
    bad = {
        "shift-handover": AsyncMock(return_value={}),
        "training-coach": AsyncMock(return_value={}),
        "documentation-synthesizer": AsyncMock(return_value={}),
    }
    with pytest.raises(ValueError, match="knowledge-curator"):
        build_knowledge_subgraph(bad)


def test_build_knowledge_subgraph_minimal_only_knowledge_curator() -> None:
    """A minimal valid build needs only the fallback agent."""
    fn = AsyncMock(return_value={"thread_id": "executed-by:knowledge-curator"})
    fn.__name__ = "knowledge_curator"
    g = build_knowledge_subgraph({"knowledge-curator": fn})
    assert isinstance(g, StateGraph)
    compiled = g.compile()
    assert compiled is not None
