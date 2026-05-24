"""Contract tests for DemandForecaster MAPE computation (SCM-04, CR-05).

CONTRACT: compute_mape() deterministic pure function:
  - Computes Mean Absolute Percentage Error over matched (actual, forecast) pairs
  - Skips pairs where actual <= 0 (division by zero guard)
  - Per-point contribution clamped to 1.0 (100%) — prevents outlier dominance
  - Returns 0.0 on empty input or when no valid pairs remain
  - MAPE clamped to <= 100 before model construction (CR-05 — ValidationError prevention)

Phase 8 CR-05: Training coach KPI overflow → ValidationError on Pydantic model with le=.
MAPE must be clamped to <=100 before being stored in any Pydantic model field.

Implementation target: scm_demand_forecaster.mape.compute_mape
(Wave 2-3 plan: 09-05)
"""

from __future__ import annotations

import pytest

from scm_demand_forecaster.mape import compute_mape


# ---------------------------------------------------------------------------
# Basic MAPE computation
# ---------------------------------------------------------------------------


def test_compute_mape_basic_accuracy() -> None:
    """compute_mape: basic example with known values (SCM-04).

    actuals=[100, 200], forecasts=[110, 180]:
    - pair 1: |100-110|/100 = 0.10, clamped: 0.10
    - pair 2: |200-180|/200 = 0.10, clamped: 0.10
    - MAPE = (0.10+0.10)/2 * 100 = 10.0%
    Implementation target: scm_demand_forecaster.mape.compute_mape
    """
    result = compute_mape([100.0, 200.0], [110.0, 180.0])
    assert result == pytest.approx(10.0, abs=1e-9), f"Expected 10.0, got {result}"


def test_compute_mape_perfect_forecast_returns_zero() -> None:
    """compute_mape: perfect forecast (actuals == forecasts) returns 0.0 (SCM-04).

    Implementation target: scm_demand_forecaster.mape.compute_mape
    """
    result = compute_mape([100.0, 200.0, 300.0], [100.0, 200.0, 300.0])
    assert result == pytest.approx(0.0, abs=1e-9), f"Expected 0.0, got {result}"


# ---------------------------------------------------------------------------
# Skip actuals <= 0 contract
# ---------------------------------------------------------------------------


def test_compute_mape_skips_pairs_where_actual_is_zero() -> None:
    """compute_mape: skips pairs where actual == 0 (division guard, SCM-04).

    actuals=[0, 200], forecasts=[50, 180]:
    - pair 1: actual=0 → skip
    - pair 2: |200-180|/200 = 0.10, clamped: 0.10
    - MAPE = 0.10/1 * 100 = 10.0%
    Implementation target: scm_demand_forecaster.mape.compute_mape
    """
    result = compute_mape([0.0, 200.0], [50.0, 180.0])
    assert result == pytest.approx(10.0, abs=1e-9), f"Expected 10.0, got {result}"


def test_compute_mape_skips_pairs_where_actual_is_negative() -> None:
    """compute_mape: skips pairs where actual < 0 (SCM-04).

    Implementation target: scm_demand_forecaster.mape.compute_mape
    """
    result = compute_mape([-50.0, 100.0], [30.0, 120.0])
    assert result == pytest.approx(20.0, abs=1e-9), (
        f"Expected 20.0 (only pair 2: |100-120|/100=0.20), got {result}"
    )


def test_compute_mape_returns_zero_when_all_actuals_are_zero_or_negative() -> None:
    """compute_mape: returns 0.0 when no valid pairs remain after filtering (SCM-04).

    Implementation target: scm_demand_forecaster.mape.compute_mape
    """
    result = compute_mape([0.0, -10.0, 0.0], [5.0, 8.0, 3.0])
    assert result == pytest.approx(0.0, abs=1e-9), f"Expected 0.0, got {result}"


# ---------------------------------------------------------------------------
# Per-point contribution clamp to 1.0 (100%)
# ---------------------------------------------------------------------------


def test_per_point_contribution_clamped_to_one_hundred_percent() -> None:
    """compute_mape: per-point contribution clamped to 1.0 (100%) — outlier guard (SCM-04).

    Without clamping, a forecast of 200% error dominates: |actual-forecast|/actual = 2.0.
    With clamping: contribution = min(2.0, 1.0) = 1.0.

    actuals=[100], forecasts=[300]:
    - raw: |100-300|/100 = 2.0, clamped: 1.0
    - MAPE = 1.0/1 * 100 = 100.0%
    Implementation target: scm_demand_forecaster.mape.compute_mape
    """
    result = compute_mape([100.0], [300.0])
    assert result == pytest.approx(100.0, abs=1e-9), (
        f"Expected 100.0 (clamped from 200%), got {result}"
    )


def test_per_point_clamp_does_not_affect_normal_contributions() -> None:
    """compute_mape: clamp has no effect on contributions already < 1.0 (SCM-04).

    Implementation target: scm_demand_forecaster.mape.compute_mape
    """
    result = compute_mape([100.0, 100.0], [110.0, 300.0])
    # Pair 1: 0.10 (no clamp). Pair 2: min(2.0, 1.0) = 1.0.
    # Average: (0.10+1.0)/2 * 100 = 55.0%
    assert result == pytest.approx(55.0, abs=1e-6), (
        f"Expected 55.0, got {result}"
    )


# ---------------------------------------------------------------------------
# Empty input returns 0.0
# ---------------------------------------------------------------------------


def test_compute_mape_empty_actuals_returns_zero() -> None:
    """compute_mape: empty actuals list returns 0.0 (SCM-04).

    Implementation target: scm_demand_forecaster.mape.compute_mape
    """
    result = compute_mape([], [])
    assert result == 0.0


def test_compute_mape_empty_forecasts_returns_zero() -> None:
    """compute_mape: empty forecasts list returns 0.0 (SCM-04).

    Implementation target: scm_demand_forecaster.mape.compute_mape
    """
    result = compute_mape([100.0], [])
    # zip stops at shortest list → 0 pairs → returns 0.0
    assert result == 0.0


# ---------------------------------------------------------------------------
# MAPE clamped to <= 100 before model construction (CR-05)
# ---------------------------------------------------------------------------


def test_mape_is_clamped_to_100_before_model_construction() -> None:
    """MAPE is clamped to <=100 before use in Pydantic model fields (CR-05).

    Phase 8 CR-05: KPI exceeding model le= constraint causes ValidationError
    at model construction time. MAPE is theoretically bounded by 100% with
    per-point clamping, but this test verifies the clamp is applied explicitly
    before model assignment.

    Implementation target: scm_demand_forecaster.mape.compute_mape (or caller site)
    """
    # Even with extreme error, result must be clamped to <= 100.0
    result = compute_mape([100.0], [300.0])
    assert result <= 100.0, f"MAPE must be <= 100.0, got {result}"

    # Verify with multiple outlier pairs
    result_multi = compute_mape([1.0, 1.0, 1.0], [1000.0, 2000.0, 3000.0])
    assert result_multi <= 100.0, f"MAPE with outliers must be <= 100.0, got {result_multi}"
