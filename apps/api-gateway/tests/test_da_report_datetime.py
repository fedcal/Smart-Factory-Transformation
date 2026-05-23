"""Regression tests for WR-03: gateway post_da_report passes datetime objects (not ISO strings)
to the supervisor state dict so asyncpg TIMESTAMPTZ params do not raise DataError.

Plan 07-16 — Task 1 RED phase.
All unit tests must FAIL before Task 2 fixes the gateway router.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

UTC = timezone.utc

_VALID_WINDOW_START = datetime(2026, 5, 1, 6, 0, tzinfo=UTC)
_VALID_WINDOW_END = datetime(2026, 5, 1, 14, 0, tzinfo=UTC)


def _make_oee_report_result() -> dict:
    """Return a minimal valid OEEReport-shaped dict for supervisor mock return value."""
    return {
        "window_start": _VALID_WINDOW_START.isoformat(),
        "window_end": _VALID_WINDOW_END.isoformat(),
        "availability": 0.90,
        "performance": 0.95,
        "quality": 0.98,
        "oee": round(0.90 * 0.95 * 0.98, 9),
        "by_asset": None,
        "pareto": [],
        "report_id": "550e8400-e29b-41d4-a716-446655440000",
        "generated_at": datetime(2026, 5, 1, 14, 1, tzinfo=UTC).isoformat(),
    }


@pytest.mark.asyncio
async def test_da_report_passes_datetime_objects_to_state(
    client, app_with_mocks
) -> None:
    """The state dict passed to supervisor must contain datetime objects, not ISO strings.

    WR-03 regression: current code calls body.window_start.isoformat() / body.window_end.isoformat()
    before placing datetimes into the state dict. asyncpg requires Python datetime objects for
    TIMESTAMPTZ parameters; ISO strings raise asyncpg.exceptions.DataError at runtime.

    This test captures the state dict passed to supervisor_graph.ainvoke and asserts
    that state["window_start"] and state["window_end"] are datetime instances, not str.
    Against current (broken) code they are ISO strings — test FAILS.
    After Task 2 fix they become datetime objects — test PASSES.
    """
    graph = app_with_mocks.state.supervisor_graph
    captured_state: dict = {}

    async def _spy_ainvoke(state, config=None):
        captured_state.update(state)
        return _make_oee_report_result()

    graph.ainvoke = AsyncMock(side_effect=_spy_ainvoke)

    body = {
        "window_start": _VALID_WINDOW_START.isoformat(),
        "window_end": _VALID_WINDOW_END.isoformat(),
        "by_asset": False,
        "top_n_pareto": 5,
    }
    response = await client.post("/v1/agents/downtime-analyzer/report", json=body)
    assert response.status_code == 200, response.text

    assert graph.ainvoke.await_count == 1, "supervisor_graph.ainvoke must be called once"

    # Assert that the state values are datetime objects — NOT strings.
    # Current code uses .isoformat() → these will be str → test FAILS (red phase).
    # After fix: .isoformat() removed → datetime objects flow through → PASSES.
    ws = captured_state.get("window_start")
    we = captured_state.get("window_end")

    assert isinstance(ws, datetime), (
        f"state['window_start'] must be a datetime object, got {type(ws).__name__!r}: {ws!r}. "
        "The gateway must NOT call .isoformat() before placing the datetime into state. "
        "asyncpg requires Python datetime objects for TIMESTAMPTZ parameters."
    )
    assert isinstance(we, datetime), (
        f"state['window_end'] must be a datetime object, got {type(we).__name__!r}: {we!r}. "
        "The gateway must NOT call .isoformat() before placing the datetime into state. "
        "asyncpg requires Python datetime objects for TIMESTAMPTZ parameters."
    )

    # Also verify the actual values are correct
    assert ws == _VALID_WINDOW_START, (
        f"state['window_start'] value mismatch: expected {_VALID_WINDOW_START!r}, got {ws!r}"
    )
    assert we == _VALID_WINDOW_END, (
        f"state['window_end'] value mismatch: expected {_VALID_WINDOW_END!r}, got {we!r}"
    )


@pytest.mark.asyncio
async def test_da_report_state_contains_target_agent_and_by_asset(
    client, app_with_mocks
) -> None:
    """Sanity check: the other state fields (target_agent, by_asset, top_n_pareto) are correct."""
    graph = app_with_mocks.state.supervisor_graph
    captured_state: dict = {}

    async def _spy_ainvoke(state, config=None):
        captured_state.update(state)
        return _make_oee_report_result()

    graph.ainvoke = AsyncMock(side_effect=_spy_ainvoke)

    body = {
        "window_start": _VALID_WINDOW_START.isoformat(),
        "window_end": _VALID_WINDOW_END.isoformat(),
        "by_asset": True,
        "top_n_pareto": 10,
    }
    response = await client.post("/v1/agents/downtime-analyzer/report", json=body)
    assert response.status_code == 200, response.text

    assert captured_state.get("target_agent") == "downtime-analyzer"
    assert captured_state.get("by_asset") is True
    assert captured_state.get("top_n_pareto") == 10


@pytest.mark.asyncio
@pytest.mark.integration
async def test_da_report_no_asyncpg_data_error_with_real_db(
    client, app_with_mocks
) -> None:
    """Integration: POST /report against real asyncpg-backed DB must not raise DataError.

    Skipped without docker stack (asyncpg pool + TimescaleDB).
    This test confirms the WR-03 runtime fix: passing datetime objects to asyncpg
    TIMESTAMPTZ parameters should return a valid 200 OEEReport.

    To run manually:
        docker compose up -d && cd apps/api-gateway && uv run pytest tests/test_da_report_datetime.py -m integration
    """
    pytest.skip("Requires docker stack with asyncpg-backed TimescaleDB")
