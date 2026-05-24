---
phase: 09-agents-supply-chain-economics
plan: 00b
subsystem: supply-agents-test-scaffold
tags: [nyquist, tdd, test-scaffold, hitl, supply-chain]
dependency_graph:
  requires: [09-00a]
  provides: [acceptance-surface-inventory-manager, acceptance-surface-energy-optimizer, acceptance-surface-cost-analyzer, acceptance-surface-demand-forecaster]
  affects: [09-02, 09-03, 09-04, 09-05]
tech_stack:
  added: []
  patterns: [nyquist-scaffold, interrupt-then-audit, stable-id-from-thread_id, decision-auto, mape-clamp, per-agent-importlib]
key_files:
  created:
    - apps/agents/supply/inventory-manager/tests/__init__.py
    - apps/agents/supply/inventory-manager/tests/conftest.py
    - apps/agents/supply/inventory-manager/tests/test_reorder.py
    - apps/agents/supply/inventory-manager/tests/test_inventory_hitl.py
    - apps/agents/supply/energy-optimizer/tests/__init__.py
    - apps/agents/supply/energy-optimizer/tests/conftest.py
    - apps/agents/supply/energy-optimizer/tests/test_enpi.py
    - apps/agents/supply/energy-optimizer/tests/test_energy_hitl.py
    - apps/agents/supply/cost-analyzer/tests/__init__.py
    - apps/agents/supply/cost-analyzer/tests/conftest.py
    - apps/agents/supply/cost-analyzer/tests/test_oepv.py
    - apps/agents/supply/cost-analyzer/tests/test_cost_analyzer_agent.py
    - apps/agents/supply/demand-forecaster/tests/__init__.py
    - apps/agents/supply/demand-forecaster/tests/conftest.py
    - apps/agents/supply/demand-forecaster/tests/test_holt_winters.py
    - apps/agents/supply/demand-forecaster/tests/test_mape.py
    - apps/agents/supply/demand-forecaster/tests/test_demand_hitl.py
  modified:
    - apps/agents/supply/inventory-manager/pyproject.toml
    - apps/agents/supply/energy-optimizer/pyproject.toml
    - apps/agents/supply/cost-analyzer/pyproject.toml
    - apps/agents/supply/demand-forecaster/pyproject.toml
decisions:
  - "Supply agent test scaffold uses pytest.fail() bodies naming the unimplemented contract; no module-level pytest.skip (mirrors Phase 6/7/8 decision)"
  - "pytest asyncio_mode=auto + import-mode=importlib added to all 4 supply agent pyproject.toml (Rule 3 auto-fix, mirrors shift-handover pattern)"
  - "Monorepo conftest collision (ImportPathMismatchError: tests.conftest) when running pytest apps/agents/supply together is a pre-existing issue identical to Phase 7/8 — accepted; per-agent execution is the intended nx workflow"
  - "conftest.py uses make_interrupt_fn factory (NOT MagicMock) per WR-01 — MagicMock silently swallows raise behaviour"
  - "test_cost_analyzer_agent.py asserts interrupt never called (autonomous Decision.AUTO) — mirrors KnowledgeCurator D-KC-04 pattern"
  - "test_demand_hitl.py encodes Open Question 2 resolution: cross-cluster to ProductionPlanner via state['demand_plan'], not direct invocation"
metrics:
  duration: 15min
  completed: "2026-05-24T14:06:37Z"
  tasks: 1
  files_created: 17
  files_modified: 4
---

# Phase 9 Plan 00b: Supply Agent Test Scaffolds (Nyquist) Summary

**One-liner:** Nyquist test-contract scaffolds for 4 supply agents encoding interrupt-then-audit, stable-id-from-thread_id, Decision.AUTO, MAPE clamp, and OEPV parametric contracts before any Wave 2-5 implementation.

## Objective

Wave 1 foundation B for Phase 9: scaffold every supply agent test file so downstream waves implement against a known contract (Nyquist rule — tests before implementation). Mirrors the 08-00b pattern exactly.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Supply agent test scaffolds (Nyquist) | 0e15fdf | 17 created, 4 modified |

## What Was Built

**4 test packages** (each with `__init__.py` + `conftest.py`):
- `inventory-manager/tests/` — AsyncMock pool + audit_writer + make_interrupt_fn factory
- `energy-optimizer/tests/` — same fixtures + make_interrupt_fn
- `cost-analyzer/tests/` — pool + audit_writer only (autonomous agent, no interrupt)
- `demand-forecaster/tests/` — full fixtures including make_interrupt_fn

**9 test files with explicit `pytest.fail()` contract bodies:**

| File | Contract Named | Requirements |
|------|---------------|--------------|
| `test_reorder.py` | check_reorder: is_below_threshold, deficit_qty, estimated_cost_eur, Decimal arithmetic | SCM-01 |
| `test_inventory_hitl.py` | interrupt-then-audit + PURCHASE_RECOMMENDATION_DRAFT/SIGNOFF + stable recommendation_id from thread_id + approval_id=None | SCM-01, CR-02/CR-03/CR-04 |
| `test_enpi.py` | compute_enpi ISO 50001 kWh/kg: valid slots, deviation_pct, off_peak_pct, ValueError | SCM-02 |
| `test_energy_hitl.py` | ENERGY_PROPOSAL/SIGNOFF lifecycle + CR guardrails | SCM-02, CR-02/CR-03/CR-04 |
| `test_oepv.py` | compute_oepv: 0.70*Pt+0.30*Pe, non-linear ribasso curve, OepvConfig no-hardcode, anomaly warning, sensitivity ±1/5/10% | SCM-03, ECO-02/ECO-05 |
| `test_cost_analyzer_agent.py` | Autonomous: no interrupt, Decision.AUTO, COST_REPORT, read-only, positional AuditRecord | SCM-03 |
| `test_holt_winters.py` | Deterministic HW output, seasonal_naive fallback < min_periods, non-negative forecasts | SCM-04 |
| `test_mape.py` | Per-point contribution clamp 1.0, skip actuals<=0, empty input → 0.0, MAPE<=100 | SCM-04, CR-05 |
| `test_demand_hitl.py` | DEMAND_PLAN_DRAFT/SIGNOFF, state['demand_plan'] >= 2 SKU groups, cross-cluster via state (Open Q2), CR guardrails | SCM-04, CR-02/CR-03/CR-04 |

**Test collection counts (per-agent, clean):**
- inventory-manager: 15 tests
- energy-optimizer: 14 tests
- cost-analyzer: 20 tests
- demand-forecaster: 25 tests
- **Total: 74 tests**

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added pytest asyncio_mode + import-mode=importlib to all 4 supply agent pyproject.toml**
- **Found during:** Task 1 verification (`pytest apps/agents/supply --co` shows `ImportPathMismatchError`)
- **Issue:** All 4 `tests/conftest.py` files had the same module name `tests.conftest`. When collected together, pytest's default import mode causes `ImportPathMismatchError: Plugin already registered under a different name`.
- **Fix:** Added `[tool.pytest.ini_options] asyncio_mode = "auto" / addopts = "--import-mode=importlib"` to all 4 supply agent `pyproject.toml` files. Mirrors the shift-handover pattern from Phase 8 (identical fix).
- **Note:** The monorepo-wide conftest collision when running `pytest apps/agents/supply` in a single invocation is a **pre-existing issue identical to Phase 7/8**. The intended execution model is per-package (`nx run scm-inventory-manager:test`) or per-agent pytest invocation. All 74 tests collect cleanly per-agent.
- **Files modified:** `inventory-manager/pyproject.toml`, `energy-optimizer/pyproject.toml`, `cost-analyzer/pyproject.toml`, `demand-forecaster/pyproject.toml`
- **Commit:** 0e15fdf

## Phase 8 Anti-Bug Guardrails Encoded

| Bug | Guard in scaffold |
|-----|-------------------|
| CR-02: audit write before interrupt (double-write on replay) | All HITL tests assert `write.call_count == 0` before interrupt raises |
| CR-02: AuditWriter called with kwargs | All HITL tests assert positional AuditRecord call |
| CR-03: approval_id fabricated UUID | All HITL tests assert `approval_id=None` on pending rows |
| CR-04: uuid4() inline — unstable ID on replay | All HITL tests assert stable ID from `thread_id` (grep confirms `thread_id` present) |
| CR-05: KPI overflow past Pydantic le= | test_mape.py asserts MAPE <= 100 before model construction |
| WR-01: MagicMock masking interrupt failure | conftest uses `make_interrupt_fn` factory — NOT `MagicMock` for interrupt |

## Known Stubs

None — this plan creates test scaffolds only. All test functions call `pytest.fail()` with explicit contract-naming messages. No implementation stubs or placeholder data.

## Threat Flags

None — test scaffold files only; no network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

All 17 test files + 4 pyproject.toml modifications verified present and committed (0e15fdf).
Per-agent collection: 15 + 14 + 20 + 25 = 74 tests collected without import errors.
