"""
tests/load/test_ingestion_throughput.py

Full load test 5k msg/s × 60s steady-state (IOT-10 full gate) — D-48 asset mix.

Gated da PR-label `load-test` in CI o flag `--full-load-test` da riga di comando.
NON eseguito di default in CI (runtime ~75s su standard runner).

Design (D-48):
- Mix asset realistico: 60% loom, 20% spinning, 10% dyeing/finishing, 10% warping
- Steady-state senza ramp-up: il sistema deve essere stabile dal secondo zero
- Phase 3 amplifica i 30 asset reali per raggiungere il rate target (valido per
  misurare il bottleneck I/O TimescaleDB, NON per simulare 100 telai reali)
- Harness custom asyncio via tests/load/harness.py (asyncpg.Pool min=10 max=20)

Thresholds IOT-10:
- total_events >= FULL_RATE * FULL_DURATION * 0.95  (285_000 eventi min)
- p99_ms < FULL_P99_MS_TARGET  (200ms)
"""

import pytest

from tests.load.harness import run_load

# ============================================================
# Costanti D-48
# ============================================================
FULL_RATE = 5000               # eventi/s target
FULL_DURATION = 60             # secondi steady-state
FULL_P99_MS_TARGET = 200       # ms — IOT-10 gate

# ============================================================
# Asset mix D-48 (Phase 3 amplificazione dei 30 asset reali)
# Rate target ~5000 msg/s totale:
#   60% loom    (~3000 msg/s): 12 LOOM × 5 tag × ripetizione
#   20% spinning (~1000 msg/s): 8 SPIN × 5 tag × ripetizione
#   10% dyeing    (~300 msg/s): 4 DYE × 6 tag
#   10% warping   (~300 msg/s): 4 WARP × 5 tag
# Il harness cicla round-robin sugli asset per colmare il rate target.
# ============================================================

# 60% loom: combinazioni asset_id / tag per core mix (12 loom × 5 tag = 60 combo)
_LOOM_MIX = [
    (f"LOOM-{i:02d}", "loom", tag)
    for i in range(1, 13)
    for tag in [
        "warp_tension",
        "pick_density",
        "creel_speed",
        "broken_pick_count",
        "loom_temperature",
    ]
]

# 20% spinning: 8 ring frames × 5 tag = 40 combo
_SPIN_MIX = [
    (f"SPIN-{i:02d}", "spinning", tag)
    for i in range(1, 9)
    for tag in [
        "spindle_speed",
        "yarn_tension",
        "roller_temperature",
        "broken_end_count",
        "spindle_vibration",
    ]
]

# 10% dyeing: 4 DYE × 6 tag = 24 combo
_DYE_MIX = [
    (f"DYE-{i:02d}", "dyeing", tag)
    for i in range(1, 5)
    for tag in [
        "bath_temperature",
        "bath_ph",
        "dye_flow_rate",
        "drum_speed",
        "steam_pressure",
        "liquor_ratio",
    ]
]

# 10% finishing (stenter): 2 STEN × 6 tag = 12 combo
_STEN_MIX = [
    (f"STEN-{i:02d}", "finishing", tag)
    for i in range(1, 3)
    for tag in [
        "fabric_tension",
        "oven_temperature",
        "humidity_level",
        "web_speed",
        "chain_tension",
        "air_pressure",
    ]
]

# 10% warping: 4 WARP × 5 tag = 20 combo
_WARP_MIX = [
    (f"WARP-{i:02d}", "warping", tag)
    for i in range(1, 5)
    for tag in [
        "beam_tension",
        "creel_feed_rate",
        "warp_speed",
        "tension_imbalance",
        "yarn_count",
    ]
]

# Mix pesato per raggiungere distribuzione 60/20/10/10 via ripetizione
# Round-robin sul pool aggregato rispecchia il peso relativo
_FULL_ASSETS_MIX: list[tuple[str, str, str]] = (
    _LOOM_MIX * 3        # 60 × 3 = 180 entry — peso 60%
    + _SPIN_MIX * 1      # 40 × 1 = 40 entry  — peso ~13%
    + _DYE_MIX * 1       # 24 × 1 = 24 entry  — peso ~8%
    + _STEN_MIX * 1      # 12 × 1 = 12 entry  — peso ~4%
    + _WARP_MIX * 1      # 20 × 1 = 20 entry  — peso ~7%
)
# Totale: 276 entry → round-robin distribuisce ≈ 60/13/8/4/7 ≈ close enough per harness


@pytest.fixture()
def full_load_enabled(pytestconfig: pytest.Config) -> None:
    """Fixture che salta il test se --full-load-test non è passato.

    Garantisce che il full load test NON esegua in CI default (D-48 + claudes_discretion
    CI strategy: full test gated da PR-label `load-test`).
    """
    if not pytestconfig.getoption("--full-load-test", default=False):
        pytest.skip(
            "Full load test disabilitato. "
            "Abilitare con: --full-load-test (CLI) o PR-label `load-test` (CI). "
            "Esegui localmente con: make load-test-full"
        )


@pytest.mark.load_full
@pytest.mark.integration
@pytest.mark.asyncio
async def test_5k_60s(
    compose_stack: dict,  # fixture da tests/integration/conftest.py — fornisce DSN + NATS_URL
    full_load_enabled: None,  # fixture skip guard — deve essere PRIMA nell'args
) -> None:
    """Full load test IOT-10: 5k msg/s × 60s steady-state, p99 < 200ms (D-48).

    Pubblica ~300.000 eventi (5000/s × 60s) su NATS JetStream bypassando
    sim-textile per isolare il bottleneck I/O TimescaleDB con mix asset realistico.

    Asset mix D-48:
    - 60% loom (warp_tension, pick_density, creel_speed, broken_pick_count, loom_temperature)
    - 20% spinning (spindle_speed, yarn_tension, roller_temperature, broken_end_count, spindle_vibration)
    - 10% dyeing (bath_temperature, bath_ph, dye_flow_rate, drum_speed, steam_pressure, liquor_ratio)
    - 10% finishing/warping (fabric_tension, beam_tension, ...)

    Assertions IOT-10:
    - total_events >= 285_000 (95% del target)
    - p99_ms < 200ms

    Output PR-description:
        FULL LOAD: total=<N>, p50=<ms>ms, p99=<ms>ms, rate=<N>/s
    """
    dsn = compose_stack["TIMESCALE_DSN"]
    nats_url = compose_stack["NATS_URL"]

    result = await run_load(
        dsn=dsn,
        nats_url=nats_url,
        target_rate=FULL_RATE,
        duration_s=FULL_DURATION,
        assets=_FULL_ASSETS_MIX,
    )

    # Stampa report per PR description (copy-paste friendly)
    print(
        f"\nFULL LOAD: total={result.total_events}, "
        f"p50={result.p50_ms:.0f}ms, "
        f"p99={result.p99_ms:.0f}ms, "
        f"rate={result.rate_per_s:.0f}/s"
    )

    # IOT-10 gate: throughput >= 95% del target (285_000 eventi)
    min_expected = int(FULL_RATE * FULL_DURATION * 0.95)
    assert result.total_events >= min_expected, (
        f"Throughput insufficiente: {result.total_events} eventi pubblicati "
        f"(atteso >= {min_expected}). "
        f"Rate effettivo: {result.rate_per_s:.1f} msg/s "
        f"(target: {FULL_RATE} msg/s). "
        f"Controllare: D-48 harness rate control + asyncpg pool saturation."
    )

    # IOT-10 gate: p99 ingest latency < 200ms
    assert result.p99_ms < FULL_P99_MS_TARGET, (
        f"IOT-10 FAIL: p99 ingest latency = {result.p99_ms:.1f}ms "
        f"(soglia: {FULL_P99_MS_TARGET}ms). "
        f"Total events: {result.total_events}, rate: {result.rate_per_s:.1f} msg/s. "
        f"Considerare COPY batch fallback (RESEARCH §Pattern 4) o tune asyncpg pool."
    )
