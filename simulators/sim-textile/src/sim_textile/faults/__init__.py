"""Fault injection pure functions per sim-textile (IOT-03).

Tutte le funzioni sono pure: nessun side-effect, testabili isolatamente.
Mutazione stato tramite dataclasses.replace() — mai in-place (Pattern S-1).

Espone:
    maybe_nan(value, nan_probability) -> float
    apply_drift(state, rate_per_hour, dt_seconds) -> tuple[EmitterState, float]
    apply_jitter(value, band_pct) -> float
    apply_burst(base_value, magnitude_pct, t_in_burst, duration_s) -> float
    check_alarm_storm(state, now, threshold, window_s) -> tuple[EmitterState, bool]
"""

from sim_textile.faults.alarm_storm import check_alarm_storm
from sim_textile.faults.burst import apply_burst
from sim_textile.faults.drift import apply_drift
from sim_textile.faults.jitter import apply_jitter
from sim_textile.faults.nan import maybe_nan

__all__ = [
    "apply_burst",
    "apply_drift",
    "apply_jitter",
    "check_alarm_storm",
    "maybe_nan",
]
