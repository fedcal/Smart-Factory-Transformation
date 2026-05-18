"""Fault injection: burst noise — picco temporaneo di rumore ad alta ampiezza.

Funzione pura: non ha side-effects, testabile isolatamente (IOT-03).
"""

from __future__ import annotations


def apply_burst(
    base_value: float,
    magnitude_pct: float,
    t_in_burst: float,
    duration_s: float,
) -> float:
    """Applica burst noise con decay lineare verso la fine della durata.

    Durante il burst (0 <= t_in_burst <= duration_s), il valore viene amplificato
    di magnitude_pct% con decay lineare che riduce l'ampiezza a zero alla fine.
    Fuori dal burst (t_in_burst > duration_s), ritorna base_value invariato.

    Args:
        base_value: Valore nominale del sensore.
        magnitude_pct: Ampiezza massima burst in % del valore base (es. 200 = +200%).
        t_in_burst: Tempo trascorso dall'inizio del burst in secondi.
        duration_s: Durata totale del burst in secondi.

    Returns:
        float: Valore con burst noise applicato (o base_value se fuori burst).
    """
    if duration_s <= 0 or t_in_burst > duration_s or t_in_burst < 0:
        return base_value

    # Decay lineare: ampiezza piena all'inizio, zero alla fine del burst
    decay_factor = 1.0 - (t_in_burst / duration_s)
    amplitude = magnitude_pct / 100.0 * decay_factor
    return base_value * (1.0 + amplitude)
