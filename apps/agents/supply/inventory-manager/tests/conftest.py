"""Conftest for InventoryManager agent tests (Phase 9, Wave 0 scaffold).

Provides shared fixtures mirroring the shift-handover conftest pattern:
- AsyncMock asyncpg pool and connection
- AsyncMock audit_writer fixture
- Patched interrupt() that raises GraphInterrupt on first call and returns
  payload on subsequent calls (NOT a MagicMock — per WR-01 lesson from Phase 8).

WR-03 (Phase 9 review): mock_pool now returns one SKU-below-threshold row by
default, so that the HITL contracts (draft/signoff audit writes) are exercised.
Tests that want the empty-rows path should use make_empty_pool() directly.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Synthetic inventory row — SKU below reorder threshold to trigger HITL path
# ---------------------------------------------------------------------------

_BELOW_THRESHOLD_ROW: dict[str, Any] = {
    "sku_id": "SKU-FAB-JERSEY-BLU",
    "quantity": Decimal("310.000"),       # 310 < reorder_point 500 → below threshold
    "ts": None,                           # not used by check_reorder
    "reorder_point": Decimal("500.00"),
    "reorder_qty": Decimal("1500.00"),
    "unit_cost_eur": Decimal("8.4000"),
    "lead_time_days": 5,
}


def _make_pool_with_rows(rows: list[dict[str, Any]]) -> MagicMock:
    """Build a mock asyncpg pool whose connection.fetch() returns `rows`.

    Used by mock_pool (HITL path, rows non-empty) and make_empty_pool (WR-03 path).
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
    pool.fetch = AsyncMock(return_value=rows)
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=rows)
    conn.execute = AsyncMock()
    return pool


@pytest.fixture()
def mock_pool() -> MagicMock:
    """AsyncMock asyncpg connection pool with one below-threshold SKU row.

    Returns a pool whose connection.fetch() yields one synthetic inventory row
    (SKU-FAB-JERSEY-BLU, qty=310, reorder_point=500) so that the HITL path is
    triggered and audit contracts (DRAFT/SIGNOFF writes) can be verified.

    WR-03: pool must return non-empty rows for the HITL contracts to fire.
    Tests that want the empty-rows early-exit path should use make_empty_pool.
    """
    return _make_pool_with_rows([_BELOW_THRESHOLD_ROW])


@pytest.fixture()
def make_empty_pool() -> MagicMock:
    """AsyncMock asyncpg connection pool that returns no rows (empty fetch).

    Use this fixture when testing the WR-03 early-exit path: inventory_manager
    must return {reorder_recommendation: None, reorder_alert: None} and emit
    a warning log when the repository returns zero rows, without firing HITL.
    """
    return _make_pool_with_rows([])


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
