---
status: partial
phase: 09-agents-supply-chain-economics
source: [09-VERIFICATION.md]
started: 2026-05-24T16:00:00Z
updated: 2026-05-24T16:00:00Z
---

## Current Test

[awaiting human testing — requires Docker/testcontainers]

## Tests

### 1. Migration 011 (scm.* schema) su TimescaleDB
expected: `make migrate-timescale` applica 011 in modo idempotente; schema scm.* con 5 tabelle (sku_master, inventory_levels + energy_readings hypertable, historical_orders, enpi_baseline), CHECK su category/process.
result: [pending]

### 2. Migration 012 (ActionType enum lockstep)
expected: 012 estende il CHECK con gli 8 valori Phase 9 (incl. COST_REPORT) senza regressioni sui valori legacy Phase 1-8; Decision CHECK invariato; lockstep byte-identico con enums.py.
result: [pending]

### 3. Idempotenza seed Mantis su hypertable
expected: doppio caricamento di scm_mantis_seed.sql lascia i row count stabili su tutte e 5 le tabelle (DELETE-guard sulle 2 hypertable senza PK — fix WR-01).
result: [pending]

### 4. E2E supply cluster (4 agenti) su testcontainers
expected: test_supply_cluster_e2e.py verde — InventoryManager reorder→draft→signoff, EnergyOptimizer EnPI→proposal→signoff, CostAnalyzer autonomo COST_REPORT (Decision.AUTO), DemandForecaster forecast→signoff→demand_plan in state; conteggi audit per agente esatti, no double-write su replay, OEPV offer_eur coerente.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
