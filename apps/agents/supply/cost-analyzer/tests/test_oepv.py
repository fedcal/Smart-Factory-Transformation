"""Contract tests for CostAnalyzer OEPV parametric simulator pure function (SCM-03, ECO-02/ECO-05).

CONTRACT: compute_oepv() deterministic pure function (OEPV scoring):
  - total_score = weight_technical * Pt + weight_economic * Pe (default: 0.70*Pt + 0.30*Pe)
  - Pe from non-linear ribasso curve: Pe_max * (1 - exp(-lambda * Ri / Ri_ref))
  - offer_eur = BA * (1 - Ri/100)
  - is_anomaly_warning = True when Ri >= anomaly_threshold_pct (configurable warning, NOT definitive)
  - sensitivity dict for ±1%, ±5%, ±10% ribasso variations
  - ValueError on out-of-range ribasso (outside [0,100])
  - ValueError on out-of-range Pt (outside [0, 100*weight_technical])
  - ALL coefficients from OepvConfig (no hardcoded values in implementation — ECO-05)
  - No LLM; no asyncpg; fully synchronous.

OEPV boundary note (F9 vs F12):
  Phase 9 is a PARAMETRIC SIMULATOR — coefficients are configurable, not definitively
  calibrated to Codice Appalti 2023. Phase 12 provides the legally precise formula.

Mantis anchor (synthetic): Base d'Asta = €108,000 (configurable)

Implementation target: scm_cost_analyzer.oepv.compute_oepv
(Wave 2-3 plan: 09-04)
"""

from __future__ import annotations

import math
import pytest

from scm_cost_analyzer.oepv import OepvConfig, compute_oepv


# ---------------------------------------------------------------------------
# total_score = 0.70*Pt + 0.30*Pe contract
# ---------------------------------------------------------------------------


def test_total_score_is_weighted_sum_of_pt_and_pe() -> None:
    """compute_oepv: total_score = 0.70*Pt + 0.30*Pe (default OepvConfig weights, SCM-03).

    Example: Pt=60, Ri=10% → Pe = 30*(1-exp(-3*10/20)) ≈ 23.31 →
    total = 0.70*60 + 0.30*23.31 ≈ 42 + 6.993 ≈ 48.99
    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    cfg = OepvConfig()
    result = compute_oepv(ribasso_pct=10.0, pt=60.0, config=cfg)

    pe_expected = cfg.pe_max * (1 - math.exp(-cfg.lambda_curve * 10.0 / cfg.ribasso_ref_pct))
    total_expected = cfg.weight_technical * 60.0 + cfg.weight_economic * pe_expected

    assert abs(result.total_score - total_expected) < 1e-3, (
        f"total_score={result.total_score!r} expected≈{total_expected:.4f}"
    )


def test_total_score_uses_config_weights_not_hardcoded() -> None:
    """compute_oepv: weights come from OepvConfig, not hardcoded 0.70/0.30 (ECO-05).

    Testing with custom weights (0.60 technical, 0.40 economic) verifies no hardcoding.
    Implementation target: scm_cost_analyzer.oepv.compute_oepv + OepvConfig
    """
    cfg = OepvConfig(weight_technical=0.60, weight_economic=0.40)
    result = compute_oepv(ribasso_pct=10.0, pt=50.0, config=cfg)

    pe_expected = cfg.pe_max * (1 - math.exp(-cfg.lambda_curve * 10.0 / cfg.ribasso_ref_pct))
    total_expected = 0.60 * 50.0 + 0.40 * pe_expected

    assert abs(result.total_score - total_expected) < 1e-3, (
        f"total_score={result.total_score!r} expected≈{total_expected:.4f} "
        f"with custom weights 0.60/0.40"
    )


# ---------------------------------------------------------------------------
# Pe non-linear ribasso curve contract
# ---------------------------------------------------------------------------


def test_pe_from_nonlinear_ribasso_curve() -> None:
    """compute_oepv: Pe = Pe_max * (1 - exp(-lambda * Ri / Ri_ref)) (ECO-02).

    Default OepvConfig: pe_max=30, lambda_curve=3.0, ribasso_ref_pct=20.0
    Example: Ri=10% → Pe = 30*(1-exp(-3*10/20)) = 30*(1-exp(-1.5)) ≈ 30*(1-0.2231) ≈ 23.31
    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    cfg = OepvConfig()
    result = compute_oepv(ribasso_pct=10.0, pt=60.0, config=cfg)

    pe_expected = cfg.pe_max * (1 - math.exp(-cfg.lambda_curve * 10.0 / cfg.ribasso_ref_pct))

    assert abs(result.pe - pe_expected) < 1e-2, (
        f"pe={result.pe!r} expected≈{pe_expected:.4f}"
    )


def test_pe_curve_monotonically_increases_with_ribasso() -> None:
    """compute_oepv: Pe is monotonically non-decreasing as ribasso increases (ECO-02).

    The non-linear exponential curve means higher ribasso always yields higher (or equal) Pe.
    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    cfg = OepvConfig()
    pe_5 = compute_oepv(ribasso_pct=5.0, pt=50.0, config=cfg).pe
    pe_10 = compute_oepv(ribasso_pct=10.0, pt=50.0, config=cfg).pe
    pe_15 = compute_oepv(ribasso_pct=15.0, pt=50.0, config=cfg).pe
    pe_20 = compute_oepv(ribasso_pct=20.0, pt=50.0, config=cfg).pe

    assert pe_5 < pe_10, f"Pe(5%)={pe_5} should be < Pe(10%)={pe_10}"
    assert pe_10 < pe_15, f"Pe(10%)={pe_10} should be < Pe(15%)={pe_15}"
    assert pe_15 < pe_20, f"Pe(15%)={pe_15} should be < Pe(20%)={pe_20}"


# ---------------------------------------------------------------------------
# offer_eur contract
# ---------------------------------------------------------------------------


def test_offer_eur_is_ba_times_one_minus_ribasso_fraction() -> None:
    """compute_oepv: offer_eur = BA * (1 - Ri/100) (SCM-03, Mantis anchor BA=€108,000).

    Example: BA=108000, Ri=10% → offer_eur = 108000 * 0.90 = 97200.00
    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    cfg = OepvConfig()  # base_d_asta_eur=108000 (default)
    result = compute_oepv(ribasso_pct=10.0, pt=60.0, config=cfg)

    expected_offer = 108_000.0 * (1 - 10.0 / 100)
    assert abs(result.offer_eur - expected_offer) < 1e-2, (
        f"offer_eur={result.offer_eur!r} expected={expected_offer:.2f}"
    )


def test_offer_eur_uses_config_base_d_asta_not_hardcoded() -> None:
    """compute_oepv: BA comes from OepvConfig.base_d_asta_eur (not hardcoded 108000, ECO-05).

    Testing with custom BA=200000 verifies no hardcoding.
    Implementation target: scm_cost_analyzer.oepv.compute_oepv + OepvConfig
    """
    cfg = OepvConfig(base_d_asta_eur=200_000.0)
    result = compute_oepv(ribasso_pct=10.0, pt=60.0, config=cfg)

    expected_offer = 200_000.0 * (1 - 10.0 / 100)
    assert abs(result.offer_eur - expected_offer) < 1e-2, (
        f"offer_eur={result.offer_eur!r} expected={expected_offer:.2f} "
        f"with custom BA=200000"
    )


# ---------------------------------------------------------------------------
# is_anomaly_warning contract (configurable — NOT definitive F12 boundary)
# ---------------------------------------------------------------------------


def test_is_anomaly_warning_true_when_ribasso_at_or_above_threshold() -> None:
    """compute_oepv: is_anomaly_warning=True when Ri >= anomaly_threshold_pct (SCM-03).

    Default threshold: 20.0%. F9 = warning only (NOT definitive Codice Appalti exclusion).
    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    cfg = OepvConfig()  # anomaly_threshold_pct=20.0 (default)
    result = compute_oepv(ribasso_pct=20.0, pt=60.0, config=cfg)

    assert result.is_anomaly_warning is True, (
        "is_anomaly_warning deve essere True quando Ri(20%) >= threshold(20%) — "
        "NOTA: warning configurabile, NON esclusione definitiva (F12)."
    )


def test_is_anomaly_warning_false_when_ribasso_below_threshold() -> None:
    """compute_oepv: is_anomaly_warning=False when Ri < anomaly_threshold_pct (SCM-03).

    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    cfg = OepvConfig()  # anomaly_threshold_pct=20.0 (default)
    result = compute_oepv(ribasso_pct=15.0, pt=60.0, config=cfg)

    assert result.is_anomaly_warning is False, (
        "is_anomaly_warning deve essere False quando Ri(15%) < threshold(20%)."
    )


def test_anomaly_threshold_is_configurable_via_oepv_config() -> None:
    """compute_oepv: anomaly_threshold comes from OepvConfig, not hardcoded (ECO-05).

    Testing with custom threshold=30.0 verifies no hardcoding.
    Implementation target: scm_cost_analyzer.oepv.compute_oepv + OepvConfig
    """
    cfg = OepvConfig(anomaly_threshold_pct=30.0)

    result_below = compute_oepv(ribasso_pct=25.0, pt=60.0, config=cfg)
    assert result_below.is_anomaly_warning is False, (
        "Ri(25%) < threshold(30%) deve produrre is_anomaly_warning=False."
    )

    result_at = compute_oepv(ribasso_pct=30.0, pt=60.0, config=cfg)
    assert result_at.is_anomaly_warning is True, (
        "Ri(30%) >= threshold(30%) deve produrre is_anomaly_warning=True."
    )


# ---------------------------------------------------------------------------
# sensitivity dict contract (ECO-05)
# ---------------------------------------------------------------------------


def test_sensitivity_dict_contains_plus_minus_1_5_10_percent_keys() -> None:
    """compute_oepv: sensitivity dict has keys for ±1%, ±5%, ±10% ribasso deltas (ECO-05).

    Expected keys: '-10%', '-5%', '-1%', '+1%', '+5%', '+10%'
    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    result = compute_oepv(ribasso_pct=10.0, pt=60.0)

    expected_keys = {"-10%", "-5%", "-1%", "+1%", "+5%", "+10%"}
    assert expected_keys.issubset(set(result.sensitivity.keys())), (
        f"Chiavi sensitivity mancanti. Trovate: {set(result.sensitivity.keys())}, "
        f"attese almeno: {expected_keys}"
    )


def test_sensitivity_values_are_score_deltas() -> None:
    """compute_oepv: sensitivity['+1%'] = total_score(Ri+1) - total_score(Ri) (ECO-05).

    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    ribasso = 10.0
    pt = 60.0
    result = compute_oepv(ribasso_pct=ribasso, pt=pt)

    # Calcola il delta atteso per +1%
    result_plus1 = compute_oepv(ribasso_pct=ribasso + 1.0, pt=pt)
    expected_delta = round(result_plus1.total_score - result.total_score, 4)

    assert abs(result.sensitivity["+1%"] - expected_delta) < 1e-4, (
        f"sensitivity['+1%']={result.sensitivity['+1%']!r} "
        f"expected≈{expected_delta:.4f}"
    )


# ---------------------------------------------------------------------------
# ValueError contracts
# ---------------------------------------------------------------------------


def test_compute_oepv_raises_value_error_on_ribasso_above_100() -> None:
    """compute_oepv raises ValueError when ribasso_pct > 100 (SCM-03).

    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    with pytest.raises(ValueError, match="ribasso_pct"):
        compute_oepv(ribasso_pct=101.0, pt=60.0)


def test_compute_oepv_raises_value_error_on_ribasso_below_zero() -> None:
    """compute_oepv raises ValueError when ribasso_pct < 0 (SCM-03).

    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    with pytest.raises(ValueError):
        compute_oepv(ribasso_pct=-1.0, pt=60.0)


def test_compute_oepv_raises_value_error_on_pt_out_of_range() -> None:
    """compute_oepv raises ValueError when Pt exceeds configured maximum (SCM-03).

    Default max Pt = 100 * weight_technical = 70.0.
    Implementation target: scm_cost_analyzer.oepv.compute_oepv
    """
    with pytest.raises(ValueError, match="pt"):
        compute_oepv(ribasso_pct=10.0, pt=75.0)
