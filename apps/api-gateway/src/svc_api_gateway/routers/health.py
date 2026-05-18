"""GET /v1/health + /v1/ready — liveness + readiness probes (Plan 04-07 Task 1).

/v1/health (liveness): always returns 200; the body's
``dependencies.{pg,nats}`` field communicates per-dependency status.
``status`` flips to ``degraded`` when ANY dependency is down (operators see at
a glance from the status field alone whether everything is green).

/v1/ready (readiness): returns 200 only when ALL dependencies are up.
Returns 503 + same body otherwise. Used by k8s ReadinessProbe (Phase 11).
"""

from __future__ import annotations

from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from svc_api_gateway.dependencies import get_nats_publisher, get_pool

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["health"])


class HealthResponse(BaseModel):
    """JSON body for /v1/health and /v1/ready."""

    model_config = {"extra": "forbid"}

    status: Literal["ok", "degraded"]
    dependencies: dict[str, Literal["up", "down"]]


async def _check_pg(pool: Any) -> Literal["up", "down"]:
    """Acquire a connection + run SELECT 1; return 'up' on success."""
    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001
        logger.warning("health_pg_check_failed", error=str(exc))
        return "down"
    return "up"


def _check_nats(nats_publisher: Any) -> Literal["up", "down"]:
    """Inspect AuditNatsPublisher._nc.is_connected — synchronous attribute read."""
    nc = getattr(nats_publisher, "_nc", None)
    if nc is None:
        return "down"
    try:
        return "up" if bool(nc.is_connected) else "down"
    except Exception as exc:  # noqa: BLE001
        logger.warning("health_nats_check_failed", error=str(exc))
        return "down"


@router.get("/health", response_model=HealthResponse)
async def health(
    pool: Any = Depends(get_pool),
    nats_publisher: Any = Depends(get_nats_publisher),
) -> HealthResponse:
    pg_state = await _check_pg(pool)
    nats_state = _check_nats(nats_publisher)
    overall: Literal["ok", "degraded"] = (
        "ok" if pg_state == "up" and nats_state == "up" else "degraded"
    )
    return HealthResponse(
        status=overall,
        dependencies={"pg": pg_state, "nats": nats_state},
    )


@router.get("/ready", response_model=HealthResponse)
async def ready(
    request: Request,
    pool: Any = Depends(get_pool),
    nats_publisher: Any = Depends(get_nats_publisher),
):
    pg_state = await _check_pg(pool)
    nats_state = _check_nats(nats_publisher)
    body = HealthResponse(
        status="ok" if pg_state == "up" and nats_state == "up" else "degraded",
        dependencies={"pg": pg_state, "nats": nats_state},
    )
    if body.status == "ok":
        return body
    # Return 503 with the same body shape on readiness failure.
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=body.model_dump(),
    )


__all__ = ["HealthResponse", "router"]
