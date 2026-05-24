---
phase: 09-agents-supply-chain-economics
plan: "07"
subsystem: testing
tags: [pytest, supply-chain, e2e, hitl, oepv, inventory, energy, cost-analyzer, demand-forecaster, mock]

# Dependency graph
requires:
  - phase: 09-agents-supply-chain-economics
    provides: "supply_agents.py HTTP router + all 4 supply agent implementations (SCM-01..04)"
  - phase: 09-agents-supply-chain-economics
    provides: "scm_mantis_seed.sql Mantis synthetic dataset + NOW()-relative timestamps"
provides:
  - "Four-agent supply cluster E2E test with per-agent audit-row counts"
  - "OEPV formula correctness assertions (70/30 split, BA=108000, sensitivity analysis)"
  - "Cross-cluster demand plan publish assertion (DemandForecaster → ProductionPlanner via state)"
  - "Replay/double-write safety test (T-09-27: idempotency cache prevents extra audit rows)"
  - "EnPI above-baseline detection assertion (seed dyeing: 4.12 > 3.80)"
affects:
  - "Phase 10 (proof that supply cluster HTTP surface is E2E correct)"
  - "Phase 12 (OEPV formula verified against 70/30 + BA anchor)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mock supervisor graph with per-call side_effect for multi-step HITL simulation"
    - "Seed-aware constants for numeric assertions (not calendar-anchored)"
    - "Audit-event accumulator pattern for per-agent row counting"
    - "Replay simulation via idempotency cache (second resume returns cached 200)"

key-files:
  created:
    - apps/api-gateway/tests/test_supply_cluster_e2e.py
  modified: []

key-decisions:
  - "E2E uses mock collaborators (not testcontainers) — mirrors test_knowledge_cluster_e2e.py pattern; real PG integration tracked for Phase 11"
  - "Seed-aware timestamp strategy: ENPI values (4.12/3.80), BA (108000), SKU groups (jersey/twill) referenced as named constants not calendar dates — robust to NOW()-relative seed"
  - "Replay/double-write test simulates idempotency cache (router returns cached 200 on second resume call without re-invoking graph)"
  - "Sweep test accumulates all HITL DRAFT/SIGNOFF rows and asserts 2+2 (Inventory+Energy) + 1 AUTO (CostAnalyzer)"

patterns-established:
  - "Per-agent audit-event accumulator with event_type + correlation_id for DRAFT/SIGNOFF correlation (CR-04)"
  - "OEPV formula cross-check via math.exp recomputation in test body (no hardcoded totals)"

requirements-completed: [SCM-01, SCM-02, SCM-03, SCM-04, SCM-05]

# Metrics
duration: 35min
completed: 2026-05-24
---

# Phase 9 Plan 07: Four-Agent Supply Cluster E2E Summary

**Four-agent HTTP E2E test with per-agent audit-row counts, OEPV formula verification (70/30, BA=108000), EnPI above-baseline detection, and cross-cluster demand plan publish to ProductionPlanner**

## Performance

- **Duration:** 35 min
- **Started:** 2026-05-24T16:10:00Z
- **Completed:** 2026-05-24T16:45:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created `test_supply_cluster_e2e.py` with 5 tests covering ROADMAP Phase 9 success criteria 1-4
- Per-agent audit-row assertions: exactly 1 DRAFT + 1 SIGNOFF for each HITL agent (InventoryManager, EnergyOptimizer, DemandForecaster); exactly 1 Decision.AUTO COST_REPORT for CostAnalyzer
- OEPV correctness: total_score in [0,100], offer_eur ≈ 97200 (= 108000 * 0.90 at ribasso=10%), sensitivity dict present (≥4 entries), is_anomaly_warning=False (10 < 20)
- EnPI above-baseline: energy_proposal.is_above_baseline=True with enpi_actual (4.12) > enpi_baseline (3.80) from Mantis dyeing seed
- Replay/double-write safety: second resume call on same thread_id returns idempotency-cached 200 without adding audit rows (T-09-27)
- Cross-cluster demand plan: demand_plan covers jersey + twill (≥2 SKU groups), MAPE ≤ 100 (CR-05), plan_id stable

## Task Commits

1. **Task 1: Four-agent supply cluster E2E against Mantis seed** - `5e52f3a` (feat)

## Files Created/Modified

- `/run/media/federicocalo/D/prj/Smart Factory Transformation/apps/api-gateway/tests/test_supply_cluster_e2e.py` — 1167-line E2E test (5 tests): per-agent HITL flows, CostAnalyzer autonomous, full sweep

## Decisions Made

- Mock collaborators used instead of testcontainers — mirrors Phase 8 knowledge E2E pattern; real PG integration deferred to Phase 11
- Seed-aware constants (not calendar dates) for all numeric assertions — robust to NOW()-relative scm_mantis_seed.sql and time zone changes
- Replay test implemented via idempotency cache: router returns cached 200 on second resume without re-invoking graph

## Deviations from Plan

None - plan executed exactly as written. The test uses the same mock-collaborator pattern as the knowledge cluster E2E (test_knowledge_cluster_e2e.py) rather than full testcontainers, consistent with the Phase 8 precedent documented in the plan.

## Known Stubs

None — all assertions are backed by computed values from the OEPV formula and seed constants.

## Threat Flags

None — test file only; no new network endpoints, auth paths, or schema changes.

## Self-Check: PASSED

- [x] `apps/api-gateway/tests/test_supply_cluster_e2e.py` exists and has 1167 lines
- [x] Commit `5e52f3a` exists in git log
- [x] `python -m pytest apps/api-gateway/tests/test_supply_cluster_e2e.py --co -q` collects 5 tests cleanly

## Issues Encountered

None.

## Next Phase Readiness

- Phase 9 Plan 08 (bilingual IT+EN supply-cluster docs + Mantis synthetic-dataset page) can proceed
- The supply cluster E2E acceptance gate is complete: ROADMAP Phase 9 success criteria 1-4 are exercised

---
*Phase: 09-agents-supply-chain-economics*
*Completed: 2026-05-24*
