"""QueryTimescaleTool — TimescaleDB read-only query proxy.

LangChain BaseTool (langchain-core 1.x, Pydantic v2 native).
Async-first: _arun e' il metodo primario; _run solleva NotImplementedError.

CRITICAL: NESSUN f-string SQL — usa ESCLUSIVAMENTE $1, $2, ... placeholders (T-03-02-sql).
CRITICAL: SOLO import da `pydantic` v2 native (Pitfall 5 — compat shim vietato).
CRITICAL: NESSUN hardcoded TIMESCALE_DSN — solo `os.environ["TIMESCALE_DSN"]` (security.md).
CRITICAL: asyncpg.connect con statement_cache_size=0 (Pitfall 6 — TimescaleDB dynamic plan optimization).

Decisioni implementate:
    D-47 (sft-tools location)
    D-49 (sensor_events hypertable schema: asset_id, tag_id, timestamp_utc, value, unit)
    T-03-02-sql (placeholder SQL esclusivo)
    T-03-02-dos-pool (Phase 3: single connection per query — pool in Phase 11)
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import asyncpg
import pandas as pd
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from sft_tools.replay.models import QueryTimescaleArgs

UTC = timezone.utc

# SQL base per query sensor_events — SEMPRE $N placeholders, MAI f-string
# (T-03-02-sql, RESEARCH §Security check 1)
_BASE_SQL = (
    "SELECT asset_id, tag_id AS sensor_id, timestamp_utc AS timestamp, value, unit "
    "FROM sensor_events "
    "WHERE asset_id = $1 "
    "AND timestamp_utc >= $2 "
    "AND timestamp_utc <= $3"
)

_TAGS_SQL_SUFFIX = " AND tag_id = ANY($4)"


class QueryTimescaleTool(BaseTool):
    """Query read-only proxy per sensor_events hypertable TimescaleDB.

    Esegue SELECT sulla hypertable `sensor_events` via asyncpg con
    $1, $2, $3 placeholders (no f-string SQL — T-03-02-sql).

    Connessione da env TIMESCALE_DSN (no hardcode — security.md).
    statement_cache_size=0 per compatibilita' TimescaleDB plan optimization (Pitfall 6).

    Phase 3: single connection per query (no pool — pool deferred Phase 11 / plan 03-04).

    Async-first: usa await tool.ainvoke({...}) o await tool._arun(...).
    _run() e' disabilitato (solleva NotImplementedError).

    Decisioni: D-47, D-49, T-03-02-sql, Pitfall 6.
    """

    name: str = "query_timescale"
    description: str = (
        "Query TimescaleDB sensor_events hypertable for historical sensor data. "
        "Filters by asset_id, UTC time_range, and optional tag list. "
        "Returns DataFrame with columns: asset_id, sensor_id (tag_id), timestamp (UTC), "
        "value, unit. Connection via TIMESCALE_DSN environment variable. "
        "Use for Phase 4+ agents that need historical telemetry context."
    )
    args_schema: type[BaseModel] = QueryTimescaleArgs

    def _run(
        self,
        asset_id: str,
        time_range: tuple[datetime, datetime],
        tags: list[str] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Sync _run e' disabilitato — usa async _arun."""
        raise NotImplementedError(
            "QueryTimescaleTool e' async-only. "
            "Usa `await tool.ainvoke({...})` o `await tool._arun(...)` invece di _run."
        )

    async def _arun(
        self,
        asset_id: str,
        time_range: tuple[datetime, datetime],
        tags: list[str] | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """Query sensor_events hypertable con $N placeholders (no f-string SQL).

        Args:
            asset_id: Asset ID da interrogare (es. "LOOM-01").
            time_range: Tuple (start_utc, end_utc) entrambi tz-aware.
            tags: Lista tag_id da filtrare. None = tutti i tag.

        Returns:
            pandas.DataFrame con colonne:
            ["asset_id", "sensor_id", "timestamp", "value", "unit"]

        Raises:
            KeyError: Se TIMESCALE_DSN non e' nel environment.
            asyncpg.PostgresError: Su errore query.
        """
        dsn = os.environ["TIMESCALE_DSN"]  # Nessun default — security.md

        start_utc, end_utc = time_range

        # statement_cache_size=0: TimescaleDB usa dynamic plan optimization
        # che beneficia di cache miss (Pitfall 6 — RESEARCH §Pitfall 6)
        conn = await asyncpg.connect(dsn, statement_cache_size=0)
        try:
            if tags is None:
                # Query senza filtro tag: 3 parametri $1, $2, $3
                sql = _BASE_SQL
                records = await conn.fetch(sql, asset_id, start_utc, end_utc)
            else:
                # Query con filtro tag: 4 parametri $1, $2, $3, $4
                # NESSUN string interpolation — tag_id = ANY($4) con lista come parametro
                sql = _BASE_SQL + _TAGS_SQL_SUFFIX
                records = await conn.fetch(sql, asset_id, start_utc, end_utc, tags)
        finally:
            await conn.close()

        # Converte records asyncpg in DataFrame
        if not records:
            return pd.DataFrame(
                columns=["asset_id", "sensor_id", "timestamp", "value", "unit"]
            )

        rows = [dict(r) for r in records]
        df = pd.DataFrame(rows)

        # Rinomina colonne per schema consistente con ReplayRecord
        if "tag_id" in df.columns:
            df = df.rename(columns={"tag_id": "sensor_id"})
        if "timestamp_utc" in df.columns:
            df = df.rename(columns={"timestamp_utc": "timestamp"})

        return df
