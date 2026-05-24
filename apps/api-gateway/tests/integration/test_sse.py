"""Integration tests for SSE streaming endpoints — Plan 10-03 (SRV-02, HITL-10).

Covers:
    - kpi_stream generator yields kpi_update with correct 6-key shape
    - kpi_stream generator yields sse_heartbeat
    - GET /v1/stream/kpi responds with text/event-stream + X-Accel-Buffering: no
    - GET /v1/stream/kpi without token → 401
    - HITL-10 rate-limit: 13th alert suppressed, rate_limit event emitted

All tests use mocked asyncio.sleep (via monkeypatch / patch) to avoid wall-clock delay.
Pool is mocked directly; no real DB required.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Canonical SSE event names (10-UI-SPEC SSE Contratto Streaming)
# ---------------------------------------------------------------------------
KPI_KEYS = {"oee", "mttr", "mtbf", "scrap_rate", "throughput", "downtime"}
KPI_UPDATE_EVENT = "kpi_update"
HEARTBEAT_EVENT = "sse_heartbeat"


# ---------------------------------------------------------------------------
# Helper: build a mock pool whose fetchrow returns canned KPI data
# ---------------------------------------------------------------------------

def _make_kpi_pool() -> AsyncMock:
    """Return an AsyncMock pool where fetchrow returns canned downtime rows."""
    pool = AsyncMock()
    conn = AsyncMock()

    def _fetchrow_side_effect(sql, *args):
        """Return a canned row regardless of SQL content."""
        row = MagicMock()
        row.__getitem__ = lambda self, k: {
            "total_downtime_min": 0.0,
            "mttr_min": 30.0,
            "failure_count": 2.0,
            "total_count": 0,
            "avg_score": None,
            "total_kg": 0.0,
        }.get(k, 0.0)
        return row

    conn.fetchrow = AsyncMock(side_effect=_fetchrow_side_effect)
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = conn
    acquire_cm.__aexit__.return_value = False
    pool.acquire = MagicMock(return_value=acquire_cm)
    # Expose fetchrow directly so compute_kpi_snapshot takes the connection path
    pool.fetchrow = conn.fetchrow
    return pool


# ---------------------------------------------------------------------------
# Helper: request mock that disconnects after N checks
# ---------------------------------------------------------------------------

def _make_request(disconnect_after: int = 2) -> MagicMock:
    call_count = 0

    async def _is_disconnected() -> bool:
        nonlocal call_count
        call_count += 1
        return call_count > disconnect_after

    req = MagicMock()
    req.is_disconnected = _is_disconnected
    return req


# ---------------------------------------------------------------------------
# Test 1: kpi_stream generator yields kpi_update event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_generator_yields_kpi_update_event() -> None:
    """The kpi_stream async generator yields ≥ 1 event with event == 'kpi_update'
    and a data payload containing all 6 KPI keys."""
    from svc_api_gateway.routers.sse import kpi_stream

    pool = _make_kpi_pool()
    request = _make_request(disconnect_after=1)

    with patch("svc_api_gateway.routers.sse.asyncio.sleep", new=AsyncMock(return_value=None)):
        events = []
        async for event in kpi_stream(request, pool):
            events.append(event)
            break  # take only first event

    assert len(events) >= 1
    first = events[0]
    assert first["event"] == KPI_UPDATE_EVENT
    payload = json.loads(first["data"])
    assert "kpi" in payload
    assert KPI_KEYS.issubset(payload["kpi"].keys())


# ---------------------------------------------------------------------------
# Test 2: kpi_stream generator yields sse_heartbeat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_generator_yields_heartbeat_event() -> None:
    """The SSE generator also emits a heartbeat event with event == 'sse_heartbeat'.

    We force time.monotonic() to return a value far in the future so the heartbeat
    threshold is exceeded on the first iteration.
    """
    from svc_api_gateway.routers.sse import kpi_stream

    pool = _make_kpi_pool()
    request = _make_request(disconnect_after=3)

    # Mock time.monotonic: first call sets last_heartbeat = 0.0,
    # second call returns 9999.0 (forces heartbeat to fire immediately).
    monotonic_values = iter([0.0, 9999.0, 9999.0, 9999.0, 9999.0])

    with (
        patch("svc_api_gateway.routers.sse.asyncio.sleep", new=AsyncMock(return_value=None)),
        patch("svc_api_gateway.routers.sse.time.monotonic", side_effect=monotonic_values),
    ):
        events = []
        async for event in kpi_stream(request, pool):
            events.append(event)
            if any(e["event"] == HEARTBEAT_EVENT for e in events):
                break
            if len(events) >= 5:
                break

    event_names = [e["event"] for e in events]
    assert HEARTBEAT_EVENT in event_names, f"No heartbeat in {event_names}"


# ---------------------------------------------------------------------------
# Test 3: GET /v1/stream/kpi returns 200 text/event-stream (no-wait approach)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_endpoint_content_type_and_headers(app_with_mocks) -> None:
    """GET /v1/stream/kpi with a valid token → 200 + Content-Type: text/event-stream
    + X-Accel-Buffering: no (Pitfall 5 / T-10-03-03).

    Patches kpi_stream to be a finite async generator (yields 1 event then stops)
    so the HTTP connection closes quickly and the httpx client does not block.
    Combines content-type and X-Accel-Buffering checks in one stream request to
    avoid the sse-starlette AppStatus event-loop re-use issue across multiple tests.
    """
    import httpx
    from svc_api_gateway.security.jwt import create_token

    token = create_token(email="operator@mantis.it", role="operator")

    # Finite async generator: yields exactly 1 kpi_update event then stops.
    async def _bounded_kpi_stream(request, pool):
        yield {
            "event": "kpi_update",
            "data": json.dumps(
                {"kpi": {"oee": 95.0, "mttr": 25.0, "mtbf": 80.0,
                          "scrap_rate": 1.0, "throughput": 120.0, "downtime": 5.0}}
            ),
        }
        # generator finishes → EventSourceResponse closes the stream

    with patch("svc_api_gateway.routers.sse.kpi_stream", new=_bounded_kpi_stream):
        transport = httpx.ASGITransport(app=app_with_mocks)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            async def _get() -> tuple[int, str, str]:
                async with c.stream("GET", f"/v1/stream/kpi?token={token}") as resp:
                    status_code = resp.status_code
                    ct = resp.headers.get("content-type", "")
                    buffering = resp.headers.get("x-accel-buffering", "")
                    async for chunk in resp.aiter_text():
                        break  # read first chunk only
                    return status_code, ct, buffering

            status_code, ct, buffering = await asyncio.wait_for(_get(), timeout=10.0)

    assert status_code == 200
    assert "text/event-stream" in ct, f"Unexpected Content-Type: {ct}"
    assert buffering.lower() == "no", (
        f"X-Accel-Buffering must be 'no' (Pitfall 5), got: {buffering!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: GET /v1/stream/kpi without token → 401
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sse_endpoint_requires_auth(app_with_mocks) -> None:
    """GET /v1/stream/kpi without ?token= → 401 (not 500 or 200)."""
    import httpx

    transport = httpx.ASGITransport(app=app_with_mocks)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.get("/v1/stream/kpi")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Test 5: HITL-10 rate limit — unit: _check_alert_rate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alert_rate_limit_suppresses_13th_alert() -> None:
    """The alert rate limiter suppresses the 13th alert/hr per persona (HITL-10).

    Directly exercises _check_alert_rate:
        - First 12 calls → allowed (True)
        - 13th call → denied (False)
    """
    from svc_api_gateway.routers.sse import _check_alert_rate, _alert_rate_state

    principal = "rate_test_unique_persona@mantis.it"
    # Clear any prior state for this principal to isolate the test
    _alert_rate_state.pop(principal, None)

    now = 1_000_000.0  # arbitrary epoch within a 1-hour window

    for i in range(12):
        result = _check_alert_rate(principal, now + i)
        assert result is True, f"Alert {i + 1} should be allowed but was denied"

    # 13th alert — same window, must be denied
    result_13 = _check_alert_rate(principal, now + 12)
    assert result_13 is False, "13th alert in the same hour must be denied (HITL-10)"


# ---------------------------------------------------------------------------
# Test 6: alerts_stream generator emits rate_limit event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_alerts_generator_emits_rate_limit_event() -> None:
    """The alerts_stream generator emits a rate_limit event when the 13th alert arrives."""
    from svc_api_gateway.routers.sse import alerts_stream, _alert_rate_state

    principal = "rate_gen_test@mantis.it"
    _alert_rate_state.pop(principal, None)

    # Pre-fill 12 timestamps in the window so the next alert is denied
    now_ts = time.time()
    _alert_rate_state[principal] = deque(now_ts - i for i in range(12))

    # Build a mock pool that returns one "new" alert row per fetch
    pool = AsyncMock()
    conn = AsyncMock()

    def _fake_fetch(sql, *args):
        row = MagicMock()
        row.__getitem__ = lambda self, k: {
            "alert_id": "alert-xyz-001",
            "message": "ANOMALY_ALERT",
            "severity": "warning",
        }[k]
        return [row]

    conn.fetch = AsyncMock(side_effect=_fake_fetch)
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = conn
    acquire_cm.__aexit__.return_value = False
    pool.acquire = MagicMock(return_value=acquire_cm)

    request = _make_request(disconnect_after=3)

    with patch("svc_api_gateway.routers.sse.asyncio.sleep", new=AsyncMock(return_value=None)):
        events = []
        async for event in alerts_stream(request, pool, principal):
            events.append(event)
            if any(e["event"] == "rate_limit" for e in events):
                break
            if len(events) >= 10:
                break

    event_names = [e["event"] for e in events]
    assert "rate_limit" in event_names, (
        f"Expected a rate_limit event but got: {event_names}"
    )
    # alert_new must NOT be in events (all suppressed since window is already full)
    assert "alert_new" not in event_names, (
        f"alert_new must be suppressed when rate limit is exceeded; got: {event_names}"
    )


# Note: X-Accel-Buffering header test is combined into
# test_sse_endpoint_content_type_and_headers above to avoid sse-starlette
# AppStatus event-loop re-use issues across multiple test functions.
