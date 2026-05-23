"""Quality event generator — pubblica QualityEvent stocastici su NATS (plan 06-09).

Pattern S-6: `datetime.now(UTC)` OBBLIGATORIO (Pitfall 7, T-V6-naive-datetime).
Rate limit: <=10 eventi/min sotto profilo nominale, <=30 eventi/min sotto
profilo faulted (T-V6-dos-event-flood).

Il generator e' un task asyncio per-asset, analogo a `asset_emitter` in
`emitter.py`. Ad ogni tick:

    1. Calls `production_state.maybe_rotate(now)` per rotazione dye_lot_id.
    2. Decide se emettere un evento (Bernoulli con prob clamp <= nominale/faulted).
    3. Se emette: sceglie defect_type biased dalla family dell'asset + fault
       activity, costruisce QualityEvent valido, e fa
       `await nc.publish(f"quality.events.{asset.asset_id}", payload_json)`.

D-QI-04: dye_lot_id matcha `^DL-[A-Z0-9-]+-\\d{8}-[0-9a-f]+$` (validato da
QualityEvent Pydantic field pattern).

Determinismo: ogni asset ha un `random.Random` seeded da `hash(asset_id)` per
riproducibilita' nei test (no global random.seed pollution).
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog
from sft_assets._models import Asset, AssetFamily
from sft_domain.ops.quality import DefectType, QualityEvent

from sim_textile.models import FaultProfile
from sim_textile.production_state import ProductionState

_log = structlog.get_logger("sim-textile.quality-events")

# Per-family defect bias: ogni family ha un set di defect "naturali" che
# riceve il 90% della massa probabilistica; il resto si distribuisce uniforme
# sui defect rimanenti. Il bias riflette la realta' tessile (RESEARCH §10).
_FAMILY_DEFECT_BIAS: dict[AssetFamily, tuple[DefectType, ...]] = {
    AssetFamily.LOOM: ("broken_end", "mispick", "selvage_fault"),
    AssetFamily.SPINNING: ("slub", "neppy"),
    AssetFamily.WARPING: ("broken_end", "selvage_fault"),
    AssetFamily.DYEING: ("shade_deviation", "unlevel_dyeing"),
    AssetFamily.FINISHING: ("shade_deviation", "selvage_fault"),
}

_ALL_DEFECTS: tuple[DefectType, ...] = (
    "broken_end",
    "mispick",
    "slub",
    "neppy",
    "selvage_fault",
    "shade_deviation",
    "unlevel_dyeing",
)

# Rate limits (eventi/minuto/asset).
_RATE_NOMINAL_PER_MIN = 10
_RATE_FAULTED_PER_MIN = 30

# Frazione probabilistica del bias family: 90% massa sui defect "naturali".
_FAMILY_BIAS_WEIGHT = 0.90

# Probabilita' di emettere un difetto a tutta larghezza (full_width=True).
_FULL_WIDTH_PROBABILITY = 0.05


def _is_profile_faulted(profile: FaultProfile) -> bool:
    """Un profilo e' "faulted" se almeno una fault injection e' enabled."""
    fi = profile.fault_injection
    return bool(
        fi.drift.enabled
        or fi.jitter.enabled
        or fi.burst_noise.enabled
        or fi.alarm_storm.enabled
        or fi.nan_probability > 0.0
    )


def _compute_emit_probability(profile: FaultProfile, dt_sim_s: float) -> float:
    """Calcola la probabilita' di emit per-tick clamp ai rate limits.

    Args:
        profile: FaultProfile dell'asset.
        dt_sim_s: Sim-time per tick in secondi (1/sample_rate_hz).

    Returns:
        Probabilita' Bernoulli per-tick (in [0, 1]).
    """
    rate_per_min = (
        _RATE_FAULTED_PER_MIN if _is_profile_faulted(profile) else _RATE_NOMINAL_PER_MIN
    )
    ticks_per_min = 60.0 / max(dt_sim_s, 1e-9)
    if ticks_per_min <= 0:
        return 0.0
    p = rate_per_min / ticks_per_min
    return max(0.0, min(1.0, p))


def _pick_defect_type(
    asset_family: AssetFamily, rng: random.Random
) -> DefectType:
    """Scegli un defect_type con bias 90% sui defect family-naturali."""
    biased = _FAMILY_DEFECT_BIAS.get(asset_family, ())
    if not biased:
        return rng.choice(_ALL_DEFECTS)
    if rng.random() < _FAMILY_BIAS_WEIGHT:
        return rng.choice(biased)
    # 10% massa: scegli uniformemente dai defect NON-biased.
    others = tuple(d for d in _ALL_DEFECTS if d not in biased)
    if not others:
        return rng.choice(biased)
    return rng.choice(others)


def _defect_length_inches(defect_type: DefectType, rng: random.Random) -> float:
    """Lunghezza difetto in inches (lognormal, mean variabile per defect)."""
    # Mean (in inches) per tipo di difetto; full_width tende a essere maggiore.
    mean_by_type: dict[DefectType, float] = {
        "broken_end": 6.0,
        "mispick": 2.0,
        "slub": 0.5,
        "neppy": 0.25,
        "selvage_fault": 4.0,
        "shade_deviation": 12.0,
        "unlevel_dyeing": 24.0,
    }
    mu = mean_by_type.get(defect_type, 3.0)
    # lognormal con sigma=0.5; clamp a 0 (Pydantic Field ge=0 enforce).
    value = rng.lognormvariate(mu=0.0, sigma=0.5) * mu
    return max(0.0, float(value))


async def quality_event_emitter(
    asset: Asset,
    profile: FaultProfile,
    production_state: ProductionState,
    nc: Any,
    *,
    time_scale: float = 1.0,
    emit_probability: float | None = None,
) -> None:
    """Task asyncio che emette QualityEvent stocastici su NATS per un asset.

    Pattern S-6: SOLO `datetime.now(UTC)`.
    Rate limit: <=10/min (nominal) o <=30/min (faulted) per asset.

    Args:
        asset: Asset da simulare.
        profile: FaultProfile dell'asset (usato per rate clamp + nan_probability hint).
        production_state: ProductionState che fornisce + ruota `current_dye_lot_id`.
        nc: NATS client (interfaccia `await nc.publish(subject, payload_bytes)`).
        time_scale: Fattore accelerazione tempo (1.0 = realtime, >1.0 = accelerato).
        emit_probability: Override esplicito della Bernoulli per-tick (utile nei test).
            None => clamp automatico (rate_per_min / ticks_per_min).
    """
    dt_sim = 1.0 / profile.sample_rate_hz
    dt_wall = dt_sim / max(time_scale, 1e-9)

    if emit_probability is None:
        emit_p = _compute_emit_probability(profile, dt_sim)
    else:
        emit_p = max(0.0, min(1.0, float(emit_probability)))

    # RNG per-asset deterministico (asset_id seed) — no global random.seed pollution.
    # I difetti restano comunque "stocastici" rispetto al tempo di simulazione perche'
    # i tick avvengono a frequenza alta e la sequenza dipende dall'ordine asset+tick.
    rng = random.Random(asset.asset_id)

    asset_id = asset.asset_id
    family = asset.asset_family

    _log.info(
        "quality_event_emitter_started",
        asset_id=asset_id,
        family=family.value,
        emit_probability=emit_p,
        rate_per_min_cap=(
            _RATE_FAULTED_PER_MIN if _is_profile_faulted(profile) else _RATE_NOMINAL_PER_MIN
        ),
        time_scale=time_scale,
    )

    try:
        while True:
            now = datetime.now(UTC)  # SEMPRE tz-aware (Pattern S-6)

            production_state.maybe_rotate(now)

            if rng.random() < emit_p:
                defect_type = _pick_defect_type(family, rng)
                full_width = rng.random() < _FULL_WIDTH_PROBABILITY
                event = QualityEvent(
                    event_id=uuid4(),
                    asset_id=asset_id,
                    dye_lot_id=production_state.current_dye_lot_id,
                    defect_type=defect_type,
                    defect_length_inches=_defect_length_inches(defect_type, rng),
                    full_width=full_width,
                    position_meters=rng.uniform(0.0, 500.0),
                    timestamp=now,
                    source="simulator",
                )
                payload = event.model_dump_json().encode("utf-8")
                subject = f"quality.events.{asset_id}"
                try:
                    await nc.publish(subject, payload)
                except Exception as e:
                    # Errore di publish: log + continua (no silent swallow).
                    _log.error(
                        "quality_event_publish_error",
                        asset_id=asset_id,
                        subject=subject,
                        exc_info=e,
                    )

            await asyncio.sleep(dt_wall)

    except asyncio.CancelledError:
        _log.info("quality_event_emitter_cancelled", asset_id=asset_id)
        raise
    except Exception as e:
        _log.error("quality_event_emitter_error", asset_id=asset_id, exc_info=e)
        raise


def start_quality_event_tasks(
    assets: list[Asset],
    profiles: dict[str, FaultProfile],
    nc: Any,
    production_states: dict[str, ProductionState],
    *,
    time_scale: float = 1.0,
) -> list[asyncio.Task[None]]:
    """Crea (e ritorna) un task `quality_event_emitter` per ogni asset.

    Args:
        assets: Lista di asset da simulare.
        profiles: Dict family -> FaultProfile.
        nc: NATS client condiviso.
        production_states: Dict asset_id -> ProductionState (uno per asset).
        time_scale: Fattore accelerazione tempo applicato a tutti i task.

    Returns:
        Lista di asyncio.Task — il chiamante e' responsabile della cancellazione.
    """
    tasks: list[asyncio.Task[None]] = []
    for asset in assets:
        profile = profiles.get(asset.asset_family.value)
        if profile is None:
            _log.warning(
                "quality_event_emitter_skip_no_profile",
                asset_id=asset.asset_id,
                family=asset.asset_family.value,
            )
            continue
        ps = production_states.get(asset.asset_id)
        if ps is None:
            ps = ProductionState.bootstrap(asset_id=asset.asset_id)
            production_states[asset.asset_id] = ps
        task = asyncio.create_task(
            quality_event_emitter(asset, profile, ps, nc, time_scale=time_scale),
            name=f"quality-events-{asset.asset_id}",
        )
        tasks.append(task)
    return tasks


__all__ = ["quality_event_emitter", "start_quality_event_tasks"]
