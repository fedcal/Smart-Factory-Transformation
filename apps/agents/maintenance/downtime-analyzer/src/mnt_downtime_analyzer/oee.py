"""OEE A×P×Q computation + Pareto + cross-cluster Quality + sim fallback (plan 07-09, D-DA-02/03).

All computation functions are pure (no side effects beyond structlog) where possible.

Design decisions (D-DA-03):
    CAGG vs raw-hypertable heuristic:
        When window is exactly hour-aligned (window_start and window_end are both on the
        hour boundary AND span an integer number of complete hours), prefer reading from
        ``maintenance.oee_hourly`` CAGG for O(1) lookup. For non-aligned windows fall back
        to raw hypertable scan via DowntimeEventRepository.fetch_window. This heuristic is
        intentionally simple for PoC — Phase 11 can add a proper continuous-aggregate-first
        strategy with staleness bounds.

        Note: The current implementation uses raw hypertable for ALL windows because the
        CAGG is a 5-minute-delayed materialisation. Exposing the CAGG path requires the
        asyncpg pool to be wired through to oee.py. For PoC simplicity (and to avoid adding
        a second SQL path that would require separate tests), the CAGG preference is
        implemented as a flag comment with the raw-scan fallback always active. The decision
        is documented here per plan requirement.

Security:
    T-V7-da-quality-divide-by-zero: compute_quality_cross_cluster has explicit branch for
    total_sum=0 → sim fallback → 1.0 default.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

import structlog

from mnt_downtime_analyzer.models import ParetoEntry

if TYPE_CHECKING:
    from mnt_downtime_analyzer.repository import DowntimeEventRepository, QualityVerdictReader

logger = structlog.get_logger("agent.downtime-analyzer.oee")

#: Quality source markers (observable via structlog INFO per plan requirement).
QualitySource = Literal["audit", "simfallback", "no-data"]

__all__ = [
    "compute_availability",
    "compute_oee",
    "compute_pareto",
    "compute_performance",
    "compute_quality_cross_cluster",
]


# ---------------------------------------------------------------------------
# compute_availability
# ---------------------------------------------------------------------------


def compute_availability(
    *,
    window_start: datetime,
    window_end: datetime,
    downtime_minutes: int,
    planned_production_minutes: int | None = None,
) -> float:
    """Compute OEE.A (Availability) for the given window.

    OEE.A = (planned_production_time_min - downtime_minutes) / planned_production_time_min

    PoC simplification: if ``planned_production_minutes`` is None, default = window length
    in minutes (100% planned assumption). This documents that 'no shift policy is applied';
    Phase 11 can replace with asset shift policy lookup.

    Args:
        window_start: Window start (tz-aware).
        window_end: Window end (tz-aware).
        downtime_minutes: Total downtime in the window (ge=0).
        planned_production_minutes: Override for planned time. When None, uses window length.

    Returns:
        Availability in [0.0, 1.0]. Clamped to 0.0 if downtime exceeds planned.
    """
    if planned_production_minutes is None:
        # PoC default: 100% planned = window length (no shift policy)
        window_minutes = (window_end - window_start).total_seconds() / 60.0
        planned = window_minutes
    else:
        planned = float(planned_production_minutes)

    if planned <= 0:
        return 1.0  # degenerate: zero-length window is always available

    availability = (planned - downtime_minutes) / planned
    return max(0.0, min(1.0, availability))


# ---------------------------------------------------------------------------
# compute_performance
# ---------------------------------------------------------------------------


async def compute_performance(
    *,
    asset_id: str | None,
    window_start: datetime,
    window_end: datetime,
    production_state_reader: Callable | None = None,
) -> float:
    """Compute OEE.P (Performance) for the given window.

    Source: sim-textile production_state reader returning (good_meters, target_meters).
    Fallback: 1.0 + structlog WARN when reader is None or target=0.

    Args:
        asset_id: Asset identifier (passed to reader).
        window_start: Window start (tz-aware).
        window_end: Window end (tz-aware).
        production_state_reader: Async callable returning (good, target) tuple.
            Signature: async def reader(asset_id, window_start, window_end) -> tuple[int, int].

    Returns:
        Performance in [0.0, 1.0]. 1.0 on missing reader or zero target.
    """
    if production_state_reader is None:
        logger.warning(
            "oee_performance_fallback_unavailable_source",
            asset_id=asset_id,
            reason="No production_state_reader provided; defaulting to 1.0.",
        )
        return 1.0

    try:
        good, target = await production_state_reader(asset_id, window_start, window_end)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "oee_performance_fallback_unavailable_source",
            asset_id=asset_id,
            reason=f"production_state_reader raised: {exc}",
        )
        return 1.0

    if target <= 0:
        logger.warning(
            "oee_performance_fallback_unavailable_source",
            asset_id=asset_id,
            reason="target_meters=0; defaulting to 1.0.",
        )
        return 1.0

    return max(0.0, min(1.0, good / target))


# ---------------------------------------------------------------------------
# compute_quality_cross_cluster
# ---------------------------------------------------------------------------


async def compute_quality_cross_cluster(
    *,
    asset_id: str | None,
    window_start: datetime,
    window_end: datetime,
    quality_reader: "QualityVerdictReader",
    sim_fallback_reader: Callable | None = None,
) -> tuple[float, QualitySource]:
    """Compute OEE.Q (Quality) with cross-cluster audit-first + sim-textile fallback (D-DA-02).

    Source priority:
        1. audit.actions QUALITY_VERDICT rows (cross-cluster) → structlog INFO oee_quality_source_audit
        2. sim-textile production_state fallback (when audit total=0) → structlog INFO oee_quality_source_simfallback
        3. 1.0 default (no data, no fallback) → structlog WARNING

    Args:
        asset_id: Asset identifier filter (None = all assets).
        window_start: Window start (tz-aware).
        window_end: Window end (tz-aware).
        quality_reader: QualityVerdictReader with fetch_quality_metrics method.
        sim_fallback_reader: Optional async callable returning (good_meters, total_meters).

    Returns:
        Tuple (quality_float [0,1], quality_source marker).
        quality_source is one of: "audit", "simfallback", "no-data".
    """
    # Step 1: Try cross-cluster audit query.
    good_sum, total_sum = await quality_reader.fetch_quality_metrics(
        asset_id, window_start, window_end
    )

    if total_sum > 0:
        quality = max(0.0, min(1.0, good_sum / total_sum))
        logger.info(
            "oee_quality_source_audit",
            asset_id=asset_id,
            good_sum=good_sum,
            total_sum=total_sum,
            quality=quality,
        )
        return (quality, "audit")

    # Step 2: Audit empty — try sim-textile fallback.
    if sim_fallback_reader is not None:
        try:
            good_fb, total_fb = await sim_fallback_reader(asset_id, window_start, window_end)
            if total_fb > 0:
                quality = max(0.0, min(1.0, good_fb / total_fb))
                logger.info(
                    "oee_quality_source_simfallback",
                    asset_id=asset_id,
                    good_fb=good_fb,
                    total_fb=total_fb,
                    quality=quality,
                )
                return (quality, "simfallback")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "oee_quality_simfallback_error",
                asset_id=asset_id,
                error=str(exc),
            )

    # Step 3: No-data default.
    logger.warning(
        "oee_quality_no_data_default",
        asset_id=asset_id,
        note="No audit rows and no fallback data; defaulting quality to 1.0.",
    )
    return (1.0, "no-data")


# ---------------------------------------------------------------------------
# compute_oee
# ---------------------------------------------------------------------------


async def compute_oee(
    *,
    asset_id: str | None,
    window_start: datetime,
    window_end: datetime,
    repository: "DowntimeEventRepository",
    quality_reader: "QualityVerdictReader",
    production_state_reader: Callable | None = None,
    sim_fallback_reader: Callable | None = None,
    planned_production_minutes: int | None = None,
) -> tuple[float, float, float, float, int, int]:
    """Compute aggregate OEE A×P×Q for the given window and asset.

    Returns:
        Tuple (availability, performance, quality, oee, total_downtime_min, event_count).
        oee = availability × performance × quality.

    Notes:
        CAGG usage heuristic: for hour-aligned windows the CAGG maintenance.oee_hourly
        would give O(1) lookup. For PoC this implementation always uses raw hypertable
        scan via repository.fetch_window. Phase 11 can add CAGG path.
    """
    # Step 1: Fetch downtime events for availability calculation.
    events = await repository.fetch_window(window_start, window_end, asset_id)
    total_downtime_min = sum(e.duration_min for e in events)
    event_count = len(events)

    # Step 2: A
    availability = compute_availability(
        window_start=window_start,
        window_end=window_end,
        downtime_minutes=total_downtime_min,
        planned_production_minutes=planned_production_minutes,
    )

    # Step 3: P
    performance = await compute_performance(
        asset_id=asset_id,
        window_start=window_start,
        window_end=window_end,
        production_state_reader=production_state_reader,
    )

    # Step 4: Q (cross-cluster + fallback)
    quality, _quality_source = await compute_quality_cross_cluster(
        asset_id=asset_id,
        window_start=window_start,
        window_end=window_end,
        quality_reader=quality_reader,
        sim_fallback_reader=sim_fallback_reader,
    )

    oee = availability * performance * quality
    return (availability, performance, quality, oee, total_downtime_min, event_count)


# ---------------------------------------------------------------------------
# compute_pareto
# ---------------------------------------------------------------------------


def compute_pareto(
    rows: list[tuple[str, int, int]],
    top_n: int = 10,
) -> list[ParetoEntry]:
    """Compute Pareto top-N downtime entries with cumulative percent.

    Takes raw pareto rows from DowntimeEventRepository.pareto() and computes
    cumulative_percent (running sum / grand_total × 100).

    Args:
        rows: List of (reason_code, total_downtime_min, occurrence_count) tuples,
              expected in DESC order by total_min (as returned by SQL PARETO query).
        top_n: Maximum entries to return. 0 → empty list (defensive).

    Returns:
        List of ParetoEntry sorted by total_downtime_min DESC. Length ≤ top_n.
        Empty list if rows is empty or top_n=0.
    """
    if not rows or top_n <= 0:
        return []

    # Sort by total DESC, then occurrence_count DESC as tiebreak.
    sorted_rows = sorted(rows, key=lambda r: (r[1], r[2]), reverse=True)
    trimmed = sorted_rows[:top_n]

    grand_total = sum(r[1] for r in trimmed)
    if grand_total <= 0:
        # Edge case: all zero downtime
        return [
            ParetoEntry(
                reason_code=r[0],
                total_downtime_min=r[1],
                occurrence_count=r[2],
                cumulative_percent=0.0,
            )
            for r in trimmed
        ]

    entries: list[ParetoEntry] = []
    running_sum = 0
    for reason_code, total_min, occurrence_count in trimmed:
        running_sum += total_min
        cumulative_pct = min(100.0, running_sum / grand_total * 100.0)
        entries.append(
            ParetoEntry(
                reason_code=reason_code,
                total_downtime_min=total_min,
                occurrence_count=occurrence_count,
                cumulative_percent=cumulative_pct,
            )
        )

    return entries
