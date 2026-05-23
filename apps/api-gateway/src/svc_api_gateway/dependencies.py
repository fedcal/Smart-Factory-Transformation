"""FastAPI dependency factories — Plan 04-07 Task 1, extended Plan 07-10.

Each factory reads an attribute from ``request.app.state`` (populated during
:func:`svc_api_gateway.lifespan.lifespan`). If the state attribute is missing,
the factory raises ``HTTPException(503)`` so calls during startup/teardown
return a clear status code rather than crashing with AttributeError.

Plan 07-10 extensions:
    ``get_maintenance_children`` — returns app.state.maintenance_children dict
    mapping maintenance agent slugs to their async __call__ callables.
    Used to build the maintenance subgraph via build_maintenance_subgraph (07-04).

    Note on supervisor multi-cluster routing: the existing build_supervisor_graph
    uses build_cluster_subgraph (placeholder) for the maintenance cluster. Phase 7
    real agent callables are wired via app.state.maintenance_children, which the
    lifespan populates for use by any direct-DI access patterns. The supervisor
    graph's maintenance node is still the Phase 4 placeholder subgraph — Phase 11
    will wire real callables into the supervisor when the full stack is ready.
    For 07-10, the maintenance router calls supervisor_graph.ainvoke which routes
    into the maintenance cluster; the tests mock supervisor_graph so the internal
    cluster routing is verified end-to-end in 07-12 E2E scenarios.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status


def _require_state(request: Request, name: str) -> Any:
    obj = getattr(request.app.state, name, None)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"service_unavailable: app.state.{name} not initialized",
        )
    return obj


def get_pool(request: Request) -> Any:
    """Return ``app.state.pool`` (asyncpg.Pool) or 503."""
    return _require_state(request, "pool")


def get_audit_writer(request: Request) -> Any:
    """Return ``app.state.audit_writer`` (sft_agents.audit.AuditWriter) or 503."""
    return _require_state(request, "audit_writer")


def get_queue_writer(request: Request) -> Any:
    """Return ``app.state.queue_writer`` (sft_agents.hitl.ApprovalQueueWriter) or 503."""
    return _require_state(request, "queue_writer")


def get_supervisor_graph(request: Request) -> Any:
    """Return ``app.state.supervisor_graph`` (compiled LangGraph) or 503."""
    return _require_state(request, "supervisor_graph")


def get_checkpointer(request: Request) -> Any:
    """Return ``app.state.checkpointer`` (AsyncPostgresSaver) or 503."""
    return _require_state(request, "checkpointer")


def get_nats_publisher(request: Request) -> Any:
    """Return ``app.state.nats_publisher`` (AuditNatsPublisher) or 503."""
    return _require_state(request, "nats_publisher")


def get_idempotency_cache(request: Request) -> Any:
    """Return ``app.state.idempotency_cache`` (IdempotencyCache) or 503."""
    return _require_state(request, "idempotency_cache")


def get_maintenance_children(request: Request) -> Any:
    """Return ``app.state.maintenance_children`` (dict[str, callable]) or 503.

    The dict maps maintenance agent slugs to their async __call__ callables:
        {
            'predictive-maintenance': PredictiveMaintenance.__call__,
            'rca-specialist': RCASpecialist.__call__,
            'maintenance-coach': MaintenanceCoach.__call__,
            'downtime-analyzer': DowntimeAnalyzer.__call__,
        }

    Populated by :func:`svc_api_gateway.lifespan.lifespan` during app startup.
    Can be used with build_maintenance_subgraph (07-04) for direct DI wiring.
    """
    return _require_state(request, "maintenance_children")


__all__ = [
    "get_audit_writer",
    "get_checkpointer",
    "get_idempotency_cache",
    "get_maintenance_children",
    "get_nats_publisher",
    "get_pool",
    "get_queue_writer",
    "get_supervisor_graph",
]
