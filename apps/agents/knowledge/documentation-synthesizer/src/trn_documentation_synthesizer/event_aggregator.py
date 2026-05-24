"""Historical event aggregator for DocumentationSynthesizer (D-DS-02, Open Q4).

Fetches historical RCA/downtime/coach audit events for SOP synthesis.

SQL strategy (Open Q4 resolved):
    INTERVAL cannot be parameterized in asyncpg. The window start datetime is
    computed in Python (WR-03 pattern) and passed as $1 TIMESTAMPTZ.
    Failure mode and asset_id are filtered via JSONB operators on evidence_panel.

Security (Shared Pattern E — T-V5-sql gate):
    All SQL is stored as ClassVar string constants with $N parameterized
    placeholders ONLY. No f-string or %-format interpolation in SQL.
    The meta-tests can inspect _SQL_HISTORY for parameterization compliance.

No schema change:
    Reads audit.actions using existing JSONB operators.
    action_type filter: RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT (SC-4, D-DS-02).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger("agent.documentation-synthesizer.event_aggregator")


class HistoricalEventAggregator:
    """Fetches historical RCA/downtime/coach audit events for SOP synthesis (D-DS-02).

    Reads audit.actions WHERE action_type IN (RCA_CHAIN, COACH_STEP, DOWNTIME_VERDICT)
    filtered by evidence_panel->>'failure_mode' + evidence_panel->>'asset_id' + window.
    No schema change needed — uses existing JSONB operators (Open Q4 resolved).

    Window computation (WR-03 pattern):
        Window start = now(UTC) - window_days days, computed in Python and
        passed as $1 TIMESTAMPTZ. asyncpg receives a datetime object (not an
        ISO string — Pattern C fix).

    Usage::

        aggregator = HistoricalEventAggregator(pool=asyncpg_pool)
        events = await aggregator.fetch(
            failure_mode="overheating",
            asset_id="loom-01",
            window_days=180,
        )
    """

    #: Canonical SQL for historical event retrieval (ClassVar for test inspection).
    #: Window start computed in Python as TIMESTAMPTZ — INTERVAL not parameterizable.
    #: JSONB operators: ->>'failure_mode' and ->>'asset_id' filter on evidence_panel.
    _SQL_HISTORY: ClassVar[str] = (
        "SELECT ts, agent_id, action_type, evidence_panel "
        "FROM audit.actions "
        "WHERE action_type IN ('RCA_CHAIN', 'COACH_STEP', 'DOWNTIME_VERDICT') "
        "AND ts >= $1 "
        "AND ($2::TEXT IS NULL OR evidence_panel->>'failure_mode' = $2) "
        "AND ($3::TEXT IS NULL OR evidence_panel->>'asset_id' = $3) "
        "ORDER BY ts DESC "
        "LIMIT 100"
    )

    def __init__(self, *, pool: Any) -> None:
        """Bind asyncpg connection pool.

        Args:
            pool: asyncpg.Pool instance (keyword-only to prevent positional swaps).
        """
        self._pool = pool

    async def fetch(
        self,
        *,
        failure_mode: str | None = None,
        asset_id: str | None = None,
        window_days: int = 180,
    ) -> list[dict[str, Any]]:
        """Fetch historical audit events for SOP synthesis (D-DS-02).

        Computes window_start = now(UTC) - window_days days in Python (WR-03 pattern)
        and passes it as $1 TIMESTAMPTZ. asyncpg receives a datetime object.

        Args:
            failure_mode: Optional JSONB filter on evidence_panel->>'failure_mode'.
                          When None, all failure modes are included.
            asset_id:     Optional JSONB filter on evidence_panel->>'asset_id'.
                          When None, all assets are included.
            window_days:  Lookback window in days (default 180).

        Returns:
            List of event dicts with keys: ts, agent_id, action_type, evidence_panel.
            Ordered by ts DESC (most recent first). At most 100 rows.
        """
        # WR-03 fix: compute window start as datetime object, not ISO string
        window_start: datetime = datetime.now(timezone.utc) - timedelta(days=window_days)

        logger.debug(
            "historical_event_aggregator_fetch",
            failure_mode=failure_mode,
            asset_id=asset_id,
            window_days=window_days,
            window_start=window_start.isoformat(),
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                self._SQL_HISTORY,
                window_start,       # $1 TIMESTAMPTZ (datetime object — WR-03)
                failure_mode,       # $2 TEXT | NULL
                asset_id,           # $3 TEXT | NULL
            )

        result: list[dict[str, Any]] = []
        for row in rows:
            try:
                event = {
                    "ts": row["ts"],
                    "agent_id": row["agent_id"],
                    "action_type": row["action_type"],
                    "evidence_panel": row["evidence_panel"],
                }
                result.append(event)
            except (KeyError, Exception) as exc:  # noqa: BLE001
                logger.warning(
                    "historical_event_aggregator_row_parse_error",
                    error=str(exc),
                )

        logger.info(
            "historical_event_aggregator_fetched",
            count=len(result),
            failure_mode=failure_mode,
            asset_id=asset_id,
        )
        return result


__all__ = ["HistoricalEventAggregator"]
