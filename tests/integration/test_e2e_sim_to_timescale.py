"""
tests/integration/test_e2e_sim_to_timescale.py

End-to-end roundtrip test: sim-textile → ot-bridge → NATS → TimescaleDB.

Verifica che dopo l'avvio dello stack, gli eventi emessi da sim-textile
vengano ingeriti in TimescaleDB con source='live' entro 1 minuto.

Requirements: IOT-06 (roundtrip E2E), IOT-04 (NATS path)
Decisions: D-49 (hypertable sensor_events), D-52 (NATS subjects)
"""

import asyncio

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sim_to_timescale_roundtrip(compose_stack: dict) -> None:
    """Verifica il roundtrip completo sim-textile → ot-bridge → NATS → TimescaleDB.

    Attende 10s per permettere il flush del buffer ot-bridge, poi interroga
    sensor_events per ≥1 row con source='live' nell'ultimo minuto.

    Verifica anche che almeno un asset_id distinto sia stato ingerito.
    """
    try:
        import asyncpg  # noqa: PLC0415
    except ImportError:
        pytest.skip("asyncpg non disponibile — installa con uv add asyncpg")
        return

    dsn = compose_stack["TIMESCALE_DSN"]

    # Attesa buffer flush ot-bridge (batch write interval)
    await asyncio.sleep(10)

    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS n, COUNT(DISTINCT asset_id) AS assets "
            "FROM sensor_events "
            "WHERE timestamp_utc > NOW() - INTERVAL '1 minute' "
            "AND source = $1",
            "live",
        )
    finally:
        await conn.close()

    assert row is not None, "Query sensor_events ha restituito None"
    n = row["n"]
    assets = row["assets"]

    assert n > 0, (
        f"Nessun evento con source='live' trovato in sensor_events nell'ultimo minuto. "
        f"Verificare che ot-bridge stia pubblicando (logs: docker compose logs ot-bridge)."
    )
    assert assets > 0, (
        f"Trovati {n} eventi ma 0 asset distinti — dati malformati o bug nel writer."
    )
