---
phase: 09-agents-supply-chain-economics
plan: "08"
subsystem: docs
tags:
  - docs
  - supply-cluster
  - bilingual
  - synthetic-dataset
  - SCM-05
dependency_graph:
  requires:
    - "09-02"
    - "09-03"
    - "09-04"
    - "09-05"
    - "09-06"
  provides:
    - bilingual IT/EN supply cluster documentation
    - Mantis synthetic dataset documentation (SCM-05)
  affects:
    - docs/mkdocs.yml
tech_stack:
  added: []
  patterns:
    - Mirror Phase 8 knowledge-cluster doc layout (IT canonical + EN parallel)
    - Explicit synthetic banner pattern (SCM-05 requirement)
    - mkdocs i18n plugin nav_translations for Supply Chain section
key_files:
  created:
    - docs/docs/agents/supply/supply-cluster.md
    - docs/docs/agents/supply/mantis-synthetic-dataset.md
    - docs/docs/en/agents/supply/supply-cluster.md
    - docs/docs/en/agents/supply/mantis-synthetic-dataset.md
  modified:
    - docs/mkdocs.yml
decisions:
  - "Followed Phase 8 knowledge-cluster layout exactly: IT canonical in docs/docs/agents/supply/, EN parallel in docs/docs/en/agents/supply/"
  - "CostAnalyzer documented as fully autonomous (Decision.AUTO) with explicit note on OEPV F9 vs F12 legal precision"
  - "nav_translations in mkdocs.yml extended with Supply Chain / Supply Cluster / Mantis Synthetic Dataset entries"
metrics:
  duration: "20min"
  completed: "2026-05-24"
  tasks_completed: 1
  files_changed: 5
---

# Phase 9 Plan 08: Bilingual Supply Cluster Docs + Mantis Synthetic Dataset Summary

## One-liner

Bilingual IT/EN docs for the four supply agents (tools, data sources, HITL tier, KPIs from metadata.py) plus a dedicated Mantis synthetic dataset page explicitly labeled synthetic (SCM-05), wired into mkdocs nav with a green strict build.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Bilingual supply-cluster + Mantis synthetic dataset docs + mkdocs nav (SCM-05) | e603bcf | docs/docs/agents/supply/supply-cluster.md, docs/docs/agents/supply/mantis-synthetic-dataset.md, docs/docs/en/agents/supply/supply-cluster.md, docs/docs/en/agents/supply/mantis-synthetic-dataset.md, docs/mkdocs.yml |

## Deviations from Plan

None — plan executed exactly as written.

## Acceptance Criteria Verification

- [x] All four IT+EN pages exist and are in the docs/mkdocs.yml nav under the agents section.
- [x] The Mantis dataset page explicitly labels all values synthetic (IT "sintetici", EN "synthetic").
- [x] `mkdocs build --strict` succeeds (no broken links); grep finds zero "Accenture" references.
- [x] InventoryManager documented in IT supply-cluster.md.
- [x] mantis-synthetic-dataset.md contains "sintetic" (verified by automated check).

## Content Summary

### supply-cluster.md (IT + EN)

Documenta i quattro agenti del cluster supply con la struttura identica al knowledge-cluster:

- **InventoryManager** (SCM-01): tools `fetch_inventory_levels`, `check_reorder`, `escalate_to_procurement_supervisor`; fonti `scm.inventory_levels` + `scm.sku_master`; HITL supervisor; KPI `inventory_stockout_risk`, `procurement_lead_time`, `reorder_cost_eur`.
- **EnergyOptimizer** (SCM-02): tools `fetch_energy_readings`, `compute_enpi`, `propose_off_peak_schedule`, `escalate_to_energy_supervisor`; fonti `scm.energy_readings` + `scm.enpi_baseline`; HITL supervisor; KPI `enpi_kwh_per_kg`, `off_peak_kwh_pct`, `energy_deviation_pct`, `peak_hour_cost_eur`.
- **CostAnalyzer** (SCM-03): tools `cost_aggregation`, `oepv_simulation`, `sensitivity_analysis`; fonte `audit.actions` (read-only); AUTONOMO (Decision.AUTO); KPI `roi_breakdown_eur`, `oepv_total_score`, `oepv_sensitivity_pct`; nota esplicita su F9 vs F12 (precisione legale OEPV demandata a Phase 12).
- **DemandForecaster** (SCM-04): tools `fetch_monthly_orders`, `forecast_holt_winters`, `compute_mape`, `escalate_to_production_planner`; fonte `scm.historical_orders`; HITL supervisor verso ProductionPlanner; KPI `demand_forecast_mape`, `production_plan_accuracy`, `inventory_buffer_weeks`.

### mantis-synthetic-dataset.md (IT + EN)

Pagina dedicata SCM-05 con banner prominente "dati completamente sintetici / completely synthetic data":

- SKU master (8 SKU: filati, coloranti, ricambi, tessuti jersey/twill) con soglie, prezzi, lead time.
- Baseline EnPI ISO 50001: tintoria 3,80 target / 4,12 YTD (+8,4%), finissaggio 2,20 target / 2,18 YTD (-0,9%).
- Capacità produttiva Mantis (12 telai, 4 vasche tintoria, 2 stentatoi).
- Serie storiche 19 mesi (Gen 2024 – Lug 2025): jersey ~12.000 kg/mese (picco estivo +35%, invernale +20%), twill ~8.000 kg/mese (CV ~12%).
- Parametri OEPV sintetici: BA=108.000€, scoring 70/30, λ=3.0, Ri_ref=20%.
- Provenance table: label `source = 'mantis_synthetic'` in tutte le righe seed.

### mkdocs.yml

Aggiunta sezione "Supply Chain" sotto "Agenti" con:
- `agents/supply/supply-cluster.md` (IT)
- `agents/supply/mantis-synthetic-dataset.md` (IT)
- Voci EN via `nav_translations`: "Supply Chain", "Supply Cluster", "Mantis Synthetic Dataset"

## Known Stubs

None — all content is sourced directly from metadata.py files and 09-RESEARCH.md Pattern 11.

## Threat Flags

None — purely documental; no new runtime surface introduced. T-09-28 (synthetic data mislabeled) and T-09-29 (brand reference leak) both mitigated: banner explicit + grep verified zero brand references.

## Self-Check: PASSED

- [x] docs/docs/agents/supply/supply-cluster.md — FOUND
- [x] docs/docs/agents/supply/mantis-synthetic-dataset.md — FOUND
- [x] docs/docs/en/agents/supply/supply-cluster.md — FOUND
- [x] docs/docs/en/agents/supply/mantis-synthetic-dataset.md — FOUND
- [x] Commit e603bcf — FOUND
- [x] mkdocs build --strict — PASSED (Documentation built in 3.54 seconds)
- [x] "sintetic" in mantis-synthetic-dataset.md — VERIFIED
- [x] Zero "accenture" in all 4 files — VERIFIED
- [x] "InventoryManager" in supply-cluster.md — VERIFIED
