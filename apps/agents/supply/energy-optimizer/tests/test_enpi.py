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


# ---------------------------------------------------------------------------
# enpi_actual contract
# ---------------------------------------------------------------------------


def test_enpi_actual_is_sum_kwh_over_sum_kg_for_valid_slots() -> None:
    """compute_enpi: enpi_actual = sum(kwh_valid) / sum(kg_valid) for slots with kg>0 (SCM-02).

    Example: kwh=[100,200,150], kg=[0,50,30] → valid=(200,50),(150,30) →
    enpi = (200+150)/(50+30) = 350/80 = 4.375 kWh/kg
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: compute_enpi("
        "kwh_readings=[100.0, 200.0, 150.0], kg_readings=[0.0, 50.0, 30.0], "
        "enpi_baseline_kwh_per_kg=3.80, is_peak_hour_flags=[False,False,False]) "
        "→ enpi_actual == 4.375. Slots with kg=0 must be skipped."
    )


def test_enpi_actual_mantis_dyeing_baseline() -> None:
    """compute_enpi: Mantis tintoria anchor — 4.12 kWh/kg, above baseline 3.80 (SCM-02, SCM-05).

    Mantis synthetic dataset: tintoria YTD 4.12 kWh/kg vs baseline 3.80 kWh/kg.
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: Mantis dyeing anchor: "
        "kwh_readings=[412.0], kg_readings=[100.0], baseline=3.80 "
        "→ enpi_actual=4.12, deviation_pct≈8.42, is_above_baseline=True."
    )


# ---------------------------------------------------------------------------
# deviation_pct contract
# ---------------------------------------------------------------------------


def test_deviation_pct_formula_actual_minus_baseline_over_baseline() -> None:
    """compute_enpi: deviation_pct = (actual - baseline) / baseline * 100 (SCM-02).

    Example: actual=4.375, baseline=3.80 → deviation_pct=(4.375-3.80)/3.80*100 ≈ 15.13%
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: deviation_pct formula: "
        "(enpi_actual - enpi_baseline) / enpi_baseline * 100. "
        "Example: actual=4.375, baseline=3.80 → deviation_pct ≈ 15.13 (rounded to 2dp)."
    )


def test_deviation_pct_negative_when_below_baseline() -> None:
    """compute_enpi: deviation_pct < 0 when enpi_actual < enpi_baseline (SCM-02).

    Mantis finishing: actual=2.18, baseline=2.20 → deviation_pct ≈ -0.91 (within target).
    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: deviation_pct is negative when "
        "enpi_actual < enpi_baseline. "
        "Mantis finishing: actual=2.18, baseline=2.20 → deviation_pct ≈ -0.91."
    )


# ---------------------------------------------------------------------------
# is_above_baseline contract
# ---------------------------------------------------------------------------


def test_is_above_baseline_true_when_enpi_actual_exceeds_baseline() -> None:
    """compute_enpi: is_above_baseline=True when enpi_actual > enpi_baseline (SCM-02).

    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: is_above_baseline=True when "
        "enpi_actual (4.375) > enpi_baseline (3.80)."
    )


def test_is_above_baseline_false_when_enpi_actual_below_baseline() -> None:
    """compute_enpi: is_above_baseline=False when enpi_actual <= enpi_baseline (SCM-02).

    Implementation target: scm_energy_optimizer.enpi.compute_enpi
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: is_above_baseline=False when "
        "enpi_actual (2.18) <= enpi_baseline (2.20). "
        "Mantis finishing example (within target)."
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
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: off_peak_kwh_pct uses ALL kwh_readings "
        "(not just valid kg>0 slots). Example: kwh=[100,200,150], is_peak=[True,False,False] "
        "→ off_peak_pct ≈ 77.78 (rounded to 2dp)."
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
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: compute_enpi("
        "kwh_readings=[100.0, 200.0], kg_readings=[0.0, 0.0], ...) "
        "must raise ValueError('Nessun dato valido (kg > 0) nei readings forniti') "
        "or similar. No silent inf/NaN return."
    )
