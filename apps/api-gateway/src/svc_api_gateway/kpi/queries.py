"""KPI SQL aggregation functions — Plan 10-02 (SRV-02).

Provides 6 async KPI aggregation functions plus compute_kpi_snapshot() which
combines them into a single dict for use by the GET /v1/kpi endpoint.

Security guardrails (CR-05 / T-10-02-01):
  - ALL SQL uses asyncpg $N positional parameters only.
  - No f-string interpolation in SQL statements.
  - Interval / threshold values bound as parameters.
  - NULLIF guards prevent division-by-zero.

OEE approximation (RESEARCH Pattern 7, documented per plan objective):
  OEE = Availability-only with P=1.0 and Q=1.0.
  Availability formula reused from
  apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py
  (compute_availability):
    availability = max(0.0, (planned - downtime) / planned)
  multiplied by 100 for the percentage form used in the dashboard.
  Phase 11 can wire real Performance (production_state_reader) and
  Quality (QualityVerdictReader cross-cluster) sources.

Time windows (RESEARCH Pattern 7):
  OEE / downtime  — last 8 hours
  MTTR / MTBF     — last 30 days

Source tables:
  maintenance.downtime_events  — duration_min, started_at, resolved_at
  scm.historical_orders        — quantity_kg, order_date (throughput kg/h)
  audit.actions                — QUALITY_VERDICT rows, evidence_panel JSONB
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Window constants (bound as $N params, not interpolated into SQL)
# ---------------------------------------------------------------------------

_OEE_WINDOW_HOURS: int = 8
_MTTR_MTBF_WINDOW_DAYS: int = 30
_THROUGHPUT_WINDOW_HOURS: int = 8

# Planned production minutes for the OEE window (100% assumption per oee.py PoC default).
# Reflects the 8-hour window when no shift policy is available.
_PLANNED_PRODUCTION_MINUTES: float = _OEE_WINDOW_HOURS * 60.0


# ---------------------------------------------------------------------------
# Individual KPI functions (each receives an asyncpg connection)
# ---------------------------------------------------------------------------


async def oee_availability(
    conn: Any,
    window_start: datetime,
    window_end: datetime,
) -> float | None:
    """Compute OEE Availability (%) for the given window.

    Reuses the compute_availability formula from
    mnt_downtime_analyzer.oee (Plan 07-09):
      availability = max(0.0, (planned - downtime_min) / planned)
    returned as a percentage [0, 100].

    SQL uses $1 (window_start) and $2 (window_end) only — no f-string.
    NULLIF prevents division-by-zero when planned = 0.
    """
    sql = """
        SELECT COALESCE(SUM(duration_min), 0)::float AS total_downtime_min
        FROM maintenance.downtime_events
        WHERE started_at >= $1
          AND started_at <  $2
    """
    row = await conn.fetchrow(sql, window_start, window_end)
    if row is None:
        return None

    downtime_min: float = float(row["total_downtime_min"] or 0.0)
    planned: float = _PLANNED_PRODUCTION_MINUTES

    # Replicate compute_availability from oee.py (Phase 7 — citation):
    #   availability = max(0.0, min(1.0, (planned - downtime) / planned))
    if planned <= 0:
        return 100.0  # degenerate: zero-length window is always available

    availability_ratio = max(0.0, min(1.0, (planned - downtime_min) / planned))
    return round(availability_ratio * 100.0, 2)


async def mttr(
    conn: Any,
    window_start: datetime,
    window_end: datetime,
) -> float | None:
    """Compute Mean Time To Repair (minutes) over the window.

    MTTR = AVG(duration_min) for resolved downtime events.
    Returns None when no events exist.
    """
    sql = """
        SELECT AVG(duration_min)::float AS mttr_min
        FROM maintenance.downtime_events
        WHERE started_at >= $1
          AND started_at <  $2
          AND resolved_at IS NOT NULL
    """
    row = await conn.fetchrow(sql, window_start, window_end)
    if row is None or row["mttr_min"] is None:
        return None
    return round(float(row["mttr_min"]), 2)


async def mtbf(
    conn: Any,
    window_start: datetime,
    window_end: datetime,
) -> float | None:
    """Compute Mean Time Between Failures (hours) over the window.

    MTBF = window_hours / failure_count.
    Returns None when no failures exist.
    """
    window_hours = (window_end - window_start).total_seconds() / 3600.0

    sql = """
        SELECT COUNT(*)::float AS failure_count
        FROM maintenance.downtime_events
        WHERE started_at >= $1
          AND started_at <  $2
    """
    row = await conn.fetchrow(sql, window_start, window_end)
    if row is None:
        return None

    failure_count = float(row["failure_count"] or 0.0)
    if failure_count <= 0:
        return None  # no failures → MTBF undefined

    return round(window_hours / failure_count, 2)


async def scrap_rate(
    conn: Any,
    window_start: datetime,
    window_end: datetime,
) -> float | None:
    """Compute scrap / quality reject rate (%) using QUALITY_VERDICT audit rows.

    Proxy: reads evidence_panel->tool_calls->0->result->>'score' from
    audit.actions where action_type = 'QUALITY_VERDICT' (RESEARCH Pattern 7).
    Score is expected in [0, 1]; scrap_rate = (1 - AVG(score)) * 100.

    Falls back to 0.0 when no QUALITY_VERDICT rows exist (no audit data).
    SQL uses $1 (action_type literal bound as param), $2/$3 (window).
    """
    sql = """
        SELECT
            COUNT(*) AS total_count,
            AVG(
                (evidence_panel->'tool_calls'->0->'result'->>'score')::float
            ) AS avg_score
        FROM audit.actions
        WHERE action_type = $1
          AND created_at  >= $2
          AND created_at  <  $3
          AND (evidence_panel->'tool_calls'->0->'result'->>'score') IS NOT NULL
    """
    row = await conn.fetchrow(sql, "QUALITY_VERDICT", window_start, window_end)
    if row is None or row["total_count"] == 0 or row["avg_score"] is None:
        return 0.0  # no quality data → assume 0% scrap

    avg_score = float(row["avg_score"])
    # Clamp to [0, 100] (CR-05 safe bounds)
    scrap = max(0.0, min(100.0, (1.0 - avg_score) * 100.0))
    return round(scrap, 2)


async def throughput(
    conn: Any,
    window_start: datetime,
    window_end: datetime,
) -> float | None:
    """Compute production throughput (kg/h) from scm.historical_orders.

    Throughput = SUM(quantity_kg) / window_hours for orders shipped in the window.
    Returns None when no orders exist.
    """
    window_hours = (window_end - window_start).total_seconds() / 3600.0
    if window_hours <= 0:
        return None

    sql = """
        SELECT COALESCE(SUM(quantity_kg), 0)::float AS total_kg
        FROM scm.historical_orders
        WHERE order_date >= $1
          AND order_date <  $2
    """
    row = await conn.fetchrow(sql, window_start, window_end)
    if row is None or row["total_kg"] is None:
        return None

    total_kg = float(row["total_kg"])
    if total_kg <= 0:
        return 0.0

    return round(total_kg / window_hours, 2)


async def downtime_pct(
    conn: Any,
    window_start: datetime,
    window_end: datetime,
) -> float | None:
    """Compute downtime fraction (%) for the window.

    downtime% = SUM(duration_min) / planned_min * 100, clamped [0, 100].
    Returns 0.0 when no downtime events exist.
    """
    sql = """
        SELECT COALESCE(SUM(duration_min), 0)::float AS total_downtime_min
        FROM maintenance.downtime_events
        WHERE started_at >= $1
          AND started_at <  $2
    """
    row = await conn.fetchrow(sql, window_start, window_end)
    if row is None:
        return 0.0

    total_min = float(row["total_downtime_min"] or 0.0)
    planned = _PLANNED_PRODUCTION_MINUTES
    if planned <= 0:
        return 0.0

    pct = max(0.0, min(100.0, total_min / planned * 100.0))
    return round(pct, 2)


# ---------------------------------------------------------------------------
# compute_kpi_snapshot — accepts a connection (for testability)
# ---------------------------------------------------------------------------


async def compute_kpi_snapshot(
    conn_or_pool: Any,
) -> dict[str, float | None]:
    """Compute all 6 KPIs and return them in a dict.

    Accepts either an asyncpg connection or a pool-like object.
    When called with a pool (has ``acquire`` method), acquires one connection
    and runs all 6 functions sequentially sharing that connection.
    When called with a raw connection (has ``fetchrow`` but not ``acquire``),
    uses it directly — simplifies unit testing with mock connections.

    Returns:
        dict with keys: oee, mttr, mtbf, scrap_rate, throughput, downtime
        Values are float | None (None when no data is available).

    Time windows:
        oee / downtime  — last _OEE_WINDOW_HOURS hours
        mttr / mtbf     — last _MTTR_MTBF_WINDOW_DAYS days
        throughput      — last _THROUGHPUT_WINDOW_HOURS hours
    """
    now = datetime.now(UTC)
    oee_window_start = now - timedelta(hours=_OEE_WINDOW_HOURS)
    mttr_window_start = now - timedelta(days=_MTTR_MTBF_WINDOW_DAYS)
    throughput_window_start = now - timedelta(hours=_THROUGHPUT_WINDOW_HOURS)

    # Distinguish a raw connection (has fetchrow) from a pool (has acquire but
    # not fetchrow). AsyncMock objects always have all attributes, so we check
    # for fetchrow first — a real asyncpg Connection exposes fetchrow directly,
    # while a Pool does not.  This allows unit tests to pass a mock connection
    # directly without going through the acquire() context manager.
    if hasattr(conn_or_pool, "fetchrow"):
        # Raw connection — used in unit tests with mock conn.
        return await _run_all_kpis(
            conn_or_pool, now, oee_window_start, mttr_window_start, throughput_window_start
        )
    else:
        # Pool-like object — acquire a connection.
        async with conn_or_pool.acquire() as conn:
            return await _run_all_kpis(
                conn, now, oee_window_start, mttr_window_start, throughput_window_start
            )


async def _run_all_kpis(
    conn: Any,
    now: datetime,
    oee_window_start: datetime,
    mttr_window_start: datetime,
    throughput_window_start: datetime,
) -> dict[str, float | None]:
    """Execute all 6 KPI queries sequentially on the given connection."""
    try:
        oee_val = await oee_availability(conn, oee_window_start, now)
    except Exception:  # noqa: BLE001
        logger.exception("kpi_oee_query_failed")
        oee_val = None

    try:
        mttr_val = await mttr(conn, mttr_window_start, now)
    except Exception:  # noqa: BLE001
        logger.exception("kpi_mttr_query_failed")
        mttr_val = None

    try:
        mtbf_val = await mtbf(conn, mttr_window_start, now)
    except Exception:  # noqa: BLE001
        logger.exception("kpi_mtbf_query_failed")
        mtbf_val = None

    try:
        scrap_val = await scrap_rate(conn, oee_window_start, now)
    except Exception:  # noqa: BLE001
        logger.exception("kpi_scrap_rate_query_failed")
        scrap_val = None

    try:
        throughput_val = await throughput(conn, throughput_window_start, now)
    except Exception:  # noqa: BLE001
        logger.exception("kpi_throughput_query_failed")
        throughput_val = None

    try:
        downtime_val = await downtime_pct(conn, oee_window_start, now)
    except Exception:  # noqa: BLE001
        logger.exception("kpi_downtime_pct_query_failed")
        downtime_val = None

    return {
        "oee": oee_val,
        "mttr": mttr_val,
        "mtbf": mtbf_val,
        "scrap_rate": scrap_val,
        "throughput": throughput_val,
        "downtime": downtime_val,
    }


__all__ = [
    "compute_kpi_snapshot",
    "oee_availability",
    "mttr",
    "mtbf",
    "scrap_rate",
    "throughput",
    "downtime_pct",
]
