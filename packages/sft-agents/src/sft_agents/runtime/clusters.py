"""Cluster subgraph builder — placeholder children only (Plan 04-05 Task 2).

Phase 4 ships StateGraph skeletons only; per-agent business logic is filled in
Phase 6 (Ops), Phase 7 (Maintenance), Phase 8 (Knowledge-*), Phase 9 (Supply).

Each placeholder child node simply logs and returns ``{}`` — the supervisor wires
inter-cluster routing; intra-cluster routing is a linear START → first child →
END skeleton that future phases will extend with conditional edges.
"""
from __future__ import annotations

import structlog
from langgraph.graph import END, START, StateGraph

from sft_agents.runtime.state import VALID_CLUSTERS, AgentState

_log = structlog.get_logger(__name__)


def build_cluster_subgraph(cluster_name: str, child_agent_slugs: list[str]) -> StateGraph:
    """Return an *uncompiled* StateGraph(AgentState) for a single cluster.

    Parameters
    ----------
    cluster_name:
        Hyphenated cluster identifier (one of VALID_CLUSTERS).
    child_agent_slugs:
        Kebab-case agent slugs for the placeholder child nodes; must be
        non-empty. Order determines the linear START → first → ... → END
        traversal Phase 4 ships.

    Returns
    -------
    StateGraph
        Caller is responsible for ``.compile(...)`` (the supervisor compiles
        each cluster subgraph as a node).

    Raises
    ------
    ValueError
        If `cluster_name` is not in VALID_CLUSTERS, or `child_agent_slugs` is
        empty.
    """
    if cluster_name not in VALID_CLUSTERS:
        raise ValueError(
            f"cluster_name must be one of {sorted(VALID_CLUSTERS)}, got {cluster_name!r}"
        )
    if not child_agent_slugs:
        raise ValueError(
            f"child_agent_slugs must be non-empty for cluster {cluster_name!r}"
        )

    g: StateGraph = StateGraph(AgentState)

    def _make_placeholder(slug: str):  # type: ignore[no-untyped-def]
        async def _placeholder_node(_state: AgentState) -> dict:  # type: ignore[no-untyped-def]
            _log.info(
                "cluster_child_placeholder",
                cluster=cluster_name,
                agent_id=slug,
                message="Phase 6-9 will implement business logic",
            )
            return {}

        _placeholder_node.__name__ = f"_placeholder_{slug.replace('-', '_')}"
        return _placeholder_node

    for slug in child_agent_slugs:
        g.add_node(slug, _make_placeholder(slug))

    # Linear skeleton: START → slug[0] → slug[1] → ... → END.
    g.add_edge(START, child_agent_slugs[0])
    for prev, nxt in zip(child_agent_slugs, child_agent_slugs[1:]):
        g.add_edge(prev, nxt)
    g.add_edge(child_agent_slugs[-1], END)

    return g


__all__ = ["build_cluster_subgraph"]
