"""Simulatore OEPV parametrico (Plan 09-04, ECO-02/ECO-05).

BOUNDARY NOTE (F9 vs F12):
  Questo modulo implementa un SIMULATORE PARAMETRICO funzionante — la formula è
  configurabile tramite OepvConfig (coefficienti, Base d'Asta, soglie).
  La soglia ribasso anomalo (anomaly_threshold_pct) è un WARNING CONFIGURABILE,
  NON la regola definitiva del Codice Appalti 2023 (demandata a Phase 12).
  Nessun coefficiente è hardcoded nel percorso della formula: tutti i valori
  numerici provengono da attributi di OepvConfig (ECO-05).

Formula OEPV:
  total_score = weight_technical * Pt + weight_economic * Pe
  Pe = pe_max * (1 - exp(-lambda_curve * Ri / ribasso_ref_pct))
  offer_eur = base_d_asta_eur * (1 - ribasso_pct / 100)
  is_anomaly_warning = ribasso_pct >= anomaly_threshold_pct  (WARNING, non esclusione legale)

Pattern: .planning/phases/09-agents-supply-chain-economics/09-RESEARCH.md Pattern 8
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OepvConfig:
    """Parametri configurabili del modello OEPV F9.

    Tutti i coefficienti sono input espliciti — nessun valore hardcoded nel percorso
    della formula. Phase 12 sostituirà con i valori definitivi del Codice Appalti 2023.

    Attributes:
        base_d_asta_eur: Base d'Asta in EUR (anchor Mantis: 108.000 EUR).
        weight_technical: Peso del punteggio tecnico (default 0.70 = 70%).
        weight_economic: Peso del punteggio economico (default 0.30 = 30%).
        pe_max: Punteggio economico massimo raggiungibile (default 30).
        lambda_curve: Curvatura della curva ribasso (parametrico F9; default 3.0).
        ribasso_ref_pct: Ribasso di riferimento per normalizzazione (default 20.0%).
        anomaly_threshold_pct: Soglia WARNING ribasso anomalo (CONFIGURABILE, non
            definitiva — la regola legale è demandata a F12; default 20.0%).
    """

    base_d_asta_eur: float = 108_000.0
    weight_technical: float = 0.70
    weight_economic: float = 0.30
    pe_max: float = 30.0
    lambda_curve: float = 3.0
    ribasso_ref_pct: float = 20.0
    anomaly_threshold_pct: float = 20.0  # WARNING configurabile — NON regola definitiva F12


@dataclass(frozen=True)
class OepvResult:
    """Risultato del calcolo OEPV per un dato ribasso e punteggio tecnico.

    Attributes:
        ribasso_pct: Ribasso percentuale di input.
        offer_eur: Offerta economica in EUR (= BA * (1 - Ri/100)).
        pt: Punteggio tecnico (input).
        pe: Punteggio economico calcolato dalla curva ribasso.
        total_score: Punteggio totale (weight_technical*Pt + weight_economic*Pe).
        is_anomaly_warning: True quando Ri >= anomaly_threshold_pct (WARNING configurabile,
            NON esclusione definitiva del Codice Appalti — demandata a F12).
        sensitivity: Dict {delta_ribasso: score_delta} per ±1%, ±5%, ±10%.
    """

    ribasso_pct: float
    offer_eur: float
    pt: float
    pe: float
    total_score: float
    is_anomaly_warning: bool
    sensitivity: dict


@dataclass(frozen=True)
class SensitivityRow:
    """Riga della tabella di sensitivity per un dato ribasso.

    Attributes:
        ribasso_pct: Ribasso percentuale.
        pe: Punteggio economico calcolato.
        total_score: Punteggio totale.
    """

    ribasso_pct: float
    pe: float
    total_score: float


def compute_oepv(
    ribasso_pct: float,
    pt: float,
    config: OepvConfig = OepvConfig(),
) -> OepvResult:
    """Calcola il punteggio OEPV per un dato ribasso % e punteggio tecnico.

    Formula (parametrica F9 — coefficienti da config, nessun hardcoded):
      Pe = config.pe_max * (1 - exp(-config.lambda_curve * ribasso_pct / config.ribasso_ref_pct))
      total_score = config.weight_technical * pt + config.weight_economic * Pe
      offer_eur = config.base_d_asta_eur * (1 - ribasso_pct / 100)
      is_anomaly_warning = ribasso_pct >= config.anomaly_threshold_pct

    La soglia anomalia è un WARNING CONFIGURABILE, non la regola definitiva
    del Codice Appalti 2023 (precision legale demandata a F12).

    Args:
        ribasso_pct: Ribasso percentuale sull'offerta economica (es. 10.5 = 10.5%).
            Deve essere in [0, 100].
        pt: Punteggio tecnico assegnato. Deve essere in [0, 100 * config.weight_technical].
        config: Parametri configurabili del modello (OepvConfig).

    Returns:
        OepvResult con score totale, offer_eur, sensitivity analysis e warning anomalia.

    Raises:
        ValueError: Se ribasso_pct non è in [0, 100].
        ValueError: Se pt non è in [0, 100 * config.weight_technical].
    """
    if not (0 <= ribasso_pct <= 100):
        raise ValueError(
            f"ribasso_pct deve essere in [0, 100], ricevuto: {ribasso_pct}"
        )
    pt_max = 100 * config.weight_technical
    if not (0 <= pt <= pt_max):
        raise ValueError(
            f"pt deve essere in [0, {pt_max}], ricevuto: {pt}"
        )

    # Curva ribasso non lineare (parametrica F9 — coefficienti da config)
    pe = config.pe_max * (
        1 - math.exp(-config.lambda_curve * ribasso_pct / config.ribasso_ref_pct)
    )

    # Punteggio totale OEPV
    total = config.weight_technical * pt + config.weight_economic * pe

    # Offerta economica in EUR
    offer = config.base_d_asta_eur * (1 - ribasso_pct / 100)

    # WARNING anomalia ribasso (configurabile — NON la regola definitiva F12)
    is_anomaly = ribasso_pct >= config.anomaly_threshold_pct

    # Sensitivity: variazione score per ribasso ±1%, ±5%, ±10%
    sensitivity: dict[str, float] = {}
    for delta in [-10.0, -5.0, -1.0, +1.0, +5.0, +10.0]:
        r_alt = max(0.0, min(100.0, ribasso_pct + delta))
        pe_alt = config.pe_max * (
            1 - math.exp(-config.lambda_curve * r_alt / config.ribasso_ref_pct)
        )
        total_alt = config.weight_technical * pt + config.weight_economic * pe_alt
        sensitivity[f"{delta:+.0f}%"] = round(total_alt - total, 4)

    return OepvResult(
        ribasso_pct=ribasso_pct,
        offer_eur=round(offer, 2),
        pt=round(pt, 4),
        pe=round(pe, 4),
        total_score=round(total, 4),
        is_anomaly_warning=is_anomaly,
        sensitivity=sensitivity,
    )


def build_sensitivity_table(
    ribasso_range: list[float],
    pt: float,
    config: OepvConfig = OepvConfig(),
) -> list[SensitivityRow]:
    """Genera una tabella di sensitivity OEPV su un range di ribassi.

    Args:
        ribasso_range: Lista di valori ribasso percentuale da valutare.
        pt: Punteggio tecnico fisso (stesso per tutti i ribassi).
        config: Parametri configurabili del modello.

    Returns:
        Lista di SensitivityRow, una per ogni ribasso nel range.
    """
    return [
        SensitivityRow(
            ribasso_pct=r,
            pe=compute_oepv(r, pt, config).pe,
            total_score=compute_oepv(r, pt, config).total_score,
        )
        for r in ribasso_range
    ]


__all__ = [
    "OepvConfig",
    "OepvResult",
    "SensitivityRow",
    "compute_oepv",
    "build_sensitivity_table",
]
