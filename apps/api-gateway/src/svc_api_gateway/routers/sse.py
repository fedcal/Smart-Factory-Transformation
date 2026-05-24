"""SSE streaming endpoints — Plan 10-03 (SRV-02, SRV-04, UI-06, HITL-10).

Three EventSourceResponse endpoints over /v1/stream/:
    GET /v1/stream/kpi        — kpi_update (every 5 s) + sse_heartbeat (every 30 s)
    GET /v1/stream/approvals  — approval_pending + approval_resolved + sse_heartbeat
    GET /v1/stream/alerts     — alert_new + sse_heartbeat; HITL-10 12/hr/persona rate-limit

Security:
    JWT accepted via `?token=` query parameter (EventSource cannot set custom headers —
    post_research_resolution #2). Validated identically to the Authorization-header path
    via the same decode_token + require_roles_qs dependency.

Threat mitigations implemented here:
    T-10-03-02 — HITL-10 12/hr/persona sliding-window in-process rate limit (alerts only)
    T-10-03-03 — sse_heartbeat every 30 s + X-Accel-Buffering: no (Pitfall 5)
    T-10-03-04 — require_roles_qs enforces role from signed JWT claim (V4)
    T-10-03-05 — Generic 500 body + structlog (CR-02); never leaks internal detail

Notes:
    - Rate-limit state is stored in a module-level dict guarded for the single-process
      dev gateway. Distributed enforcement is a Phase 11 concern (documented in SUMMARY).
    - The approvals + alerts generators poll the DB at a coarse interval (5 s) as a
      placeholder; Phase 11 will replace the polling loop with a NATS JetStream consumer.
    - asyncio.sleep is NOT imported at module level so it can be monkeypatched by tests.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from typing import Annotated, Any, AsyncGenerator

import structlog
from fastapi import APIRouter, Depends, Request
from sse_starlette.sse import EventSourceResponse

from svc_api_gateway.dependencies import get_pool
from svc_api_gateway.kpi.queries import compute_kpi_snapshot
from svc_api_gateway.security.rbac import require_roles_qs

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/stream", tags=["sse"])

# ---------------------------------------------------------------------------
# Roles allowed on each channel (T-10-03-04)
# ---------------------------------------------------------------------------

_KPI_ROLES = ("operator", "shift-supervisor", "manager", "admin")
_APPROVAL_ROLES = ("operator", "shift-supervisor", "manager", "admin")
_ALERT_ROLES = ("operator", "shift-supervisor", "manager", "admin")

# ---------------------------------------------------------------------------
# HITL-10 rate-limit state (T-10-03-02)
# ---------------------------------------------------------------------------
# Per-principal (email/sub from JWT) sliding window: stores emission timestamps
# (float seconds) for the last hour. Access from a single asyncio event loop
# (single-process dev gateway) — no locking needed.
#
# Distributed enforcement deferred to Phase 11 (Redis-backed sliding window).
# ---------------------------------------------------------------------------

_ALERT_RATE_LIMIT = 12         # max alerts per window per persona (HITL-10)
_ALERT_WINDOW_SECONDS = 3600   # 1 hour sliding window

# Dict[principal_sub: str, deque[emission_timestamp: float]]
_alert_rate_state: dict[str, deque[float]] = {}


def _check_alert_rate(principal_sub: str, now: float) -> bool:
    """Return True if the alert is allowed; False if the rate limit is exceeded.

    Maintains a sliding-window deque of emission timestamps per principal.
    Mutates _alert_rate_state in-place (immutable data not applicable here —
    we maintain a cumulative state as required by the sliding-window algorithm).
    """
    window_start = now - _ALERT_WINDOW_SECONDS
    if principal_sub not in _alert_rate_state:
        _alert_rate_state[principal_sub] = deque()
    window = _alert_rate_state[principal_sub]
    # Evict timestamps outside the window
    while window and window[0] < window_start:
        window.popleft()
    if len(window) >= _ALERT_RATE_LIMIT:
        return False
    window.append(now)
    return True


# ---------------------------------------------------------------------------
# SSE response headers
# ---------------------------------------------------------------------------

_SSE_HEADERS = {
    "X-Accel-Buffering": "no",  # Pitfall 5 — disable nginx / reverse-proxy buffering
    "Cache-Control": "no-cache",
}

# ---------------------------------------------------------------------------
# Generator intervals
# ---------------------------------------------------------------------------

_KPI_INTERVAL_SECONDS = 5.0
_HEARTBEAT_INTERVAL_SECONDS = 30.0
_POLL_INTERVAL_SECONDS = 5.0


# ---------------------------------------------------------------------------
# KPI stream generator
# ---------------------------------------------------------------------------


async def kpi_stream(
    request: Request,
    pool: Any,
) -> AsyncGenerator[dict[str, str], None]:
    """Async generator for the KPI channel.

    Yields:
        kpi_update   — every _KPI_INTERVAL_SECONDS (5 s) with compute_kpi_snapshot result
        sse_heartbeat — every _HEARTBEAT_INTERVAL_SECONDS (30 s)

    Terminates cleanly when the client disconnects (request.is_disconnected()).
    Generic 500 body on unexpected errors (T-10-03-05).
    """
    last_heartbeat = time.monotonic()
    elapsed = 0.0

    while True:
        if await request.is_disconnected():
            logger.info("sse_kpi_client_disconnected")
            break

        # Emit kpi_update
        try:
            snapshot = await compute_kpi_snapshot(pool)
            yield {"event": "kpi_update", "data": json.dumps({"kpi": snapshot})}
        except Exception:  # noqa: BLE001
            logger.exception("sse_kpi_snapshot_failed")
            yield {
                "event": "error",
                "data": json.dumps({"detail": "internal_server_error"}),
            }

        # Emit heartbeat if due
        now = time.monotonic()
        if now - last_heartbeat >= _HEARTBEAT_INTERVAL_SECONDS:
            yield {"event": "sse_heartbeat", "data": json.dumps({})}
            last_heartbeat = now

        elapsed += _KPI_INTERVAL_SECONDS
        await asyncio.sleep(_KPI_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Approvals stream generator
# ---------------------------------------------------------------------------


async def approvals_stream(
    request: Request,
    pool: Any,
) -> AsyncGenerator[dict[str, str], None]:
    """Async generator for the approvals channel.

    Polls audit.actions for pending approvals every _POLL_INTERVAL_SECONDS.
    Yields:
        approval_pending  — new pending rows (approval_id, agent, tier, sla_seconds)
        approval_resolved — newly resolved rows (approval_id, status)
        sse_heartbeat     — every _HEARTBEAT_INTERVAL_SECONDS

    Phase 11: replace polling with NATS JetStream consumer.
    """
    last_heartbeat = time.monotonic()
    seen_ids: set[str] = set()

    while True:
        if await request.is_disconnected():
            logger.info("sse_approvals_client_disconnected")
            break

        try:
            async with pool.acquire() as conn:
                # Poll pending approvals not yet emitted.
                # Use parameterised != ALL($1::text[]) to avoid SQL injection
                # (CR-01 — never interpolate IDs via f-string/join).
                seen_list = list(seen_ids)
                pending_rows = await conn.fetch(
                    "SELECT action_id::text AS approval_id, agent_id AS agent,"
                    "       'operator' AS tier, 120 AS sla_seconds"
                    " FROM audit.actions"
                    " WHERE decision = 'hitl_operator'"
                    "   AND action_id::text != ALL($1::text[])"
                    " LIMIT 10",
                    seen_list,
                )
                for row in pending_rows:
                    aid = str(row["approval_id"])
                    seen_ids.add(aid)
                    yield {
                        "event": "approval_pending",
                        "data": json.dumps(
                            {
                                "approval_id": aid,
                                "agent": row["agent"],
                                "tier": row["tier"],
                                "sla_seconds": row["sla_seconds"],
                            }
                        ),
                    }

                # Poll recently resolved
                resolved_rows = await conn.fetch(
                    "SELECT action_id::text AS approval_id,"
                    "       decision AS status"
                    " FROM audit.actions"
                    " WHERE decision IN ('auto', 'logged', 'rolled_back')"
                    "   AND created_at >= NOW() - INTERVAL '1 minute'"
                    " LIMIT 10"
                )
                for row in resolved_rows:
                    yield {
                        "event": "approval_resolved",
                        "data": json.dumps(
                            {
                                "approval_id": str(row["approval_id"]),
                                "status": (
                                    "approved"
                                    if row["status"] in ("auto", "logged")
                                    else "rejected"
                                ),
                            }
                        ),
                    }
        except Exception:  # noqa: BLE001
            logger.exception("sse_approvals_poll_failed")

        now = time.monotonic()
        if now - last_heartbeat >= _HEARTBEAT_INTERVAL_SECONDS:
            yield {"event": "sse_heartbeat", "data": json.dumps({})}
            last_heartbeat = now

        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Alerts stream generator (with HITL-10 rate limit)
# ---------------------------------------------------------------------------


async def alerts_stream(
    request: Request,
    pool: Any,
    principal_sub: str,
) -> AsyncGenerator[dict[str, str], None]:
    """Async generator for the alerts channel with HITL-10 rate limiting.

    Yields:
        alert_new   — new ANOMALY_ALERT / GOVERNOR_ALERT rows (alert_id, message, severity)
        rate_limit  — when the per-persona 12/hr limit is exceeded (suppresses alert_new)
        sse_heartbeat — every _HEARTBEAT_INTERVAL_SECONDS

    Rate-limit state is in-process (module-level _alert_rate_state). Phase 11 will
    replace with a Redis-backed distributed counter.
    """
    last_heartbeat = time.monotonic()
    seen_ids: set[str] = set()
    rate_limit_notified = False  # emit rate_limit event at most once per threshold crossing

    while True:
        if await request.is_disconnected():
            logger.info("sse_alerts_client_disconnected", principal=principal_sub)
            break

        try:
            async with pool.acquire() as conn:
                # Use parameterised != ALL($1::text[]) — CR-01 SQL injection fix.
                seen_list = list(seen_ids)
                alert_rows = await conn.fetch(
                    "SELECT action_id::text AS alert_id,"
                    "       action_type AS message,"
                    "       'warning' AS severity"
                    " FROM audit.actions"
                    " WHERE action_type IN ('ANOMALY_ALERT', 'GOVERNOR_ALERT')"
                    "   AND action_id::text != ALL($1::text[])"
                    " ORDER BY created_at DESC LIMIT 10",
                    seen_list,
                )
                for row in alert_rows:
                    aid = str(row["alert_id"])
                    seen_ids.add(aid)
                    now_ts = time.time()
                    if _check_alert_rate(principal_sub, now_ts):
                        rate_limit_notified = False  # window freed up
                        yield {
                            "event": "alert_new",
                            "data": json.dumps(
                                {
                                    "alert_id": aid,
                                    "message": row["message"],
                                    "severity": row["severity"],
                                }
                            ),
                        }
                    else:
                        if not rate_limit_notified:
                            yield {
                                "event": "rate_limit",
                                "data": json.dumps(
                                    {"limit": _ALERT_RATE_LIMIT, "window": "1h"}
                                ),
                            }
                            rate_limit_notified = True
                        logger.warning(
                            "sse_alert_rate_limited",
                            principal=principal_sub,
                            alert_id=aid,
                        )
        except Exception:  # noqa: BLE001
            logger.exception("sse_alerts_poll_failed")

        now = time.monotonic()
        if now - last_heartbeat >= _HEARTBEAT_INTERVAL_SECONDS:
            yield {"event": "sse_heartbeat", "data": json.dumps({})}
            last_heartbeat = now

        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# FastAPI endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/kpi",
    summary="Live KPI stream (SSE)",
    description=(
        "Server-Sent Events stream emitting kpi_update (every 5 s) and sse_heartbeat "
        "(every 30 s). Authenticate via ?token=<JWT>. "
        "Allowed roles: operator, shift-supervisor, manager, admin."
    ),
)
async def stream_kpi(
    request: Request,
    principal: Annotated[dict, Depends(require_roles_qs(*_KPI_ROLES))],
    pool: Annotated[Any, Depends(get_pool)],
) -> EventSourceResponse:
    """Stream live KPI updates as Server-Sent Events."""
    return EventSourceResponse(
        kpi_stream(request, pool),
        headers=_SSE_HEADERS,
    )


@router.get(
    "/approvals",
    summary="Live approvals stream (SSE)",
    description=(
        "Server-Sent Events stream emitting approval_pending, approval_resolved, and "
        "sse_heartbeat. Authenticate via ?token=<JWT>."
    ),
)
async def stream_approvals(
    request: Request,
    principal: Annotated[dict, Depends(require_roles_qs(*_APPROVAL_ROLES))],
    pool: Annotated[Any, Depends(get_pool)],
) -> EventSourceResponse:
    """Stream live approval events as Server-Sent Events."""
    return EventSourceResponse(
        approvals_stream(request, pool),
        headers=_SSE_HEADERS,
    )


@router.get(
    "/alerts",
    summary="Live alerts stream (SSE, HITL-10 rate-limited)",
    description=(
        "Server-Sent Events stream emitting alert_new (HITL-10 max 12/hr/persona), "
        "rate_limit (when limit exceeded), and sse_heartbeat. "
        "Authenticate via ?token=<JWT>."
    ),
)
async def stream_alerts(
    request: Request,
    principal: Annotated[dict, Depends(require_roles_qs(*_ALERT_ROLES))],
    pool: Annotated[Any, Depends(get_pool)],
) -> EventSourceResponse:
    """Stream live alert events as Server-Sent Events (with per-persona rate limiting)."""
    principal_sub: str = principal.get("sub", principal.get("email", "unknown"))
    return EventSourceResponse(
        alerts_stream(request, pool, principal_sub),
        headers=_SSE_HEADERS,
    )


__all__ = [
    "router",
    "kpi_stream",
    "approvals_stream",
    "alerts_stream",
    "_check_alert_rate",
    "_alert_rate_state",
    "_ALERT_RATE_LIMIT",
    "_ALERT_WINDOW_SECONDS",
]
