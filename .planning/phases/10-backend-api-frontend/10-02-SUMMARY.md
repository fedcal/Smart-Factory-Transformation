---
phase: 10-backend-api-frontend
plan: "02"
subsystem: api-gateway/kpi
tags: [kpi, oee, timescaledb, rbac, fastapi, asyncpg]
dependency_graph:
  requires: ["10-01"]
  provides: ["compute_kpi_snapshot", "GET /v1/kpi"]
  affects: ["10-03"]
tech_stack:
  added: []
  patterns:
    - asyncpg $N params (CR-05 SQL injection guardrail)
    - Pydantic frozen model with extra=forbid (CR-03)
    - OEE availability formula reused from Phase 7 mnt_downtime_analyzer/oee.py
    - conn-vs-pool dispatch pattern (fetchrow presence check) for testability
key_files:
  created:
    - apps/api-gateway/src/svc_api_gateway/kpi/__init__.py
    - apps/api-gateway/src/svc_api_gateway/kpi/queries.py
    - apps/api-gateway/src/svc_api_gateway/routers/kpi.py
  modified:
    - apps/api-gateway/src/svc_api_gateway/main.py
    - apps/api-gateway/tests/unit/test_kpi_queries.py
decisions:
  - OEE = Availability-only (P=1.0, Q=1.0 PoC approximation) — RESEARCH Pattern 7; Phase 11 can wire real P/Q
  - scrap_rate uses QUALITY_VERDICT audit rows as a proxy (no sensor_events direct path in this plan)
  - conn-vs-pool dispatch checks fetchrow attribute (not acquire) to avoid AsyncMock false positives
  - Preexisting supply_cluster_e2e failures (2 tests) not caused by this plan — logged to deferred items
metrics:
  duration: "35min"
  completed: "2026-05-24"
  tasks_completed: 2
  files_changed: 5
---

# Phase 10 Plan 02: KPI Aggregations (SRV-02) Summary

**One-liner:** Real OEE/MTTR/MTBF/scrap/throughput/downtime aggregations from TimescaleDB via asyncpg $N params, served by RBAC-protected GET /v1/kpi endpoint reusing Phase 7 availability formula.

## What Was Built

### Task 1: kpi/queries.py — 6 aggregations + compute_kpi_snapshot (TDD)

**RED commit:** `7d7cc4c` — unskipped 3 of 4 contract tests (ModuleNotFoundError confirmed fail)

**GREEN commit:** `a0b437d` — implemented `kpi/queries.py` + `kpi/__init__.py`

6 async aggregation functions, each accepting an asyncpg connection:

| Function | Source Table | Window | Returns |
|----------|-------------|--------|---------|
| `oee_availability` | maintenance.downtime_events | last 8h | % [0,100] |
| `mttr` | maintenance.downtime_events (resolved only) | last 30d | minutes |
| `mtbf` | maintenance.downtime_events | last 30d | hours |
| `scrap_rate` | audit.actions (QUALITY_VERDICT) | last 8h | % [0,100] |
| `throughput` | scm.historical_orders | last 8h | kg/h |
| `downtime_pct` | maintenance.downtime_events | last 8h | % [0,100] |

`compute_kpi_snapshot(conn_or_pool)` orchestrates all 6 and returns `dict[str, float | None]`.
Pool vs connection dispatch uses `hasattr(conn_or_pool, "fetchrow")` — avoids `AsyncMock` false positives from `acquire` attribute.

**OEE approximation (documented per RESEARCH note):**
OEE = Availability-only; Performance=1.0, Quality=1.0 (PoC simplification).
Formula reused verbatim from `mnt_downtime_analyzer/oee.py` (Phase 7):
```
availability = max(0.0, min(1.0, (planned - downtime_min) / planned)) * 100
```
Planned = 8h * 60 = 480 minutes (100% planned assumption; no shift policy yet — Phase 11 can wire asset shift policy lookup).

### Task 2: routers/kpi.py + main.py wiring

**Commit:** `9645973`

- `KpiSnapshot`: frozen Pydantic response model (`extra="forbid"`, CR-03), 6 `float | None` fields.
- `GET /v1/kpi`: RBAC-protected (`operator`, `shift-supervisor`, `manager`, `admin`); calls `compute_kpi_snapshot(pool)`; wraps unexpected errors as `HTTPException(500, "internal_server_error")` (T-10-02-03 generic body).
- `main.py`: `include_router(kpi_router.router)` inserted after auth router.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed conn-vs-pool dispatch using wrong attribute**
- **Found during:** Task 1 GREEN (first test run)
- **Issue:** `hasattr(conn_or_pool, "acquire")` is always True for `AsyncMock` objects (they respond to any attribute), causing the pool branch to execute on mock connections with `TypeError: 'coroutine' object does not support the asynchronous context manager protocol`.
- **Fix:** Reversed the check to `hasattr(conn_or_pool, "fetchrow")` — a real asyncpg `Connection` has `fetchrow` directly; a `Pool` does not. Mock connections also have `fetchrow` explicitly set in the test helper, so the check is correct for both test and production paths.
- **Files modified:** `apps/api-gateway/src/svc_api_gateway/kpi/queries.py`
- **Commit:** included in `a0b437d`

### Out-of-scope preexisting failures (deferred)

2 tests in `tests/test_supply_cluster_e2e.py` were already failing before this plan:
- `test_inventory_manager_check_and_signoff_audit_rows`
- `test_supply_cluster_four_agent_full_sweep`

These are NOT caused by this plan's changes. Logged to `deferred-items.md`.

## Security Review (Threat Register)

| Threat ID | Status |
|-----------|--------|
| T-10-02-01 Tampering / SQL injection | Mitigated — all SQL uses `$N` params only; no f-strings in SQL; `test_kpi_sql_uses_parameterised_placeholders` asserts this |
| T-10-02-02 Elevation of Privilege | Mitigated — `require_roles("operator","shift-supervisor","manager","admin")` on GET /v1/kpi |
| T-10-02-03 Information Disclosure | Mitigated — `HTTPException(500, "internal_server_error")` generic body; detail in structlog only |
| T-10-02-04 Denial of Service | Accepted — bounded read-only window queries; rate-limiting deferred to Phase 11 |

## Known Stubs

None. All 6 KPI values are computed from real SQL over TimescaleDB tables.

**OEE approximation note:** OEE is Availability-only (P=1.0, Q=1.0). This is documented as a PoC simplification per RESEARCH Pattern 7, not a stub — the formula is mathematically correct; only the Performance and Quality inputs are simplified until Phase 11 wires real sources.

## Threat Flags

No new security surface outside the plan's threat model.

## Self-Check: PASSED

Files created:
- apps/api-gateway/src/svc_api_gateway/kpi/__init__.py — FOUND
- apps/api-gateway/src/svc_api_gateway/kpi/queries.py — FOUND
- apps/api-gateway/src/svc_api_gateway/routers/kpi.py — FOUND

Commits:
- 7d7cc4c (RED test commit) — FOUND
- a0b437d (Task 1 GREEN) — FOUND
- 9645973 (Task 2 router) — FOUND

Test results: 11 unit tests passed, 2 skipped (intentional scaffold), 0 failures in unit suite.
Full suite: 110 passed, 7 skipped, 2 preexisting failures (supply_cluster_e2e — unrelated).
