"""Tests for safe_invoke recursion_limit-to-HITL escalation (Plan 04-05 Task 2, CORE-03).

Success criterion #2: exceeding recursion_limit does NOT crash — instead the
supervisor emits a ProposedAction with action_type=GRAPH_RECURSION_REVIEW that
escalates to the HITL Manager tier (Plan 04-06 picks it up).

Also verifies that recursion_limit is mandatory at invoke time (ValueError if
missing — defense against unbounded LLM token consumption per T-04-Budget-Exhaust).
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph


def _build_intentionally_recursive_graph(checkpointer):
    """A 1-node loop. Combined with recursion_limit=3 it overshoots immediately."""
    from sft_agents.runtime import AgentState

    async def _loop_node(state):  # type: ignore[no-untyped-def]
        return {"messages": [HumanMessage("loop")]}

    g = StateGraph(AgentState)
    g.add_node("loop", _loop_node)
    g.add_edge(START, "loop")
    g.add_edge("loop", "loop")  # infinite loop
    return g.compile(checkpointer=checkpointer)


async def test_safe_invoke_catches_recursion_error_and_emits_hitl_action() -> None:
    from sft_agents.models import ActionType, Tier
    from sft_agents.runtime import format_thread_id, safe_invoke

    graph = _build_intentionally_recursive_graph(MemorySaver())
    thread_id = format_thread_id("ops", "operator-assistant", uuid4())
    config = {
        "configurable": {"thread_id": thread_id, "checkpoint_ns": ""},
        "recursion_limit": 3,
    }

    out = await safe_invoke(
        graph,
        {"messages": [HumanMessage("start")], "proposed_actions": []},
        config=config,
    )

    pas = out.get("proposed_actions", [])
    assert len(pas) >= 1, f"safe_invoke must emit a HITL ProposedAction, got {pas!r}"
    action = pas[-1]
    assert action.action_type == ActionType.GRAPH_RECURSION_REVIEW
    # requires_tier semantically lives in args (ProposedAction has no field).
    assert action.args.get("requires_tier") == Tier.MANAGER.value
    assert action.args.get("thread_id") == thread_id
    assert action.args.get("recursion_limit") == 3


async def test_safe_invoke_requires_recursion_limit_in_config() -> None:
    from sft_agents.runtime import format_thread_id, safe_invoke

    graph = _build_intentionally_recursive_graph(MemorySaver())
    thread_id = format_thread_id("ops", "operator-assistant", uuid4())
    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}  # no recursion_limit

    with pytest.raises(ValueError, match="recursion_limit"):
        await safe_invoke(
            graph,
            {"messages": [HumanMessage("start")], "proposed_actions": []},
            config=config,
        )


async def test_safe_invoke_passes_through_on_normal_completion() -> None:
    """When the graph completes within recursion_limit, no HITL action is emitted."""
    from sft_agents.runtime import AgentState, format_thread_id, safe_invoke

    async def _terminator(state):  # type: ignore[no-untyped-def]
        return {"messages": [HumanMessage("done")]}

    g = StateGraph(AgentState)
    g.add_node("terminator", _terminator)
    g.add_edge(START, "terminator")
    g.add_edge("terminator", END)
    graph = g.compile(checkpointer=MemorySaver())

    thread_id = format_thread_id("ops", "operator-assistant", uuid4())
    out = await safe_invoke(
        graph,
        {"messages": [HumanMessage("start")], "proposed_actions": []},
        config={
            "configurable": {"thread_id": thread_id, "checkpoint_ns": ""},
            "recursion_limit": 5,
        },
    )
    # No GRAPH_RECURSION_REVIEW emitted because no overflow occurred.
    pas = out.get("proposed_actions", [])
    assert all(
        a.action_type.value != "GRAPH_RECURSION_REVIEW" for a in pas
    ), f"unexpected recursion review action emitted: {pas!r}"
