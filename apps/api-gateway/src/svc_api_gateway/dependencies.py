"""FastAPI dependency factories — Plan 04-07 Task 1.

Each factory reads an attribute from ``request.app.state`` (populated during
:func:`svc_api_gateway.lifespan.lifespan`). If the state attribute is missing,
the factory raises ``HTTPException(503)`` so calls during startup/teardown
return a clear status code rather than crashing with AttributeError.
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


__all__ = [
    "get_audit_writer",
    "get_checkpointer",
    "get_idempotency_cache",
    "get_nats_publisher",
    "get_pool",
    "get_queue_writer",
    "get_supervisor_graph",
]
