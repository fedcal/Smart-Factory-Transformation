"""Fault injection: drift — deriva incrementale nel tempo.

Funzione pura con mutazione replace-based su EmitterState frozen (Pattern S-1, IOT-03).
RESEARCH §Pattern 2 (lines 487-490): delta = rate_per_hour * (dt_seconds / 3600.0).
"""

from __future__ import annotations

from dataclasses import replace

from sim_textile.models import EmitterState


def apply_drift(
    state: EmitterState,
    rate_per_hour: float,
    dt_seconds: float,
) -> tuple[EmitterState, float]:
    """Applica deriva incrementale allo stato emitter.

    Funzione pura: non muta state, ritorna nuovo stato con drift aggiornato.

    Args:
        state: Stato emitter corrente (frozen dataclass).
        rate_per_hour: Tasso di deriva per ora.
        dt_seconds: Intervallo temporale in secondi dall'ultima chiamata.

    Returns:
        Tupla (new_state, drift_accumulated) dove new_state e' il nuovo stato
        con drift_accumulated aggiornato.
    """
    delta = rate_per_hour * (dt_seconds / 3600.0)
    new_state = replace(state, drift_accumulated=state.drift_accumulated + delta)
    return new_state, new_state.drift_accumulated
