"""Cluster subgraph builder — placeholder children + per-cluster routers.

Phase 4 ships StateGraph skeletons only; per-agent business logic is filled in
Phase 6 (Ops), Phase 7 (Maintenance), Phase 8 (Knowledge-*), Phase 9 (Supply).

* ``build_cluster_subgraph`` — original Phase 4 linear placeholder skeleton
  (untouched, still used by knowledge/supply until those phases wire real
  callables).
* ``build_ops_subgraph`` — Phase 6 (Plan 06-05) router subgraph that branches
  from ``START`` on ``state["target_agent"]`` to the matching child callable
  and falls back to ``operator-assistant`` on missing / unknown target.
  See RESEARCH §Pattern 9 + D-X OPS routing.
* ``build_maintenance_subgraph`` — Phase 7 (Plan 07-04) router subgraph that
  mirrors :func:`build_ops_subgraph` shape (D-X OPS routing pattern reused).
  Falls back to ``rca-specialist`` per planner decision: RCASpecialist is the
  always-supervisor agent (D-RCA-02) so an unknown-target route falls into
  the safest possible path (HITL gate guaranteed). Emits ``mnt_route_unknown_target``
  structlog warning when the fallback is taken.
* ``build_knowledge_subgraph`` — Phase 8 (Plan 08-01) router subgraph that
  mirrors :func:`build_maintenance_subgraph` shape (D-X-04 gateway pattern).
  Falls back to ``knowledge-curator`` (autonomous, D-KC-04) — no HITL, no
  irreversible side effects. Emits ``knw_route_unknown_target`` structlog
  warning when the fallback is taken.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import structlog
from langgraph.graph import END, START, StateGraph

from sft_agents.runtime.state import VALID_CLUSTERS, AgentState

_log = structlog.get_logger(__name__)

#: Default fallback target for the ops router (D-X OPS-routing).
_OPS_DEFAULT_AGENT: str = "operator-assistant"

#: Default fallback target for the maintenance router (Plan 07-04 planner
#: decision). RCASpecialist is the always-supervisor agent (D-RCA-02 literal
#: success criterion) so an unknown-target routing falls into the safest
#: possible path — the HITL gate is guaranteed even when the supervisor
#: routing table drifts.
_MNT_DEFAULT_AGENT: str = "rca-specialist"

#: Default fallback target for the knowledge router (Plan 08-01 planner decision).
#: KnowledgeCurator is autonomous (D-KC-04) — no HITL, no irreversible side effects.
#: Unknown-target routing to an autonomous agent is the safest fallback.
_KNW_DEFAULT_AGENT: str = "knowledge-curator"


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


def build_ops_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    """Return an *uncompiled* OPS-cluster StateGraph with conditional routing.

    Each entry in ``child_callables`` is the agent's async ``__call__`` (already
    a coroutine that returns a state-delta dict). The graph wires:

        START → conditional_edges(_route) → <selected slug> → END

    ``_route(state)`` reads ``state.get("target_agent")``. If the value is
    missing or not present in ``child_callables``, the router falls back to
    ``operator-assistant`` and emits a ``ops_route_unknown_target`` structlog
    warning so observability still surfaces the routing-table drift.

    Parameters
    ----------
    child_callables:
        Mapping of agent slug (kebab-case, e.g. ``operator-assistant``) to the
        async callable that implements the agent's node body. MUST include
        ``operator-assistant`` (the fallback) — otherwise the fallback would
        silently fail at run-time. Non-empty.

    Returns
    -------
    StateGraph
        Uncompiled StateGraph(AgentState). Caller is responsible for
        ``.compile(...)`` — the supervisor typically compiles each cluster
        subgraph as a supervisor node.

    Raises
    ------
    ValueError
        If ``child_callables`` is empty or does not contain
        ``operator-assistant``.
    """
    if not child_callables:
        raise ValueError("child_callables must be non-empty for the ops subgraph")
    if _OPS_DEFAULT_AGENT not in child_callables:
        raise ValueError(
            f"child_callables must include {_OPS_DEFAULT_AGENT!r} (the fallback "
            f"target for the OPS router); got slugs {sorted(child_callables)}"
        )

    # Defensive copy — callers should not mutate the mapping after build, and
    # the router closure should not be affected by post-build edits.
    children: dict[str, Callable[[AgentState], Awaitable[dict[str, Any]]]] = dict(
        child_callables
    )

    g: StateGraph = StateGraph(AgentState)
    for slug, fn in children.items():
        g.add_node(slug, fn)

    def _route(state: AgentState) -> str:
        # ``state`` is a TypedDict (mapping-like at runtime).
        target = state.get("target_agent") if isinstance(state, dict) else None
        if not target or target not in children:
            _log.warning(
                "ops_route_unknown_target",
                target=target,
                fallback=_OPS_DEFAULT_AGENT,
            )
            return _OPS_DEFAULT_AGENT
        return str(target)

    g.add_conditional_edges(START, _route, {slug: slug for slug in children})
    for slug in children:
        g.add_edge(slug, END)

    return g


def build_maintenance_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    """Return an *uncompiled* MAINTENANCE-cluster StateGraph with conditional routing.

    Structural mirror of :func:`build_ops_subgraph` (D-X OPS routing pattern
    reused per 07-PATTERNS.md Section 1). Each entry in ``child_callables`` is
    the maintenance-agent's async ``__call__`` (already a coroutine that
    returns a state-delta dict). The graph wires:

        START → conditional_edges(_route) → <selected slug> → END

    ``_route(state)`` reads ``state.get("target_agent")``. If the value is
    missing or not present in ``child_callables``, the router falls back to
    ``rca-specialist`` (the always-supervisor agent — see D-RCA-02; planner
    decision documented in Plan 07-04) and emits a ``mnt_route_unknown_target``
    structlog warning so observability still surfaces the routing-table drift.

    Parameters
    ----------
    child_callables:
        Mapping of agent slug (kebab-case, e.g. ``predictive-maintenance``,
        ``rca-specialist``, ``maintenance-coach``, ``downtime-analyzer``) to
        the async callable that implements the agent's node body. MUST
        include ``rca-specialist`` (the fallback) — otherwise the fallback
        would silently fail at run-time. Non-empty.

    Returns
    -------
    StateGraph
        Uncompiled StateGraph(AgentState). Caller is responsible for
        ``.compile(...)`` — the supervisor typically compiles each cluster
        subgraph as a supervisor node.

    Raises
    ------
    ValueError
        If ``child_callables`` is empty or does not contain ``rca-specialist``.
    """
    if not child_callables:
        raise ValueError(
            "child_callables must be non-empty for the maintenance subgraph"
        )
    if _MNT_DEFAULT_AGENT not in child_callables:
        raise ValueError(
            f"child_callables must include {_MNT_DEFAULT_AGENT!r} (the fallback "
            f"target for the maintenance router); got slugs {sorted(child_callables)}"
        )

    # Defensive copy — callers should not mutate the mapping after build, and
    # the router closure should not be affected by post-build edits.
    children: dict[str, Callable[[AgentState], Awaitable[dict[str, Any]]]] = dict(
        child_callables
    )

    g: StateGraph = StateGraph(AgentState)
    for slug, fn in children.items():
        g.add_node(slug, fn)

    def _route(state: AgentState) -> str:
        # ``state`` is a TypedDict (mapping-like at runtime).
        target = state.get("target_agent") if isinstance(state, dict) else None
        if not target or target not in children:
            _log.warning(
                "mnt_route_unknown_target",
                target=target,
                fallback=_MNT_DEFAULT_AGENT,
            )
            return _MNT_DEFAULT_AGENT
        return str(target)

    g.add_conditional_edges(START, _route, {slug: slug for slug in children})
    for slug in children:
        g.add_edge(slug, END)

    return g


def build_knowledge_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    """Return an *uncompiled* KNOWLEDGE-cluster StateGraph with conditional routing.

    Structural mirror of :func:`build_maintenance_subgraph` (D-X-04 gateway pattern).
    Each entry in ``child_callables`` is the knowledge-agent's async ``__call__``
    (already a coroutine that returns a state-delta dict). The graph wires:

        START → conditional_edges(_route) → <selected slug> → END

    ``_route(state)`` reads ``state.get("target_agent")``. If the value is
    missing or not present in ``child_callables``, the router falls back to
    ``knowledge-curator`` (autonomous, D-KC-04) and emits a
    ``knw_route_unknown_target`` structlog warning so observability still surfaces
    the routing-table drift.

    Parameters
    ----------
    child_callables:
        Mapping of agent slug (kebab-case, e.g. ``shift-handover``,
        ``training-coach``, ``knowledge-curator``, ``documentation-synthesizer``)
        to the async callable that implements the agent's node body. MUST include
        ``knowledge-curator`` (the fallback) — otherwise the fallback would
        silently fail at run-time. Non-empty.

    Returns
    -------
    StateGraph
        Uncompiled StateGraph(AgentState). Caller is responsible for
        ``.compile(...)`` — the supervisor typically compiles each cluster
        subgraph as a supervisor node.

    Raises
    ------
    ValueError
        If ``child_callables`` is empty or does not contain ``knowledge-curator``.
    """
    if not child_callables:
        raise ValueError(
            "child_callables must be non-empty for the knowledge subgraph"
        )
    if _KNW_DEFAULT_AGENT not in child_callables:
        raise ValueError(
            f"child_callables must include {_KNW_DEFAULT_AGENT!r} (the fallback "
            f"target for the knowledge router); got slugs {sorted(child_callables)}"
        )

    # Defensive copy — callers should not mutate the mapping after build, and
    # the router closure should not be affected by post-build edits.
    children: dict[str, Callable[[AgentState], Awaitable[dict[str, Any]]]] = dict(
        child_callables
    )

    g: StateGraph = StateGraph(AgentState)
    for slug, fn in children.items():
        g.add_node(slug, fn)

    def _route(state: AgentState) -> str:
        # ``state`` is a TypedDict (mapping-like at runtime).
        target = state.get("target_agent") if isinstance(state, dict) else None
        if not target or target not in children:
            _log.warning(
                "knw_route_unknown_target",
                target=target,
                fallback=_KNW_DEFAULT_AGENT,
            )
            return _KNW_DEFAULT_AGENT
        return str(target)

    g.add_conditional_edges(START, _route, {slug: slug for slug in children})
    for slug in children:
        g.add_edge(slug, END)

    return g


__all__ = [
    "build_cluster_subgraph",
    "build_knowledge_subgraph",
    "build_maintenance_subgraph",
    "build_ops_subgraph",
]
