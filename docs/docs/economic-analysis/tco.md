# TCO — Total Cost of Ownership 3 anni

<!-- Numeri generati da docs/economic-analysis/tco_oepv.py — non editare a mano -->
<!-- Rigenera con: python3 docs/economic-analysis/tco_oepv.py -->

Il TCO triennale copre le sei componenti di costo operative e di investimento previste
per il deployment di Smart Factory Transformation in un sito Mantis (singolo sito,
ECO-03/ECO-06). Tutti i valori derivano da `params.toml` via lo script riproducibile.

## Breakdown 6 Componenti

| Componente | Descrizione | Annuale (EUR) | TCO 3 anni (EUR) |
|---|---|---:|---:|
| gpu_amortization | Ammortamento GPU/Server (3 anni) | 5.000,00 | 15.000,00 |
| energy | Energia (kWh x 0,25 EUR/kWh, inference continua) | 2.190,00 | 6.570,00 |
| fte_partial | FTE parziale (ops + IT support, 1 FTE equivalente) | 45.000,00 | 135.000,00 |
| change_management | Change management (formazione organizzativa, 2 anni) | 6.000,00 | 18.000,00 |
| it_ot_integration | IT/OT integration (OPC-UA bridge, NATS, connettori ERP) | 3.000,00 | 9.000,00 |
| training | Training specifico (operatori e tecnici HITL) | 2.000,00 | 6.000,00 |
| **totale** | **TCO totale 3 anni** | **63.190,00** | **189.570,00** |

> Fonte: `tco_table.csv` — generato deterministicamente da `tco_oepv.py`.

## Parametri di calcolo

| Parametro | Valore | Componente |
|---|---|---|
| `gpu_cost_eur` | 15.000 EUR | gpu_amortization |
| `gpu_amort_years` | 3 anni | gpu_amortization |
| `energy_kwh_annual` | 8.760 kWh/anno | energy |
| `energy_eur_kwh` | 0,25 EUR/kWh | energy |
| `fte_annual_cost_eur` | 45.000 EUR/anno | fte_partial |
| `fte_partial` | 1,0 (1 FTE equivalente) | fte_partial |
| `change_mgmt_eur` | 12.000 EUR totali | change_management |
| `change_mgmt_years` | 2 anni | change_management |
| `integration_eur` | 9.000 EUR totali | it_ot_integration |
| `integration_years` | 3 anni | it_ot_integration |
| `training_eur` | 6.000 EUR totali | training |
| `training_years` | 3 anni | training |

## Nota sulle Componenti (ECO-06)

### 1. GPU/Server amortization
Server GPU dedicato per inferenza self-hosted (Qwen2.5-7B via Ollama/vLLM).
Ammortamento lineare su 3 anni: 15.000 EUR / 3 = **5.000 EUR/anno**.

### 2. Energia
Consumo stimato ~1 kW medio in modalita inference mixed-mode (GPU attiva ~60% del tempo).
8.760 ore/anno × 1 kW × 0,25 EUR/kWh = **2.190 EUR/anno**.
La tariffa 0,25 EUR/kWh e il parametro ARERA per uso industriale (configurabile).

### 3. FTE parziale
1 FTE equivalente (0,5 FTE operazioni + 0,5 FTE IT support).
Costo medio FTE IT/OT area tessile Nord Italia inclusi oneri: **45.000 EUR/anno**.
Componente dominante: 71% del TCO totale — area critica per la valutazione.

### 4. Change management
Costi di formazione organizzativa, comunicazione e gestione del cambiamento (processo,
non tecnologia). Distribuito su 2 anni: 12.000 / 2 = **6.000 EUR/anno**.

### 5. IT/OT integration
Configurazione OPC-UA bridge, NATS JetStream, connettori ERP stub (fase MVP).
Distribuito su 3 anni: 9.000 / 3 = **3.000 EUR/anno**.

### 6. Training specifico
Workshop utilizzo sistema HITL, formazione operatori e tecnici.
Distribuito su 3 anni: 6.000 / 3 = **2.000 EUR/anno**.

## Formula di calcolo

```
gpu_annual   = gpu_cost_eur / gpu_amort_years
energy_annual = energy_kwh_annual * energy_eur_kwh
fte_annual   = fte_annual_cost_eur * fte_partial
change_annual = change_mgmt_eur / change_mgmt_years
integration_annual = integration_eur / integration_years
training_annual = training_eur / training_years

tco_annual = somma delle 6 componenti
tco_3yr    = tco_annual * 3
```

## Relazione con il modello OEPV

Il TCO e la componente tecnico-economica del progetto. Il ribasso sull'offerta
(derivato dalla Base d'Asta di 108.000 EUR) viene valutato nel modello OEPV
separatamente. Vedi [OEPV](oepv.md) per la simulazione del punteggio gara.
