"""Fault injection: NaN — disconnessione sensore simulata.

Funzione pura: non ha side-effects, testabile isolatamente (IOT-03).
"""

from __future__ import annotations

import random


def maybe_nan(value: float, nan_probability: float) -> float:
    """Restituisce NaN con probabilita' nan_probability, altrimenti value.

    Args:
        value: Valore del sensore.
        nan_probability: Probabilita' di generare NaN (0.0 = mai, 1.0 = sempre).

    Returns:
        float: value oppure float("nan") secondo la probabilita'.
    """
    return float("nan") if random.random() < nan_probability else value
