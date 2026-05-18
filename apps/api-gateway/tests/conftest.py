"""Shared pytest fixtures for svc-api-gateway unit tests.

Provides:
    app_with_mocks      — FastAPI app with state populated by AsyncMock dependencies
                          (no lifespan, no real PG/NATS)
    client              — httpx.AsyncClient wired to ASGITransport(app)
    mock_pool           — AsyncMock asyncpg.Pool with acquire() context manager
    mock_audit_writer   — AsyncMock AuditWriter (only `.write` consumed)
    mock_queue_writer   — AsyncMock ApprovalQueueWriter
    mock_supervisor_graph — AsyncMock with `.ainvoke`
    mock_checkpointer   — AsyncMock with `.aget_tuple`
    mock_nats_publisher — AsyncMock publisher (publish_approval_*, drain, _nc.is_connected)

Integration fixtures (tests/integration owned by Plan 04-07 Task 3) live at the
repo root tests/conftest.py — this file is unit-test only.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_pool() -> AsyncMock:
    """AsyncMock asyncpg.Pool with acquire() returning an async-context-manager."""
    pool = AsyncMock()
    conn = AsyncMock()
    # conn.execute / fetch / fetchrow are AsyncMocks by default
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = conn
    acquire_cm.__aexit__.return_value = False
    pool.acquire = MagicMock(return_value=acquire_cm)
    pool._test_conn = conn  # expose for assertions
    return pool


@pytest.fixture
def mock_audit_writer() -> AsyncMock:
    writer = AsyncMock()
    writer.write = AsyncMock(return_value=None)
    return writer


@pytest.fixture
def mock_queue_writer() -> AsyncMock:
    qw = AsyncMock()
    qw.insert = AsyncMock(return_value=None)
    qw.update_decision = AsyncMock(return_value=None)
    return qw


@pytest.fixture
def mock_supervisor_graph() -> AsyncMock:
    graph = AsyncMock()
    graph.ainvoke = AsyncMock(return_value={"messages": [], "proposed_actions": []})
    return graph


@pytest.fixture
def mock_checkpointer() -> AsyncMock:
    cp = AsyncMock()
    cp.aget_tuple = AsyncMock(return_value=None)
    return cp


@pytest.fixture
def mock_nats_publisher() -> AsyncMock:
    pub = AsyncMock()
    pub.publish_approval_new = AsyncMock(return_value=None)
    pub.publish_approval_resolved = AsyncMock(return_value=None)
    pub.publish_audit = AsyncMock(return_value=None)
    pub.drain = AsyncMock(return_value=None)
    # _nc.is_connected for /health
    nc = MagicMock()
    nc.is_connected = True
    pub._nc = nc
    return pub


@pytest.fixture
def app_with_mocks(
    mock_pool: AsyncMock,
    mock_audit_writer: AsyncMock,
    mock_queue_writer: AsyncMock,
    mock_supervisor_graph: AsyncMock,
    mock_checkpointer: AsyncMock,
    mock_nats_publisher: AsyncMock,
) -> Any:
    """Return a FastAPI app instance with state attrs populated for unit tests.

    Lifespan is NOT executed — we attach mock objects directly to ``app.state``
    so route dependencies resolve without needing a real PG/NATS connection.
    """
    from svc_api_gateway.main import build_app  # local import — module-time test isolation

    app = build_app()
    app.state.pool = mock_pool
    app.state.audit_writer = mock_audit_writer
    app.state.queue_writer = mock_queue_writer
    app.state.supervisor_graph = mock_supervisor_graph
    app.state.checkpointer = mock_checkpointer
    app.state.nats_publisher = mock_nats_publisher
    # Idempotency cache must exist (cleared between tests via reset_idempotency_cache fixture if needed)
    from svc_api_gateway.idempotency import IdempotencyCache  # local import
    app.state.idempotency_cache = IdempotencyCache(ttl_seconds=300)
    return app


@pytest.fixture
async def client(app_with_mocks: Any):
    """httpx.AsyncClient wired to ASGITransport(app)."""
    import httpx

    transport = httpx.ASGITransport(app=app_with_mocks)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
