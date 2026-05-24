---
lang: it
cluster: supply-chain-economics
requirements:
  - SCM-01
  - SCM-02
  - SCM-03
  - SCM-04
tags:
  - agents
  - supply
  - economics
  - SCM-01
  - SCM-02
  - SCM-03
  - SCM-04
---

# Cluster Supply Chain & Economics

## Panoramica

Il cluster **Supply Chain & Economics** aggrega i quattro agenti responsabili della
gestione della catena di fornitura, dell'efficienza energetica, dell'analisi dei costi
e della previsione della domanda per l'impresa tessile:

| Agente | Responsabilità principale | HITL |
|--------|--------------------------|------|
| **InventoryManager** | Monitoraggio livelli magazzino + alert riordino con firma responsabile acquisti | Supervisor sign-off (SCM-01) |
| **EnergyOptimizer** | Analisi consumi ISO 50001 EnPI kWh/kg + proposta schedule off-peak con HITL | Supervisor sign-off (SCM-02) |
| **CostAnalyzer** | Breakdown ROI + simulatore OEPV parametrico 70/30 + sensitivity analysis (autonomo) | Nessun HITL (SCM-03, Decision.AUTO) |
| **DemandForecaster** | Previsione domanda Holt-Winters deterministica + piano pubblicato a ProductionPlanner via HITL | Supervisor sign-off verso ProductionPlanner (SCM-04) |

Tutti e quattro gli agenti sono **LLM-free** nel percorso decisionale principale: le
elaborazioni (reorder-point, EnPI, OEPV, Holt-Winters) sono pure function deterministiche.
Il subgraph supply viene instanziato da `build_supply_subgraph` in `clusters.py`, con
`cost-analyzer` come fallback (autonomo, read-only, nessun effetto collaterale irreversibile).

---

## InventoryManager

### Panoramica

`InventoryManager` monitora i livelli di magazzino delle materie prime, degli accessori
e dei ricambi in tempo reale. Calcola deterministicamente il punto di riordino (reorder-point)
confrontando la quantità attuale con la soglia configurata per ogni SKU. Quando la quantità
scende sotto la soglia, genera un alert di riordino e lo sottopone alla firma del responsabile
acquisti (procurement-supervisor) tramite HITL (SCM-01). Il calcolo è LLM-free.

### Strumenti Utilizzati

| Strumento | Origine | Funzione |
|-----------|---------|----------|
| `fetch_inventory_levels` | scm-inventory-manager.repository | Recupera i livelli più recenti per ogni SKU da `scm.inventory_levels` con JOIN su `scm.sku_master` per soglie e costi. |
| `check_reorder` | scm-inventory-manager.reorder | Pure function: confronta `current_qty` con `reorder_point`; calcola `deficit_qty` e `estimated_cost_eur`. |
| `escalate_to_procurement_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Invia l'alert di riordino al responsabile acquisti per approvazione HITL. |

### Fonti Dati

- **TimescaleDB `scm.inventory_levels`** — hypertable time-series dei livelli di magazzino;
  il record più recente per `sku_id` fornisce la quantità attuale.
- **TimescaleDB `scm.sku_master`** — tabella master con `reorder_point`, `reorder_qty`,
  `lead_time_days`, `unit_cost_eur`; fonte delle soglie per il calcolo reorder.

### HITL Tier

| Decisione | Tier | Approvatore |
|-----------|------|-------------|
| Alert riordino sotto soglia | supervisor (Decision.HITL_SUPERVISOR) | Responsabile acquisti (procurement-supervisor) |

### KPI Impattati

- **inventory_stockout_risk** — percentuale di SKU sotto il punto di riordino.
- **procurement_lead_time** — giorni medi tra alert riordino e ricezione merce.
- **reorder_cost_eur** — valore economico degli ordini di riordino generati.

### Invocazione

- **Endpoint API**: `POST /v1/agents/supply/inventory-manager/analyze`
  con body `{"sku_ids": ["SKU-YARN-NE20-BLU", "..."], "user_roles": ["procurement_supervisor"]}`
- **Resume**: `POST /v1/agents/supply/inventory-manager/resume`
  con body `{"thread_id": "<id>", "decision": "approved"}`
- **Thread ID**: convenzione `supply.inventory-manager.<uuid4>`.
- **Risposta analyze**: `202 Accepted` (HITL asincrono).
- **Risposta resume**: `200 OK` con `reorder_recommendation`.

### Audit Footprint

- `REORDER_ALERT` — una riga per ogni sessione dopo il resume HITL.
- Ogni riga porta `approval_id` popolato solo dopo l'approvazione del supervisore.

---

## EnergyOptimizer

### Panoramica

`EnergyOptimizer` analizza i consumi energetici (kWh) per processo (tintoria, finissaggio,
filatura, tessitura) calcolando l'indicatore ISO 50001 EnPI in kWh/kg e confrontandolo con
il baseline configurato. Identifica le opportunità di spostamento del carico in ore off-peak
e propone uno schedule energetico al supervisore via HITL (SCM-02). Il calcolo è LLM-free.

### Strumenti Utilizzati

| Strumento | Origine | Funzione |
|-----------|---------|----------|
| `fetch_energy_readings` | scm-energy-optimizer.repository | Recupera le letture da `scm.energy_readings` per processo e finestra temporale; filtra `kwh`, `kg_processed`, `is_peak_hour`. |
| `compute_enpi` | scm-energy-optimizer.enpi | Pure function ISO 50001: calcola `enpi_actual = kwh_total / kg_total`; confronto con baseline; calcola `off_peak_kwh_pct` sul totale delle letture. |
| `propose_off_peak_schedule` | scm-energy-optimizer.scheduler | Genera la proposta di spostamento carichi in fascia off-peak con stima risparmio kWh e €. |
| `escalate_to_energy_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Invia la proposta energetica al supervisore per approvazione prima del dispatch al turno. |

### Fonti Dati

- **TimescaleDB `scm.energy_readings`** — hypertable time-series delle letture energetiche;
  colonne chiave: `ts`, `asset_id`, `process`, `kwh`, `kg_processed`, `is_peak_hour`.
- **TimescaleDB `scm.enpi_baseline`** — baseline ISO 50001 per processo (target kWh/kg e YTD);
  fonte per il confronto `enpi_actual` vs `enpi_baseline`.

### HITL Tier

| Decisione | Tier | Approvatore |
|-----------|------|-------------|
| Proposta schedule off-peak | supervisor (Decision.HITL_SUPERVISOR) | Supervisore energia / caposquadra |

### KPI Impattati

- **enpi_kwh_per_kg** — indice di prestazione energetica misurato (ISO 50001).
- **off_peak_kwh_pct** — percentuale del consumo totale nelle ore fuori picco.
- **energy_deviation_pct** — scostamento percentuale `enpi_actual` vs `enpi_baseline`.
- **peak_hour_cost_eur** — costo stimato del consumo in ore di picco tariffario.

### Invocazione

- **Endpoint API**: `POST /v1/agents/supply/energy-optimizer/analyze`
  con body `{"process": "dyeing", "ts_from": "<ISO-UTC>", "ts_to": "<ISO-UTC>", "user_roles": ["energy_supervisor"]}`
- **Resume**: `POST /v1/agents/supply/energy-optimizer/resume`
  con body `{"thread_id": "<id>", "decision": "approved"}`
- **Thread ID**: convenzione `supply.energy-optimizer.<uuid4>`.
- **Risposta analyze**: `202 Accepted` (HITL asincrono).
- **Risposta resume**: `200 OK` con `off_peak_proposal`.

### Audit Footprint

- `ENERGY_PROPOSAL` — una riga per ogni sessione dopo il resume HITL.
- Ogni riga porta `enpi_actual`, `enpi_baseline`, `off_peak_kwh_pct` nel campo `evidence_panel`.

---

## CostAnalyzer

### Panoramica

`CostAnalyzer` calcola il breakdown ROI delle attività operative aggregando le righe di
audit (downtime, scrap, energia) e simula il punteggio OEPV (Offerta Economicamente Più
Vantaggiosa) con la formula parametrica 70/30: 70% punteggio tecnico + 30% punteggio
economico con curva ribasso non lineare (SCM-03, ECO-02, ECO-05). Include una sensitivity
analysis sul ribasso. L'agente è **completamente autonomo** (Decision.AUTO) — nessun HITL:
opera in modalità read-only su `audit.actions` e scrive una sola riga `COST_REPORT`.

> **Nota F9 / F12:** Il simulatore OEPV implementato in Phase 9 è parametrico
> (coefficienti, Base d'Asta, soglie sono input configurabili). La precisione legale
> definitiva conforme al Codice dei Contratti Pubblici (D.Lgs. 36/2023) è demandata
> a **Phase 12**. Il calcolo attuale è adeguato per analisi gestionali interne.

### Strumenti Utilizzati

| Strumento | Origine | Funzione |
|-----------|---------|----------|
| `cost_aggregation` | scm-cost-analyzer.cost_aggregator | Aggrega le righe `audit.actions` per tipo (downtime, scrap, energia) e calcola il breakdown costi nel periodo. |
| `oepv_simulation` | scm-cost-analyzer.oepv | Pure function: calcola `Pe = Pe_max * (1 - exp(-lambda * Ri / Ri_ref))`; score totale `0.70 * Pt + 0.30 * Pe`; warning ribasso anomalo se `ribasso >= anomaly_threshold_pct`. |
| `sensitivity_analysis` | scm-cost-analyzer.oepv | Genera la tabella sensitivity per ribasso ±1%, ±5%, ±10% rispetto al valore di input. |

### Fonti Dati

- **TimescaleDB `audit.actions`** — unica fonte dati (read-only); righe di tipo
  downtime/scrap/energia lette per aggregazione costi.

### HITL Tier

`CostAnalyzer` è completamente autonomo (Decision.AUTO su tutte le operazioni).
Nessun HITL previsto (SCM-03). Non è presente l'endpoint `/resume`.

### KPI Impattati

- **roi_breakdown_eur** — breakdown del ROI per categoria di costo.
- **oepv_total_score** — punteggio OEPV totale simulato (0–100, parametrico F9).
- **oepv_sensitivity_pct** — variazione del punteggio totale per ±1%/±5%/±10% di ribasso.

### Invocazione

- **Endpoint API**: `POST /v1/agents/supply/cost-analyzer/analyze`
  con body `{"ts_from": "<ISO-UTC>", "ts_to": "<ISO-UTC>", "ribasso_pct": 12.5, "pt": 60.0, "user_roles": ["cost_analyst"]}`
- **Thread ID**: convenzione `supply.cost-analyzer.<uuid4>`.
- **Risposta**: `200 OK` (sincrona, autonoma — mai 202).
- Nessun endpoint `/resume` — l'agente è autonomo per definizione (D-SCM-AUTO).

### Audit Footprint

- `COST_REPORT` — una riga per ogni invocazione (autonoma, senza HITL).
- Il campo `evidence_panel` include `roi_breakdown_eur`, `oepv_total_score`, tabella sensitivity.

---

## DemandForecaster

### Panoramica

`DemandForecaster` prevede la domanda futura per gruppi SKU (es. jersey, twill) usando
l'algoritmo Holt-Winters Triple Exponential Smoothing additivo, implementato hand-rolled
con numpy (deterministico, LLM-free). Per serie con meno di 24 mesi di storia attiva il
fallback seasonal-naive. Il piano di domanda generato è sottoposto al ProductionPlanner
via approvazione HITL prima di essere consolidato (SCM-04). Il KPI di qualità della
previsione è il rolling MAPE.

### Strumenti Utilizzati

| Strumento | Origine | Funzione |
|-----------|---------|----------|
| `fetch_monthly_orders` | scm-demand-forecaster.repository | Aggrega ordini mensili per `sku_group` da `scm.historical_orders` su finestra configurabile (default 24 mesi). |
| `forecast_holt_winters` | scm-demand-forecaster.holt_winters | Triple Exponential Smoothing additivo (α=0.3, β=0.1, γ=0.3, stagionalità=12); fallback seasonal-naive se serie < 24 mesi. |
| `compute_mape` | scm-demand-forecaster.mape | Pure function: calcola il rolling MAPE tra valori attesi e previsti; clamp a 100% per evitare outlier. |
| `escalate_to_production_planner` | Phase 6 (`sft_agents.tools.hitl`) | Pubblica il piano domanda al ProductionPlanner per approvazione HITL prima del consolidamento. |

### Fonti Dati

- **TimescaleDB `scm.historical_orders`** — tabella relazionale degli ordini storici;
  colonne chiave: `sku_group`, `order_date`, `quantity_kg`; aggregazione mensile per gruppo.

### HITL Tier

| Decisione | Tier | Approvatore |
|-----------|------|-------------|
| Piano domanda draft → ProductionPlanner | supervisor (Decision.HITL_SUPERVISOR) | ProductionPlanner (cross-cluster via state) |

Il piano viene incluso in `state["demand_plan"]` dopo il resume. Il gateway può routarlo
separatamente al ProductionPlanner in un secondo step.

### KPI Impattati

- **demand_forecast_mape** — Mean Absolute Percentage Error del modello Holt-Winters (rolling).
- **production_plan_accuracy** — percentuale di mesi con scarto pianificato/effettivo ≤ 15%.
- **inventory_buffer_weeks** — settimane di scorta preventiva coperte dal piano.

### Invocazione

- **Endpoint API**: `POST /v1/agents/supply/demand-forecaster/forecast`
  con body `{"sku_groups": ["jersey", "twill"], "horizon_months": 6, "user_roles": ["production_planner"]}`
- **Resume**: `POST /v1/agents/supply/demand-forecaster/resume`
  con body `{"thread_id": "<id>", "decision": "approved"}`
- **Thread ID**: convenzione `supply.demand-forecaster.<uuid4>`.
- **Risposta forecast**: `202 Accepted` (HITL asincrono).
- **Risposta resume**: `200 OK` con `demand_plan` approvato.

### Audit Footprint

- `DEMAND_PLAN_DRAFT` — una riga dopo il primo calcolo (pre-HITL, approvazione pending).
- `DEMAND_PLAN_SIGNOFF` — una riga dopo il resume HITL approvato.
- Il campo `evidence_panel` include il metodo di previsione usato (holt_winters / seasonal_naive),
  l'orizzonte, il MAPE rolling e i `sku_groups` coperti.

---

## Dataset Sintetico Mantis

Per i dettagli numerici (SKU master, baseline EnPI, capacità produttiva, serie storiche ordini)
usati come base per la calibrazione degli agenti e i test di integrazione, fare riferimento
alla pagina dedicata:

- [Dataset Sintetico Mantis](mantis-synthetic-dataset.md)

> Tutti i valori del dataset Mantis sono **sintetici** — generati per dimostrazione e test.
> Non contengono dati reali di alcuna azienda (SCM-05).

---

## Garanzia Determinismo (Decision.AUTO / HITL)

Tutti e quattro gli agenti del cluster Supply Chain & Economics rispettano il principio
di **determinismo trasparente**: le decisioni operative (riordino, EnPI, OEPV, previsione HW)
sono calcolate da pure function testabili con input e output verificabili.

- Gli agenti HITL (InventoryManager, EnergyOptimizer, DemandForecaster) non eseguono
  azioni irreversibili senza il sign-off del supervisore.
- L'agente autonomo (CostAnalyzer) è read-only: aggrega dati esistenti senza modificare
  lo stato operativo.
- Ogni decisione è tracciata in `audit.actions` con `evidence_panel` contenente tutti i
  parametri usati nel calcolo.

```
SCM-03 (Decision.AUTO): "CostAnalyzer è completamente autonomo — nessun HITL.
        Opera in modalità read-only su audit.actions."
        — verificato da test_supply_cluster_e2e.py::test_cost_analyzer_no_hitl_autonomous
```
