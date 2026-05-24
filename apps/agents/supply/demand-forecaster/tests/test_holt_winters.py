"""Contract tests for DemandForecaster Holt-Winters forecasting function (SCM-04).

CONTRACT: forecast_holt_winters() deterministic pure function (numpy, no statsmodels):
  - Deterministic output for fixed series + fixed alpha/beta/gamma (exact rounded values)
  - Falls back to seasonal_naive method when len(series) < min_periods (default 24)
  - seasonal_naive fallback: ForecastResult.method == 'seasonal_naive'
  - All forecast values are non-negative (clamped to 0.0 — CR-05 analog)
  - No LLM; no asyncpg; fully synchronous; numpy-only.

Mantis series anchors (synthetic):
  SKU group "jersey": ~12,000 kg/month, +35% summer peak, +20% winter peak
  SKU group "twill": ~8,000 kg/month, CV ~12% (more stable)

Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
(Wave 2-3 plan: 09-05)
"""

from __future__ import annotations

import pytest

from scm_demand_forecaster.holt_winters import (
    HoltWintersConfig,
    ForecastResult,
    _seasonal_naive_fallback,
    forecast_holt_winters,
)

# ---------------------------------------------------------------------------
# Synthetic 24-element series (2 full seasons of 12 months)
# Anchored on Mantis SKU group "jersey": ~12,000 kg/month, seasonal peaks
# ---------------------------------------------------------------------------

_JERSEY_SERIES: list[float] = [
    8000, 9000, 10000, 12000, 11000, 9000, 8000, 8500, 9000, 10500, 11500, 12500,
    8200, 9100, 10200, 12200, 11200, 9100, 8100, 8600, 9100, 10600, 11600, 12600,
]

_DEFAULT_CONFIG = HoltWintersConfig(
    alpha=0.3, beta=0.1, gamma=0.3, season_length=12, min_periods=24
)


# ---------------------------------------------------------------------------
# Deterministic output contract
# ---------------------------------------------------------------------------


def test_forecast_holt_winters_deterministic_output_for_fixed_params() -> None:
    """forecast_holt_winters: same series + same config → exact same forecast (SCM-04).

    Tests that the implementation is truly deterministic (no random seed, no MLE).
    Two calls with identical inputs must return identical forecast values.
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    r1 = forecast_holt_winters(_JERSEY_SERIES, horizon=6, config=_DEFAULT_CONFIG, sku_group="jersey")
    r2 = forecast_holt_winters(_JERSEY_SERIES, horizon=6, config=_DEFAULT_CONFIG, sku_group="jersey")
    assert r1.forecast == r2.forecast, "forecast_holt_winters must be deterministic"
    assert len(r1.forecast) == 6


def test_forecast_holt_winters_exact_values_for_fixed_series() -> None:
    """forecast_holt_winters: known series + fixed params → exact rounded forecast values (SCM-04).

    Uses the 24-element synthetic series from test module header.
    Expected values computed from the corrected Holt-Winters formula:
        seasonals[n + (h % m)]
    (CR-01/CR-02 fix: the old formula seasonals[n + h - m + (h % m)] was wrong
    and caused IndexError for horizon >= 19 and numerically wrong forecasts for h >= 1).
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    result = forecast_holt_winters(
        _JERSEY_SERIES, horizon=3, config=_DEFAULT_CONFIG, sku_group="jersey"
    )
    # Expected values computed from the corrected formula seasonals[n + (h % m)].
    # h=0: seasonals[24], h=1: seasonals[25], h=2: seasonals[26]
    expected = [8180.01, 9135.54, 10164.19]
    assert result.forecast == pytest.approx(expected, abs=0.01), (
        f"Expected {expected}, got {result.forecast}"
    )


def test_forecast_holt_winters_returns_forecast_result_with_correct_fields() -> None:
    """forecast_holt_winters: returns ForecastResult with all required fields (SCM-04).

    Fields: sku_group (str), horizon (int), forecast (list[float]),
            method (str), config (HoltWintersConfig).
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    result = forecast_holt_winters(
        _JERSEY_SERIES, horizon=6, config=_DEFAULT_CONFIG, sku_group="jersey"
    )
    assert result.sku_group == "jersey"
    assert result.horizon == 6
    assert len(result.forecast) == 6
    assert result.method == "holt_winters"
    assert isinstance(result.config, HoltWintersConfig)


# ---------------------------------------------------------------------------
# Seasonal naive fallback contract
# ---------------------------------------------------------------------------


def test_seasonal_naive_fallback_when_series_shorter_than_min_periods() -> None:
    """forecast_holt_winters: series < min_periods → fallback to seasonal_naive (SCM-04).

    Default min_periods = 24. A 12-element series triggers the fallback.
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    result = forecast_holt_winters(
        [8000.0] * 12, horizon=3, config=HoltWintersConfig(min_periods=24)
    )
    assert result.method == "seasonal_naive", (
        f"Expected 'seasonal_naive', got '{result.method}'"
    )


def test_seasonal_naive_forecast_repeats_last_season() -> None:
    """seasonal_naive: forecast repeats the last season_length values cyclically (SCM-04).

    For series=[100,200,300,400], season_length=4, horizon=6:
    → forecast=[100,200,300,400,100,200] (cycles through last season).
    Implementation target: scm_demand_forecaster.holt_winters._seasonal_naive_fallback
    """
    result = forecast_holt_winters(
        [100.0, 200.0, 300.0, 400.0],
        horizon=6,
        config=HoltWintersConfig(season_length=4, min_periods=8),
    )
    assert result.forecast == [100.0, 200.0, 300.0, 400.0, 100.0, 200.0], (
        f"Expected [100.0, 200.0, 300.0, 400.0, 100.0, 200.0], got {result.forecast}"
    )


def test_seasonal_naive_method_tag_in_result() -> None:
    """seasonal_naive fallback: result.method == 'seasonal_naive' (SCM-04).

    Distinguishing the method tag allows downstream consumers (and the API) to
    indicate to operators that the forecast uses the simpler fallback.
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    # Short series → seasonal_naive
    short_result = forecast_holt_winters([8000.0] * 12, horizon=3, config=_DEFAULT_CONFIG)
    assert short_result.method == "seasonal_naive"

    # Full series → holt_winters
    full_result = forecast_holt_winters(_JERSEY_SERIES, horizon=3, config=_DEFAULT_CONFIG)
    assert full_result.method == "holt_winters"


# ---------------------------------------------------------------------------
# Non-negative forecasts contract
# ---------------------------------------------------------------------------


def test_forecast_values_are_non_negative() -> None:
    """forecast_holt_winters: all forecast values are >= 0.0 (CR-05 analog, SCM-04).

    A decreasing trend + additive seasonality can produce negative forecast values.
    These must be clamped to 0.0 (demand cannot be negative).

    Phase 8 CR-05: KPI values that overflow model bounds cause ValidationError.
    The SCM analog: negative demand values are nonsensical and break downstream models.

    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    # Strongly declining series — likely to produce negative raw HW forecasts
    declining = [1000, 500, 200, 100, 50, 25, 10, 5, 2, 1, 0.5, 0.1] * 2
    result = forecast_holt_winters(declining, horizon=6, config=_DEFAULT_CONFIG)
    assert all(f >= 0.0 for f in result.forecast), (
        f"All forecast values must be >= 0.0, got {result.forecast}"
    )


# ---------------------------------------------------------------------------
# CR-01 regression: no IndexError for horizon=36 (the router maximum)
# ---------------------------------------------------------------------------


def test_forecast_holt_winters_no_index_error_for_horizon_36() -> None:
    """forecast_holt_winters: horizon=36 must NOT raise IndexError (CR-01 regression).

    The API router accepts horizon up to 36 (le=36 in DemandForecastRequest).
    Before the CR-01 fix, the formula seasonals[n + h - m + (h % m)] caused
    IndexError for h >= 18 (with m=12, n=24: index n+m=36 is out-of-bounds for
    an array of size n+m=36, since valid indices are 0..35).

    After the fix (seasonals[n + (h % m)]), the maximum index is n+m-1=35, which
    is always valid. This test asserts no exception is raised and the forecast
    has exactly 36 elements.

    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    result = forecast_holt_winters(
        _JERSEY_SERIES,
        horizon=36,
        config=_DEFAULT_CONFIG,
        sku_group="jersey",
    )
    assert len(result.forecast) == 36, (
        f"Expected 36 forecast values for horizon=36, got {len(result.forecast)}"
    )
    assert all(isinstance(v, float) for v in result.forecast), (
        "All forecast values must be float"
    )
    assert all(v >= 0.0 for v in result.forecast), (
        f"All forecast values must be non-negative, got {result.forecast}"
    )


# ---------------------------------------------------------------------------
# CR-02 regression: correct multi-step seasonal alignment
# ---------------------------------------------------------------------------


def test_forecast_holt_winters_correct_seasonal_alignment_on_periodic_series() -> None:
    """forecast_holt_winters: perfectly periodic series → forecasts repeat the seasonal pattern (CR-02).

    A series of exactly [100, 200, 300, 400] repeated 6 times (24 points, m=4)
    has zero trend and constant seasonal components. With gamma > 0, the HW
    smoothing converges the seasonal estimates to the true values.

    For a zero-trend perfectly-periodic series, the formula seasonals[n + (h % m)]
    produces forecasts that exactly reproduce the seasonal pattern:
      h=0 → 100.0, h=1 → 200.0, h=2 → 300.0, h=3 → 400.0,
      h=4 → 100.0, h=5 → 200.0, ...

    The old formula seasonals[n + h - m + (h % m)] would instead access stale
    mid-cycle seasonals, producing wrong values (e.g. h=1: 300.0 instead of 200.0).

    This test asserts that forecast[h] is within 1.0 of the expected seasonal value
    for the first 8 steps (two full cycles).

    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    periodic_pattern = [100.0, 200.0, 300.0, 400.0]
    # 24 points = 6 full seasons of length 4 — enough for HW (min_periods=24)
    series = periodic_pattern * 6

    config = HoltWintersConfig(
        alpha=0.3,
        beta=0.1,
        gamma=0.3,
        season_length=4,
        min_periods=24,
    )
    result = forecast_holt_winters(series, horizon=8, config=config, sku_group="test-periodic")

    assert result.method == "holt_winters", (
        f"Expected 'holt_winters' method, got '{result.method}'"
    )
    assert len(result.forecast) == 8

    for h in range(8):
        expected_seasonal = periodic_pattern[h % 4]
        got = result.forecast[h]
        assert abs(got - expected_seasonal) < 1.0, (
            f"h={h}: expected ~{expected_seasonal} (h%4={h%4}), "
            f"got {got} — seasonal misalignment detected (CR-02 regression)."
        )
