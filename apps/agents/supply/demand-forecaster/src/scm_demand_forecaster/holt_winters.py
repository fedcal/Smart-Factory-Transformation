"""Holt-Winters additive forecasting — deterministic, numpy-only (SCM-04).

Triple Exponential Smoothing (Holt-Winters additive):
    - Fixed alpha/beta/gamma parameters (no MLE optimisation)
    - Seasonal-naive fallback for short series (len < min_periods)
    - All forecast values clamped to >= 0.0 (demand cannot be negative)
    - Fully reproducible: same series + same config → identical forecast

Phase 9 Pattern 9 (verbatim from 09-RESEARCH.md).
No statsmodels — numpy only (minimal deps + determinism).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HoltWintersConfig:
    """Configuration for triple exponential smoothing.

    All fields have fixed defaults per 09-RESEARCH.md Pattern 9.
    No MLE optimisation — parameters are locked at construction time.
    """

    alpha: float = 0.3        # level smoothing factor
    beta: float = 0.1         # trend smoothing factor
    gamma: float = 0.3        # seasonal smoothing factor
    season_length: int = 12   # 12 months for textile demand
    min_periods: int = 24     # minimum points for HW; below → fallback seasonal-naive


@dataclass(frozen=True)
class ForecastResult:
    """Output of forecast_holt_winters / _seasonal_naive_fallback.

    Attributes:
        sku_group:  SKU group identifier (passed through from caller).
        horizon:    Number of forecast steps.
        forecast:   List of forecast values, rounded to 2dp, all >= 0.0.
        method:     "holt_winters" | "seasonal_naive"
        config:     HoltWintersConfig used to produce this forecast.
    """

    sku_group: str
    horizon: int
    forecast: list[float]
    method: str               # "holt_winters" | "seasonal_naive"
    config: HoltWintersConfig


def _seasonal_naive_fallback(
    series: list[float],
    horizon: int,
    config: HoltWintersConfig,
    sku_group: str,
) -> ForecastResult:
    """Seasonal naive: repeat the last available season cyclically.

    For series=[100,200,300,400], season_length=4, horizon=6:
    → forecast=[100.0, 200.0, 300.0, 400.0, 100.0, 200.0]

    Args:
        series:    Historical demand series (any length).
        horizon:   Number of forecast steps.
        config:    HoltWintersConfig (uses season_length).
        sku_group: SKU group identifier.

    Returns:
        ForecastResult with method="seasonal_naive".
    """
    m = config.season_length
    tail = series[-m:] if len(series) >= m else series
    n_tail = len(tail)
    forecast = [float(tail[i % n_tail]) for i in range(horizon)]
    return ForecastResult(
        sku_group=sku_group,
        horizon=horizon,
        forecast=[round(f, 2) for f in forecast],
        method="seasonal_naive",
        config=config,
    )


def forecast_holt_winters(
    series: list[float],
    horizon: int,
    config: HoltWintersConfig = HoltWintersConfig(),
    sku_group: str = "unknown",
) -> ForecastResult:
    """Triple Exponential Smoothing (Holt-Winters additive) — deterministic, numpy-only.

    Falls back to seasonal_naive when len(series) < config.min_periods.
    All parameters are fixed (no MLE optimisation) — fully reproducible.
    All forecast values are clamped to >= 0.0 (demand cannot be negative).

    Initialisation (per 09-RESEARCH.md Pattern 9):
        L = mean(arr[:m])
        T = (mean(arr[m:2m]) - mean(arr[:m])) / m   if n >= 2m, else 0.0
        S = arr[:m] - L

    Recurrence for t in range(n):
        s_idx = t % m
        L_new = alpha * (arr[t] - S[s_idx]) + (1 - alpha) * (L + T)
        T_new = beta * (L_new - L) + (1 - beta) * T
        S[t + m] = gamma * (arr[t] - L) + (1 - gamma) * S[s_idx]
        L, T = L_new, T_new

    Forecast for h in range(horizon):
        f_h = max(0.0, L + (h+1)*T + S[n + (h % m)])

    Args:
        series:    Historical demand series. Must have len >= config.min_periods for HW;
                   shorter series fall back to seasonal_naive.
        horizon:   Number of forecast steps (>= 1).
        config:    HoltWintersConfig with fixed alpha/beta/gamma/season_length/min_periods.
        sku_group: SKU group identifier passed through to ForecastResult.

    Returns:
        ForecastResult with len(forecast) == horizon, method in {"holt_winters", "seasonal_naive"}.
    """
    n = len(series)
    if n < config.min_periods:
        return _seasonal_naive_fallback(series, horizon, config, sku_group)

    arr = np.array(series, dtype=float)
    m = config.season_length
    alpha, beta, gamma = config.alpha, config.beta, config.gamma

    # Initialisation
    L = float(np.mean(arr[:m]))
    T = float((np.mean(arr[m : 2 * m]) - np.mean(arr[:m])) / m) if n >= 2 * m else 0.0
    S = arr[:m] - L

    levels = np.zeros(n)
    trends = np.zeros(n)
    # Allocate n + m to accommodate seasonal updates (t + m can reach n - 1 + m).
    # We read back from seasonals for the forecast using the last-season slice.
    seasonals = np.zeros(n + m)
    seasonals[:m] = S

    for t in range(n):
        s_idx = t % m
        L_new = alpha * (arr[t] - seasonals[s_idx]) + (1 - alpha) * (L + T)
        T_new = beta * (L_new - L) + (1 - beta) * T
        seasonals[t + m] = gamma * (arr[t] - L) + (1 - gamma) * seasonals[s_idx]
        L, T = L_new, T_new
        levels[t] = L
        trends[t] = T

    forecasts = [
        max(0.0, L + (h + 1) * T + seasonals[n + (h % m)])
        for h in range(horizon)
    ]

    return ForecastResult(
        sku_group=sku_group,
        horizon=horizon,
        forecast=[round(f, 2) for f in forecasts],
        method="holt_winters",
        config=config,
    )


__all__ = [
    "HoltWintersConfig",
    "ForecastResult",
    "forecast_holt_winters",
    "_seasonal_naive_fallback",
]
