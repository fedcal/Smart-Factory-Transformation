"""Fault injection: alarm storm — valanga di allarmi entro finestra temporale.

Funzione pura con mutazione replace-based su EmitterState frozen (Pattern S-1, IOT-03).
RESEARCH §Pattern 2 (lines 498-503): pruning + append + storm check.

Sicurezza:
    - Usa datetime.now(UTC) upstream; questo modulo riceve datetime tz-aware (Pattern S-6)
    - Prune eventi fuori dalla finestra window_s per evitare accumulo illimitato (T-03-03-dos-emit)
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from sim_textile.models import EmitterState


def check_alarm_storm(
    state: EmitterState,
    now: datetime,
    threshold: int,
    window_s: float = 30.0,
) -> tuple[EmitterState, bool]:
    """Verifica se si e' generata una alarm storm nella finestra temporale.

    Funzione pura: non muta state, ritorna nuovo stato con recent_alarms aggiornato.
    Pruna eventi piu' vecchi di window_s prima di aggiungere il nuovo evento.

    Args:
        state: Stato emitter corrente (frozen dataclass).
        now: Timestamp corrente tz-aware (DEVE essere tz-aware — Pattern S-6).
        threshold: Numero minimo eventi nella finestra per scatenare storm.
        window_s: Larghezza finestra temporale in secondi (default 30).

    Returns:
        Tupla (new_state, is_storm) dove is_storm=True se il numero di eventi
        nella finestra raggiunge o supera threshold.
    """
    cutoff = now.timestamp() - window_s
    # Pruna eventi fuori dalla finestra (RESEARCH lines 499-500)
    pruned = tuple(t for t in state.recent_alarms if t.timestamp() >= cutoff)
    # Aggiunge l'evento corrente
    new_state = replace(state, recent_alarms=pruned + (now,))
    # Storm se raggiunge threshold DOPO l'aggiunta (RESEARCH line 502)
    storm = len(new_state.recent_alarms) >= threshold
    return new_state, storm
