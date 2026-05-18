"""
tests/load/test_ingestion_smoke.py

Smoke load test — IOT-10 gate (1k msg/s × 10s).

Verifica che il pipeline NATS → TimescaleDB sostenga 1000 msg/s per 10 secondi
con p99 di ingest latency < 200ms.

Requirements: IOT-10 (smoke gate; full 5k×60s in Plan 03-07 via PR label)
Decisions: D-48 (steady-state load, no ramp-up, asyncio harness)
"""

import pytest

from tests.load.harness import run_load


# IOT-10 smoke gate threshold
SMOKE_RATE = 1000        # eventi/s
SMOKE_DURATION = 10      # secondi
SMOKE_P99_MS_TARGET = 200  # ms — IOT-10 gate


# Mix asset copertura 5 family (subset rappresentativo per smoke test)
_SMOKE_ASSETS = [
    ("LOOM-01", "loom", "warp_tension"),
    ("LOOM-02", "loom", "pick_density"),
    ("SPIN-01", "spinning", "spindle_speed"),
    ("WARP-01", "warping", "beam_tension"),
    ("DYE-01", "dyeing", "bath_temperature"),
    ("STEN-01", "finishing", "fabric_tension"),
]


@pytest.mark.load
@pytest.mark.load_smoke
@pytest.mark.integration
@pytest.mark.asyncio
async def test_smoke_1k_10s(compose_stack: dict) -> None:
    """Smoke gate IOT-10: 1k msg/s × 10s, p99 ingest latency < 200ms.

    Pubblica 10.000 eventi (1000/s × 10s) su NATS JetStream bypassando
    sim-textile per isolare il bottleneck I/O TimescaleDB.

    Assertions:
    - total_events >= 9500 (95% del target — tolleranza rate control)
    - p99_ms < SMOKE_P99_MS_TARGET (200ms — IOT-10 gate)
    """
    dsn = compose_stack["TIMESCALE_DSN"]
    nats_url = compose_stack["NATS_URL"]

    result = await run_load(
        dsn=dsn,
        nats_url=nats_url,
        target_rate=SMOKE_RATE,
        duration_s=SMOKE_DURATION,
        assets=_SMOKE_ASSETS,
    )

    # Throughput check (95% tolleranza)
    min_expected = SMOKE_RATE * SMOKE_DURATION * 0.95
    assert result.total_events >= min_expected, (
        f"Throughput insufficiente: {result.total_events} eventi pubblicati "
        f"(atteso >= {min_expected}). Rate effettivo: {result.rate_per_s:.1f} msg/s"
    )

    # IOT-10 gate: p99 < 200ms
    assert result.p99_ms < SMOKE_P99_MS_TARGET, (
        f"IOT-10 FAIL: p99 ingest latency = {result.p99_ms:.1f}ms "
        f"(soglia: {SMOKE_P99_MS_TARGET}ms). "
        f"Total events: {result.total_events}, rate: {result.rate_per_s:.1f} msg/s. "
        f"Considerare COPY batch vs executemany (RESEARCH A1 + Pattern 4)."
    )
