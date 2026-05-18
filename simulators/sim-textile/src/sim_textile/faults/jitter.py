"""Fault injection: jitter — rumore casuale attorno al valore nominale.

Funzione pura: non ha side-effects, testabile isolatamente (IOT-03).
RESEARCH §Pattern 2 (lines 492-493): value * (1.0 + random.uniform(-band/100, band/100)).
"""

from __future__ import annotations

import random


def apply_jitter(value: float, band_pct: float) -> float:
    """Applica jitter casuale al valore nel range ±band_pct%.

    Args:
        value: Valore nominale del sensore.
        band_pct: Ampiezza banda jitter in percentuale (es. 5 = ±5%).

    Returns:
        float: Valore con rumore casuale applicato.
    """
    return value * (1.0 + random.uniform(-band_pct / 100.0, band_pct / 100.0))
