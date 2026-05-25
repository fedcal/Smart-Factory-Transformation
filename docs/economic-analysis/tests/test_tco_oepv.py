"""Test suite per il modello economico TCO + OEPV — Phase 12 Wave 1 (12-01).

Test 1: Determinismo — eseguire lo script due volte produce CSV identici (ECO-08).
Test 2: TCO 3yr calcolato da params == valore atteso con breakdown a 6 componenti (ECO-03/ECO-06).
Test 3: OEPV per (ribasso 12.5%, PT 68) == compute_oepv(12.5, 68, config).total_score (riuso vendor).
Test 4 (test_vendor_parity): _oepv_vendor.py funzionalmente identico a oepv.py originale (anti-drift).
"""

from __future__ import annotations

import csv
import importlib.util
import sys
import tomllib
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ECONOMIC_DIR = Path(__file__).parent.parent
PARAMS_FILE = ECONOMIC_DIR / "params.toml"
SCRIPT_FILE = ECONOMIC_DIR / "tco_oepv.py"
TCO_CSV = ECONOMIC_DIR / "tco_table.csv"
SENSITIVITY_CSV = ECONOMIC_DIR / "sensitivity_table.csv"
SUMMARY_MD = ECONOMIC_DIR / "summary.md"

# Percorso oepv.py originale (Phase 9 — per il test di parità anti-drift)
APPS_OEPV = (
    Path(__file__).parent.parent.parent.parent
    / "apps"
    / "agents"
    / "supply"
    / "cost-analyzer"
    / "src"
    / "scm_cost_analyzer"
    / "oepv.py"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_params() -> dict:
    with open(PARAMS_FILE, "rb") as f:
        return tomllib.load(f)


def _expected_tco(p: dict) -> tuple[float, float]:
    """Calcola il TCO atteso dalle 6 componenti per verifica indipendente.

    Componenti (ECO-03 / ECO-06):
      1. GPU amortization     = gpu_cost_eur / gpu_amort_years (annuale)
      2. Energy               = energy_kwh_annual * energy_eur_kwh (annuale)
      3. FTE partial          = fte_annual_cost_eur * fte_partial (annuale)
      4. Change management    = change_mgmt_eur / change_mgmt_years (annuale)
      5. IT/OT integration    = integration_eur / integration_years (annuale)
      6. Training             = training_eur / training_years (annuale)
    """
    tco_cfg = p["tco"]
    gpu_amort_annual = tco_cfg["gpu_cost_eur"] / tco_cfg["gpu_amort_years"]
    energy_annual = tco_cfg["energy_kwh_annual"] * tco_cfg["energy_eur_kwh"]
    fte_annual = tco_cfg["fte_annual_cost_eur"] * tco_cfg["fte_partial"]
    change_mgmt_annual = tco_cfg["change_mgmt_eur"] / tco_cfg["change_mgmt_years"]
    integration_annual = tco_cfg["integration_eur"] / tco_cfg["integration_years"]
    training_annual = tco_cfg["training_eur"] / tco_cfg["training_years"]

    annual_total = (
        gpu_amort_annual
        + energy_annual
        + fte_annual
        + change_mgmt_annual
        + integration_annual
        + training_annual
    )
    return round(annual_total, 2), round(annual_total * 3, 2)


# ---------------------------------------------------------------------------
# Test 1: Determinismo — due run producono CSV identici (ECO-08)
# ---------------------------------------------------------------------------

def test_determinism(tmp_path: Path) -> None:
    """Eseguire tco_oepv.py due volte produce CSV identici (ECO-08 single source of truth)."""
    import subprocess

    # Prima esecuzione
    result1 = subprocess.run(
        [sys.executable, str(SCRIPT_FILE)],
        cwd=str(ECONOMIC_DIR),
        capture_output=True,
        text=True,
    )
    assert result1.returncode == 0, f"Prima esecuzione fallita:\n{result1.stderr}"

    csv1_content = TCO_CSV.read_text()
    sensitivity1_content = SENSITIVITY_CSV.read_text()

    # Seconda esecuzione
    result2 = subprocess.run(
        [sys.executable, str(SCRIPT_FILE)],
        cwd=str(ECONOMIC_DIR),
        capture_output=True,
        text=True,
    )
    assert result2.returncode == 0, f"Seconda esecuzione fallita:\n{result2.stderr}"

    csv2_content = TCO_CSV.read_text()
    sensitivity2_content = SENSITIVITY_CSV.read_text()

    assert csv1_content == csv2_content, (
        "tco_table.csv non deterministico: le due esecuzioni producono output diversi"
    )
    assert sensitivity1_content == sensitivity2_content, (
        "sensitivity_table.csv non deterministico: le due esecuzioni producono output diversi"
    )


# ---------------------------------------------------------------------------
# Test 2: TCO 3yr breakdown 6 componenti (ECO-03/ECO-06)
# ---------------------------------------------------------------------------

def test_tco_breakdown_six_components() -> None:
    """TCO 3yr calcolato da params corrisponde alla somma delle 6 componenti attese."""
    assert TCO_CSV.exists(), (
        "tco_table.csv non trovato — eseguire tco_oepv.py prima di questo test"
    )

    p = _load_params()
    _expected_annual, expected_3yr = _expected_tco(p)

    # Leggi il CSV e trova la riga del totale 3yr
    with open(TCO_CSV, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Trova la riga "totale" o "tco_3yr"
    total_row = next(
        (r for r in rows if r.get("componente", "").lower() in ("totale", "tco_3yr", "total")),
        None,
    )
    assert total_row is not None, (
        f"Riga 'totale' non trovata in tco_table.csv. Righe trovate: {[r.get('componente') for r in rows]}"
    )

    actual_3yr = float(total_row["tco_3yr"])
    assert abs(actual_3yr - expected_3yr) < 1.0, (
        f"TCO 3yr atteso={expected_3yr}, ottenuto={actual_3yr} (diff={abs(actual_3yr - expected_3yr):.2f})"
    )

    # Verifica che ci siano esattamente 6 componenti (+ riga totale)
    component_rows = [r for r in rows if r.get("componente", "").lower() not in ("totale", "tco_3yr", "total")]
    assert len(component_rows) == 6, (
        f"Attese 6 componenti TCO, trovate {len(component_rows)}: {[r.get('componente') for r in component_rows]}"
    )


# ---------------------------------------------------------------------------
# Test 3: OEPV riusa il vendor — compute_oepv(12.5, 68, config) == output script
# ---------------------------------------------------------------------------

def test_oepv_reuses_vendor() -> None:
    """OEPV per (ribasso 12.5%, PT 68) dall'output script == compute_oepv(12.5, 68, config)."""
    assert SENSITIVITY_CSV.exists(), (
        "sensitivity_table.csv non trovato — eseguire tco_oepv.py prima di questo test"
    )
    assert SUMMARY_MD.exists(), (
        "summary.md non trovato — eseguire tco_oepv.py prima di questo test"
    )

    # Importa il vendor dalla stessa directory
    # Nota: registrare in sys.modules prima di exec_module per Python 3.14 compatibilità
    # (@dataclass frozen=True con from __future__ import annotations richiede il modulo
    # registrato in sys.modules per risolvere le annotazioni correttamente).
    vendor_path = ECONOMIC_DIR / "_oepv_vendor.py"
    mod_name = "_oepv_vendor_reuse_test"
    spec = importlib.util.spec_from_file_location(mod_name, vendor_path)
    assert spec is not None
    vendor = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = vendor
    assert spec.loader is not None
    spec.loader.exec_module(vendor)  # type: ignore[union-attr]

    p = _load_params()
    oepv_cfg = p["oepv"]
    config = vendor.OepvConfig(
        base_d_asta_eur=oepv_cfg["base_d_asta_eur"],
        weight_technical=oepv_cfg["weight_technical"],
        weight_economic=oepv_cfg["weight_economic"],
        pe_max=oepv_cfg["pe_max"],
        lambda_curve=oepv_cfg["lambda_curve"],
        ribasso_ref_pct=oepv_cfg["ribasso_ref_pct"],
        anomaly_threshold_pct=oepv_cfg["anomaly_threshold_pct"],
    )

    expected_result = vendor.compute_oepv(12.5, 68.0, config)
    expected_score = expected_result.total_score

    # Il summary.md deve contenere il punteggio totale OEPV per PT=68 (scenario ottimistico)
    summary_text = SUMMARY_MD.read_text()
    assert str(expected_score) in summary_text or f"{expected_score:.4f}" in summary_text, (
        f"Punteggio OEPV atteso ({expected_score}) non trovato in summary.md per verifica riuso vendor"
    )


# ---------------------------------------------------------------------------
# Test 4: Parità vendor — _oepv_vendor.py funzionalmente identico a oepv.py originale
# ---------------------------------------------------------------------------

def test_vendor_parity() -> None:
    """_oepv_vendor.py è funzionalmente identico a apps/.../oepv.py (anti-drift T-12-00-01)."""
    vendor_path = ECONOMIC_DIR / "_oepv_vendor.py"
    assert vendor_path.exists(), "_oepv_vendor.py non trovato"

    if not APPS_OEPV.exists():
        pytest.skip(
            f"oepv.py originale non trovato in {APPS_OEPV} — test di parità saltato "
            "(ambiente senza workspace apps/ completo)"
        )

    # Carica entrambi i moduli dinamicamente
    # Registra in sys.modules prima di exec_module (Python 3.14 compat)
    def _load_module_local(path: Path, name: str):
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        assert spec.loader is not None
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod

    vendor = _load_module_local(vendor_path, "_oepv_vendor_parity_test")
    original = _load_module_local(APPS_OEPV, "_oepv_original_parity_test")

    # Confronto funzionale su un set di input di riferimento
    test_inputs = [
        (0.0, 0.0),
        (5.0, 50.0),
        (12.5, 68.0),
        (15.0, 55.0),
        (20.0, 70.0),
        (19.9, 65.0),
    ]

    default_cfg_vendor = vendor.OepvConfig()
    default_cfg_original = original.OepvConfig()

    for ribasso, pt in test_inputs:
        # Salta combinazioni fuori range (pt deve essere <= 100 * weight_technical = 70)
        if pt > 100 * default_cfg_vendor.weight_technical:
            continue

        result_v = vendor.compute_oepv(ribasso, pt, default_cfg_vendor)
        result_o = original.compute_oepv(ribasso, pt, default_cfg_original)

        assert abs(result_v.total_score - result_o.total_score) < 1e-9, (
            f"Divergenza total_score per (ribasso={ribasso}, pt={pt}): "
            f"vendor={result_v.total_score}, original={result_o.total_score}"
        )
        assert abs(result_v.pe - result_o.pe) < 1e-9, (
            f"Divergenza pe per (ribasso={ribasso}, pt={pt}): "
            f"vendor={result_v.pe}, original={result_o.pe}"
        )
        assert abs(result_v.offer_eur - result_o.offer_eur) < 0.01, (
            f"Divergenza offer_eur per (ribasso={ribasso}, pt={pt}): "
            f"vendor={result_v.offer_eur}, original={result_o.offer_eur}"
        )
        assert result_v.is_anomaly_warning == result_o.is_anomaly_warning, (
            f"Divergenza is_anomaly_warning per (ribasso={ribasso}, pt={pt}): "
            f"vendor={result_v.is_anomaly_warning}, original={result_o.is_anomaly_warning}"
        )
