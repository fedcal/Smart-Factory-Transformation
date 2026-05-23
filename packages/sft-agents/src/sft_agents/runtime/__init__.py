"""sft_agents.runtime — LangGraph runtime backbone (Phase 4 Plan 04-05).

Wires the supervisor StateGraph, the 5 cluster subgraphs (D-53), the hybrid router
(D-54), and the PostgreSQL checkpointer (D-59 thread_id convention).

Public symbols (Task 1 — state + checkpointer):
    AgentState            — TypedDict (CONTEXT.md Claude's Discretion line 419)
    RoutingDecision       — Pydantic frozen Stage 1/2 routing output (D-54)
    VALID_CLUSTERS        — frozenset of the 5 cluster names (D-53)
    ALL_CLUSTERS          — ordered tuple of the 5 cluster names
    get_postgres_checkpointer — async context manager around AsyncPostgresSaver (CORE-04)
    format_thread_id      — `{cluster}.{agent_id}.{session_uuid}` (D-59)
    parse_thread_id       — inverse of format_thread_id

Public symbols (Task 2 — supervisor + router + clusters):
    build_cluster_subgraph, build_supervisor_graph, safe_invoke, HybridRouter
"""
from __future__ import annotations

from sft_agents.runtime.checkpointer import (
    format_thread_id,
    get_postgres_checkpointer,
    parse_thread_id,
)
from sft_agents.runtime.rate_limit import RateLimiter
from sft_agents.runtime.state import (
    ALL_CLUSTERS,
    VALID_CLUSTERS,
    AgentState,
    RoutingDecision,
)

__all__ = [
    "ALL_CLUSTERS",
    "AgentState",
    "HybridRouter",
    "RateLimiter",
    "RoutingDecision",
    "VALID_CLUSTERS",
    "build_cluster_subgraph",
    "build_supervisor_graph",
    "format_thread_id",
    "get_postgres_checkpointer",
    "parse_thread_id",
    "safe_invoke",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    """Lazy-import Task-2 symbols so Task-1 consumers don't pay the langgraph cost.

    Importing supervisor/clusters/HybridRouter at package import time would pull
    in langgraph.graph and pyyaml unconditionally. Lazy attribute access keeps
    ``from sft_agents.runtime import format_thread_id`` cheap.
    """
    if name in {"build_cluster_subgraph"}:
        from sft_agents.runtime.clusters import build_cluster_subgraph  # noqa: PLC0415

        return build_cluster_subgraph
    if name in {"build_supervisor_graph", "safe_invoke"}:
        from sft_agents.runtime import supervisor as _sup  # noqa: PLC0415

        return getattr(_sup, name)
    if name == "HybridRouter":
        from sft_agents.policies.routing import HybridRouter  # noqa: PLC0415

        return HybridRouter
    raise AttributeError(f"module 'sft_agents.runtime' has no attribute {name!r}")
