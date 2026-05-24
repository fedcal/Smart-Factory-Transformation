"""GET /v1/kpi — KPI snapshot endpoint — Plan 10-02 (SRV-02).

Surfaces compute_kpi_snapshot() behind RBAC: roles operator, shift-supervisor,
manager, and admin are authorised.  All other roles receive 403 "rbac_forbidden"
(frontend contract per 10-UI-SPEC).

Security mitigations:
  T-10-02-02 — require_roles restricts to the 4 dashboard roles.
  T-10-02-03 — unexpected exceptions → generic 500 body + structlog detail.

Design:
  - KpiSnapshot is frozen + extra="forbid" (CR-03 immutability guardrail).
  - pool is injected via Depends(get_pool) (from dependencies.py).
  - compute_kpi_snapshot accepts the pool and acquires its own connection.
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from svc_api_gateway.dependencies import get_pool
from svc_api_gateway.kpi.queries import compute_kpi_snapshot
from svc_api_gateway.security.rbac import require_roles

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["kpi"])

# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class KpiSnapshot(BaseModel):
    """Snapshot of the 6 real KPIs computed from TimescaleDB.

    All fields are float | None: None indicates no data was available for
    the computed window (no downtime events, no orders, etc.).

    Units:
        oee          — percentage [0, 100]
        mttr         — minutes
        mtbf         — hours
        scrap_rate   — percentage [0, 100]
        throughput   — kg/h
        downtime     — percentage [0, 100]
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    oee: float | None
    mttr: float | None
    mtbf: float | None
    scrap_rate: float | None
    throughput: float | None
    downtime: float | None


# ---------------------------------------------------------------------------
# Allowed roles (T-10-02-02)
# ---------------------------------------------------------------------------

_KPI_ROLES = ("operator", "shift-supervisor", "manager", "admin")


# ---------------------------------------------------------------------------
# GET /v1/kpi
# ---------------------------------------------------------------------------


@router.get(
    "/kpi",
    status_code=status.HTTP_200_OK,
    response_model=KpiSnapshot,
    summary="Current KPI snapshot",
    description=(
        "Returns the 6 real KPIs (OEE, MTTR, MTBF, scrap rate, throughput, downtime) "
        "computed from TimescaleDB.  Requires one of: operator, shift-supervisor, "
        "manager, admin.  OEE is Availability-only (P=1.0, Q=1.0 PoC approximation)."
    ),
)
async def get_kpi_snapshot(
    principal: Annotated[dict, Depends(require_roles(*_KPI_ROLES))],
    pool: Annotated[object, Depends(get_pool)],
) -> KpiSnapshot:
    """Compute and return a KPI snapshot.

    Raises:
        HTTPException 403 — role not in allowed set (raised by require_roles).
        HTTPException 500 — unexpected aggregation error (T-10-02-03 generic body).
    """
    try:
        data = await compute_kpi_snapshot(pool)
    except Exception:  # noqa: BLE001
        logger.exception("kpi_snapshot_failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal_server_error",  # T-10-02-03 generic body
        )

    return KpiSnapshot(**data)


__all__ = ["KpiSnapshot", "router"]
