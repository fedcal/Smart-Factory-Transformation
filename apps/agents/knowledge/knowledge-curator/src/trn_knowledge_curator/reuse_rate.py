"""Knowledge reuse-rate KPI computation for KnowledgeCurator (D-KC-03).

Provides:
  - compute_reuse_rate: standalone async function for reuse-rate computation.
  - ReuseRateKPI: class wrapping the pool with a compute() method.

KPI definition (D-KC-03):
  reuse_rate = distinct_documents_cited / total_indexed_documents

Sources:
  - distinct_cited: COUNT(DISTINCT source_uri) from audit.actions.evidence_panel
    rag_citations JSONB array, filtered by rolling window.
  - total_indexed: COUNT from documents table where indexed=true.

Rolling window: configurable window_days parameter (default 30 days).
Division-by-zero guard: returns 0.0 when total_indexed == 0.

Security: All SQL uses $N parameterized placeholders only (no f-string interpolation).

Pattern reference: 08-PATTERNS.md reuse_rate.py section (lines 956-998).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger("trn_knowledge_curator.reuse_rate")


class ReuseRateKPI:
    """Compute the knowledge reuse-rate KPI (D-KC-03).

    reuse_rate = distinct_cited_source_uris / total_indexed_documents

    Computed over a rolling window from audit.actions.evidence_panel JSONB.
    Returns 0.0 when no documents are indexed (division-by-zero guard).

    All SQL uses $N parameterized placeholders (T-08-11 analog / Shared Pattern H).
    ClassVar SQL constants enable meta-test inspection for parameterization gate.
    """

    #: Distinct source_uri citations from audit.actions evidence_panel over a window.
    _SQL_DISTINCT_CITED: ClassVar[str] = (
        "SELECT COUNT(DISTINCT ep_citation->>'source_uri') "
        "FROM audit.actions, "
        "     jsonb_array_elements(evidence_panel->'rag_citations') AS ep_citation "
        "WHERE ts BETWEEN $1 AND $2 "
        "AND ep_citation->>'source_uri' IS NOT NULL"
    )

    #: Total indexed documents (all time, not rolling).
    _SQL_TOTAL_INDEXED: ClassVar[str] = (
        "SELECT COUNT(*) FROM documents WHERE indexed = true"
    )

    def __init__(self, *, pool: Any) -> None:
        """Initialise with an asyncpg connection pool.

        Args:
            pool: asyncpg.Pool instance.
        """
        if pool is None:
            raise ValueError("pool must not be None")
        self._pool = pool

    async def compute(
        self,
        window_days: int = 30,
        *,
        now: datetime | None = None,
    ) -> float:
        """Compute the reuse-rate KPI over a rolling window.

        Args:
            window_days: Number of days in the rolling window (default 30).
            now: Reference datetime (UTC tz-aware); uses datetime.now(UTC) if None.

        Returns:
            reuse_rate in [0.0, 1.0]. Returns 0.0 when total_indexed == 0.
        """
        effective_now = now if now is not None else datetime.now(timezone.utc)
        window_start = effective_now - timedelta(days=window_days)
        window_end = effective_now

        return await compute_reuse_rate(
            pool=self._pool,
            window_start=window_start,
            window_end=window_end,
        )


async def compute_reuse_rate(
    pool: Any,
    window_start: datetime,
    window_end: datetime,
) -> float:
    """Compute reuse_rate = distinct_cited / total_indexed.

    Args:
        pool: asyncpg.Pool — must support fetchrow() direct method or acquire() context.
        window_start: Rolling window start (UTC tz-aware).
        window_end: Rolling window end (UTC tz-aware).

    Returns:
        Float in [0.0, 1.0]. Returns 0.0 when total_indexed == 0.

    Note:
        SQL queries evidence_panel JSONB from audit.actions (not a separate citations table).
        Timestamp filter on audit.actions.ts bounds the rolling window (D-KC-03).
    """
    # Use pool.fetchrow directly (matches conftest mock_pool pattern).
    row = await pool.fetchrow(
        _SQL_COMBINED,
        window_start,
        window_end,
    )

    if row is None:
        return 0.0

    distinct_cited = row["distinct_cited"] or 0
    total_indexed = row["total_indexed"] or 0

    if total_indexed == 0:
        logger.info("reuse_rate_zero_indexed", window_start=window_start, window_end=window_end)
        return 0.0

    rate = float(distinct_cited) / float(total_indexed)
    logger.info(
        "reuse_rate_computed",
        distinct_cited=distinct_cited,
        total_indexed=total_indexed,
        rate=rate,
        window_days=(window_end - window_start).days,
    )
    return rate


# Combined query used by compute_reuse_rate — returns both metrics in one round-trip.
# Uses a subquery pattern to compute distinct cited and total indexed in a single statement.
# Parameterized with $1=window_start, $2=window_end (rolling window filter on ts).
_SQL_COMBINED: str = (
    "SELECT "
    "  (SELECT COUNT(DISTINCT ep_citation->>'source_uri') "
    "   FROM audit.actions, "
    "        jsonb_array_elements(evidence_panel->'rag_citations') AS ep_citation "
    "   WHERE ts BETWEEN $1 AND $2 "
    "   AND ep_citation->>'source_uri' IS NOT NULL"
    "  ) AS distinct_cited, "
    "  (SELECT COUNT(*) FROM documents WHERE indexed = true) AS total_indexed"
)


__all__ = [
    "ReuseRateKPI",
    "compute_reuse_rate",
]
