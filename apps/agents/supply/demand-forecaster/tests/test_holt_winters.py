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


# ---------------------------------------------------------------------------
# Deterministic output contract
# ---------------------------------------------------------------------------


def test_forecast_holt_winters_deterministic_output_for_fixed_params() -> None:
    """forecast_holt_winters: same series + same config → exact same forecast (SCM-04).

    Tests that the implementation is truly deterministic (no random seed, no MLE).
    Two calls with identical inputs must return identical forecast values.
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract: "
        "Calling forecast_holt_winters(series, horizon=6, config=HoltWintersConfig()) twice "
        "with the same series must return identical forecast lists. "
        "No random seed or optimization — purely deterministic with fixed alpha/beta/gamma."
    )


def test_forecast_holt_winters_exact_values_for_fixed_series() -> None:
    """forecast_holt_winters: known series + fixed params → exact rounded forecast values (SCM-04).

    Uses a 24-element synthetic series with known seasonal pattern.
    Expected forecast values are pre-computed from the Holt-Winters formula.
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract: "
        "For series=[8000,9000,10000,12000,11000,9000,8000,8500,9000,10500,11500,12500, "
        "8200,9100,10200,12200,11200,9100,8100,8600,9100,10600,11600,12600], "
        "horizon=3, config=HoltWintersConfig(alpha=0.3, beta=0.1, gamma=0.3, season_length=12, min_periods=24): "
        "compute the expected values via the formula in 09-RESEARCH.md Pattern 9 and assert exact results "
        "(rounded to 2dp). The test body must contain the expected values once computed."
    )


def test_forecast_holt_winters_returns_forecast_result_with_correct_fields() -> None:
    """forecast_holt_winters: returns ForecastResult with all required fields (SCM-04).

    Fields: sku_group (str), horizon (int), forecast (list[float]),
            method (str), config (HoltWintersConfig).
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract: "
        "result.sku_group == 'jersey', result.horizon == 6, "
        "len(result.forecast) == 6, result.method == 'holt_winters', "
        "result.config is a HoltWintersConfig instance."
    )


# ---------------------------------------------------------------------------
# Seasonal naive fallback contract
# ---------------------------------------------------------------------------


def test_seasonal_naive_fallback_when_series_shorter_than_min_periods() -> None:
    """forecast_holt_winters: series < min_periods → fallback to seasonal_naive (SCM-04).

    Default min_periods = 24. A 12-element series triggers the fallback.
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract: "
        "forecast_holt_winters(series=[8000]*12, horizon=3, config=HoltWintersConfig(min_periods=24)) "
        "→ result.method == 'seasonal_naive'. "
        "Series of 12 elements < min_periods=24 triggers the fallback."
    )


def test_seasonal_naive_forecast_repeats_last_season() -> None:
    """seasonal_naive: forecast repeats the last season_length values cyclically (SCM-04).

    For series=[100,200,300,400], season_length=4, horizon=6:
    → forecast=[100,200,300,400,100,200] (cycles through last season).
    Implementation target: scm_demand_forecaster.holt_winters._seasonal_naive_fallback
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract: "
        "With series=[100,200,300,400] and config=HoltWintersConfig(season_length=4, min_periods=8), "
        "forecast_holt_winters(series, horizon=6) → "
        "result.forecast == [100.0, 200.0, 300.0, 400.0, 100.0, 200.0] "
        "(cycles through last season, rounded to 2dp)."
    )


def test_seasonal_naive_method_tag_in_result() -> None:
    """seasonal_naive fallback: result.method == 'seasonal_naive' (SCM-04).

    Distinguishing the method tag allows downstream consumers (and the API) to
    indicate to operators that the forecast uses the simpler fallback.
    Implementation target: scm_demand_forecaster.holt_winters.forecast_holt_winters
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract: "
        "When series length < min_periods, result.method == 'seasonal_naive'. "
        "When full HW is used, result.method == 'holt_winters'."
    )


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
    pytest.fail(
        "NOT IMPLEMENTED YET (09-05) — contract: "
        "A strongly declining series (e.g. [1000,500,200,100,50,25,10,5,2,1,0.5,0.1]*2) "
        "must produce non-negative forecasts. All values: max(0.0, raw_value). "
        "Never return negative demand in ForecastResult.forecast."
    )
