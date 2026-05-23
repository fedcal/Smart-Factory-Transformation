"""Local pytest fixtures for the anomaly-detector test suite (Plan 06-06).

Provides mocks for the agent's three injected collaborators:

* ``mock_pool`` — AsyncMock simulating an asyncpg.Pool whose acquire() ctx
  manager yields a connection with ``fetchval`` / ``fetchrow`` / ``execute``
  AsyncMocks. Mirrors ``packages/sft-agents/tests/conftest.py`` shape so the
  RateLimiter under test sees the contract it expects.
* ``mock_audit_writer`` — AsyncMock with a single ``write(AuditRecord)``
  coroutine; tests inspect ``.call_args_list`` to assert decision / action_type.
* ``mock_query_tool`` — AsyncMock with ``_arun`` returning a pandas.DataFrame.
  Each test sets the per-asset return mapping via ``.side_effect``.

The fixtures are pure-Python — no Docker / testcontainers required.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_pool() -> AsyncMock:
    """Return an AsyncMock simulating an asyncpg.Pool (acquire context manager)."""
    conn = AsyncMock()
    conn.fetchval = AsyncMock(return_value=0)
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock(return_value="INSERT 0 1")

    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__ = AsyncMock(return_value=conn)
    acquire_ctx.__aexit__ = AsyncMock(return_value=False)

    pool = AsyncMock()
    pool.acquire = MagicMock(return_value=acquire_ctx)
    return pool


@pytest.fixture
def mock_audit_writer() -> AsyncMock:
    """Return an AsyncMock with an awaitable ``write(record)`` method."""
    writer = AsyncMock()
    writer.write = AsyncMock(return_value=None)
    return writer


@pytest.fixture
def mock_query_tool() -> AsyncMock:
    """Return an AsyncMock with an awaitable ``_arun(...)`` method.

    Tests override the return value (or ``.side_effect``) per case.
    """
    tool = AsyncMock()
    tool._arun = AsyncMock(return_value=None)
    return tool


@pytest.fixture
def fixed_count_pool(mock_pool: AsyncMock) -> Any:
    """Variant: pool whose ``fetchval`` always returns 0 (no prior alerts).

    The agent's RateLimiter calls ``conn.fetchval(SQL, agent_id, action_type, ts)``;
    returning ``0`` keeps every alert below the 12/h cap.
    """
    mock_pool.acquire.return_value.__aenter__.return_value.fetchval.return_value = 0
    return mock_pool
