"""asyncpg repository for EnergyOptimizer SCM-02 (Plan 09-03).

Queries scm.energy_readings to fetch slot data for EnPI computation, and
scm.enpi_baseline to obtain the ISO 50001 target for a given process.

Critical rules:
    - NEVER use .isoformat() on datetime params for asyncpg — pass datetime objects
      directly (Pitfall 7 from 09-RESEARCH.md / WR-03 from Phase 8).
    - All SQL uses $N positional parameters only — no string interpolation (T-09-12).
    - ClassVar SQL strings prevent accidental per-instance mutation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger("repository.energy")


class EnergyRepository:
    """asyncpg-based repository for scm.energy_readings + scm.enpi_baseline (SCM-02).

    Thread-safe: all state is in the injected pool (no instance-level mutable state).
    The pool is acquired per query and released immediately (connection pooling).

    Security: T-09-12 — SQL parameters passed via asyncpg $N placeholders; no
    f-string interpolation or string concatenation with external input.

    asyncpg datetime handling: datetime objects are passed directly to the driver
    as $N parameters — never .isoformat() serialized (Pitfall 7 / WR-03).
    """

    #: Fetch energy readings for a process within a time window.
    #: Returns ts, asset_id, kwh, kg_processed, is_peak_hour ordered by ts.
    #: Parameters: $1=process (TEXT), $2=ts_from (TIMESTAMPTZ), $3=ts_to (TIMESTAMPTZ).
    _SQL_READINGS: ClassVar[str] = """
        SELECT
            ts,
            asset_id,
            kwh,
            kg_processed,
            is_peak_hour
        FROM scm.energy_readings
        WHERE process = $1
          AND ts >= $2
          AND ts  < $3
        ORDER BY ts
    """

    #: Fetch the ISO 50001 baseline for a given process.
    #: Returns kwh_per_kg_target + kwh_per_kg_actual_ytd.
    #: Parameters: $1=process (TEXT).
    _SQL_BASELINE: ClassVar[str] = """
        SELECT
            kwh_per_kg_target,
            kwh_per_kg_actual_ytd,
            baseline_year,
            notes
        FROM scm.enpi_baseline
        WHERE process = $1
    """

    def __init__(self, pool: Any) -> None:
        """Bind the asyncpg pool.

        Args:
            pool: asyncpg.Pool — the connection pool managed by the lifespan.
        """
        self._pool = pool

    async def fetch_energy_readings(
        self,
        process: str,
        ts_from: datetime,
        ts_to: datetime,
    ) -> list[dict[str, Any]]:
        """Fetch energy readings for a process within a time window.

        Parameters are passed as native Python objects to asyncpg — NEVER as
        .isoformat() strings (Pitfall 7, WR-03). asyncpg handles TIMESTAMPTZ
        ↔ datetime conversion internally.

        Args:
            process:  Process name (e.g. 'dyeing', 'finishing').
            ts_from:  Window start (inclusive). Must be tz-aware datetime.
            ts_to:    Window end (exclusive). Must be tz-aware datetime.

        Returns:
            List of dicts with keys: ts, asset_id, kwh, kg_processed, is_peak_hour.
            Returns [] when no rows match the window.

        Note:
            kg_processed may be None for slots where production is not measurable.
            compute_enpi() handles None values by skipping such slots.
        """
        logger.debug(
            "energy_repository_fetch_readings",
            process=process,
            ts_from=ts_from.isoformat(),
            ts_to=ts_to.isoformat(),
        )
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(self._SQL_READINGS, process, ts_from, ts_to)
        return [dict(r) for r in rows]

    async def fetch_baseline(self, process: str) -> dict[str, Any] | None:
        """Fetch the ISO 50001 EnPI baseline for a given process.

        Args:
            process: Process name (e.g. 'dyeing', 'finishing').

        Returns:
            Dict with keys: kwh_per_kg_target, kwh_per_kg_actual_ytd,
            baseline_year, notes. Returns None when no baseline row exists.
        """
        logger.debug("energy_repository_fetch_baseline", process=process)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(self._SQL_BASELINE, process)
        if row is None:
            return None
        return dict(row)


__all__ = ["EnergyRepository"]
