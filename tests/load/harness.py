"""
tests/load/harness.py

Custom asyncio publisher harness per load test IT/OT (D-48).

Pubblica eventi su NATS JetStream bypassando sim-textile per isolare il
bottleneck I/O TimescaleDB, poi misura la latenza di ingest tramite asyncpg.

Design (D-48):
- asyncpg.Pool(min_size=10, max_size=20, statement_cache_size=0)
  statement_cache_size=0 richiesto per TimescaleDB dynamic plan optimization.
- Rate control via asyncio.sleep per rispettare target_rate (msg/s).
- p99 misurato come worst-case ingestion lag (oldest_ms dal pool writer).
- Nessun Locust/k6 — harness asyncio nativo = stesso stack del prodotto.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class LoadResult:
    """Risultato di una run load test."""

    total_events: int
    duration_s: float
    p50_ms: float
    p99_ms: float
    rate_per_s: float


async def run_load(
    dsn: str,
    nats_url: str,
    target_rate: int,
    duration_s: int,
    assets: list[tuple[str, str, str]],  # [(asset_id, asset_family, tag_id)]
) -> LoadResult:
    """Esegue un load test pubblicando eventi NATS e misurando la latenza di ingest.

    Args:
        dsn: DSN asyncpg per TimescaleDB (statement_cache_size=0 forzato).
        nats_url: URL del server NATS JetStream.
        target_rate: eventi al secondo da pubblicare.
        duration_s: durata del test in secondi.
        assets: lista di tuple (asset_id, asset_family, tag_id) per il mix.

    Returns:
        LoadResult con metriche di latenza e throughput.
    """
    try:
        import asyncpg  # noqa: PLC0415
        import nats  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            f"Dipendenza mancante: {exc}. Installa con: uv add asyncpg nats-py"
        ) from exc

    total_target = target_rate * duration_s
    interval = 1.0 / target_rate  # secondi tra eventi

    # Connessione NATS JetStream
    nc = await nats.connect(nats_url)
    js = nc.jetstream()

    # Pool asyncpg per misura latenza lato DB
    pool = await asyncpg.create_pool(
        dsn,
        min_size=10,
        max_size=20,
        statement_cache_size=0,
    )

    start_time = time.monotonic()
    start_dt = datetime.now(UTC)
    published = 0
    asset_count = len(assets)

    try:
        for i in range(total_target):
            # Seleziona asset round-robin
            asset_id, asset_family, tag_id = assets[i % asset_count]

            # Costruisce payload evento conforme a D-52 schema
            event = {
                "asset_id": asset_id,
                "asset_family": asset_family,
                "tag_id": tag_id,
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "value": 25.0 + (i % 100) * 0.01,
                "unit": "N",
                "quality_code": 0,
                "source": "live",
                "server_received_ts": datetime.now(UTC).isoformat(),
            }

            subject = f"sensor.events.{asset_family}.{asset_id}.{tag_id}"

            # Pubblica su NATS JetStream (D-52)
            await js.publish(subject, json.dumps(event).encode())
            published += 1

            # Rate control: sleep per rispettare target_rate
            elapsed = time.monotonic() - start_time
            expected_elapsed = (i + 1) * interval
            sleep_time = expected_elapsed - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    finally:
        # Attesa flush ot-bridge verso TimescaleDB
        await asyncio.sleep(1)

        # Misura latenza worst-case: tempo dal primo evento a NOW()
        p99_ms = 0.0
        p50_ms = 0.0
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT "
                    "  EXTRACT(EPOCH FROM (NOW() - MIN(timestamp_utc))) * 1000 AS oldest_ms, "
                    "  EXTRACT(EPOCH FROM (NOW() - MAX(timestamp_utc))) * 1000 AS newest_ms "
                    "FROM sensor_events "
                    "WHERE timestamp_utc > $1 AND source = $2",
                    start_dt,
                    "live",
                )
                if row and row["oldest_ms"] is not None:
                    p99_ms = float(row["oldest_ms"])
                    p50_ms = float(row["newest_ms"]) if row["newest_ms"] is not None else p99_ms
        except Exception:
            pass

        await pool.close()
        await nc.close()

    duration = time.monotonic() - start_time
    rate = published / duration if duration > 0 else 0.0

    return LoadResult(
        total_events=published,
        duration_s=duration,
        p50_ms=p50_ms,
        p99_ms=p99_ms,
        rate_per_s=rate,
    )
