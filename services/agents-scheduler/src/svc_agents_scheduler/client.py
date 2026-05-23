"""httpx-based client that triggers AnomalyDetector via the api-gateway.

The scheduler container POSTs to ``/v1/agents/anomaly-detector/scan`` (06-12
ships the endpoint). Payload is constant by design — the scheduler only
varies on cadence, never on inputs:

* ``window_minutes`` — defaults to 15 (matches D-AD-04 / 06-06 contract).
* ``triggered_by``  — constant ``"scheduler"`` so the audit row carries the
  provenance without an extra query.

httpx ``AsyncHTTPTransport(retries=3)`` handles transient HTTP 5xx + connect
errors. We deliberately do NOT add per-request retries — Pitfall §5's
``coalesce=True`` means the next cron fire will catch up if the gateway
is hard-down for the full retry budget.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

_log = structlog.get_logger("agents-scheduler.client")

#: Canonical anomaly-scan endpoint (Plan 06-12 ships the gateway handler).
ANOMALY_SCAN_PATH: str = "/v1/agents/anomaly-detector/scan"

#: Default HTTP timeout — generous because the gateway runs the full scan
#: synchronously (Phase 6 scope; an async accept-202 path is a future plan).
DEFAULT_TIMEOUT_S: float = 60.0

#: Transport-level retry budget for transient gateway hiccups.
RETRIES: int = 3


def build_http_client(
    *, timeout: float = DEFAULT_TIMEOUT_S
) -> httpx.AsyncClient:
    """Return an ``AsyncClient`` with ``AsyncHTTPTransport(retries=3)``.

    Factored out so the test suite can inspect ``AsyncHTTPTransport`` kwargs
    without standing up a real socket.
    """
    transport = httpx.AsyncHTTPTransport(retries=RETRIES)
    return httpx.AsyncClient(timeout=timeout, transport=transport)


async def trigger_anomaly_scan(
    *,
    gateway_url: str,
    window_minutes: int,
    client: Any | None = None,
) -> int:
    """POST a single anomaly-scan request and return the HTTP status code.

    Parameters
    ----------
    gateway_url:
        Base URL of the api-gateway (no trailing slash). Joined with
        ``ANOMALY_SCAN_PATH`` at call time.
    window_minutes:
        Time window the detector should consider — forwarded verbatim
        into the JSON body.
    client:
        Optional pre-built ``httpx.AsyncClient`` (injected from tests or
        from ``__main__.main`` to keep the connection pool warm across
        cron fires). When ``None`` a one-shot client is constructed and
        closed before returning.

    Returns
    -------
    int
        HTTP status code from the gateway. Caller is free to log / count
        but should NOT raise on non-2xx — the next cron fire retries.
    """
    base = gateway_url.rstrip("/")
    url = f"{base}{ANOMALY_SCAN_PATH}"
    body = {"window_minutes": int(window_minutes), "triggered_by": "scheduler"}

    if client is None:
        async with build_http_client() as owned:
            response = await owned.post(url, json=body)
    else:
        response = await client.post(url, json=body)

    status_code = int(getattr(response, "status_code", 0))
    _log.info(
        "scheduler_invoked",
        status_code=status_code,
        window_minutes=int(window_minutes),
        url=url,
    )
    return status_code


__all__ = [
    "ANOMALY_SCAN_PATH",
    "DEFAULT_TIMEOUT_S",
    "RETRIES",
    "build_http_client",
    "trigger_anomaly_scan",
]
