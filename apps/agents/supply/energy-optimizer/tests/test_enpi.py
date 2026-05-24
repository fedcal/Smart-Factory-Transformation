"""Contract tests for EnergyOptimizer EnPI pure function (SCM-02).

CONTRACT: compute_enpi() deterministic pure function (ISO 50001 kWh/kg):
  - enpi_actual = sum(kwh) / sum(kg) over slots where kg > 0
  - deviation_pct = (enpi_actual - enpi_baseline) / enpi_baseline * 100
  - is_above_baseline = enpi_actual > enpi_baseline
  - off_peak_kwh_pct = % of total kWh consumed in off-peak hours
  - Raises ValueError when no slot with kg > 0 exists
  - Exact numeric results (use abs(...) < tolerance for floats)
  - No LLM; no asyncpg; fully synchronous.

Mantis EnPI anchors (synthetic):
  Dyeing (tintoria):    baseline 3.80 kWh/kg, actual YTD 4.12 kWh/kg → 8.42% above
  Finishing (finishing): baseline 2.20 kWh/kg, actual YTD 2.18 kWh/kg → -0.91% (within)

Implementation target: scm_energy_optimizer.enpi.compute_enpi
(Wave 2-3 plan: 09-03)
"""

from __future__ import annotations

import pytest

from scm_energy_optimizer.enpi import compute_enpi


# ---------------------------------------------------------------------------
# enpi_actual contract
# ---------------------------------------------------------------------------


def test_enpi_actual_is_sum_kwh_over_sum_kg_for_valid_slots() -> None:
    """compute_enpi: enpi_actual = sum(kwh_valid) / sum(kg_valid) for slots with kg>0 (SCM-02).

    Example: kwh=[100,200,150], kg=[0,50,30] → valid=(200,50),(150,30) →
    enpi = (200+150)/(50+30) = 350/80 = 4.375 kWh/kg
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    report = compute_enpi(
        kwh_readings=[100.0, 200.0, 150.0],
        kg_readings=[0.0, 50.0, 30.0],
        enpi_baseline_kwh_per_kg=3.80,
        is_peak_hour_flags=[False, False, False],
    )
    # Slot kg=0 must be skipped: valid slots are (200,50) and (150,30)
    # enpi_actual = (200+150)/(50+30) = 350/80 = 4.375
    assert abs(report.enpi_actual - 4.375) < 0.001, (
        f"Expected enpi_actual ≈ 4.375, got {report.enpi_actual}"
    )


def test_enpi_actual_mantis_dyeing_baseline() -> None:
    """compute_enpi: Mantis tintoria anchor — 4.12 kWh/kg, above baseline 3.80 (SCM-02, SCM-05).

    Mantis synthetic dataset: tintoria YTD 4.12 kWh/kg vs baseline 3.80 kWh/kg.
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    report = compute_enpi(
        kwh_readings=[412.0],
        kg_readings=[100.0],
        enpi_baseline_kwh_per_kg=3.80,
        is_peak_hour_flags=[True],
    )
    # enpi_actual = 412/100 = 4.12
    assert abs(report.enpi_actual - 4.12) < 0.001, (
        f"Expected enpi_actual ≈ 4.12, got {report.enpi_actual}"
    )
    # deviation_pct = (4.12 - 3.80) / 3.80 * 100 ≈ 8.42
    assert abs(report.deviation_pct - 8.42) < 0.05, (
        f"Expected deviation_pct ≈ 8.42, got {report.deviation_pct}"
    )
    assert report.is_above_baseline is True, "Mantis dyeing is above baseline"


# ---------------------------------------------------------------------------
# deviation_pct contract
# ---------------------------------------------------------------------------


def test_deviation_pct_formula_actual_minus_baseline_over_baseline() -> None:
    """compute_enpi: deviation_pct = (actual - baseline) / baseline * 100 (SCM-02).

    Example: actual=4.375, baseline=3.80 → deviation_pct=(4.375-3.80)/3.80*100 ≈ 15.13%
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    report = compute_enpi(
        kwh_readings=[100.0, 200.0, 150.0],
        kg_readings=[0.0, 50.0, 30.0],
        enpi_baseline_kwh_per_kg=3.80,
        is_peak_hour_flags=[False, False, False],
    )
    # enpi_actual = 4.375; deviation = (4.375 - 3.80) / 3.80 * 100 ≈ 15.13
    expected_deviation = (4.375 - 3.80) / 3.80 * 100
    assert abs(report.deviation_pct - round(expected_deviation, 2)) < 0.01, (
        f"Expected deviation_pct ≈ {round(expected_deviation, 2)}, got {report.deviation_pct}"
    )


def test_deviation_pct_negative_when_below_baseline() -> None:
    """compute_enpi: deviation_pct < 0 when enpi_actual < enpi_baseline (SCM-02).

    Mantis finishing: actual=2.18, baseline=2.20 → deviation_pct ≈ -0.91 (within target).
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    report = compute_enpi(
        kwh_readings=[218.0],
        kg_readings=[100.0],
        enpi_baseline_kwh_per_kg=2.20,
        is_peak_hour_flags=[False],
    )
    # enpi_actual = 2.18; deviation = (2.18 - 2.20) / 2.20 * 100 ≈ -0.91
    assert report.deviation_pct < 0, (
        f"Expected deviation_pct < 0 for below-baseline case, got {report.deviation_pct}"
    )
    assert abs(report.deviation_pct - (-0.91)) < 0.05, (
        f"Expected deviation_pct ≈ -0.91, got {report.deviation_pct}"
    )


# ---------------------------------------------------------------------------
# is_above_baseline contract
# ---------------------------------------------------------------------------


def test_is_above_baseline_true_when_enpi_actual_exceeds_baseline() -> None:
    """compute_enpi: is_above_baseline=True when enpi_actual > enpi_baseline (SCM-02).

    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    report = compute_enpi(
        kwh_readings=[100.0, 200.0, 150.0],
        kg_readings=[0.0, 50.0, 30.0],
        enpi_baseline_kwh_per_kg=3.80,
        is_peak_hour_flags=[False, False, False],
    )
    # enpi_actual = 4.375 > baseline 3.80
    assert report.is_above_baseline is True, (
        f"Expected is_above_baseline=True (actual={report.enpi_actual} > baseline={report.enpi_baseline})"
    )


def test_is_above_baseline_false_when_enpi_actual_below_baseline() -> None:
    """compute_enpi: is_above_baseline=False when enpi_actual <= enpi_baseline (SCM-02).

    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    report = compute_enpi(
        kwh_readings=[218.0],
        kg_readings=[100.0],
        enpi_baseline_kwh_per_kg=2.20,
        is_peak_hour_flags=[False],
    )
    # enpi_actual = 2.18 < baseline 2.20 → is_above_baseline = False
    assert report.is_above_baseline is False, (
        f"Expected is_above_baseline=False for Mantis finishing (actual={report.enpi_actual} <= baseline={report.enpi_baseline})"
    )


# ---------------------------------------------------------------------------
# off_peak_kwh_pct contract
# ---------------------------------------------------------------------------


def test_off_peak_kwh_pct_is_percentage_of_total_kwh_in_off_peak_hours() -> None:
    """compute_enpi: off_peak_kwh_pct = off_peak_kwh / total_kwh * 100 (SCM-02).

    Example: kwh=[100,200,150], is_peak=[True,False,False] →
    off_peak_kwh=350, total=450, off_peak_pct=77.78%
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    report = compute_enpi(
        kwh_readings=[100.0, 200.0, 150.0],
        kg_readings=[0.0, 50.0, 30.0],
        enpi_baseline_kwh_per_kg=3.80,
        is_peak_hour_flags=[True, False, False],
    )
    # All kwh_readings used: off_peak = 200+150 = 350; total = 450
    # off_peak_pct = 350/450*100 ≈ 77.78
    expected_pct = 350 / 450 * 100
    assert abs(report.off_peak_kwh_pct - round(expected_pct, 2)) < 0.01, (
        f"Expected off_peak_kwh_pct ≈ {round(expected_pct, 2)}, got {report.off_peak_kwh_pct}"
    )


# ---------------------------------------------------------------------------
# ValueError contract
# ---------------------------------------------------------------------------


def test_compute_enpi_raises_value_error_when_no_kg_positive_slot() -> None:
    """compute_enpi raises ValueError when all kg_readings are 0 or None (SCM-02).

    An EnPI computation with no valid production data is meaningless and must
    fail explicitly rather than returning inf or NaN.
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    with pytest.raises(ValueError, match="Nessun dato valido"):
        compute_enpi(
            kwh_readings=[100.0, 200.0],
            kg_readings=[0.0, 0.0],
            enpi_baseline_kwh_per_kg=3.80,
            is_peak_hour_flags=[False, False],
        )
