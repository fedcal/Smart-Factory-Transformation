"""Tests for sft_agents.runtime.supervisor (Plan 04-05 Task 2, CORE-02).

Verifies:
    - build_supervisor_graph(...) returns a compiled StateGraph attached to the supplied checkpointer
    - Rule-routed input lands in the expected cluster node (`Allarme su macchina T-12` → ops)
    - Conditional routing dispatches by state['routing_decision'].cluster
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage


async def test_build_supervisor_graph_returns_compiled_graph() -> None:
    from langgraph.checkpoint.memory import MemorySaver

    from sft_agents.runtime import build_supervisor_graph

    g = build_supervisor_graph(checkpointer=MemorySaver())
    assert g is not None
    # CompiledStateGraph exposes ainvoke.
    assert hasattr(g, "ainvoke")


async def test_supervisor_routes_ops_input_to_ops_cluster() -> None:
    """Rule-based path: 'Allarme' + 'macchina T-12' both hit ops → routed to ops."""
    from langgraph.checkpoint.memory import MemorySaver

    from sft_agents.runtime import build_supervisor_graph, format_thread_id

    g = build_supervisor_graph(checkpointer=MemorySaver())
    thread_id = format_thread_id("ops", "operator-assistant", uuid4())
    config = {
        "configurable": {"thread_id": thread_id, "checkpoint_ns": ""},
        "recursion_limit": 25,
    }
    out = await g.ainvoke(
        {"messages": [HumanMessage("Allarme su macchina T-12 turno notte")]},
        config=config,
    )
    assert out["cluster"] == "ops"
    assert out["routing_decision"].cluster == "ops"
    assert out["routing_decision"].strategy == "rules"


async def test_supervisor_routes_supply_input_to_supply_cluster() -> None:
    from langgraph.checkpoint.memory import MemorySaver

    from sft_agents.runtime import build_supervisor_graph, format_thread_id

    g = build_supervisor_graph(checkpointer=MemorySaver())
    thread_id = format_thread_id("supply", "inventory-manager", uuid4())
    config = {
        "configurable": {"thread_id": thread_id, "checkpoint_ns": ""},
        "recursion_limit": 25,
    }
    out = await g.ainvoke(
        {"messages": [HumanMessage("Verifica inventario ordine demand previsione")]},
        config=config,
    )
    assert out["cluster"] == "supply"
