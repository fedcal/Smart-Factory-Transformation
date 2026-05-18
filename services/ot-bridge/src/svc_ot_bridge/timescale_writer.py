"""TimescaleDB writer per svc-ot-bridge — asyncpg batch INSERT con executemany.

Accumula SensorEvent in buffer (size=500 o flush ogni 100ms) poi esegue
executemany con SQL parametrizzato $1..$7 (T-V5-sql — zero f-string SQL).

Sicurezza (T-03-04-sql):
    - _INSERT_SQL e' costante modulo — nessuna f-string interpolation
    - Solo placeholder $1..$7 — parametrized query, zero SQL injection path

Performance (T-03-04-pool-dos + Pitfall 6):
    - asyncpg.create_pool(min_size=10, max_size=20, statement_cache_size=0, command_timeout=10.0)
    - statement_cache_size=0 obbligatorio per TimescaleDB (piano dinamico non compatibile con prepared cache)
    - command_timeout=10s previene pool exhaustion su batch lenti
"""

from __future__ import annotations

import asyncio
from typing import Any

import asyncpg
import structlog

from svc_ot_bridge.models import SensorEvent

logger = structlog.get_logger(__name__)

# SQL parametrizzato — COSTANTE modulo, zero f-string (T-03-04-sql, T-V5-sql)
# Placeholder $1..$7: asset_id, tag_id, timestamp_utc, value, unit, quality_code, source
_INSERT_SQL = (
    "INSERT INTO sensor_events "
    "(asset_id, tag_id, timestamp_utc, value, unit, quality_code, source) "
    "VALUES ($1, $2, $3, $4, $5, $6, $7)"
)


class TimescaleWriter:
    """Writer asyncpg per TimescaleDB — batch executemany con flush per dimensione o intervallo.

    Accumula eventi in buffer fino a batch_size=500 o flush_interval_s=100ms,
    poi esegue executemany con _INSERT_SQL parametrizzato.

    Pool config (Pitfall 6 + T-PERF):
        min_size=10, max_size=20, statement_cache_size=0, command_timeout=10.0

    Usage:
        writer = TimescaleWriter(dsn="postgresql://...")
        await writer.start()
        await writer.push(event)
        await writer.close()
    """

    def __init__(
        self,
        dsn: str,
        batch_size: int = 500,
        flush_interval_s: float = 0.1,
    ) -> None:
        """Inizializza il writer.

        Args:
            dsn: PostgreSQL DSN (da env TIMESCALE_DSN).
            batch_size: Dimensione massima batch prima di flush (default 500).
            flush_interval_s: Intervallo max flush in secondi (default 0.1 = 100ms).
        """
        self._dsn = dsn
        self._batch_size = batch_size
        self._flush_interval_s = flush_interval_s
        self._buffer: list[SensorEvent] = []
        self._lock = asyncio.Lock()
        self._pool: Any = None
        self._flush_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Crea asyncpg pool e avvia il flush loop periodico.

        Pool config (Pitfall 6 + T-03-04-pool-dos):
            min_size=10, max_size=20 — capacity sostenuta 5k msg/s
            statement_cache_size=0 — TimescaleDB ha piano dinamico (breaking con prepared cache)
            command_timeout=10.0 — timeout per batch lenti, previene pool exhaustion
        """
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn,
            min_size=10,
            max_size=20,
            statement_cache_size=0,  # OBBLIGATORIO per TimescaleDB (Pitfall 6)
            command_timeout=10.0,
        )
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("timescale_writer_started", dsn_prefix=self._dsn[:20])

    async def push(self, event: SensorEvent) -> None:
        """Aggiunge un evento al buffer; flush se buffer >= batch_size.

        Args:
            event: SensorEvent da accodare.
        """
        async with self._lock:
            self._buffer.append(event)
            if len(self._buffer) >= self._batch_size:
                await self._flush_locked()

    async def _flush(self) -> None:
        """Flush pubblico — acquisce lock e chiama _flush_locked."""
        async with self._lock:
            await self._flush_locked()

    async def _flush_locked(self) -> None:
        """Flush interno — deve essere chiamato con lock gia' acquisto.

        Estrae il buffer corrente, costruisce le rows per executemany,
        esegue INSERT in batch con _INSERT_SQL parametrizzato ($1..$7).
        """
        if not self._buffer:
            return

        batch = self._buffer[:]
        self._buffer = []

        rows = [
            (
                e.asset_id,
                e.tag_id,
                e.timestamp_utc,
                e.value,
                e.unit,
                e.quality_code,
                e.source,
            )
            for e in batch
        ]

        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(_INSERT_SQL, rows)
            logger.debug("timescale_batch_written", count=len(rows))
        except Exception as exc:
            logger.error(
                "timescale_write_error",
                error=str(exc),
                batch_size=len(rows),
            )
            # Re-append falliti (best-effort recovery — Phase 11 gestira' dead-letter queue)
            # Per ora logga e droppa (evita blocking del bridge)

    async def _flush_loop(self) -> None:
        """Loop periodico di flush — flush ogni flush_interval_s secondi.

        Eseguito come asyncio.Task da start(). Termina su CancelledError.
        """
        try:
            while True:
                await asyncio.sleep(self._flush_interval_s)
                await self._flush()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("flush_loop_error", error=str(exc))

    async def close(self) -> None:
        """Cancella il flush loop, esegue flush finale e chiude il pool."""
        if self._flush_task is not None:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Flush finale di tutto il buffer rimasto
        await self._flush()

        if self._pool is not None:
            await self._pool.close()
            logger.info("timescale_writer_closed")
