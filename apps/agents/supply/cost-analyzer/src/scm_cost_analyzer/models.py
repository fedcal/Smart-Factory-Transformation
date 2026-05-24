"""Modelli Pydantic per CostAnalyzer (Plan 09-04, SCM-03/ECO-02/ECO-05).

Modelli frozen + extra="forbid":
  - CostBreakdown: aggregato costi (downtime + scrap + energia) da audit.actions.
  - OepvReport: wrapper OepvResult + tabella sensitivity per il report finale.

Pattern: sft_agents.models.audit (frozen + extra=forbid); 09-RESEARCH.md Pattern 8.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from scm_cost_analyzer.oepv import OepvResult, SensitivityRow


class CostBreakdown(BaseModel):
    """Aggregato costi da audit.actions (read-only cross-cluster query).

    Rappresenta il ROI breakdown per il periodo analizzato:
      - downtime_cost_eur: costo fermo macchina (DOWNTIME_VERDICT).
      - scrap_cost_eur: costo scarto (QUALITY_VERDICT).
      - energy_cost_eur: costo energia (ANOMALY_ALERT energy).
      - total_eur: somma dei tre componenti.
      - roi_savings_pct: stima risparmio potenziale rispetto al totale (0–100%).

    Frozen + extra=forbid per prevenire mutazioni post-costruzione.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    downtime_cost_eur: float = Field(ge=0.0, description="Costo downtime aggregato in EUR")
    scrap_cost_eur: float = Field(ge=0.0, description="Costo scarto aggregato in EUR")
    energy_cost_eur: float = Field(ge=0.0, description="Costo energia aggregato in EUR")
    total_eur: float = Field(ge=0.0, description="Totale costi aggregati in EUR")
    roi_savings_pct: float = Field(
        ge=0.0,
        le=100.0,
        description="Stima risparmio potenziale (0–100%)",
    )


class OepvReport(BaseModel):
    """Report OEPV completo: risultato simulatore + tabella sensitivity.

    Wrappa OepvResult (score totale, Pe, offer_eur, anomaly warning)
    e la tabella di sensitivity generata da build_sensitivity_table.

    Frozen + extra=forbid.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    ribasso_pct: float = Field(description="Ribasso percentuale analizzato")
    pt: float = Field(description="Punteggio tecnico (input)")
    pe: float = Field(description="Punteggio economico calcolato")
    total_score: float = Field(description="Punteggio OEPV totale (0–100)")
    offer_eur: float = Field(description="Offerta economica in EUR (BA * (1 - Ri/100))")
    is_anomaly_warning: bool = Field(
        description=(
            "True quando ribasso >= anomaly_threshold_pct. "
            "WARNING CONFIGURABILE — NON esclusione definitiva del Codice Appalti (F12)."
        )
    )
    sensitivity: dict[str, float] = Field(
        description="Score delta per ±1%, ±5%, ±10% ribasso"
    )
    sensitivity_table: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Tabella sensitivity estesa (SensitivityRow serializzate)",
    )

    @classmethod
    def from_oepv_result(
        cls,
        result: OepvResult,
        sensitivity_table: list[SensitivityRow] | None = None,
    ) -> "OepvReport":
        """Costruisce un OepvReport da OepvResult + tabella sensitivity opzionale.

        Args:
            result: OepvResult calcolato da compute_oepv.
            sensitivity_table: Lista di SensitivityRow opzionale.

        Returns:
            OepvReport immutabile.
        """
        table_dicts: list[dict[str, Any]] = []
        if sensitivity_table:
            table_dicts = [
                {
                    "ribasso_pct": row.ribasso_pct,
                    "pe": row.pe,
                    "total_score": row.total_score,
                }
                for row in sensitivity_table
            ]
        return cls(
            ribasso_pct=result.ribasso_pct,
            pt=result.pt,
            pe=result.pe,
            total_score=result.total_score,
            offer_eur=result.offer_eur,
            is_anomaly_warning=result.is_anomaly_warning,
            sensitivity=result.sensitivity,
            sensitivity_table=table_dicts,
        )


__all__ = [
    "CostBreakdown",
    "OepvReport",
]
