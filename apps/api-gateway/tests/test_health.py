"""Unit tests for the /v1/health endpoint (Plan 04-07 Task 1).

Validates:
    1. healthy → 200 with {"status":"ok","dependencies":{"pg":"up","nats":"up"}}
    2. pg pool failure → dependencies.pg="down" (still 200 — liveness only, not readiness)
    3. NATS disconnected → dependencies.nats="down"
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok_when_dependencies_up(client) -> None:
    response = await client.get("/v1/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["dependencies"] == {"pg": "up", "nats": "up"}


@pytest.mark.asyncio
async def test_health_marks_pg_down_when_pool_raises(client, app_with_mocks) -> None:
    # Force the pool acquire to raise — health route translates to pg='down'.
    pool = app_with_mocks.state.pool
    pool._test_conn.execute = AsyncMock(side_effect=RuntimeError("pg connection lost"))
    response = await client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["dependencies"]["pg"] == "down"
    assert body["dependencies"]["nats"] == "up"
    assert body["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_marks_nats_down_when_disconnected(client, app_with_mocks) -> None:
    app_with_mocks.state.nats_publisher._nc.is_connected = False
    response = await client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["dependencies"]["nats"] == "down"
    assert body["dependencies"]["pg"] == "up"
    assert body["status"] == "degraded"
