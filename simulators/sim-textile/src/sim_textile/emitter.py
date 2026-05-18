"""Per-asset asyncio emitter task per sim-textile (IOT-01, D-50).

Ogni asset_emitter e' un asyncio task che genera eventi sensore realistici
applicando fault injection (drift, jitter, burst, nan, alarm_storm) in sequenza.

Pattern S-6: datetime.now(UTC) OBBLIGATORIO — mai naive datetime senza tz (Pitfall 7).
IOT-03: chain di fault functions pure (from sim_textile.faults).
RESEARCH §Pattern 2 (lines 468-503): struttura loop + apply fault.
"""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime

import structlog
from asyncua import ua

from sft_assets._models import Asset

from sim_textile.faults import (
    apply_burst,
    apply_drift,
    apply_jitter,
    check_alarm_storm,
    maybe_nan,
)
from sim_textile.metrics import (
    sim_events_emitted_total,
    sim_fault_injected_total,
)
from sim_textile.models import EmitterState, FaultProfile

logger = structlog.get_logger("sim-textile.emitter")


async def asset_emitter(
    asset: Asset,
    profile: FaultProfile,
    vars_map: dict,
    *,
    time_scale: float = 1.0,
) -> None:
    """Task asyncio che emette valori sensore per un asset con fault injection.

    Emette un campione per ogni tag_id nel profilo default_baseline ogni
    1/sample_rate_hz secondi (scalato per time_scale).

    Pattern S-6: SOLO datetime.now(UTC) — mai naive senza tz (Pitfall 7, T-03-03-tz-naive).
    IOT-03: chain fault pura (drift → jitter → burst → nan → alarm_storm).

    Args:
        asset: Asset da simulare (sft-assets Asset model).
        profile: FaultProfile con fault injection config.
        vars_map: Dict[(asset_id, tag_id) -> OPC-UA Node].
        time_scale: Fattore di accelerazione tempo (1.0 = realtime, >1.0 = accelerato).
    """
    state = EmitterState()
    dt = (1.0 / profile.sample_rate_hz) / time_scale
    asset_family = asset.asset_family.value
    asset_id = asset.asset_id

    logger.info(
        "emitter_started",
        asset_id=asset_id,
        family=asset_family,
        sample_rate_hz=profile.sample_rate_hz,
        time_scale=time_scale,
        dt_s=dt,
    )

    try:
        while True:
            # CRITICAL: tz-aware datetime (Pattern S-6, T-03-03-tz-naive)
            now = datetime.now(UTC)  # SEMPRE tz-aware UTC — mai naive (Pitfall 7, Pattern S-6)

            for tag_ref in asset.tags:
                tag_id = tag_ref.tag_id
                baseline_obj = profile.default_baseline.get(tag_id)
                if baseline_obj is None:
                    # Tag non ha baseline nel profilo — skip silenzioso
                    continue

                value = baseline_obj.value

                # --- Chain fault injection (drift → jitter → burst → nan) ---

                # 1. Drift
                fi = profile.fault_injection
                if fi.drift.enabled and tag_id in fi.drift.affected_tags:
                    state, drift_val = apply_drift(state, fi.drift.rate_per_hour, dt)
                    value += drift_val * baseline_obj.value
                    sim_fault_injected_total.labels(
                        type="drift", asset_family=asset_family
                    ).inc()

                # 2. Jitter
                if fi.jitter.enabled and tag_id in fi.jitter.affected_tags:
                    value = apply_jitter(value, fi.jitter.band_pct)
                    sim_fault_injected_total.labels(
                        type="jitter", asset_family=asset_family
                    ).inc()

                # 3. Burst noise
                if fi.burst_noise.enabled and tag_id in fi.burst_noise.affected_tags:
                    if state.burst_t_started is None:
                        # Inizia burst se t mod period_s < duration_s
                        period_s = fi.burst_noise.period_s
                        if period_s > 0:
                            t_in_period = now.timestamp() % period_s
                            if t_in_period < fi.burst_noise.duration_s:
                                from dataclasses import replace as dc_replace
                                state = dc_replace(state, burst_t_started=now)

                    if state.burst_t_started is not None:
                        t_in_burst = (now - state.burst_t_started).total_seconds()
                        if t_in_burst <= fi.burst_noise.duration_s:
                            value = apply_burst(
                                value,
                                fi.burst_noise.magnitude_pct,
                                t_in_burst,
                                fi.burst_noise.duration_s,
                            )
                            sim_fault_injected_total.labels(
                                type="burst", asset_family=asset_family
                            ).inc()
                        else:
                            # Fine burst — reset burst_t_started
                            from dataclasses import replace as dc_replace
                            state = dc_replace(state, burst_t_started=None)

                # 4. NaN (disconnessione sensore)
                value = maybe_nan(value, fi.nan_probability)
                if math.isnan(value):
                    sim_fault_injected_total.labels(
                        type="nan", asset_family=asset_family
                    ).inc()

                # --- Quality code OPC-UA ---
                quality_code = (
                    ua.StatusCode(0x80AF0000) if math.isnan(value) else ua.StatusCode(0)
                )

                # 5. Alarm storm (verifica dopo NaN per includere NaN come evento)
                if fi.alarm_storm.enabled and tag_id in fi.alarm_storm.affected_tags:
                    state, is_storm = check_alarm_storm(
                        state, now, fi.alarm_storm.threshold_events, fi.alarm_storm.window_s
                    )
                    if is_storm:
                        quality_code = ua.StatusCode(0x80AF0000)
                        sim_fault_injected_total.labels(
                            type="alarm_storm", asset_family=asset_family
                        ).inc()

                # --- Scrivi valore su OPC-UA Variable ---
                var_key = (asset_id, tag_id)
                if var_key in vars_map:
                    dv = ua.DataValue(
                        ua.Variant(value, ua.VariantType.Double),
                        SourceTimestamp=now,
                        StatusCode_=quality_code,
                    )
                    await vars_map[var_key].write_value(dv)

                # --- Prometheus counter ---
                sim_events_emitted_total.labels(
                    asset_family=asset_family,
                    asset_id=asset_id,
                    tag_id=tag_id,
                ).inc()

            await asyncio.sleep(dt)

    except asyncio.CancelledError:
        logger.info("emitter_cancelled", asset_id=asset_id)
        raise
    except Exception as e:
        # No silent swallow — log errore completo (coding-style.md error handling)
        logger.error("emitter_error", asset_id=asset_id, exc_info=e)
        await asyncio.sleep(1)
