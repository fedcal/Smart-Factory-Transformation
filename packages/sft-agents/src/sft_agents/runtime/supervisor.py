"""Supervisor StateGraph + safe_invoke (Plan 04-05 Task 2, CORE-02 + CORE-03).

Topology:
    START → route → conditional_edges → {ops, maintenance, kc, kt, supply} → END

The ``route`` node calls HybridRouter.route(state) and returns
``{"routing_decision": ..., "cluster": ...}``. Conditional edges dispatch by
``state['routing_decision'].cluster`` into the matching compiled cluster
subgraph (which itself terminates at END within the supervisor — Phase 4 has
no inter-cluster routing per CONTEXT.md scope_boundaries).

``safe_invoke`` wraps ``graph.ainvoke`` with two guarantees:

  1. ``config['recursion_limit']`` MUST be set (ValueError if missing) — defense
     against unbounded LLM token consumption (T-04-Budget-Exhaust + success
     criterion #2).
  2. ``GraphRecursionError`` is caught and converted into a HITL Manager-tier
     ProposedAction (action_type=GRAPH_RECURSION_REVIEW). The function does NOT
     re-raise. Plan 04-06's HITL middleware will route the action.
"""
from __future__ import annotations

import importlib
from typing import Any

import structlog
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph

from sft_agents.clusters import ALL_CLUSTERS
from sft_agents.models import ActionType, ProposedAction, Tier
from sft_agents.policies.routing import HybridRouter
from sft_agents.runtime.clusters import build_cluster_subgraph
from sft_agents.runtime.state import AgentState

_log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Build the supervisor graph
# ---------------------------------------------------------------------------

# Cluster identifier (hyphenated) → Python sub-module name (underscored).
_CLUSTER_MODULES: dict[str, str] = {
    "ops": "sft_agents.clusters.ops",
    "maintenance": "sft_agents.clusters.maintenance",
    "knowledge-curation": "sft_agents.clusters.knowledge_curation",
    "knowledge-training": "sft_agents.clusters.knowledge_training",
    "supply": "sft_agents.clusters.supply",
}


def build_supervisor_graph(
    *,
    checkpointer: Any,
    router: HybridRouter | None = None,
) -> Any:
    """Compile the supervisor StateGraph with 5 cluster subgraph nodes (D-53)."""
    if checkpointer is None:
        raise ValueError("checkpointer is required (MemorySaver for unit tests, AsyncPostgresSaver for prod)")

    if router is None:
        router = HybridRouter()

    g: StateGraph = StateGraph(AgentState)

    # `route` node: invoke HybridRouter and emit routing_decision + cluster fields.
    async def _route_node(state: AgentState) -> dict:
        decision = await router.route(state)
        return {"routing_decision": decision, "cluster": decision.cluster}

    g.add_node("route", _route_node)

    # Build + compile + register one cluster subgraph per ALL_CLUSTERS entry.
    for cluster_name in ALL_CLUSTERS:
        module = importlib.import_module(_CLUSTER_MODULES[cluster_name])
        slugs: list[str] = module.CHILD_AGENT_SLUGS
        compiled_subgraph = build_cluster_subgraph(cluster_name, slugs).compile()
        g.add_node(cluster_name, compiled_subgraph)

    # Wiring: START → route → (conditional fan-out) → cluster → END.
    g.add_edge(START, "route")
    g.add_conditional_edges(
        "route",
        lambda s: s["routing_decision"].cluster,
        {c: c for c in ALL_CLUSTERS},
    )
    for cluster_name in ALL_CLUSTERS:
        g.add_edge(cluster_name, END)

    return g.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# safe_invoke — recursion_limit-to-HITL escalation (CORE-03)
# ---------------------------------------------------------------------------


async def safe_invoke(
    graph: Any,
    initial_state: AgentState | dict[str, Any],
    *,
    config: dict[str, Any],
) -> AgentState | dict[str, Any]:
    """Invoke graph and convert GraphRecursionError into a HITL ProposedAction.

    Parameters
    ----------
    graph:
        Compiled LangGraph StateGraph (output of ``build_supervisor_graph`` or
        any custom subgraph).
    initial_state:
        Initial AgentState dict (must include `messages` and ideally
        `proposed_actions` — the latter is initialised to ``[]`` if missing).
    config:
        LangGraph invoke config. MUST contain ``recursion_limit`` — a missing key
        raises ValueError (defense against unbounded LLM token spend).

    Returns
    -------
    AgentState dict
        On normal completion: whatever the graph yields.
        On GraphRecursionError: the augmented state with a new HITL Manager-tier
        ProposedAction appended to ``proposed_actions`` (no exception raised).
    """
    if "recursion_limit" not in config:
        raise ValueError(
            "safe_invoke requires config['recursion_limit'] to be set "
            "(success criterion #2 — every invoke must enforce a budget cap)."
        )
    thread_id = config.get("configurable", {}).get("thread_id", "")
    recursion_limit = config["recursion_limit"]

    state: dict[str, Any] = dict(initial_state) if not isinstance(initial_state, dict) else {**initial_state}
    state.setdefault("proposed_actions", [])

    try:
        return await graph.ainvoke(state, config=config)
    except GraphRecursionError as exc:
        _log.warning(
            "supervisor.recursion_limit_exceeded",
            thread_id=thread_id,
            recursion_limit=recursion_limit,
            error=str(exc),
        )
        review_action = ProposedAction.from_payload(
            thread_id=thread_id or "unknown",
            action_type=ActionType.GRAPH_RECURSION_REVIEW,
            args={
                "thread_id": thread_id,
                "recursion_limit": recursion_limit,
                "requires_tier": Tier.MANAGER.value,
                "reason": (
                    "recursion_limit exceeded — Plan 04-06 HITL middleware will "
                    "route to Manager tier"
                ),
            },
        )
        existing: list[ProposedAction] = list(state.get("proposed_actions") or [])
        existing.append(review_action)
        state["proposed_actions"] = existing
        return state


__all__ = ["build_supervisor_graph", "safe_invoke"]
