---
phase: 09-agents-supply-chain-economics
plan: 00a
subsystem: infra/migrations + packages/sft-agents
tags: [migration, timescaledb, scm-schema, audit-enum, lockstep, hypertable]
dependency_graph:
  requires: [08-00a]
  provides: [scm-schema-ddl, audit-action-type-phase9]
  affects: [09-00b, 09-01, 09-02, 09-03, 09-04, 09-05, 09-06, 09-07]
tech_stack:
  added: []
  patterns: [timescaledb-hypertable, drop-add-check-idempotent, enum-sql-lockstep]
key_files:
  created:
    - infra/migrations/timescale/011_create_scm_schema.sql
    - infra/migrations/timescale/tests/test_migration_011.py
    - infra/migrations/timescale/012_extend_audit_scm.sql
    - infra/migrations/timescale/tests/test_migration_012.py
  modified:
    - packages/sft-agents/src/sft_agents/models/enums.py
decisions:
  - "8 Phase 9 ActionType values (incl. COST_REPORT) chosen to cover all 4 supply agents: 3 HITL agents (InventoryManager, EnergyOptimizer, DemandForecaster) × draft+signoff pairs + CostAnalyzer autonomous COST_REPORT"
  - "scm.historical_orders is NOT a hypertable — order frequency too low for time-series partitioning; relational table with timestamp index is sufficient for DemandForecaster"
metrics:
  duration: "6 minutes"
  completed: "2026-05-24"
  tasks: 2
  files: 5
---

# Phase 9 Plan 00a: Migration 011 (scm.* schema) + Migration 012 (ActionType enum/CHECK lockstep) Summary

**One-liner:** scm.* TimescaleDB schema with 2 hypertables + 8-value Phase 9 ActionType lockstep (incl. COST_REPORT) across SQL CHECK and Python enum.

## What Was Built

### Task 1: Migration 011 — scm.* Schema DDL + Hypertables

**File:** `infra/migrations/timescale/011_create_scm_schema.sql`

Created the synthetic `scm.*` schema with 5 tables required by all four Phase 9 supply-chain agents:

- `scm.sku_master` — SKU reference table with `category CHECK IN ('raw_yarn','accessory','spare_part','fabric')`
- `scm.inventory_levels` — TimescaleDB hypertable (partition key: `ts`); InventoryManager stock-level queries
- `scm.energy_readings` — TimescaleDB hypertable (partition key: `ts`) with `process CHECK IN ('dyeing','finishing','spinning','weaving','other')`; EnergyOptimizer kWh/kg EnPI
- `scm.historical_orders` — relational table with timestamp; DemandForecaster Holt-Winters input
- `scm.enpi_baseline` — ISO 50001 kWh/kg targets per process (reference table)

All DDL uses `IF NOT EXISTS` / `if_not_exists => TRUE` for idempotency. Includes composite indexes for efficient per-SKU/per-process time-ordered queries.

**Test file:** `infra/migrations/timescale/tests/test_migration_011.py`

12 integration tests covering: schema existence, all 5 tables via `to_regclass`, both hypertables via `timescaledb_information.hypertables`, `sku_master.category` CHECK reject, `energy_readings.process` CHECK reject, idempotency double-apply, migrate() runner glob.

### Task 2: Migration 012 + ActionType Enum Lockstep + Migration Test

**File:** `infra/migrations/timescale/012_extend_audit_scm.sql`

Extended `audit.actions.action_type` CHECK constraint (idempotent DROP IF EXISTS + ADD) with 8 new Phase 9 values while preserving all Phase 1-8 legacy values:

| Value | Agent | Pattern |
|-------|-------|---------|
| `REORDER_ALERT` | InventoryManager | SCM-01 reorder threshold crossed |
| `PURCHASE_RECOMMENDATION_DRAFT` | InventoryManager | SCM-01 HITL draft |
| `PURCHASE_SIGNOFF` | InventoryManager | SCM-01 supervisor sign-off |
| `ENERGY_PROPOSAL` | EnergyOptimizer | SCM-02 off-peak proposal draft |
| `ENERGY_SIGNOFF` | EnergyOptimizer | SCM-02 supervisor sign-off |
| `DEMAND_PLAN_DRAFT` | DemandForecaster | SCM-04 demand plan draft |
| `DEMAND_PLAN_SIGNOFF` | DemandForecaster | SCM-04 ProductionPlanner publish sign-off |
| `COST_REPORT` | CostAnalyzer | SCM-03 autonomous ROI/OEPV report (Decision.AUTO) |

**File:** `packages/sft-agents/src/sft_agents/models/enums.py`

Appended 8 `ActionType` enum members with string values byte-identical to the SQL CHECK literals. Updated docstring to reference migration 012. All enum member names match their values exactly (lockstep invariant).

**Test file:** `infra/migrations/timescale/tests/test_migration_012.py`

35 integration tests covering: pre-migration reject of `REORDER_ALERT`, post-migration admit, parametrized admit-all-Phase9 (×8), parametrized legacy-regression (×22 covering all Phase 1-8 values incl. Phase 8), Decision-CHECK-unchanged, idempotent double-apply, migrate() runner glob.

## Verification Results

| Check | Result |
|-------|--------|
| `011` DDL: all 5 tables + `CREATE SCHEMA IF NOT EXISTS scm` | PASS |
| `011` DDL: `create_hypertable` called ≥ 2 times | PASS (2 calls) |
| `test_migration_011.py` collects ≥ 5 tests | PASS (12 collected) |
| `012` SQL: all 8 Phase 9 literals present | PASS |
| `012` SQL: `SOP_DRAFT`, `OEE_REPORT`, `ANOMALY_ALERT` present (legacy) | PASS |
| `012` SQL: `DROP CONSTRAINT IF EXISTS` present | PASS |
| `enums.py`: all 8 Phase 9 enum members importable | PASS |
| `ActionType.REORDER_ALERT.value == 'REORDER_ALERT'` | PASS |
| `ActionType.COST_REPORT.value == 'COST_REPORT'` | PASS |
| `test_migration_012.py` collects ≥ 7 tests | PASS (35 collected) |

## Commits

| Task | Commit | Files |
|------|--------|-------|
| Task 1: Migration 011 + test | `9a8e77f` | `011_create_scm_schema.sql`, `test_migration_011.py` |
| Task 2: Migration 012 + enum + test | `d642284` | `012_extend_audit_scm.sql`, `enums.py`, `test_migration_012.py` |

## Deviations from Plan

None — plan executed exactly as written.

Both tasks followed the exact migration patterns from 010_extend_audit_knw.sql and test_migration_010.py.

## Threat Model Compliance

| Threat ID | Status |
|-----------|--------|
| T-09-01: migration 012 CHECK — legacy regression | Mitigated — test_migration_012.py asserts all Phase 1-8 values still admitted (22 parametrized tests) |
| T-09-02: enum/SQL lockstep drift | Mitigated — automated verify confirms byte-identical 8-value set in both files |
| T-09-03: scm.* category/process CHECK | Mitigated — test_migration_011.py rejects `invalid_category` and `invalid_process` |
| T-09-SC: no package installs | Accepted — no new packages installed; `statsmodels` not used as decided |

## Known Stubs

None — this plan creates DDL and tests only. No agent logic, no placeholder data, no UI rendering.

## Self-Check: PASSED

- `infra/migrations/timescale/011_create_scm_schema.sql` — EXISTS
- `infra/migrations/timescale/tests/test_migration_011.py` — EXISTS (12 tests collected)
- `infra/migrations/timescale/012_extend_audit_scm.sql` — EXISTS
- `infra/migrations/timescale/tests/test_migration_012.py` — EXISTS (35 tests collected)
- `packages/sft-agents/src/sft_agents/models/enums.py` — MODIFIED (8 new members)
- Commit `9a8e77f` — EXISTS (`feat(09-00a): migration 011...`)
- Commit `d642284` — EXISTS (`feat(09-00a): migration 012...`)
