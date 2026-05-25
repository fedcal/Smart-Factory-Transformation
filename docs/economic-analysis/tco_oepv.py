"""TCO 3 anni + OEPV scoring — Phase 12 modello economico riproducibile.

Singola sorgente di verita per tutti i numeri nelle tabelle docs/docs/economic-analysis/.
Legge params.toml, riusa compute_oepv/build_sensitivity_table da _oepv_vendor.py (Phase 9),
genera tco_table.csv, sensitivity_table.csv e summary.md in modo deterministico (ECO-08).

Usage:
    python3 docs/economic-analysis/tco_oepv.py

Output (committed):
    docs/economic-analysis/tco_table.csv        (breakdown TCO 6 componenti)
    docs/economic-analysis/sensitivity_table.csv (sensitivity OEPV ribasso 0-20% step 0.5)
    docs/economic-analysis/summary.md           (tabelle Markdown + note soglia anomalia)

Requisiti coperti: ECO-01, ECO-03, ECO-04, ECO-06, ECO-07, ECO-08, DOC-10, DEL-06.
"""

from __future__ import annotations

import csv
import tomllib
from pathlib import Path

from _oepv_vendor import OepvConfig, SensitivityRow, build_sensitivity_table, compute_oepv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
PARAMS_FILE = ROOT / "params.toml"
TCO_CSV = ROOT / "tco_table.csv"
SENSITIVITY_CSV = ROOT / "sensitivity_table.csv"
SUMMARY_MD = ROOT / "summary.md"


# ---------------------------------------------------------------------------
# 1. Carica parametri
# ---------------------------------------------------------------------------

def load_params(path: Path = PARAMS_FILE) -> dict:
    """Legge params.toml via tomllib (stdlib Python 3.11+)."""
    with open(path, "rb") as f:
        return tomllib.load(f)


# ---------------------------------------------------------------------------
# 2. Calcolo TCO 3 anni (6 componenti, ECO-03/ECO-06)
# ---------------------------------------------------------------------------

def compute_tco(params: dict) -> dict:
    """Calcola il TCO 3 anni con breakdown a 6 componenti.

    Componenti (ECO-03 / ECO-06):
      1. gpu_amortization   = gpu_cost_eur / gpu_amort_years
      2. energy             = energy_kwh_annual * energy_eur_kwh
      3. fte_partial        = fte_annual_cost_eur * fte_partial
      4. change_management  = change_mgmt_eur / change_mgmt_years
      5. it_ot_integration  = integration_eur / integration_years
      6. training           = training_eur / training_years

    Returns un dizionario con annual e 3yr per ogni componente + totale.
    I valori sono arrotondati a 2 decimali per output deterministico.
    """
    tco = params["tco"]

    gpu_annual = round(tco["gpu_cost_eur"] / tco["gpu_amort_years"], 2)
    energy_annual = round(tco["energy_kwh_annual"] * tco["energy_eur_kwh"], 2)
    fte_annual = round(tco["fte_annual_cost_eur"] * tco["fte_partial"], 2)
    change_annual = round(tco["change_mgmt_eur"] / tco["change_mgmt_years"], 2)
    integration_annual = round(tco["integration_eur"] / tco["integration_years"], 2)
    training_annual = round(tco["training_eur"] / tco["training_years"], 2)

    total_annual = round(
        gpu_annual + energy_annual + fte_annual + change_annual + integration_annual + training_annual,
        2,
    )

    return {
        "components": [
            {
                "componente": "gpu_amortization",
                "descrizione": "Ammortamento GPU/Server (3 anni)",
                "annual_eur": gpu_annual,
                "tco_3yr": round(gpu_annual * 3, 2),
            },
            {
                "componente": "energy",
                "descrizione": "Energia (kWh x 0.25 EUR/kWh, inference continua)",
                "annual_eur": energy_annual,
                "tco_3yr": round(energy_annual * 3, 2),
            },
            {
                "componente": "fte_partial",
                "descrizione": "FTE parziale (ops + IT support, 1 FTE equivalente)",
                "annual_eur": fte_annual,
                "tco_3yr": round(fte_annual * 3, 2),
            },
            {
                "componente": "change_management",
                "descrizione": "Change management (formazione organizzativa, 2 anni)",
                "annual_eur": change_annual,
                "tco_3yr": round(change_annual * 3, 2),
            },
            {
                "componente": "it_ot_integration",
                "descrizione": "IT/OT integration (OPC-UA bridge, NATS, connettori ERP)",
                "annual_eur": integration_annual,
                "tco_3yr": round(integration_annual * 3, 2),
            },
            {
                "componente": "training",
                "descrizione": "Training specifico (operatori e tecnici HITL)",
                "annual_eur": training_annual,
                "tco_3yr": round(training_annual * 3, 2),
            },
        ],
        "totale": {
            "componente": "totale",
            "descrizione": "TCO totale 3 anni",
            "annual_eur": total_annual,
            "tco_3yr": round(total_annual * 3, 2),
        },
    }


# ---------------------------------------------------------------------------
# 3. OEPV per i 2 scenari PT (ECO-01)
# ---------------------------------------------------------------------------

def compute_oepv_scenarios(params: dict, config: OepvConfig) -> dict:
    """Calcola OEPV per i 2 scenari PT definiti nell'Assumption Register.

    Scenari (ECO-01 / Assumption Register):
      - PT ottimistico: pt_optimistic (default 68.0) — massimo tecnico raggiungibile
      - PT base: pt_base (default 55.0) — scenario realistico per offerta solida

    I punteggi sono SIMULATED TARGET (ECO-04/SC-3) — non promesse.
    """
    oepv_cfg = params["oepv"]
    ribasso = oepv_cfg["ribasso_pct"]
    pt_opt = oepv_cfg["pt_optimistic"]
    pt_base = oepv_cfg["pt_base"]

    result_opt = compute_oepv(ribasso, pt_opt, config)
    result_base = compute_oepv(ribasso, pt_base, config)

    return {
        "ribasso_pct": ribasso,
        "anomaly_threshold_pct": config.anomaly_threshold_pct,
        "ottimistico": result_opt,
        "base": result_base,
    }


# ---------------------------------------------------------------------------
# 4. Sensitivity table (ribasso 0-20% step 0.5, ECO-05/SC-2)
# ---------------------------------------------------------------------------

def compute_sensitivity(params: dict, config: OepvConfig) -> list[SensitivityRow]:
    """Genera la tabella sensitivity OEPV su ribasso 0-20% passo 0.5.

    Usa build_sensitivity_table dal vendor (Phase 9 — nessuna re-derivazione).
    PT fisso = pt_optimistic (scenario ottimistico per la tabella di sensitivity).
    """
    pt = params["oepv"]["pt_optimistic"]
    ribasso_range = [round(r * 0.5, 1) for r in range(0, 41)]  # 0.0 ... 20.0
    return build_sensitivity_table(ribasso_range, pt, config)


# ---------------------------------------------------------------------------
# 5. Scrittura CSV
# ---------------------------------------------------------------------------

def write_tco_csv(tco: dict, out_path: Path = TCO_CSV) -> None:
    """Scrive tco_table.csv con breakdown a 6 componenti + totale."""
    fieldnames = ["componente", "descrizione", "annual_eur", "tco_3yr"]
    rows = [*tco["components"], tco["totale"]]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_sensitivity_csv(
    rows: list[SensitivityRow], out_path: Path = SENSITIVITY_CSV
) -> None:
    """Scrive sensitivity_table.csv con ribasso, pe, total_score."""
    fieldnames = ["ribasso_pct", "pe", "total_score"]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "ribasso_pct": row.ribasso_pct,
                    "pe": row.pe,
                    "total_score": row.total_score,
                }
            )


# ---------------------------------------------------------------------------
# 6. Scrittura summary.md (Markdown — copiato nelle docs IT+EN)
# ---------------------------------------------------------------------------

def write_summary_md(
    tco: dict,
    oepv_scenarios: dict,
    sensitivity_rows: list[SensitivityRow],
    params: dict,
    out_path: Path = SUMMARY_MD,
) -> None:
    """Genera summary.md con tabelle Markdown + nota soglia anomalia + citazione."""
    oepv_cfg = params["oepv"]
    tco_cfg = params["tco"]

    totale = tco["totale"]
    components = tco["components"]
    opt = oepv_scenarios["ottimistico"]
    base_scenario = oepv_scenarios["base"]
    ribasso = oepv_scenarios["ribasso_pct"]
    anomaly_thr = oepv_scenarios["anomaly_threshold_pct"]

    # Tabella TCO
    tco_header = "| Componente | Descrizione | Annuale (EUR) | TCO 3 anni (EUR) |"
    tco_sep = "|---|---|---:|---:|"
    tco_rows = "\n".join(
        f"| {c['componente']} | {c['descrizione']} | {c['annual_eur']:,.2f} | {c['tco_3yr']:,.2f} |"
        for c in components
    )
    tco_total_row = (
        f"| **{totale['componente']}** | **{totale['descrizione']}** "
        f"| **{totale['annual_eur']:,.2f}** | **{totale['tco_3yr']:,.2f}** |"
    )

    # Tabella OEPV scenari
    oepv_header = "| Scenario PT | Ribasso % | PT | Pe | Punteggio Totale | Offerta (EUR) | WARNING Anomalia |"
    oepv_sep = "|---|---:|---:|---:|---:|---:|:---:|"
    oepv_row_opt = (
        f"| Ottimistico (PT={oepv_cfg['pt_optimistic']}) "
        f"| {ribasso} | {opt.pt} | {opt.pe} | **{opt.total_score}** "
        f"| {opt.offer_eur:,.2f} | {'SI' if opt.is_anomaly_warning else 'NO'} |"
    )
    oepv_row_base = (
        f"| Base (PT={oepv_cfg['pt_base']}) "
        f"| {ribasso} | {base_scenario.pt} | {base_scenario.pe} | **{base_scenario.total_score}** "
        f"| {base_scenario.offer_eur:,.2f} | {'SI' if base_scenario.is_anomaly_warning else 'NO'} |"
    )

    # Sensitivity table (prime 10 righe + ultima)
    sens_rows_subset = sensitivity_rows[:10] + [sensitivity_rows[-1]]
    sens_header = "| Ribasso % | Pe | Punteggio Totale |"
    sens_sep = "|---:|---:|---:|"
    sens_rows_md = "\n".join(
        f"| {r.ribasso_pct} | {r.pe} | {r.total_score} |"
        for r in sens_rows_subset
    )

    content = f"""<!-- AUTOGENERATED by docs/economic-analysis/tco_oepv.py — NON EDITARE A MANO -->
<!-- Rigenera con: python3 docs/economic-analysis/tco_oepv.py -->

# Modello Economico — Riepilogo

> **Nota:** Tutti i numeri in questa pagina sono generati deterministicamente da
> `params.toml` via `tco_oepv.py`. Non modificare i valori a mano.
> Rigenera con: `python3 docs/economic-analysis/tco_oepv.py`

## TCO 3 anni — Breakdown 6 Componenti

Parametri base: GPU {tco_cfg['gpu_cost_eur']:,.0f} EUR (amm. {tco_cfg['gpu_amort_years']} anni),
energia {tco_cfg['energy_kwh_annual']:,.0f} kWh/anno × {tco_cfg['energy_eur_kwh']} EUR/kWh,
FTE {tco_cfg['fte_partial']} × {tco_cfg['fte_annual_cost_eur']:,.0f} EUR/anno.

{tco_header}
{tco_sep}
{tco_rows}
{tco_total_row}

## OEPV — Scenari PT (SIMULATED TARGET, non promesse)

Ribasso ipotizzato: **{ribasso}%** — range tipico 10-15% con giustificazione scritta.

> **SIMULATED TARGET per valutazione economica** (ECO-04, SC-3).
> I punteggi tecnici PT sono assunzioni dell'Assumption Register (A-051/A-052),
> non punteggi assegnati da giuria. Vedere `docs/docs/assumptions/index.md`.

{oepv_header}
{oepv_sep}
{oepv_row_opt}
{oepv_row_base}

## Sensitivity OEPV — Ribasso 0-20% (step 0.5%)

PT fisso = {oepv_cfg['pt_optimistic']} (scenario ottimistico). Curva non lineare (lambda={oepv_cfg['lambda_curve']}).

{sens_header}
{sens_sep}
{sens_rows_md}
| ... | ... | ... |

Tabella completa in `sensitivity_table.csv` (41 righe, ribasso 0-20% passo 0.5%).

## Soglia Anomalia Ribasso

> **WARNING configurabile al {anomaly_thr}% — NON esclusione legale.**
>
> La soglia `anomaly_threshold_pct = {anomaly_thr}` in `params.toml` è un **proxy
> conservativo configurabile** ai sensi dell'art. 54 D.Lgs. 36/2023 (Codice dei Contratti
> Pubblici). Il Codice prevede un meccanismo di verifica dell'anomalia basato su
> scarto medio dei ribassi — la formula legale esatta richiede consulenza specialistica.
> Questa simulazione usa il 20% come soglia WARNING indicativa.
>
> Il flag `is_anomaly_warning` in `OepvConfig` è CONFIGURABILE: modificare
> `anomaly_threshold_pct` in `params.toml` e rigenerare.

Ribasso {ribasso}% → WARNING anomalia: **{'SI' if opt.is_anomaly_warning else 'NO'}**

## Punteggi OEPV di riferimento

| PT | total_score |
|---|---:|
| {opt.pt} (ottimistico) | {opt.total_score} |
| {base_scenario.pt} (base) | {base_scenario.total_score} |
"""

    out_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# 7. Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Calcola TCO + OEPV + sensitivity da params.toml e scrive i 3 output."""
    params = load_params()

    # Costruisce OepvConfig dai parametri
    oepv_cfg = params["oepv"]
    config = OepvConfig(
        base_d_asta_eur=oepv_cfg["base_d_asta_eur"],
        weight_technical=oepv_cfg["weight_technical"],
        weight_economic=oepv_cfg["weight_economic"],
        pe_max=oepv_cfg["pe_max"],
        lambda_curve=oepv_cfg["lambda_curve"],
        ribasso_ref_pct=oepv_cfg["ribasso_ref_pct"],
        anomaly_threshold_pct=oepv_cfg["anomaly_threshold_pct"],
    )

    # Calcoli
    tco = compute_tco(params)
    oepv_scenarios = compute_oepv_scenarios(params, config)
    sensitivity_rows = compute_sensitivity(params, config)

    # Output
    write_tco_csv(tco)
    write_sensitivity_csv(sensitivity_rows)
    write_summary_md(tco, oepv_scenarios, sensitivity_rows, params)

    # Stampa riepilogo a console
    totale = tco["totale"]
    opt = oepv_scenarios["ottimistico"]
    base = oepv_scenarios["base"]
    print(f"TCO 3yr:           EUR {totale['tco_3yr']:,.2f}")
    print(f"OEPV ottimistico:  {opt.total_score} (PT={opt.pt}, ribasso={oepv_scenarios['ribasso_pct']}%)")
    print(f"OEPV base:         {base.total_score} (PT={base.pt}, ribasso={oepv_scenarios['ribasso_pct']}%)")
    print(f"WARNING anomalia:  {'SI' if opt.is_anomaly_warning else 'NO'} (soglia {config.anomaly_threshold_pct}%)")
    print(f"Output: {TCO_CSV.name}, {SENSITIVITY_CSV.name}, {SUMMARY_MD.name}")


if __name__ == "__main__":
    main()
