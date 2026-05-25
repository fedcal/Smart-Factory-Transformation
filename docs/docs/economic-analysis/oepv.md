# OEPV — Offerta Economicamente Piu Vantaggiosa

<!-- Numeri generati da docs/economic-analysis/tco_oepv.py — non editare a mano -->
<!-- Rigenera con: python3 docs/economic-analysis/tco_oepv.py -->

Il simulatore OEPV parametrico (ECO-01, ECO-02, ECO-05) e implementato in
`apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/oepv.py` (Phase 9) e
vendorizzato in `docs/economic-analysis/_oepv_vendor.py` per la riproducibilita
del modello economico senza dipendenze dal workspace Nx.

## Formula OEPV (Phase 9 — ECO-02)

```
Pe = pe_max * (1 - exp(-lambda * Ri / ribasso_ref))
total_score = weight_technical * Pt + weight_economic * Pe
offer_eur = base_d_asta_eur * (1 - ribasso_pct / 100)
is_anomaly_warning = ribasso_pct >= anomaly_threshold_pct
```

Parametri (tutti configurabili in `params.toml`):

| Parametro | Valore | Descrizione |
|---|---:|---|
| `base_d_asta_eur` | 108.000 EUR | Base d'Asta Mantis |
| `weight_technical` | 0,70 | Peso punteggio tecnico (70%) |
| `weight_economic` | 0,30 | Peso punteggio economico (30%) |
| `pe_max` | 30,0 | Punteggio economico massimo |
| `lambda_curve` | 3,0 | Curvatura curva ribasso |
| `ribasso_ref_pct` | 20,0% | Ribasso di riferimento normalizzazione |
| `anomaly_threshold_pct` | 20,0% | Soglia WARNING ribasso anomalo (configurabile) |

## Scenari PT — SIMULATED TARGET

> **SIMULATED TARGET per valutazione economica** (ECO-04, SC-3).
> I punteggi tecnici PT sono assunzioni dell'Assumption Register (vedere
> `docs/docs/assumptions/index.md`), non punteggi assegnati da giuria.
> Non costituiscono una promessa di risultato.

Ribasso ipotizzato: **12.5%** (range tipico 10-15% con giustificazione scritta).

| Scenario PT | Ribasso % | PT | Pe | Punteggio Totale | Offerta (EUR) | WARNING Anomalia |
|---|---:|---:|---:|---:|---:|:---:|
| Ottimistico (PT=68.0) | 12.5 | 68.0 | 25.3994 | **55.2198** | 94.500,00 | NO |
| Base (PT=55.0) | 12.5 | 55.0 | 25.3994 | **46.1198** | 94.500,00 | NO |

**Scenario ottimistico (PT=68.0/70):** punteggio tecnico prossimo al massimo teorico (70 punti
su 100 con peso 70%). Assumption Register: A-051 — SIMULATED TARGET.

**Scenario base (PT=55.0):** punteggio tecnico realistico per un'offerta solida e completa.
Assumption Register: A-052 — SIMULATED TARGET.

## Sensitivity Non Lineare — Ribasso 0-20% (ECO-05, SC-2)

PT fisso = 68.0 (scenario ottimistico). Curva non lineare con lambda=3.0.

| Ribasso % | Pe | Punteggio Totale |
|---:|---:|---:|
| 0.0 | 0.0 | 47.6 |
| 0.5 | 2.1677 | 48.2503 |
| 1.0 | 4.1788 | 48.8536 |
| 1.5 | 6.0445 | 49.4134 |
| 2.0 | 7.7755 | 49.9326 |
| 2.5 | 9.3813 | 50.4144 |
| 3.0 | 10.8712 | 50.8613 |
| 4.0 | 13.5357 | 51.6607 |
| 5.0 | 15.9373 | 52.3812 |
| 7.5 | 20.7086 | 53.8126 |
| 10.0 | 24.2628 | 54.9788 |
| 12.5 | 25.3994 | 55.2198 |
| 15.0 | 27.1273 | 55.738 |
| 17.5 | 27.9296 | 55.9788 |
| 20.0 | 28.5064 | 56.1519 |

> Tabella completa (41 righe, step 0.5%): `docs/economic-analysis/sensitivity_table.csv`
> Fonte: `build_sensitivity_table()` da `_oepv_vendor.py` (Phase 9 — nessuna re-derivazione).

La curva e non lineare: la maggior parte del guadagno Pe si ottiene nei primi
10 punti percentuali di ribasso. Oltre il 15% l'incremento marginale e minimo.

## Soglia Anomalia Ribasso (art. 54 D.Lgs. 36/2023)

> **WARNING configurabile al 20% — NON esclusione legale.**
>
> La soglia `anomaly_threshold_pct = 20.0` in `params.toml` e un **proxy
> conservativo configurabile** ai sensi dell'art. 54 D.Lgs. 36/2023 (Codice dei
> Contratti Pubblici). Il Codice prevede un meccanismo di verifica dell'anomalia
> basato sullo scarto medio dei ribassi presentati — la formula legale esatta
> richiede consulenza specialistica e dipende dal numero di offerte concorrenti.
>
> **Questo simulatore NON implementa la formula legale definitiva**: usa il 20%
> come soglia WARNING indicativa. Il flag `is_anomaly_warning` e CONFIGURABILE:
> modificare `anomaly_threshold_pct` in `params.toml` e rigenerare.

Con ribasso 12.5%, il WARNING anomalia e: **NO** (distanza di 7.5 punti percentuali dalla soglia).

## Riproducibilita

Il simulatore OEPV e identico all'implementazione della Phase 9 (`oepv.py`).
Un test CI verifica la parita funzionale (`test_vendor_parity.py`, T-12-00-01)
per prevenire la deriva tra il vendor e la sorgente originale.

```bash
# Rigenerare tutti gli output da params.toml
python3 docs/economic-analysis/tco_oepv.py

# Eseguire i test di parita vendor
python3 -m pytest docs/economic-analysis/tests/ -v
```
