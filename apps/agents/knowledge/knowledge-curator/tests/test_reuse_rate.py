"""Contract tests for KnowledgeCurator reuse-rate KPI (D-KC-03).

CONTRACT: Reuse-rate KPI = distinct_documents_cited / total_indexed_documents
over a rolling window, computed from source_uri citations in audit.actions.

Computed from asyncpg query against audit.actions:
  - distinct_cited: COUNT(DISTINCT evidence_panel->>'source_uri') in the rolling window
  - total_indexed: COUNT from the document index (Qdrant or ingest_state table)

Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
(Wave 2-3 plan: 08-06)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from trn_knowledge_curator.reuse_rate import compute_reuse_rate


# Reference window for all tests (deterministic).
_NOW = datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc)
_WINDOW_DAYS = 30
_WINDOW_START = _NOW - timedelta(days=_WINDOW_DAYS)
_WINDOW_END = _NOW


def _make_mock_pool(distinct_cited: int, total_indexed: int) -> MagicMock:
    """Return a mock asyncpg pool whose fetchrow returns the given values."""
    pool = MagicMock()
    row = {"distinct_cited": distinct_cited, "total_indexed": total_indexed}
    pool.fetchrow = AsyncMock(return_value=row)
    return pool


# ---------------------------------------------------------------------------
# Contract 1: Basic reuse-rate computation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reuse_rate_distinct_cited_over_total_indexed() -> None:
    """compute_reuse_rate returns distinct_cited / total_indexed from mock asyncpg.

    D-KC-03: reuse_rate = distinct_documents_cited / total_indexed_documents.

    Given mock pool.fetchrow returning (distinct_cited=3, total_indexed=10),
    compute_reuse_rate() must return 0.3 (3/10).

    Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
    """
    pool = _make_mock_pool(distinct_cited=3, total_indexed=10)
    rate = await compute_reuse_rate(pool, _WINDOW_START, _WINDOW_END)
    assert rate == pytest.approx(0.3), (
        f"reuse_rate(distinct=3, total=10) must be 0.3, got {rate}"
    )


@pytest.mark.asyncio
async def test_reuse_rate_zero_indexed_returns_zero() -> None:
    """compute_reuse_rate returns 0.0 when total_indexed == 0 (no divide-by-zero).

    D-KC-03: guard against division by zero when no documents are indexed yet.

    Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
    """
    pool = _make_mock_pool(distinct_cited=0, total_indexed=0)
    rate = await compute_reuse_rate(pool, _WINDOW_START, _WINDOW_END)
    assert rate == 0.0, (
        f"compute_reuse_rate with total_indexed=0 must return 0.0, got {rate}"
    )


@pytest.mark.asyncio
async def test_reuse_rate_queries_source_uri_from_evidence_panel_jsonb() -> None:
    """compute_reuse_rate queries distinct source_uri from evidence_panel JSONB.

    D-KC-03: citations come from evidence_panel JSONB in audit.actions.
    Verify the mock pool.fetchrow was called with a query containing
    evidence_panel and source_uri (not a separate table).

    Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
    """
    pool = _make_mock_pool(distinct_cited=5, total_indexed=20)
    await compute_reuse_rate(pool, _WINDOW_START, _WINDOW_END)

    # Verify pool.fetchrow was called.
    assert pool.fetchrow.called, "pool.fetchrow must be called by compute_reuse_rate()"

    # Verify the SQL query contains evidence_panel and source_uri.
    call_args = pool.fetchrow.call_args
    sql_query: str = call_args[0][0]  # First positional arg is the SQL string.
    assert "evidence_panel" in sql_query, (
        f"SQL must reference evidence_panel JSONB column. Got SQL: {sql_query!r}"
    )
    assert "source_uri" in sql_query, (
        f"SQL must reference source_uri field from rag_citations. Got SQL: {sql_query!r}"
    )


@pytest.mark.asyncio
async def test_reuse_rate_uses_rolling_window_not_all_time() -> None:
    """compute_reuse_rate is computed over a configurable rolling window, not all-time.

    D-KC-03: rolling window parameter (window_start, window_end). Verify the asyncpg query
    includes a timestamp filter (ts BETWEEN window_start AND window_end).

    Implementation target: trn_knowledge_curator.reuse_rate.compute_reuse_rate()
    """
    pool = _make_mock_pool(distinct_cited=2, total_indexed=8)
    await compute_reuse_rate(pool, _WINDOW_START, _WINDOW_END)

    # Verify pool.fetchrow was called with window parameters.
    call_args = pool.fetchrow.call_args
    sql_query: str = call_args[0][0]
    positional_args = call_args[0][1:]  # Args after the SQL string.

    # Verify SQL contains a timestamp filter (BETWEEN).
    assert "BETWEEN" in sql_query, (
        f"SQL must include BETWEEN for rolling window filter. Got SQL: {sql_query!r}"
    )
    assert "ts" in sql_query, (
        f"SQL must filter on ts (timestamp) column. Got SQL: {sql_query!r}"
    )

    # Verify window_start and window_end are passed as parameters (not hardcoded).
    assert _WINDOW_START in positional_args, (
        f"window_start must be passed as a SQL parameter. Got args: {positional_args!r}"
    )
    assert _WINDOW_END in positional_args, (
        f"window_end must be passed as a SQL parameter. Got args: {positional_args!r}"
    )
