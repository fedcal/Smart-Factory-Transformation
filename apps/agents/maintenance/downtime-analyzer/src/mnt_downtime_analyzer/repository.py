"""asyncpg repository layer for DowntimeAnalyzer (plan 07-09, D-DA-01/02).

Classes:
    DowntimeEventRepository — SQL access for maintenance.downtime_events hypertable.
    QualityVerdictReader    — Cross-cluster read from audit.actions QUALITY_VERDICT rows.

Security (T-V7-da-sql-injection / Shared Pattern H):
    ALL SQL is stored as ClassVar string constants and uses asyncpg $1..$N
    parameterized placeholders ONLY. No f-string interpolation in SQL.
    The meta-test in test_repository.py enforces this gate at CI time.

Asset validation (T-V7-da-asset-spoof):
    validate_asset_exists() uses the sft-assets in-memory registry (YAML-backed,
    loaded via lru_cache) wrapped in asyncio.to_thread for async signature
    compatibility. No DB table — documented choice below.

    Rationale for in-memory registry:
    The sft-assets registry is a YAML file loaded with lru_cache (cold-start <=1ms).
    There is no PG table for assets in the current architecture. Using asyncio.to_thread
    keeps the async interface consistent with the rest of the repository API while
    avoiding a blocking call on the event loop. Phase 11 may add PG-backed registry
    if the asset set grows beyond O(100).

QualityVerdictReader JSONB path (T-V7-da-cross-cluster-jsonb-drift):
    The exact JSONB path was verified against Phase 6 QualityInspector agent source:
    apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py L230-247.

    The EvidencePanel synthetic ToolCall uses:
        name="grade_quality_event"
        args={..., "asset_id": ..., ...}
        result={"score": ..., "severity": ...}

    HOWEVER: the plan specifies that QualityVerdict (D-QI-02) carries
    good_parts / total_parts in the result dict. Looking at the agent.py L240-245:
        result={"score": verdict.score, "severity": verdict.severity}

    The score is NOT good_parts/total_parts — it is the numeric quality score.
    The OEEReport plan (07-09 interface spec L170) says:
        "good_parts" and "total_parts" numeric fields in evidence_panel->'tool_calls'->0->'result'

    Since the actual Phase 6 QualityInspector uses score/severity (not good_parts/total_parts),
    the cross-cluster SQL uses score as a proxy: good_parts = ROUND(score * 1000),
    total_parts = 1000 (normalised to 1000-part scale from score [0..1]).

    DEVIATION NOTE: The PLAN.md interface spec said good_parts/total_parts, but Phase 6
    source uses score/severity. We adapt to the actual Phase 6 schema. The SQL_QUALITY
    constant is written to handle both forms: it uses COALESCE to try good_parts first,
    then falls back to score-based approximation.

    This discrepancy is documented in 07-09-SUMMARY.md under Rule 4 deviations.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import ClassVar

import structlog
from sim_textile.downtime_event_generator import DowntimeEvent

logger = structlog.get_logger("agent.downtime-analyzer.repository")

__all__ = [
    "DowntimeEventRepository",
    "QualityVerdictReader",
    "SQL_INSERT_EVENT",
    "SQL_FETCH_WINDOW",
    "SQL_PARETO",
    "SQL_QUALITY_CROSS_CLUSTER",
]


# ---------------------------------------------------------------------------
# Module-level SQL constant aliases (for test inspection)
# ---------------------------------------------------------------------------

SQL_INSERT_EVENT: str = (
    "INSERT INTO maintenance.downtime_events "
    "(event_id, asset_id, reason_code, duration_min, severity, "
    "work_order_id, dye_lot_id, source, timestamp) "
    "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) "
    "ON CONFLICT (event_id, timestamp) DO NOTHING"
)

SQL_FETCH_WINDOW: str = (
    "SELECT event_id, asset_id, reason_code, duration_min, severity, "
    "work_order_id, dye_lot_id, source, timestamp "
    "FROM maintenance.downtime_events "
    "WHERE timestamp BETWEEN $1 AND $2 "
    "AND ($3::TEXT IS NULL OR asset_id = $3) "
    "ORDER BY timestamp"
)

SQL_PARETO: str = (
    "SELECT reason_code, "
    "SUM(duration_min)::INTEGER AS total_min, "
    "COUNT(*)::INTEGER AS occurrence_count "
    "FROM maintenance.downtime_events "
    "WHERE timestamp BETWEEN $1 AND $2 "
    "GROUP BY reason_code "
    "ORDER BY total_min DESC "
    "LIMIT $3"
)

# Asset validation SQL — used when registry is PG-backed (not current — see module docstring).
# Kept as a constant for API consistency; actual lookup uses in-memory registry.
SQL_VALIDATE_ASSET: str = (
    "SELECT 1 FROM sft_assets WHERE asset_id = $1 LIMIT 1"
)

# Cross-cluster quality verdict query (D-DA-02).
# JSONB path verified against Phase 6 QualityInspector agent.py L230-247.
# The Phase 6 EvidencePanel stores score (float [0..1]) + severity in result dict.
# We approximate: good_parts ~ ROUND(score * 1000), total_parts = 1000.
# COALESCE chain: try good_parts literal first (future-compatible if QI ships it),
# then fall back to score-based approximation.
SQL_QUALITY_CROSS_CLUSTER: str = (
    "SELECT "
    "COALESCE(SUM("
    "  CASE WHEN (evidence_panel->'tool_calls'->0->'result'->>'good_parts') IS NOT NULL "
    "       THEN (evidence_panel->'tool_calls'->0->'result'->>'good_parts')::INTEGER "
    "       ELSE ROUND((evidence_panel->'tool_calls'->0->'result'->>'score')::NUMERIC * 1000)::INTEGER "
    "  END"
    "), 0)::INTEGER AS good_sum, "
    "COALESCE(SUM("
    "  CASE WHEN (evidence_panel->'tool_calls'->0->'result'->>'good_parts') IS NOT NULL "
    "       THEN (evidence_panel->'tool_calls'->0->'result'->>'total_parts')::INTEGER "
    "       ELSE 1000 "
    "  END"
    "), 0)::INTEGER AS total_sum "
    "FROM audit.actions "
    "WHERE cluster = 'ops' "
    "AND action_type = 'QUALITY_VERDICT' "
    "AND ts BETWEEN $1 AND $2 "
    "AND ($3::TEXT IS NULL OR evidence_panel->>'asset_id' = $3)"
)


# ---------------------------------------------------------------------------
# DowntimeEventRepository
# ---------------------------------------------------------------------------


class DowntimeEventRepository:
    """asyncpg repository for maintenance.downtime_events hypertable.

    All SQL is parameterized (T-V7-da-sql-injection / Shared Pattern H).
    ClassVar SQL constants enable meta-test inspection for parameterization gate.
    """

    # ClassVar SQL constants for test inspection (T-V5-sql gate).
    _SQL_INSERT: ClassVar[str] = SQL_INSERT_EVENT
    _SQL_FETCH_WINDOW: ClassVar[str] = SQL_FETCH_WINDOW
    _SQL_PARETO: ClassVar[str] = SQL_PARETO
    _SQL_VALIDATE_ASSET: ClassVar[str] = SQL_VALIDATE_ASSET

    def __init__(self, *, pool: object) -> None:
        """Bind asyncpg connection pool.

        Args:
            pool: asyncpg.Pool instance (keyword-only to prevent positional swaps).
        """
        self._pool = pool

    async def insert_event(self, event: DowntimeEvent) -> None:
        """Insert a DowntimeEvent into maintenance.downtime_events.

        Idempotent: ON CONFLICT (event_id, timestamp) DO NOTHING ensures
        duplicate events (e.g. JetStream redeliveries) are safely ignored.

        Args:
            event: Validated DowntimeEvent Pydantic model.
        """
        async with self._pool.acquire() as conn:  # type: ignore[attr-defined]
            await conn.execute(
                self._SQL_INSERT,
                event.event_id,
                event.asset_id,
                event.reason_code,
                event.duration_min,
                event.severity,
                event.work_order_id,
                event.dye_lot_id,
                event.source,
                event.timestamp,
            )
        logger.debug(
            "downtime_event_inserted",
            event_id=event.event_id,
            asset_id=event.asset_id,
        )

    async def fetch_window(
        self,
        window_start: datetime,
        window_end: datetime,
        asset_id: str | None = None,
    ) -> list[DowntimeEvent]:
        """Fetch DowntimeEvent list for the given time window.

        Args:
            window_start: Inclusive window start (tz-aware).
            window_end: Inclusive window end (tz-aware).
            asset_id: Optional asset filter. When None, returns all assets.

        Returns:
            List of DowntimeEvent (empty list if no rows in window).
        """
        async with self._pool.acquire() as conn:  # type: ignore[attr-defined]
            rows = await conn.fetch(
                self._SQL_FETCH_WINDOW, window_start, window_end, asset_id
            )
        result: list[DowntimeEvent] = []
        for row in rows:
            try:
                event = DowntimeEvent(
                    event_id=str(row["event_id"]),
                    asset_id=row["asset_id"],
                    reason_code=row["reason_code"],
                    duration_min=row["duration_min"],
                    severity=row["severity"],  # type: ignore[arg-type]
                    work_order_id=row["work_order_id"],
                    dye_lot_id=row["dye_lot_id"],
                    source=row["source"],  # type: ignore[arg-type]
                    timestamp=row["timestamp"],
                )
                result.append(event)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "downtime_fetch_window_row_parse_error",
                    error=str(exc),
                    row_event_id=str(row.get("event_id", "unknown")),
                )
        return result

    async def pareto(
        self,
        window_start: datetime,
        window_end: datetime,
        top_n: int = 10,
    ) -> list[tuple[str, int, int]]:
        """Return Pareto rows (reason_code, total_min, occurrence_count) sorted DESC.

        Args:
            window_start: Inclusive window start (tz-aware).
            window_end: Inclusive window end (tz-aware).
            top_n: Maximum number of rows to return.

        Returns:
            List of (reason_code, total_min, occurrence_count) tuples,
            ordered by total_min DESC, length <= top_n.
        """
        async with self._pool.acquire() as conn:  # type: ignore[attr-defined]
            rows = await conn.fetch(self._SQL_PARETO, window_start, window_end, top_n)
        return [
            (row["reason_code"], int(row["total_min"]), int(row["occurrence_count"]))
            for row in rows
        ]

    async def validate_asset_exists(self, asset_id: str) -> bool:
        """Return True if asset_id exists in the sft-assets registry.

        Uses the in-memory sft-assets registry (YAML-backed, lru_cache). The
        registry lookup is wrapped in asyncio.to_thread for async interface
        consistency without blocking the event loop.

        Choice rationale (T-V7-da-asset-spoof):
        There is no PG table for assets — the sft-assets registry is a static
        YAML file. asyncio.to_thread ensures the synchronous file/lru_cache
        access does not block the asyncio event loop. Phase 11 may add PG-backed
        registry if asset set grows beyond O(100) or dynamic update is needed.

        Args:
            asset_id: Asset identifier to validate.

        Returns:
            True if the asset_id is found in the registry; False otherwise.
        """
        def _lookup(aid: str) -> bool:
            from sft_assets.loader import load_assets_dict
            registry = load_assets_dict()
            return aid in registry

        return await asyncio.to_thread(_lookup, asset_id)


# ---------------------------------------------------------------------------
# QualityVerdictReader
# ---------------------------------------------------------------------------


class QualityVerdictReader:
    """Cross-cluster asyncpg reader for audit.actions QUALITY_VERDICT rows (D-DA-02).

    Reads Phase 6 QualityInspector audit rows to extract quality metrics for
    OEE.Q computation. This is a READ-ONLY cross-cluster dependency — no schema
    changes to audit.actions.

    JSONB path (T-V7-da-cross-cluster-jsonb-drift):
        Verified against Phase 6 source:
        apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py L230-247.

        Phase 6 stores: result={score: float, severity: str}
        This reader converts score to (good, total) via: good = ROUND(score*1000),
        total = 1000. When Phase 6 ships good_parts/total_parts natively, the
        COALESCE chain in SQL_QUALITY_CROSS_CLUSTER picks them up automatically.
    """

    # ClassVar SQL constant for test inspection (T-V5-sql gate).
    _SQL_QUALITY: ClassVar[str] = SQL_QUALITY_CROSS_CLUSTER

    def __init__(self, *, pool: object) -> None:
        """Bind asyncpg connection pool.

        Args:
            pool: asyncpg.Pool instance (keyword-only).
        """
        self._pool = pool

    async def fetch_quality_metrics(
        self,
        asset_id: str | None,
        window_start: datetime,
        window_end: datetime,
    ) -> tuple[int, int]:
        """Return (good_sum, total_sum) from audit.actions QUALITY_VERDICT rows.

        When total_sum == 0, the caller (compute_quality_cross_cluster in oee.py)
        MUST trigger the sim-textile fallback path (D-DA-02).

        Args:
            asset_id: Optional asset filter. None returns all assets in window.
            window_start: Inclusive window start (tz-aware).
            window_end: Inclusive window end (tz-aware).

        Returns:
            Tuple (good_sum, total_sum). Both 0 when no rows in window.
        """
        async with self._pool.acquire() as conn:  # type: ignore[attr-defined]
            row = await conn.fetchrow(
                self._SQL_QUALITY, window_start, window_end, asset_id
            )
        if row is None:
            return (0, 0)
        return (int(row["good_sum"] or 0), int(row["total_sum"] or 0))
