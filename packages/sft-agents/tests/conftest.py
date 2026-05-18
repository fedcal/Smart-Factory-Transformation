"""Shared pytest fixtures for sft-agents test suite (Phase 4, Plan 04-01 Task 1).

Provides:
    frozen_dt          — deterministic UTC datetime (2026-05-18T00:00:00Z)
    mock_pool          — AsyncMock simulating asyncpg.Pool (acquire ctx mgr + fetchrow/execute)
    mock_nats_js       — AsyncMock simulating NATS JetStream context (publish AsyncMock)
    mock_llm           — FakeListChatModel from langchain_core fake_chat_models
    mock_checkpointer  — AsyncMock with aget_tuple, aput, setup AsyncMock methods

All fixtures are Phase 4 contract: they materialize the symbol shape every Wave-2+
test stub will require (deterministic seed, no I/O, ABC-compliant shapes).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

UTC = timezone.utc


def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest markers at package level (mirrors root conftest)."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests requiring docker compose / testcontainers",
    )
    config.addinivalue_line(
        "markers",
        "load: marks long-running load tests",
    )


# ---------------------------------------------------------------------------
# Deterministic clock
# ---------------------------------------------------------------------------


@pytest.fixture
def frozen_dt() -> datetime:
    """Return a fixed UTC tz-aware datetime for deterministic tests.

    Anchored at 2026-05-18T00:00:00Z (Phase 4 kickoff date).
    """
    return datetime(2026, 5, 18, tzinfo=UTC)


# ---------------------------------------------------------------------------
# asyncpg.Pool mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_pool() -> AsyncMock:
    """Return an AsyncMock simulating an asyncpg.Pool.

    The pool exposes:
      - acquire() returning an async-context-manager whose __aenter__ yields a
        connection AsyncMock with fetchrow / fetch / execute / executemany /
        transaction methods.
      - close() / terminate() AsyncMocks.

    Tests can pre-program return values via e.g.
        mock_pool.acquire.return_value.__aenter__.return_value.fetchrow.return_value = {...}
    """
    conn = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    conn.executemany = AsyncMock(return_value=None)

    # transaction() returns an async context manager (no-op commit)
    txn = AsyncMock()
    txn.__aenter__ = AsyncMock(return_value=txn)
    txn.__aexit__ = AsyncMock(return_value=False)
    conn.transaction = MagicMock(return_value=txn)

    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)

    pool = AsyncMock()
    pool.acquire = MagicMock(return_value=acquire_ctx)
    pool.close = AsyncMock(return_value=None)
    pool.terminate = MagicMock(return_value=None)
    pool.fetchrow = AsyncMock(return_value=None)
    pool.fetch = AsyncMock(return_value=[])
    pool.execute = AsyncMock(return_value="INSERT 0 1")
    return pool


# ---------------------------------------------------------------------------
# NATS JetStream mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_nats_js() -> AsyncMock:
    """Return an AsyncMock simulating a NATS JetStream context.

    Exposes:
      - publish(subject, payload) AsyncMock returning an Ack stub
      - add_stream / update_stream AsyncMocks (for bootstrap tests)
      - subscribe / pull_subscribe AsyncMocks
    """
    js = AsyncMock()
    ack = MagicMock(stream="AUDIT_STREAM", seq=1, duplicate=False)
    js.publish = AsyncMock(return_value=ack)
    js.add_stream = AsyncMock()
    js.update_stream = AsyncMock()
    js.stream_info = AsyncMock()
    js.subscribe = AsyncMock()
    js.pull_subscribe = AsyncMock()
    return js


# ---------------------------------------------------------------------------
# LLM mock (FakeListChatModel from langchain_core)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm():
    """Return a FakeListChatModel from langchain_core fake_chat_models.

    Deterministic — cycles through the canned responses on each `.invoke()` call.
    Tests can override `.responses` attribute for case-specific outputs.
    """
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    return FakeListChatModel(
        responses=[
            "ack",
            '{"cluster": "ops", "confidence": 0.95}',
            '{"decision": "approve", "motivation": "test"}',
        ]
    )


# ---------------------------------------------------------------------------
# LangGraph checkpointer mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_checkpointer() -> AsyncMock:
    """Return an AsyncMock simulating a langgraph-checkpoint AsyncPostgresSaver.

    Exposes:
      - aget_tuple(config) AsyncMock returning None (no prior checkpoint by default)
      - aput(config, checkpoint, metadata, new_versions) AsyncMock returning config
      - aput_writes(config, writes, task_id) AsyncMock
      - alist(config) returning empty async iterator
      - setup() AsyncMock (idempotent DDL bootstrap)
    """
    cp = AsyncMock()
    cp.aget_tuple = AsyncMock(return_value=None)
    cp.aput = AsyncMock(return_value={"configurable": {"thread_id": "test"}})
    cp.aput_writes = AsyncMock(return_value=None)
    cp.setup = AsyncMock(return_value=None)

    async def _alist(_cfg, **_kw):
        if False:
            yield None
        return

    cp.alist = _alist
    return cp
