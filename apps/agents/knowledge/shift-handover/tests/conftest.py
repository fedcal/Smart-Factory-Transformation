"""Conftest for ShiftHandover agent tests (Phase 8, Wave 0 scaffold).

Provides shared fixtures mirroring the rca-specialist conftest pattern:
- AsyncMock asyncpg pool and connection
- AsyncMock audit_writer fixture
- BGE_M3_DEVICE=cpu env variable for test isolation

Real fixtures (cross-cluster query harness, dual-interrupt simulation) land
with plan 08-04 (shift-handover implementation).
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _set_bge_m3_cpu_device(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force BGE-M3 to CPU mode in all ShiftHandover tests."""
    monkeypatch.setenv("BGE_M3_DEVICE", "cpu")


@pytest.fixture()
def mock_pool() -> MagicMock:
    """AsyncMock asyncpg connection pool.

    Provides an acquire() context manager that returns a mock asyncpg connection.
    Pattern mirrors apps/agents/maintenance/rca-specialist/tests/conftest.py.
    """
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=conn), __aexit__=AsyncMock(return_value=None)))
    pool.fetchrow = AsyncMock(return_value=None)
    pool.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock()
    return pool


@pytest.fixture()
def mock_audit_writer() -> MagicMock:
    """AsyncMock audit writer fixture.

    Returns a mock with an async write() method, matching the AuditWriter interface
    from packages/sft-agents/src/sft_agents/models/audit.py.
    """
    writer = MagicMock()
    writer.write = AsyncMock()
    return writer
