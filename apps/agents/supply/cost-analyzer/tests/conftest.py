"""Conftest for CostAnalyzer agent tests (Phase 9, Wave 0 scaffold).

Provides shared fixtures mirroring the shift-handover conftest pattern:
- AsyncMock asyncpg pool and connection (read-only: CostAnalyzer only reads audit.actions)
- AsyncMock audit_writer fixture

CostAnalyzer is AUTONOMOUS (no HITL) — no interrupt fixture needed.
It writes Decision.AUTO audit rows without calling interrupt().

Real fixtures (mock audit.actions reader, OEPV config helpers) land
with plan 09-04 (cost-analyzer implementation).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture()
def mock_pool() -> MagicMock:
    """AsyncMock asyncpg connection pool (read-only for CostAnalyzer).

    CostAnalyzer only reads from audit.actions — no scm.* writes.
    Pattern mirrors apps/agents/knowledge/shift-handover/tests/conftest.py.
    """
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(
        return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=conn),
            __aexit__=AsyncMock(return_value=None),
        )
    )
    pool.fetchrow = AsyncMock(return_value=None)
    pool.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.execute = AsyncMock()
    return pool


@pytest.fixture()
def mock_audit_writer() -> MagicMock:
    """AsyncMock audit writer fixture.

    Returns a mock with an async write() method, matching the AuditWriter interface.
    CostAnalyzer uses this to write Decision.AUTO cost reports (no HITL).
    """
    writer = MagicMock()
    writer.write = AsyncMock()
    return writer
