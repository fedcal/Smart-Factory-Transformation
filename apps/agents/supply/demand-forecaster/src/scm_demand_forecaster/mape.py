"""Rolling MAPE computation — pure function (SCM-04, CR-05).

CONTRACT:
    - Computes Mean Absolute Percentage Error over matched (actual, forecast) pairs.
    - Skips pairs where actual <= 0 (division by zero guard).
    - Per-point contribution clamped to 1.0 (100%) — prevents outlier dominance.
    - Returns 0.0 on empty input or when no valid pairs remain.
    - MAPE clamped to <= 100.0 before return (CR-05 — ValidationError prevention).

Phase 9 Pattern 10 (verbatim from 09-RESEARCH.md), with explicit CR-05 final clamp.
"""

from __future__ import annotations


def compute_mape(actuals: list[float], forecasts: list[float]) -> float:
    """Compute Mean Absolute Percentage Error over matched (actual, forecast) pairs.

    Per-point contribution = min(|actual - forecast| / actual, 1.0).
    Final MAPE clamped to [0.0, 100.0] (CR-05 — prevents ValidationError on
    Pydantic models with le=100 constraint).

    Args:
        actuals:   Historical demand values. Pairs with actual <= 0 are skipped.
        forecasts: Forecast values (matched by index via zip).

    Returns:
        MAPE as a percentage in [0.0, 100.0].
        Returns 0.0 when:
            - either list is empty, or
            - all actual values are <= 0 (no valid pairs after filtering).

    Examples:
        >>> compute_mape([100.0, 200.0], [110.0, 180.0])
        10.0
        >>> compute_mape([], [])
        0.0
        >>> compute_mape([0.0, 200.0], [50.0, 180.0])
        10.0
    """
    if not actuals or not forecasts:
        return 0.0
    pairs = [(a, f) for a, f in zip(actuals, forecasts) if a > 0]
    if not pairs:
        return 0.0
    raw_mape = sum(min(abs(a - f) / a, 1.0) for a, f in pairs) / len(pairs) * 100
    # CR-05: clamp to [0.0, 100.0] before return — prevents ValidationError on
    # Pydantic models with le=100 constraint (Phase 8 Pitfall 6).
    return min(raw_mape, 100.0)


__all__ = ["compute_mape"]
