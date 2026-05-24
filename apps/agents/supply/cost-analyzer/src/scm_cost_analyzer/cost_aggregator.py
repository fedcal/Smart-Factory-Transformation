"""Aggregatore costi da audit.actions (Plan 09-04, SCM-03).

Classe:
    HistoricalCostAggregator — query read-only su audit.actions per aggregare
    downtime + scrap + energy cost in una CostBreakdown.

Security (T-09-15 / Shared Pattern H):
    Tutto l'SQL è definito come ClassVar string constants e usa placeholder
    asyncpg $1..$N. Nessuna f-string interpolation nell'SQL.

Read-only design (SCM-03):
    HistoricalCostAggregator NON scrive mai su scm.* o audit.actions.
    Legge esclusivamente da audit.actions (cross-cluster, read-only).

Stima costi da audit.actions:
    - DOWNTIME_VERDICT: durata downtime * costo_ora_macchina (costo_ora default configurabile)
    - QUALITY_VERDICT: quantità scarto * costo_unitario_scarto (default configurabile)
    - ANOMALY_ALERT (energy cluster): kwh_anomalia * costo_kwh (default configurabile)

I campi estratti dai JSONB evidence_panel->tool_calls->0->result rispecchiano
la struttura verificata nei rispettivi agenti Phase 6/7.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

import structlog

from scm_cost_analyzer.models import CostBreakdown

_log = structlog.get_logger("agent.cost-analyzer.aggregator")

# ---------------------------------------------------------------------------
# SQL constants (ClassVar — per ispezione meta-test e sicurezza SQL)
# ---------------------------------------------------------------------------

#: Query aggregazione costo downtime da DOWNTIME_VERDICT in audit.actions.
#: Estrae duration_min da evidence_panel->tool_calls->0->result.
#: Costo stimato: duration_min / 60 * cost_per_hour_eur (moltiplicazione in Python).
SQL_DOWNTIME_COST: str = (
    "SELECT "
    "COALESCE(SUM("
    "  COALESCE("
    "    (evidence_panel->'tool_calls'->0->'result'->>'duration_min')::NUMERIC, "
    "    0"
    "  )"
    "), 0.0)::FLOAT AS total_downtime_min "
    "FROM audit.actions "
    "WHERE action_type = 'DOWNTIME_VERDICT' "
    "AND ts BETWEEN $1 AND $2"
)

#: Query aggregazione costo scarto da QUALITY_VERDICT in audit.actions.
#: Estrae quantity_scrapped da evidence_panel->tool_calls->0->result.
SQL_SCRAP_COST: str = (
    "SELECT "
    "COALESCE(SUM("
    "  COALESCE("
    "    (evidence_panel->'tool_calls'->0->'result'->>'quantity_scrapped')::NUMERIC, "
    "    0"
    "  )"
    "), 0.0)::FLOAT AS total_scrapped_kg "
    "FROM audit.actions "
    "WHERE action_type = 'QUALITY_VERDICT' "
    "AND ts BETWEEN $1 AND $2"
)

#: Query aggregazione anomalia energia da ANOMALY_ALERT in audit.actions.
#: Estrae anomaly_kwh da evidence_panel->tool_calls->0->result.
SQL_ENERGY_COST: str = (
    "SELECT "
    "COALESCE(SUM("
    "  COALESCE("
    "    (evidence_panel->'tool_calls'->0->'result'->>'anomaly_kwh')::NUMERIC, "
    "    0"
    "  )"
    "), 0.0)::FLOAT AS total_anomaly_kwh "
    "FROM audit.actions "
    "WHERE action_type = 'ANOMALY_ALERT' "
    "AND ts BETWEEN $1 AND $2"
)


# ---------------------------------------------------------------------------
# HistoricalCostAggregator
# ---------------------------------------------------------------------------


class HistoricalCostAggregator:
    """Aggregatore costi storici da audit.actions (read-only, SCM-03).

    Legge righe di audit per downtime, scarto e anomalie energetiche
    nel periodo [window_start, window_end] e restituisce un CostBreakdown.

    NON scrive mai su alcuna tabella (read-only by design).

    Args:
        pool: asyncpg.Pool per le query su audit.actions.
        downtime_cost_per_hour_eur: Costo orario macchina ferma in EUR (default 120.0).
        scrap_cost_per_kg_eur: Costo per kg scartato in EUR (default 8.0).
        energy_anomaly_cost_per_kwh_eur: Costo per kWh anomalia in EUR (default 0.25).
        roi_savings_factor: Fattore stima risparmio potenziale [0,1] (default 0.15 = 15%).
    """

    # ClassVar SQL constants per ispezione test e gate sicurezza SQL.
    _SQL_DOWNTIME: ClassVar[str] = SQL_DOWNTIME_COST
    _SQL_SCRAP: ClassVar[str] = SQL_SCRAP_COST
    _SQL_ENERGY: ClassVar[str] = SQL_ENERGY_COST

    def __init__(
        self,
        pool: object,
        *,
        downtime_cost_per_hour_eur: float = 120.0,
        scrap_cost_per_kg_eur: float = 8.0,
        energy_anomaly_cost_per_kwh_eur: float = 0.25,
        roi_savings_factor: float = 0.15,
    ) -> None:
        if pool is None:
            raise ValueError("pool non deve essere None")
        self._pool = pool
        self._downtime_cost_per_hour = downtime_cost_per_hour_eur
        self._scrap_cost_per_kg = scrap_cost_per_kg_eur
        self._energy_cost_per_kwh = energy_anomaly_cost_per_kwh_eur
        self._roi_savings_factor = max(0.0, min(1.0, roi_savings_factor))

    async def aggregate(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> CostBreakdown:
        """Aggrega downtime + scrap + energy cost da audit.actions nel periodo.

        Esegue tre query read-only in sequenza (asyncpg parametrizzato).
        I costi sono stimati dai metadati JSONB in evidence_panel:
          - downtime: duration_min / 60 * costo_ora
          - scrap: quantity_scrapped_kg * costo_kg
          - energy: anomaly_kwh * costo_kwh

        Args:
            window_start: Inizio finestra temporale (tz-aware datetime).
            window_end: Fine finestra temporale (tz-aware datetime).

        Returns:
            CostBreakdown immutabile con totale e stima ROI.
        """
        downtime_min = await self._fetch_downtime_min(window_start, window_end)
        scrapped_kg = await self._fetch_scrap_kg(window_start, window_end)
        anomaly_kwh = await self._fetch_anomaly_kwh(window_start, window_end)

        downtime_cost = (downtime_min / 60.0) * self._downtime_cost_per_hour
        scrap_cost = scrapped_kg * self._scrap_cost_per_kg
        energy_cost = anomaly_kwh * self._energy_cost_per_kwh
        total = downtime_cost + scrap_cost + energy_cost

        roi_savings_pct = min(100.0, self._roi_savings_factor * 100.0) if total > 0 else 0.0

        _log.info(
            "cost_aggregation_complete",
            downtime_min=downtime_min,
            scrapped_kg=scrapped_kg,
            anomaly_kwh=anomaly_kwh,
            downtime_cost_eur=round(downtime_cost, 2),
            scrap_cost_eur=round(scrap_cost, 2),
            energy_cost_eur=round(energy_cost, 2),
            total_eur=round(total, 2),
        )

        return CostBreakdown(
            downtime_cost_eur=round(downtime_cost, 2),
            scrap_cost_eur=round(scrap_cost, 2),
            energy_cost_eur=round(energy_cost, 2),
            total_eur=round(total, 2),
            roi_savings_pct=round(roi_savings_pct, 2),
        )

    async def _fetch_downtime_min(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> float:
        """Recupera minuti totali downtime da DOWNTIME_VERDICT in audit.actions."""
        async with self._pool.acquire() as conn:  # type: ignore[attr-defined]
            row = await conn.fetchrow(self._SQL_DOWNTIME, window_start, window_end)
        if row is None:
            return 0.0
        return float(row["total_downtime_min"] or 0.0)

    async def _fetch_scrap_kg(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> float:
        """Recupera kg totali scartati da QUALITY_VERDICT in audit.actions."""
        async with self._pool.acquire() as conn:  # type: ignore[attr-defined]
            row = await conn.fetchrow(self._SQL_SCRAP, window_start, window_end)
        if row is None:
            return 0.0
        return float(row["total_scrapped_kg"] or 0.0)

    async def _fetch_anomaly_kwh(
        self,
        window_start: datetime,
        window_end: datetime,
    ) -> float:
        """Recupera kWh anomalia energia da ANOMALY_ALERT in audit.actions."""
        async with self._pool.acquire() as conn:  # type: ignore[attr-defined]
            row = await conn.fetchrow(self._SQL_ENERGY, window_start, window_end)
        if row is None:
            return 0.0
        return float(row["total_anomaly_kwh"] or 0.0)


__all__ = [
    "HistoricalCostAggregator",
    "SQL_DOWNTIME_COST",
    "SQL_SCRAP_COST",
    "SQL_ENERGY_COST",
]
