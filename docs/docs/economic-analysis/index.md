# Analisi Economica

Il modello economico del progetto Smart Factory Transformation è interamente riproducibile:
tutti i numeri presentati in questa sezione derivano da un singolo script Python
(`docs/economic-analysis/tco_oepv.py`) che legge i parametri da `params.toml` e genera
CSV + tabelle Markdown in modo deterministico (ECO-08, singola sorgente di verita).

## Come rigenerare i numeri

```bash
python3 docs/economic-analysis/tco_oepv.py
```

Questo comando aggiorna `tco_table.csv`, `sensitivity_table.csv` e `summary.md` con i
valori correnti di `params.toml`. I file generati sono committed nel repository.

## Struttura del modello

| Sezione | Contenuto | Requisito |
|---|---|---|
| [TCO](tco.md) | Total Cost of Ownership 3 anni, breakdown 6 componenti | ECO-03, ECO-06 |
| [OEPV](oepv.md) | Simulatore OEPV 70/30, sensitivity non lineare, soglia anomalia | ECO-01, ECO-02, ECO-05 |
| [Value Driver](value-drivers.md) | Riduzione downtime/scrap/MTTR come SIMULATED TARGET con citazioni | ECO-04, SC-3 |

## Risk Register ECO-07

Il seguente registro dei rischi economici accompagna la valutazione (ECO-07):

| ID | Rischio | Probabilita | Impatto | Mitigazione |
|---|---|:---:|:---:|---|
| R-ECO-01 | Costo energia superiore a 0.25 EUR/kWh (variazione tariffaria) | Media | Medio | `energy_eur_kwh` configurabile in `params.toml`; +10% porta TCO 3yr a ~190.227 EUR |
| R-ECO-02 | Scostamento costo FTE (turnover, seniorizzazione) | Media | Alto | FTE e quota parziale configurabili; componente dominante del TCO (71% del totale) |
| R-ECO-03 | Integrazione IT/OT piu complessa del previsto (costi aggiuntivi) | Alta | Medio | Stima conservativa con margine; separation OT Bridge documentata in architettura |
| R-ECO-04 | Punteggio tecnico PT assegnato dalla giuria inferiore all'assunzione | Media | Alto | Due scenari documentati (ottimistico PT=68, base PT=55); SIMULATED TARGET dichiarato |
| R-ECO-05 | Ribasso dell'offerta percepito come anomalo (>= soglia 20%) | Bassa | Alto | Soglia WARNING configurabile; ribasso 12.5% lontano dalla soglia; vedi [OEPV](oepv.md) |
| R-ECO-06 | Obsolescenza hardware GPU prima del termine ammortamento (3 anni) | Bassa | Basso | Costo GPU relativamente contenuto (15.000 EUR); componente <8% TCO totale |

## Parametri principali

| Parametro | Valore | Fonte |
|---|---|---|
| Base d'Asta | 108.000 EUR | Mantis anchor, `params.toml` |
| Ribasso ipotizzato | 12.5% | Range 10-15%, `params.toml` |
| Energia | 0.25 EUR/kWh | Tariffa industriale ARERA, `params.toml` |
| PT ottimistico | 68.0 / 70 | Assumption Register A-051, SIMULATED TARGET |
| PT base | 55.0 | Assumption Register A-052, SIMULATED TARGET |
| Soglia anomalia | 20.0% (configurabile) | Proxy art. 54 D.Lgs. 36/2023, `params.toml` |

> **Nota metodologica:** i parametri sono configurabili. Modifica `params.toml` e
> riesegui lo script per ottenere proiezioni personalizzate.
