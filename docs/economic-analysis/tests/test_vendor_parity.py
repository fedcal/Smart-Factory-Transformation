"""Test di parità vendor — guard anti-drift T-12-00-01.

Verifica che _oepv_vendor.py rimanga funzionalmente identico alla sorgente
apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/oepv.py (Phase 9).

Se l'oepv.py originale viene aggiornato ma il vendor non viene sincronizzato,
questo test fallisce prima che la divergenza si propaghi ai numeri pubblici.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ECONOMIC_DIR = Path(__file__).parent.parent

VENDOR_PATH = ECONOMIC_DIR / "_oepv_vendor.py"
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


def _load_module(path: Path, name: str):
    """Carica un modulo da file, registrandolo in sys.modules per compatibilità Python 3.14.

    Python 3.14 richiede che il modulo sia in sys.modules prima di exec_module quando
    usa @dataclass(frozen=True) con `from __future__ import annotations`.
    """
    import sys

    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None, f"Impossibile caricare spec da {path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # registra prima di exec per risolvere annotazioni
    assert spec.loader is not None
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.mark.skipif(not APPS_OEPV.exists(), reason="oepv.py originale non disponibile in questo ambiente")
class TestVendorParity:
    """Confronto funzionale tra _oepv_vendor.py e oepv.py originale (Phase 9)."""

    def test_compute_oepv_parity_zero_ribasso(self) -> None:
        """compute_oepv identico per ribasso=0, pt=0."""
        vendor = _load_module(VENDOR_PATH, "_vendor_v0")
        original = _load_module(APPS_OEPV, "_orig_v0")
        r_v = vendor.compute_oepv(0.0, 0.0)
        r_o = original.compute_oepv(0.0, 0.0)
        assert abs(r_v.total_score - r_o.total_score) < 1e-9
        assert abs(r_v.pe - r_o.pe) < 1e-9

    def test_compute_oepv_parity_mid_ribasso(self) -> None:
        """compute_oepv identico per ribasso=12.5, pt=68 (scenario ottimistico EC0-01)."""
        vendor = _load_module(VENDOR_PATH, "_vendor_v12")
        original = _load_module(APPS_OEPV, "_orig_v12")
        cfg_v = vendor.OepvConfig()
        cfg_o = original.OepvConfig()
        r_v = vendor.compute_oepv(12.5, 68.0, cfg_v)
        r_o = original.compute_oepv(12.5, 68.0, cfg_o)
        assert abs(r_v.total_score - r_o.total_score) < 1e-9, (
            f"vendor={r_v.total_score}, original={r_o.total_score}"
        )

    def test_compute_oepv_parity_anomaly_threshold(self) -> None:
        """is_anomaly_warning identico al 20% configurabile (soglia art. 54 D.Lgs. 36/2023 proxy)."""
        vendor = _load_module(VENDOR_PATH, "_vendor_va")
        original = _load_module(APPS_OEPV, "_orig_va")
        cfg_v = vendor.OepvConfig(anomaly_threshold_pct=20.0)
        cfg_o = original.OepvConfig(anomaly_threshold_pct=20.0)
        # Sotto la soglia
        r_v = vendor.compute_oepv(19.9, 55.0, cfg_v)
        r_o = original.compute_oepv(19.9, 55.0, cfg_o)
        assert r_v.is_anomaly_warning == r_o.is_anomaly_warning is False
        # Sulla soglia
        r_v2 = vendor.compute_oepv(20.0, 55.0, cfg_v)
        r_o2 = original.compute_oepv(20.0, 55.0, cfg_o)
        assert r_v2.is_anomaly_warning == r_o2.is_anomaly_warning is True

    def test_build_sensitivity_table_parity(self) -> None:
        """build_sensitivity_table produce gli stessi SensitivityRow da vendor e originale."""
        vendor = _load_module(VENDOR_PATH, "_vendor_vs")
        original = _load_module(APPS_OEPV, "_orig_vs")
        ribasso_range = [float(r) * 0.5 for r in range(0, 11)]  # 0-5% step 0.5
        rows_v = vendor.build_sensitivity_table(ribasso_range, 68.0)
        rows_o = original.build_sensitivity_table(ribasso_range, 68.0)
        assert len(rows_v) == len(rows_o)
        for rv, ro in zip(rows_v, rows_o):
            assert abs(rv.total_score - ro.total_score) < 1e-9, (
                f"Divergenza total_score a ribasso={rv.ribasso_pct}: "
                f"vendor={rv.total_score}, original={ro.total_score}"
            )

    def test_oepv_config_defaults_identical(self) -> None:
        """OepvConfig() default identici tra vendor e originale."""
        vendor = _load_module(VENDOR_PATH, "_vendor_vd")
        original = _load_module(APPS_OEPV, "_orig_vd")
        cfg_v = vendor.OepvConfig()
        cfg_o = original.OepvConfig()
        assert cfg_v.base_d_asta_eur == cfg_o.base_d_asta_eur
        assert cfg_v.weight_technical == cfg_o.weight_technical
        assert cfg_v.weight_economic == cfg_o.weight_economic
        assert cfg_v.pe_max == cfg_o.pe_max
        assert cfg_v.lambda_curve == cfg_o.lambda_curve
        assert cfg_v.ribasso_ref_pct == cfg_o.ribasso_ref_pct
        assert cfg_v.anomaly_threshold_pct == cfg_o.anomaly_threshold_pct
