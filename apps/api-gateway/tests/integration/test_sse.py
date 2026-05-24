"""Contract scaffold for SSE KPI stream endpoint.

Nyquist scaffold — all tests skipped until implementation in Plan 10-02.
Describes the acceptance contract the SSE endpoint MUST satisfy.

Architecture (10-CONTEXT.md, Streaming decision):
  - Endpoint: GET /v1/stream/kpi  (text/event-stream)
  - Events:   kpi_update — JSON payload {kpi: KpiSnapshot}
              sse_heartbeat — empty payload (every 30s)

THREAT: T-10-00b-01 (KPI SQL) is verified by test_kpi_queries.py; this file
focuses on the SSE generator + event shape contract only.

Note: asyncio.sleep is skipped-by-design here (scaffold); in implementation
tests use pytest-anyio with mocked asyncio.sleep to avoid waiting.
"""

from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# Expected KPI keys in a kpi_update payload (all 6 dashboard metrics)
# ---------------------------------------------------------------------------
KPI_KEYS = {"oee", "mttr", "mtbf", "scrap_rate", "throughput", "downtime"}

# SSE event name for live KPI pushes (10-UI-SPEC SSE Contratto Streaming)
KPI_UPDATE_EVENT = "kpi_update"
HEARTBEAT_EVENT = "sse_heartbeat"


# ---------------------------------------------------------------------------
# Generator yields kpi_update event with correct shape
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="impl in 10-02 — SSE router + kpi stream not yet created")
@pytest.mark.asyncio
async def test_sse_generator_yields_kpi_update_event(app_with_mocks) -> None:
    """The kpi_stream async generator yields ≥ 1 ServerSentEvent with:

        event == "kpi_update"
        data  == JSON object containing all 6 KPI keys

    asyncio.sleep is mocked to avoid wall-clock delay.
    The pool is mocked to return a canned KPI row.
    """
    # Implementation will expose a kpi_stream() generator from the SSE router module.
    # from svc_api_gateway.routers.sse import kpi_stream
    #
    # events = []
    # async for sse_event in kpi_stream(pool=app_with_mocks.state.pool):
    #     events.append(sse_event)
    #     break  # first event is enough
    #
    # assert len(events) >= 1
    # first = events[0]
    # assert first.event == KPI_UPDATE_EVENT
    # payload = json.loads(first.data)
    # assert "kpi" in payload
    # assert KPI_KEYS.issubset(payload["kpi"].keys())

    pytest.skip("impl in 10-02 — SSE router + kpi stream not yet created")


@pytest.mark.skip(reason="impl in 10-02 — SSE router + kpi stream not yet created")
@pytest.mark.asyncio
async def test_sse_generator_yields_heartbeat_event(app_with_mocks) -> None:
    """The SSE generator also emits a heartbeat event with event == 'sse_heartbeat'.

    Heartbeat payload is empty or '{}' (10-UI-SPEC SSE Contratto).
    """
    pytest.skip("impl in 10-02 — SSE router + kpi stream not yet created")


# ---------------------------------------------------------------------------
# HTTP endpoint: GET /v1/stream/kpi returns text/event-stream
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="impl in 10-02 — SSE router not yet created")
@pytest.mark.asyncio
async def test_sse_endpoint_content_type(client) -> None:
    """GET /v1/stream/kpi responds with Content-Type: text/event-stream.

    Uses a short-lived connection (stream consumed until first chunk).
    """
    # In implementation:
    # async with client.stream("GET", "/v1/stream/kpi", headers={"Authorization": "Bearer <jwt>"}) as resp:
    #     assert resp.status_code == 200
    #     assert "text/event-stream" in resp.headers.get("content-type", "")
    pytest.skip("impl in 10-02 — SSE router not yet created")


@pytest.mark.skip(reason="impl in 10-02 — SSE router not yet created")
@pytest.mark.asyncio
async def test_sse_endpoint_requires_auth(client) -> None:
    """GET /v1/stream/kpi without Authorization header → 401 (not 500 or 200)."""
    response = await client.get("/v1/stream/kpi")
    assert response.status_code == 401
