"""asyncpg repository for InventoryManager SCM-01.

Queries scm.inventory_levels + scm.sku_master to fetch the latest inventory
level per SKU using a DISTINCT ON window query.

Critical rules:
    - NEVER use .isoformat() on datetime params for asyncpg — pass datetime objects
      directly (Pitfall 7 from 09-RESEARCH.md).
    - All SQL uses $N positional parameters only — no string interpolation (T-09-09).
    - ClassVar SQL strings prevent accidental per-instance mutation.
"""

from __future__ import annotations

from typing import Any, ClassVar

import structlog

logger = structlog.get_logger("repository.inventory")


class InventoryRepository:
    """asyncpg-based repository for scm.inventory_levels + scm.sku_master (SCM-01).

    Thread-safe: all state is in the injected pool (no instance-level mutable state).
    The pool is acquired per query and released immediately (connection pooling).

    Security: T-09-09 — SQL parameters passed via asyncpg $N placeholders; no
    f-string interpolation or string concatenation with external input.
    """

    #: Latest inventory level per SKU via DISTINCT ON.
    #: Joins scm.inventory_levels to scm.sku_master to include reorder config.
    #: ANY($1::text[]) passes a list of sku_ids as a PostgreSQL text array — safe.
    _SQL_CURRENT_LEVELS: ClassVar[str] = """
        SELECT DISTINCT ON (il.sku_id)
            il.sku_id,
            il.quantity,
            il.ts,
            sm.reorder_point,
            sm.reorder_qty,
            sm.unit_cost_eur,
            sm.lead_time_days
        FROM scm.inventory_levels il
        JOIN scm.sku_master sm USING (sku_id)
        WHERE il.sku_id = ANY($1::text[])
        ORDER BY il.sku_id, il.ts DESC
    """

    #: Fetch all monitored SKUs when no filter is provided.
    _SQL_ALL_SKU_IDS: ClassVar[str] = """
        SELECT sku_id FROM scm.sku_master ORDER BY sku_id
    """

    def __init__(self, pool: Any) -> None:
        """Bind the asyncpg pool.

        Args:
            pool: asyncpg.Pool — the connection pool managed by the lifespan.
        """
        self._pool = pool

    async def fetch_current_levels(self, sku_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch latest inventory level per SKU.

        Uses DISTINCT ON (sku_id) to select the most recent row per SKU.
        Parameters are passed as a text[] array — never interpolated (T-09-09).

        Args:
            sku_ids: List of SKU identifier strings to query.
                     Must be non-empty; returns [] if sku_ids is empty.

        Returns:
            List of dicts with keys: sku_id, quantity, ts, reorder_point,
            reorder_qty, unit_cost_eur, lead_time_days.
            Returns [] when sku_ids is empty or no rows match.

        Note:
            datetime values from asyncpg arrive as tz-aware Python datetime objects.
            NEVER call .isoformat() on any datetime param passed to asyncpg (Pitfall 7).
        """
        if not sku_ids:
            return []

        logger.debug("inventory_repository_fetch", sku_count=len(sku_ids))
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(self._SQL_CURRENT_LEVELS, sku_ids)
        return [dict(r) for r in rows]

    async def fetch_all_sku_ids(self) -> list[str]:
        """Fetch all SKU IDs from scm.sku_master (default scope when state has no filter).

        Returns:
            List of sku_id strings ordered alphabetically.
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(self._SQL_ALL_SKU_IDS)
        return [r["sku_id"] for r in rows]


__all__ = ["InventoryRepository"]
