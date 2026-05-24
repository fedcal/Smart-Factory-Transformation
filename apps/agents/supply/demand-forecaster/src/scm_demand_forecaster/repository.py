"""asyncpg repository for DemandForecaster (SCM-04).

Reads monthly demand aggregates from scm.historical_orders.
All SQL is stored as ClassVar constants using $N parameterised placeholders only
(T-09-18: asyncpg $N params; DATE_TRUNC aggregation; datetime objects — WR-03).

No f-string interpolation in SQL.
All temporal parameters are Python datetime objects (never .isoformat() strings — Pitfall 7).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger("agent.demand-forecaster.repository")


class DemandRepository:
    """asyncpg repository for scm.historical_orders monthly aggregation.

    Security (T-09-18):
        ALL SQL uses asyncpg $N parameterised placeholders.
        No f-string or % interpolation in SQL strings.
        Parameters are Python datetime objects (not .isoformat() strings).

    Usage:
        repo = DemandRepository(pool)
        series = await repo.fetch_monthly_orders("jersey", months_back=24)
        # Returns list[float] of monthly kg totals, ordered by month ASC.
    """

    _SQL_MONTHLY_ORDERS: ClassVar[str] = (
        "SELECT DATE_TRUNC('month', order_date) AS month, "
        "SUM(quantity_kg)::FLOAT AS total_kg "
        "FROM scm.historical_orders "
        "WHERE sku_group = $1 "
        "AND order_date >= NOW() - INTERVAL '1 month' * $2 "
        "GROUP BY 1 "
        "ORDER BY 1"
    )

    def __init__(self, pool: Any) -> None:
        """Bind asyncpg connection pool.

        Args:
            pool: asyncpg.Pool instance.
        """
        self._pool = pool

    async def fetch_monthly_orders(
        self,
        sku_group: str,
        months_back: int = 24,
    ) -> list[float]:
        """Fetch monthly demand aggregates for a SKU group.

        Returns an ordered list of monthly kg totals (oldest first), suitable
        for direct use as the ``series`` argument to forecast_holt_winters().

        SQL uses DATE_TRUNC('month', order_date) SUM(quantity_kg) aggregation
        over the last N months (asyncpg $N params; datetime objects — WR-03).

        Args:
            sku_group:   SKU group identifier (e.g. "jersey", "twill").
            months_back: Number of months to look back (default 24 = min_periods).

        Returns:
            List of float (total_kg per month), ordered by month ASC.
            Empty list when no rows found for the given sku_group.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                self._SQL_MONTHLY_ORDERS,
                sku_group,
                months_back,
            )
        result: list[float] = [float(row["total_kg"]) for row in rows]
        logger.debug(
            "demand_repository_fetch_monthly",
            sku_group=sku_group,
            months_back=months_back,
            n_rows=len(result),
        )
        return result


__all__ = ["DemandRepository"]
