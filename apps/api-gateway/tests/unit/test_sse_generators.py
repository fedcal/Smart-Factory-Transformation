"""Unit tests for SSE stream generators — CR-01 SQL injection fix verification.

Verifies that approvals_stream and alerts_stream pass a Python list as the
$1 parameter to asyncpg (parameterised != ALL($1::text[])) and never interpolate
IDs via f-string / string concatenation.

Plan: 10-03 (SRV-02, SRV-04) — CR-01 fix.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch
import pytest


# ---------------------------------------------------------------------------
# Helpers — build a minimal asyncpg pool mock
# ---------------------------------------------------------------------------

def _build_pool(fetch_return: list[dict]) -> AsyncMock:
    """Return a mock pool whose conn.fetch() returns fetch_return."""
    pool = AsyncMock()
    conn = AsyncMock()
    # asyncpg record mock: support row["key"] access
    rows = []
    for item in fetch_return:
        row = MagicMock()
        row.__getitem__ = MagicMock(side_effect=lambda k, _d=item: _d[k])
        rows.append(row)
    conn.fetch = AsyncMock(return_value=rows)
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = conn
    acquire_cm.__aexit__.return_value = False
    pool.acquire = MagicMock(return_value=acquire_cm)
    pool._test_conn = conn
    return pool


def _make_request(disconnected_after: int = 1) -> MagicMock:
    """Return a mock Request that reports is_disconnected() after N calls."""
    req = MagicMock()
    call_count = [0]

    async def _is_disconnected() -> bool:
        call_count[0] += 1
        return call_count[0] > disconnected_after

    req.is_disconnected = _is_disconnected
    return req


# ---------------------------------------------------------------------------
# CR-01: approvals_stream — parameterised != ALL($1::text[])
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approvals_stream_uses_parameterised_query_not_string_interpolation() -> None:
    """CR-01: approvals_stream must pass seen_ids as a list parameter ($1),
    never concatenate IDs into the SQL string."""
    from svc_api_gateway.routers.sse import approvals_stream

    pool = _build_pool([])  # no rows — just checking the SQL call
    req = _make_request(disconnected_after=1)

    # Consume one iteration then disconnect
    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        gen = approvals_stream(req, pool)
        events = []
        async for event in gen:
            events.append(event)

    conn = pool._test_conn
    # fetch() must have been called
    assert conn.fetch.called, "conn.fetch() was never called"

    # The pending-approvals query (which filters seen_ids) must use parameterised form.
    # The resolved-approvals query uses a fixed IN ('auto', 'logged', 'rolled_back') —
    # those are literal constants, not user-derived IDs, so no parameter needed there.
    pending_calls = [
        c for c in conn.fetch.call_args_list
        if "hitl_operator" in c.args[0]
    ]
    assert pending_calls, "Expected at least one fetch() call for pending approvals"

    for c in pending_calls:
        sql: str = c.args[0]
        # Must contain parameterised placeholder, not raw f-string interpolation
        assert "$1" in sql, (
            f"SQL must use $1 parameter, got: {sql!r}"
        )
        assert "NOT IN" not in sql, (
            f"SQL must not use NOT IN string concatenation, got: {sql!r}"
        )
        # The second argument must be a list (the seen_ids list)
        if len(c.args) > 1:
            assert isinstance(c.args[1], list), (
                f"Second argument to fetch() must be a list, got: {type(c.args[1])}"
            )


@pytest.mark.asyncio
async def test_alerts_stream_uses_parameterised_query_not_string_interpolation() -> None:
    """CR-01: alerts_stream must pass seen_ids as a list parameter ($1),
    never concatenate IDs into the SQL string."""
    from svc_api_gateway.routers.sse import alerts_stream

    pool = _build_pool([])
    req = _make_request(disconnected_after=1)

    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        gen = alerts_stream(req, pool, principal_sub="operator@mantis.it")
        async for _ in gen:
            pass

    conn = pool._test_conn
    assert conn.fetch.called, "conn.fetch() was never called"

    # The alerts query filters seen_ids via parameterised form.
    alert_calls = [
        c for c in conn.fetch.call_args_list
        if "ANOMALY_ALERT" in c.args[0]
    ]
    assert alert_calls, "Expected at least one fetch() call for alerts"

    for c in alert_calls:
        sql: str = c.args[0]
        assert "$1" in sql, (
            f"SQL must use $1 parameter, got: {sql!r}"
        )
        assert "NOT IN" not in sql, (
            f"SQL must not use NOT IN string concatenation, got: {sql!r}"
        )
        if len(c.args) > 1:
            assert isinstance(c.args[1], list), (
                f"Second argument to fetch() must be a list, got: {type(c.args[1])}"
            )


@pytest.mark.asyncio
async def test_approvals_stream_passes_empty_list_when_no_seen_ids() -> None:
    """CR-01: when seen_ids is empty, the parameter must be an empty list [],
    not a fallback 'SELECT NULL WHERE false' string embedded in SQL."""
    from svc_api_gateway.routers.sse import approvals_stream

    pool = _build_pool([])
    req = _make_request(disconnected_after=1)

    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        gen = approvals_stream(req, pool)
        async for _ in gen:
            pass

    conn = pool._test_conn
    pending_calls = [c for c in conn.fetch.call_args_list if "hitl_operator" in c.args[0]]
    for c in pending_calls:
        if len(c.args) > 1:
            assert c.args[1] == [], (
                f"Empty seen_ids must produce empty list [], got: {c.args[1]!r}"
            )


@pytest.mark.asyncio
async def test_alerts_stream_passes_empty_list_when_no_seen_ids() -> None:
    """CR-01: when seen_ids is empty, alerts_stream passes [] as parameter."""
    from svc_api_gateway.routers.sse import alerts_stream

    pool = _build_pool([])
    req = _make_request(disconnected_after=1)

    with patch("asyncio.sleep", new=AsyncMock(return_value=None)):
        gen = alerts_stream(req, pool, principal_sub="operator@mantis.it")
        async for _ in gen:
            pass

    conn = pool._test_conn
    alert_calls = [c for c in conn.fetch.call_args_list if "ANOMALY_ALERT" in c.args[0]]
    for c in alert_calls:
        if len(c.args) > 1:
            assert c.args[1] == [], (
                f"Empty seen_ids must produce empty list [], got: {c.args[1]!r}"
            )
