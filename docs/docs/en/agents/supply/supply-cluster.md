---
lang: en
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

# Supply Chain & Economics Cluster

## Overview

The **Supply Chain & Economics** cluster groups the four agents responsible for
supply chain management, energy efficiency, cost analysis, and demand forecasting
in the textile factory:

| Agent | Primary Responsibility | HITL |
|-------|------------------------|------|
| **InventoryManager** | Warehouse level monitoring + reorder alert with procurement supervisor sign-off | Supervisor sign-off (SCM-01) |
| **EnergyOptimizer** | ISO 50001 EnPI kWh/kg analysis + off-peak schedule proposal with HITL | Supervisor sign-off (SCM-02) |
| **CostAnalyzer** | ROI breakdown + parametric OEPV 70/30 simulator + sensitivity analysis (autonomous) | No HITL (SCM-03, Decision.AUTO) |
| **DemandForecaster** | Deterministic Holt-Winters demand forecast + plan published to ProductionPlanner via HITL | Supervisor sign-off to ProductionPlanner (SCM-04) |

All four agents are **LLM-free** in their core decision path: the computations
(reorder-point, EnPI, OEPV, Holt-Winters) are deterministic pure functions.
The supply subgraph is instantiated by `build_supply_subgraph` in `clusters.py`,
with `cost-analyzer` as the fallback (autonomous, read-only, no irreversible side effects).

---

## InventoryManager

### Overview

`InventoryManager` monitors warehouse stock levels of raw materials, accessories,
and spare parts in real time. It deterministically computes the reorder point by
comparing the current quantity against the configured threshold for each SKU.
When the quantity falls below the threshold, it generates a reorder alert and
submits it to the procurement supervisor via HITL (SCM-01). The computation is LLM-free.

### Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `fetch_inventory_levels` | scm-inventory-manager.repository | Fetches the most recent levels for each SKU from `scm.inventory_levels` with a JOIN on `scm.sku_master` for thresholds and costs. |
| `check_reorder` | scm-inventory-manager.reorder | Pure function: compares `current_qty` against `reorder_point`; computes `deficit_qty` and `estimated_cost_eur`. |
| `escalate_to_procurement_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Sends the reorder alert to the procurement supervisor for HITL approval. |

### Data Sources

- **TimescaleDB `scm.inventory_levels`** — time-series hypertable of warehouse levels;
  the most recent record per `sku_id` provides the current quantity.
- **TimescaleDB `scm.sku_master`** — master table with `reorder_point`, `reorder_qty`,
  `lead_time_days`, `unit_cost_eur`; source of thresholds for the reorder computation.

### HITL Tier

| Decision | Tier | Approver |
|----------|------|---------|
| Reorder alert below threshold | supervisor (Decision.HITL_SUPERVISOR) | Procurement supervisor |

### KPIs Impacted

- **inventory_stockout_risk** — percentage of SKUs below the reorder point.
- **procurement_lead_time** — average days between reorder alert and goods receipt.
- **reorder_cost_eur** — economic value of generated reorder orders.

### Invocation

- **API endpoint**: `POST /v1/agents/supply/inventory-manager/analyze`
  with body `{"sku_ids": ["SKU-YARN-NE20-BLU", "..."], "user_roles": ["procurement_supervisor"]}`
- **Resume**: `POST /v1/agents/supply/inventory-manager/resume`
  with body `{"thread_id": "<id>", "decision": "approved"}`
- **Thread ID**: convention `supply.inventory-manager.<uuid4>`.
- **Analyze response**: `202 Accepted` (async HITL).
- **Resume response**: `200 OK` with `reorder_recommendation`.

### Audit Footprint

- `REORDER_ALERT` — one row per session, written after the HITL resume.
- Each row carries `approval_id` populated only after supervisor approval.

---

## EnergyOptimizer

### Overview

`EnergyOptimizer` analyses energy consumption (kWh) by process (dyeing, finishing,
spinning, weaving) by computing the ISO 50001 EnPI in kWh/kg and comparing it against
the configured baseline. It identifies opportunities to shift load to off-peak hours
and proposes an energy schedule to the supervisor via HITL (SCM-02). The computation
is LLM-free.

### Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `fetch_energy_readings` | scm-energy-optimizer.repository | Fetches readings from `scm.energy_readings` by process and time window; returns `kwh`, `kg_processed`, `is_peak_hour`. |
| `compute_enpi` | scm-energy-optimizer.enpi | Pure function ISO 50001: computes `enpi_actual = kwh_total / kg_total`; compares against baseline; computes `off_peak_kwh_pct` over all readings. |
| `propose_off_peak_schedule` | scm-energy-optimizer.scheduler | Generates a load-shifting proposal for off-peak hours with estimated kWh and cost savings. |
| `escalate_to_energy_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Sends the energy proposal to the supervisor for approval before shift dispatch. |

### Data Sources

- **TimescaleDB `scm.energy_readings`** — time-series hypertable of energy readings;
  key columns: `ts`, `asset_id`, `process`, `kwh`, `kg_processed`, `is_peak_hour`.
- **TimescaleDB `scm.enpi_baseline`** — ISO 50001 baseline per process (target kWh/kg and YTD);
  source for comparing `enpi_actual` vs `enpi_baseline`.

### HITL Tier

| Decision | Tier | Approver |
|----------|------|---------|
| Off-peak schedule proposal | supervisor (Decision.HITL_SUPERVISOR) | Energy supervisor / shift supervisor |

### KPIs Impacted

- **enpi_kwh_per_kg** — measured energy performance indicator (ISO 50001).
- **off_peak_kwh_pct** — percentage of total consumption in off-peak hours.
- **energy_deviation_pct** — percentage deviation of `enpi_actual` vs `enpi_baseline`.
- **peak_hour_cost_eur** — estimated cost of consumption during peak tariff hours.

### Invocation

- **API endpoint**: `POST /v1/agents/supply/energy-optimizer/analyze`
  with body `{"process": "dyeing", "ts_from": "<ISO-UTC>", "ts_to": "<ISO-UTC>", "user_roles": ["energy_supervisor"]}`
- **Resume**: `POST /v1/agents/supply/energy-optimizer/resume`
  with body `{"thread_id": "<id>", "decision": "approved"}`
- **Thread ID**: convention `supply.energy-optimizer.<uuid4>`.
- **Analyze response**: `202 Accepted` (async HITL).
- **Resume response**: `200 OK` with `off_peak_proposal`.

### Audit Footprint

- `ENERGY_PROPOSAL` — one row per session, written after the HITL resume.
- Each row carries `enpi_actual`, `enpi_baseline`, `off_peak_kwh_pct` in the `evidence_panel`.

---

## CostAnalyzer

### Overview

`CostAnalyzer` computes the ROI breakdown of operational activities by aggregating audit
rows (downtime, scrap, energy) and simulates the OEPV score (Most Economically Advantageous
Tender) using the parametric 70/30 formula: 70% technical score + 30% economic score
with a non-linear discount curve (SCM-03, ECO-02, ECO-05). It includes a sensitivity
analysis on the discount percentage. The agent is **fully autonomous** (Decision.AUTO) —
no HITL: it operates in read-only mode on `audit.actions` and writes a single `COST_REPORT` row.

> **Note F9 / F12:** The OEPV simulator implemented in Phase 9 is parametric
> (coefficients, Auction Base, thresholds are configurable inputs). The definitive
> legal precision compliant with the Italian Public Procurement Code (D.Lgs. 36/2023)
> is deferred to **Phase 12**. The current computation is suitable for internal
> management analysis.

### Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `cost_aggregation` | scm-cost-analyzer.cost_aggregator | Aggregates `audit.actions` rows by type (downtime, scrap, energy) and computes the cost breakdown over the period. |
| `oepv_simulation` | scm-cost-analyzer.oepv | Pure function: computes `Pe = Pe_max * (1 - exp(-lambda * Ri / Ri_ref))`; total score `0.70 * Pt + 0.30 * Pe`; anomaly warning if `discount >= anomaly_threshold_pct`. |
| `sensitivity_analysis` | scm-cost-analyzer.oepv | Generates a sensitivity table for discount ±1%, ±5%, ±10% relative to the input value. |

### Data Sources

- **TimescaleDB `audit.actions`** — sole data source (read-only); downtime/scrap/energy
  rows read for cost aggregation.

### HITL Tier

`CostAnalyzer` is fully autonomous (Decision.AUTO on all operations).
No HITL is defined (SCM-03). The `/resume` endpoint does not exist.

### KPIs Impacted

- **roi_breakdown_eur** — ROI breakdown by cost category.
- **oepv_total_score** — simulated OEPV total score (0–100, parametric F9).
- **oepv_sensitivity_pct** — total score variation for ±1%/±5%/±10% discount change.

### Invocation

- **API endpoint**: `POST /v1/agents/supply/cost-analyzer/analyze`
  with body `{"ts_from": "<ISO-UTC>", "ts_to": "<ISO-UTC>", "ribasso_pct": 12.5, "pt": 60.0, "user_roles": ["cost_analyst"]}`
- **Thread ID**: convention `supply.cost-analyzer.<uuid4>`.
- **Response**: `200 OK` (synchronous, autonomous — never 202).
- No `/resume` endpoint — the agent is autonomous by definition (D-SCM-AUTO).

### Audit Footprint

- `COST_REPORT` — one row per invocation (autonomous, no HITL).
- The `evidence_panel` includes `roi_breakdown_eur`, `oepv_total_score`, and the sensitivity table.

---

## DemandForecaster

### Overview

`DemandForecaster` forecasts future demand for SKU groups (e.g. jersey, twill) using
the Holt-Winters Triple Exponential Smoothing additive algorithm, implemented hand-rolled
with numpy (deterministic, LLM-free). For series with fewer than 24 months of history it
activates a seasonal-naive fallback. The generated demand plan is submitted to
ProductionPlanner via HITL approval before being consolidated (SCM-04). The forecast
quality KPI is the rolling MAPE.

### Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `fetch_monthly_orders` | scm-demand-forecaster.repository | Aggregates monthly orders by `sku_group` from `scm.historical_orders` over a configurable window (default 24 months). |
| `forecast_holt_winters` | scm-demand-forecaster.holt_winters | Triple Exponential Smoothing additive (α=0.3, β=0.1, γ=0.3, season=12); seasonal-naive fallback for series shorter than 24 months. |
| `compute_mape` | scm-demand-forecaster.mape | Pure function: computes rolling MAPE between actuals and forecasts; clamped to 100% to avoid outlier influence. |
| `escalate_to_production_planner` | Phase 6 (`sft_agents.tools.hitl`) | Publishes the demand plan to ProductionPlanner for HITL approval before consolidation. |

### Data Sources

- **TimescaleDB `scm.historical_orders`** — relational order history table;
  key columns: `sku_group`, `order_date`, `quantity_kg`; monthly aggregation per group.

### HITL Tier

| Decision | Tier | Approver |
|----------|------|---------|
| Demand plan draft → ProductionPlanner | supervisor (Decision.HITL_SUPERVISOR) | ProductionPlanner (cross-cluster via state) |

The plan is included in `state["demand_plan"]` after the resume. The gateway can
route it separately to ProductionPlanner in a subsequent step.

### KPIs Impacted

- **demand_forecast_mape** — Mean Absolute Percentage Error of the Holt-Winters model (rolling).
- **production_plan_accuracy** — percentage of months with planned vs actual deviation ≤ 15%.
- **inventory_buffer_weeks** — weeks of preventive stock covered by the plan.

### Invocation

- **API endpoint**: `POST /v1/agents/supply/demand-forecaster/forecast`
  with body `{"sku_groups": ["jersey", "twill"], "horizon_months": 6, "user_roles": ["production_planner"]}`
- **Resume**: `POST /v1/agents/supply/demand-forecaster/resume`
  with body `{"thread_id": "<id>", "decision": "approved"}`
- **Thread ID**: convention `supply.demand-forecaster.<uuid4>`.
- **Forecast response**: `202 Accepted` (async HITL).
- **Resume response**: `200 OK` with approved `demand_plan`.

### Audit Footprint

- `DEMAND_PLAN_DRAFT` — one row after the initial computation (pre-HITL, approval pending).
- `DEMAND_PLAN_SIGNOFF` — one row after the approved HITL resume.
- The `evidence_panel` includes the forecast method used (holt_winters / seasonal_naive),
  the horizon, the rolling MAPE, and the covered `sku_groups`.

---

## Mantis Synthetic Dataset

For numerical details (SKU master, EnPI baselines, plant capacity, historical order series)
used as the calibration base for agents and integration tests, see the dedicated page:

- [Mantis Synthetic Dataset](mantis-synthetic-dataset.md)

> All Mantis dataset values are **synthetic** — generated for demonstration and testing.
> They do not contain real data from any company (SCM-05).

---

## Determinism Guarantee (Decision.AUTO / HITL)

All four Supply Chain & Economics cluster agents comply with the principle of
**transparent determinism**: operational decisions (reorder, EnPI, OEPV, HW forecast)
are computed by testable pure functions with verifiable inputs and outputs.

- HITL agents (InventoryManager, EnergyOptimizer, DemandForecaster) do not perform
  irreversible actions without supervisor sign-off.
- The autonomous agent (CostAnalyzer) is read-only: it aggregates existing data
  without modifying operational state.
- Every decision is recorded in `audit.actions` with an `evidence_panel` containing
  all parameters used in the computation.

```
SCM-03 (Decision.AUTO): "CostAnalyzer is fully autonomous — no HITL.
        Operates in read-only mode on audit.actions."
        — verified by test_supply_cluster_e2e.py::test_cost_analyzer_no_hitl_autonomous
```
