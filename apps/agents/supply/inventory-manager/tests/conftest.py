"""Conftest for InventoryManager agent tests (Phase 9, Wave 0 scaffold).

Provides shared fixtures mirroring the shift-handover conftest pattern:
- AsyncMock asyncpg pool and connection
- AsyncMock audit_writer fixture
- Patched interrupt() that raises GraphInterrupt on first call and returns
  payload on subsequent calls (NOT a MagicMock — per WR-01 lesson from Phase 8).

Real fixtures (scm schema query harness, reorder simulation) land
with plan 09-02 (inventory-manager implementation).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture()
def mock_pool() -> MagicMock:
    """AsyncMock asyncpg connection pool.

    Provides an acquire() context manager that returns a mock asyncpg connection.
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

    Returns a mock with an async write() method, matching the AuditWriter interface
    from packages/sft-agents/src/sft_agents/models/audit.py.
    """
    writer = MagicMock()
    writer.write = AsyncMock()
    return writer


@pytest.fixture()
def make_interrupt_fn():
    """Factory fixture: returns a callable that mimics LangGraph interrupt().

    On the FIRST call: raises a GraphInterrupt-like exception (simulating the
    initial node execution that pauses for HITL approval).
    On subsequent calls: returns the provided payload dict (simulating resume).

    NOT a MagicMock — Phase 8 WR-01: MagicMock silently swallows the raise
    behaviour and causes tests to pass without validating the HITL contract.

    Usage in tests:
        interrupt_fn = make_interrupt_fn(resume_payload={"approved": True, ...})
        with patch("scm_inventory_manager.agent.interrupt", interrupt_fn):
            ...
    """
    def factory(resume_payload: dict[str, Any] | None = None) -> Any:
        """Build a callable that raises on first call, returns resume_payload after."""
        _payload = resume_payload or {"approved": True, "approver_id": "supervisor-001"}
        call_count: list[int] = [0]

        def _interrupt(value: Any) -> Any:
            call_count[0] += 1
            if call_count[0] == 1:
                # Deferred import: GraphInterrupt lives in langgraph — not available
                # until Wave 2 implementation; use a plain Exception stand-in for scaffold.
                try:
                    from langgraph.errors import GraphInterrupt  # type: ignore[import]
                    raise GraphInterrupt(value)
                except ImportError:
                    raise RuntimeError(
                        "GraphInterrupt(interrupt-then-audit scaffold): "
                        f"value={value!r}"
                    )
            return _payload

        return _interrupt

    return factory
