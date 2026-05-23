"""Downtime event generator — pubblica DowntimeEvent stocastici su NATS (plan 07-05).

Mirror diretto di `quality_event_generator.py` (Phase 6 06-09): stessa struttura
async per-asset, stesso pattern di rate-limit, stessa gestione CancelledError.

Pattern S-6: `datetime.now(UTC)` OBBLIGATORIO (Pitfall 7, T-V7-naive-datetime).
Rate limit: <=2 eventi/min sotto profilo nominale (downtime e' raro rispetto a
QualityEvent — 10/min), <=8 eventi/min sotto profilo faulted (T-V7-event-injection).

D-DA-01: payload DowntimeEvent emesso su NATS subject
`maintenance.downtime.<asset_id>`. Il reason_code e' pescato dalla
failure_modes.yaml maintenance taxonomy (MNT-05 / D-MNT-TAX) filtrata per
asset_family dell'asset corrente. Asset con family priva di entries (es.
FINISHING in YAML corrente) vengono saltati con warn-log una sola volta.

Determinismo: ogni asset ha un `random.Random` seeded da `asset_id` (oppure
`f"{seed}:{asset_id}"` quando l'utente passa un seed esplicito) per
riproducibilita' nei test (no global random.seed pollution — mirror 06-09 L172).
"""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sft_assets._models import Asset, AssetFamily
from sft_domain.failure_modes import load_failure_modes

from sim_textile.models import FaultProfile

_log = structlog.get_logger("sim-textile.downtime-events")

# ---------------------------------------------------------------------------
# D-DA-01: DowntimeEvent Pydantic model (frozen + extra=forbid)
# ---------------------------------------------------------------------------


class DowntimeEvent(BaseModel):
    """Evento di downtime — payload pubblicato su `maintenance.downtime.<asset_id>`.

    Schema D-DA-01 (07-CONTEXT.md). Tutti i campi sono validati a runtime
    via Pydantic v2; il modello e' immutabile (frozen=True) e rigetta campi
    sconosciuti (extra='forbid').
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: Annotated[str, Field(min_length=1, description="UUIDv4 identificativo evento")]
    asset_id: Annotated[str, Field(min_length=1, description="Asset id (es. 'LOOM-01')")]
    reason_code: Annotated[
        str,
        Field(
            min_length=1,
            description=(
                "Codice motivazione ISO 14224-style "
                "(da failure_modes.yaml maintenance.reason_code, MNT-05)."
            ),
        ),
    ]
    duration_min: Annotated[
        int, Field(ge=0, description="Durata downtime in minuti (>=0).")
    ]
    severity: Literal["minor", "major", "critical"]
    work_order_id: Annotated[str | None, Field(description="WO opzionale (None se nessuno)")]
    dye_lot_id: Annotated[
        str | None, Field(description="Dye lot opzionale (None se nessuno)")
    ]
    source: Literal["simulator", "operator"]
    timestamp: Annotated[datetime, Field(description="UTC tz-aware istante evento.")]

    @field_validator("timestamp")
    @classmethod
    def _ensure_tz_aware(cls, v: datetime) -> datetime:
        """Rifiuta datetime naive (Pattern S-6, T-V7-naive-datetime)."""
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("timestamp deve essere tz-aware (UTC).")
        return v


# ---------------------------------------------------------------------------
# Mapping AssetFamily (enum sft_assets) -> failure_modes asset_family (str YAML)
# ---------------------------------------------------------------------------

# `failure_modes.yaml` usa stringhe ad-hoc ("weaving", "spinning", "dyeing", ...)
# che NON corrispondono 1:1 ai valori dell'enum AssetFamily (LOOM/WARPING -> weaving).
# Questo dict materializza la mappatura "asset_family enum -> taxonomy family string"
# usata per filtrare la maintenance taxonomy.
_FAMILY_TAXONOMY_KEY: dict[AssetFamily, str] = {
    AssetFamily.LOOM: "weaving",
    AssetFamily.WARPING: "weaving",
    AssetFamily.SPINNING: "spinning",
    AssetFamily.DYEING: "dyeing",
    # FINISHING non ha (ancora) entry maintenance in failure_modes.yaml; verra'
    # filtrato fuori dal lookup _reason_codes_for_family => generator skip.
}


def _reason_codes_for_family(family: AssetFamily) -> tuple[str, ...]:
    """Restituisce i reason_code della maintenance taxonomy per la family.

    Filtra `failure_modes.yaml` selezionando le FailureMode con
    `maintenance is not None` e `asset_families` che include la stringa
    taxonomy associata al family enum.

    Returns:
        Tuple di reason_code (immutabile, ordine deterministico per id).
        Tuple vuota se la family non ha taxonomy associata o se non ci sono
        FailureMode con maintenance per quella family.
    """
    taxonomy_key = _FAMILY_TAXONOMY_KEY.get(family)
    if taxonomy_key is None:
        return ()
    fms = load_failure_modes()
    return tuple(
        fm.maintenance.reason_code
        for fm in fms
        if fm.maintenance is not None and taxonomy_key in fm.asset_families
    )


def _mttr_for_reason_code(reason_code: str) -> int:
    """Lookup MTTR target (minutes) per reason_code dalla maintenance taxonomy.

    Returns:
        MTTR target in minuti. Fallback a 30 se il reason_code non e' trovato
        (non dovrebbe mai succedere se _reason_codes_for_family ha pescato dal
        loader, ma e' un safety-net).
    """
    fms = load_failure_modes()
    for fm in fms:
        if fm.maintenance is not None and fm.maintenance.reason_code == reason_code:
            return fm.maintenance.mttr_target_minutes
    return 30


# ---------------------------------------------------------------------------
# Rate limits + sampling constants (mirror quality_event_generator.py)
# ---------------------------------------------------------------------------

# Rate limits (eventi/minuto/asset). Downtime e' raro rispetto a quality:
# nominale 2/min, faulted 8/min (vs quality 10/30).
_RATE_NOMINAL_PER_MIN = 2
_RATE_FAULTED_PER_MIN = 8

# Distribuzione severity: 75% minor, 20% major, 5% critical (07-PATTERNS Section 12).
_SEVERITY_WEIGHTS: tuple[tuple[str, float], ...] = (
    ("minor", 0.75),
    ("major", 0.20),
    ("critical", 0.05),
)

# Jitter applicato al MTTR per generare duration_min realistici (uniform +-50%).
_DURATION_JITTER_FRACTION = 0.5


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
    """Bernoulli per-tick clamp ai rate limits (mirror quality 06-09).

    Args:
        profile: FaultProfile dell'asset.
        dt_sim_s: sim-time per tick in secondi (1/sample_rate_hz).

    Returns:
        Probabilita' Bernoulli per-tick in [0, 1].
    """
    rate_per_min = (
        _RATE_FAULTED_PER_MIN if _is_profile_faulted(profile) else _RATE_NOMINAL_PER_MIN
    )
    ticks_per_min = 60.0 / max(dt_sim_s, 1e-9)
    if ticks_per_min <= 0:
        return 0.0
    p = rate_per_min / ticks_per_min
    return max(0.0, min(1.0, p))


def _pick_severity(rng: random.Random) -> str:
    """Sample severity da distribuzione pesata."""
    r = rng.random()
    cum = 0.0
    for label, weight in _SEVERITY_WEIGHTS:
        cum += weight
        if r < cum:
            return label
    return _SEVERITY_WEIGHTS[-1][0]


def _compute_duration_min(reason_code: str, severity: str, rng: random.Random) -> int:
    """Calcola duration_min per un evento.

    Base = MTTR target (failure_modes.yaml maintenance.mttr_target_minutes),
    scalato per severity (minor 0.5x, major 1.0x, critical 2.0x) + jitter +-50%.
    Clamp a [0, 10080] (limite MaintenanceSpec).
    """
    base = _mttr_for_reason_code(reason_code)
    severity_scale = {"minor": 0.5, "major": 1.0, "critical": 2.0}.get(severity, 1.0)
    scaled = base * severity_scale
    jitter = rng.uniform(1.0 - _DURATION_JITTER_FRACTION, 1.0 + _DURATION_JITTER_FRACTION)
    value = int(round(scaled * jitter))
    return max(0, min(value, 10080))


# Set di asset gia' "warn-loggati" per evitare log floods (process-local memo).
_WARNED_NO_TAXONOMY: set[str] = set()


async def downtime_event_emitter(
    asset: Asset,
    profile: FaultProfile,
    nc: Any,
    *,
    time_scale: float = 1.0,
    emit_probability: float | None = None,
    random_seed: str | None = None,
) -> None:
    """Task asyncio che emette DowntimeEvent stocastici su NATS per un asset.

    Mirror di `quality_event_emitter` (Phase 6 06-09):
        - Pattern S-6: SOLO `datetime.now(UTC)`.
        - Rate limit: <=2/min (nominal) o <=8/min (faulted) per asset.
        - Per-asset RNG seeded da `asset_id` (no global random.seed pollution).
        - `asyncio.CancelledError` viene re-raised (semantica pulita).

    Args:
        asset: Asset da simulare.
        profile: FaultProfile dell'asset (usato per rate clamp + family hint).
        nc: NATS client (`await nc.publish(subject, payload_bytes)`).
        time_scale: Fattore accelerazione tempo (1.0 = realtime).
        emit_probability: Override Bernoulli per-tick (utile nei test).
            None => clamp automatico (rate_per_min / ticks_per_min).
        random_seed: Seed opzionale; quando None usa solo `asset_id`. Quando
            valorizzato compone `f"{seed}:{asset.asset_id}"` per shift
            riproducibili in batch test multipli.
    """
    dt_sim = 1.0 / profile.sample_rate_hz
    dt_wall = dt_sim / max(time_scale, 1e-9)

    if emit_probability is None:
        emit_p = _compute_emit_probability(profile, dt_sim)
    else:
        emit_p = max(0.0, min(1.0, float(emit_probability)))

    # RNG per-asset deterministico — no global random.seed pollution (mirror 06-09 L172).
    seed_material = (
        asset.asset_id if random_seed is None else f"{random_seed}:{asset.asset_id}"
    )
    rng = random.Random(seed_material)

    asset_id = asset.asset_id
    family = asset.asset_family

    # Pre-compute reason_codes per la family. Se vuoto: log warn una volta + skip loop.
    reason_codes = _reason_codes_for_family(family)
    if not reason_codes:
        if asset_id not in _WARNED_NO_TAXONOMY:
            _log.warning(
                "downtime_event_emitter_skip_no_taxonomy",
                asset_id=asset_id,
                family=family.value,
                reason="No maintenance taxonomy entries in failure_modes.yaml for this family.",
            )
            _WARNED_NO_TAXONOMY.add(asset_id)
        # Loop comunque per onorare il contract async/cancellation, ma senza publish.
        try:
            while True:
                await asyncio.sleep(dt_wall)
        except asyncio.CancelledError:
            _log.info("downtime_event_emitter_cancelled", asset_id=asset_id)
            raise

    _log.info(
        "downtime_event_emitter_started",
        asset_id=asset_id,
        family=family.value,
        emit_probability=emit_p,
        rate_per_min_cap=(
            _RATE_FAULTED_PER_MIN if _is_profile_faulted(profile) else _RATE_NOMINAL_PER_MIN
        ),
        time_scale=time_scale,
        n_reason_codes=len(reason_codes),
    )

    try:
        while True:
            now = datetime.now(UTC)  # Pattern S-6 — SEMPRE tz-aware.

            if rng.random() < emit_p:
                reason_code = rng.choice(reason_codes)
                severity = _pick_severity(rng)
                duration_min = _compute_duration_min(reason_code, severity, rng)
                event = DowntimeEvent(
                    event_id=str(uuid4()),
                    asset_id=asset_id,
                    reason_code=reason_code,
                    duration_min=duration_min,
                    severity=severity,  # type: ignore[arg-type]
                    work_order_id=None,
                    dye_lot_id=None,
                    source="simulator",
                    timestamp=now,
                )
                payload = event.model_dump_json().encode("utf-8")
                subject = f"maintenance.downtime.{asset_id}"
                try:
                    await nc.publish(subject, payload)
                except Exception as e:
                    # Errore di publish: log + continua (no silent swallow — mirror 06-09).
                    _log.error(
                        "downtime_event_publish_error",
                        asset_id=asset_id,
                        subject=subject,
                        exc_info=e,
                    )

            await asyncio.sleep(dt_wall)

    except asyncio.CancelledError:
        _log.info("downtime_event_emitter_cancelled", asset_id=asset_id)
        raise
    except Exception as e:
        _log.error("downtime_event_emitter_error", asset_id=asset_id, exc_info=e)
        raise


def start_downtime_event_tasks(
    assets: list[Asset],
    profiles: dict[str, FaultProfile],
    nc: Any,
    *,
    time_scale: float = 1.0,
    random_seed: str | None = None,
) -> list[asyncio.Task[None]]:
    """Crea (e ritorna) un task `downtime_event_emitter` per ogni asset.

    Mirror di `start_quality_event_tasks` (06-09). Il chiamante e' responsabile
    della cancellazione (es. on graceful shutdown del simulator emitter loop).

    Args:
        assets: Lista di asset da simulare.
        profiles: Dict family -> FaultProfile.
        nc: NATS client condiviso.
        time_scale: Fattore accelerazione tempo applicato a tutti i task.
        random_seed: Seed opzionale propagato a ciascun task.

    Returns:
        Lista di asyncio.Task — il chiamante e' responsabile della cancellazione.
    """
    tasks: list[asyncio.Task[None]] = []
    for asset in assets:
        profile = profiles.get(asset.asset_family.value)
        if profile is None:
            _log.warning(
                "downtime_event_emitter_skip_no_profile",
                asset_id=asset.asset_id,
                family=asset.asset_family.value,
            )
            continue
        task = asyncio.create_task(
            downtime_event_emitter(
                asset, profile, nc, time_scale=time_scale, random_seed=random_seed
            ),
            name=f"downtime-events-{asset.asset_id}",
        )
        tasks.append(task)
    return tasks


__all__ = [
    "DowntimeEvent",
    "downtime_event_emitter",
    "start_downtime_event_tasks",
]
