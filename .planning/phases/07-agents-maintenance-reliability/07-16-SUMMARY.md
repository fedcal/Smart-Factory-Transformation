---
phase: 07-agents-maintenance-reliability
plan: 16
subsystem: downtime-analyzer
tags: [gap-closure, regression, oee, pareto, asyncio, gateway, asyncpg]
dependency_graph:
  requires: []
  provides: [WR-03-fix, WR-04-fix, CR-05-fix]
  affects: [DowntimeAnalyzer, api-gateway-maintenance-router, oee-compute]
tech_stack:
  added: []
  patterns: [asyncio.gather-with-semaphore, extended-return-tuple, tdd-red-green]
key_files:
  created:
    - apps/api-gateway/tests/test_da_report_datetime.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_pareto_grand_total.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_by_asset_bounds.py
  modified:
    - apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py
    - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py
    - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_oee.py
    - apps/api-gateway/pyproject.toml
decisions:
  - "Extend compute_oee return tuple to 7 elements (add quality_source) rather than keeping a standalone compute_quality_cross_cluster call, eliminating the redundant duplicate DB query"
  - "Use asyncio.gather with asyncio.Semaphore(10) for by_asset parallel OEE computation, bounded at _MAX_BY_ASSET=50"
  - "Add mnt-predictive-maintenance, mnt-maintenance-coach, mnt-downtime-analyzer as workspace dependencies to api-gateway pyproject.toml so gateway tests can import the maintenance router"
metrics:
  duration: 45m
  completed: 2026-05-23
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 5
---

# Phase 07 Plan 16: DowntimeAnalyzer Gap Closure Summary

One-liner: Fixed asyncpg datetime type mismatch, Pareto grand_total correctness, and bounded concurrent by_asset computation using asyncio.gather with semaphore.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write failing regression tests for WR-03, WR-04, CR-05 | 61ac6c8 | test_da_report_datetime.py, test_pareto_grand_total.py, test_by_asset_bounds.py, api-gateway/pyproject.toml |
| 2 | Fix WR-03 gateway datetime, WR-04 Pareto grand_total, CR-05 by_asset bounds + dedup | 70c5e6e | maintenance_agents.py, oee.py, agent.py, test_oee.py, test_by_asset_bounds.py |

## What Was Fixed

### WR-03: Gateway datetime type mismatch (BLOCKER)

**File:** `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py` lines 646-647

**Root cause:** `post_da_report` called `body.window_start.isoformat()` and `body.window_end.isoformat()` before placing them into the state dict. asyncpg requires Python `datetime` objects for TIMESTAMPTZ parameters — ISO strings cause `asyncpg.exceptions.DataError` at runtime for every `/report` request.

**Fix:** Removed `.isoformat()` calls. State dict now passes `body.window_start` and `body.window_end` as `datetime` objects directly. The validator-message isoformat calls (error strings) remain unchanged.

---

### WR-04: Pareto cumulative_percent uses wrong grand_total

**File:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py` line 320

**Root cause:** `grand_total = sum(r[1] for r in trimmed)` computed the sum of only the top-N trimmed rows. The last Pareto entry always showed `cumulative_percent = 100.0` regardless of whether the top-N entries actually accounted for all downtime.

**Fix:** Moved grand_total computation before trimming: `grand_total = sum(r[1] for r in sorted_rows)`. Now cumulative_percent reflects true Pareto coverage (e.g., top-10 reasons accounting for 70% of all downtime show 70.0, not 100.0).

---

### CR-05: Unbounded by_asset iteration + duplicate quality query

**File:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py` lines 229-252

**Root cause (a):** The `by_asset=True` block iterated over all assets in `_asset_registry` sequentially with no cap. For N=100 assets this issued 300 sequential asyncpg queries per request — a DoS vector.

**Root cause (b):** `compute_quality_cross_cluster` was called once inside `compute_oee` (oee.py) and then called again explicitly at agent.py lines 213-220 to capture `quality_source` for the audit row. Same expensive cross-cluster query executed twice.

**Fix (a):** Added `_MAX_BY_ASSET: int = 50` and `_BY_ASSET_CONCURRENCY: int = 10` module constants. The by_asset block now uses `assets[:_MAX_BY_ASSET]` and replaces the sequential for-loop with `asyncio.gather` using a `asyncio.Semaphore(_BY_ASSET_CONCURRENCY)`. Result dict built immutably from gathered results.

**Fix (b):** Extended `compute_oee`'s return tuple from 6 to 7 elements, adding `quality_source` as the last element. `agent.py` now unpacks the 7th element directly from `compute_oee`'s return, eliminating the standalone `compute_quality_cross_cluster` call in the aggregate path. Updated all call sites in `agent.py` and `tests/test_oee.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing maintenance package workspace dependencies in api-gateway**
- **Found during:** Task 1
- **Issue:** The api-gateway's `pyproject.toml` only listed `sft-agents` as a workspace dependency. The maintenance router imports `mnt_predictive_maintenance`, `mnt_maintenance_coach`, and `mnt_downtime_analyzer` models. Without these as workspace deps, `uv run pytest` for the api-gateway resolved to a system pytest (Python 3.14) without the workspace venv, causing `ModuleNotFoundError` for all gateway tests.
- **Fix:** Added `mnt-predictive-maintenance`, `mnt-maintenance-coach`, and `mnt-downtime-analyzer` as workspace dependencies to `apps/api-gateway/pyproject.toml` and `[tool.uv.sources]`.
- **Files modified:** `apps/api-gateway/pyproject.toml`, `uv.lock`
- **Commit:** 61ac6c8

**2. [Rule 1 - Bug] test_oee.py compute_oee call sites required 7-tuple unpacking**
- **Found during:** Task 2 implementation
- **Issue:** After extending `compute_oee` to return 7 elements (including `quality_source`), the two existing call sites in `test_oee.py` unpacked 6 elements causing `ValueError: not enough values to unpack`.
- **Fix:** Updated both `test_oee.py` call sites to unpack the 7-tuple: `availability, performance, quality, oee, total_downtime, event_count, quality_source = await compute_oee(...)`. Added assertion `assert quality_source == "audit"` to the first test for completeness.
- **Files modified:** `apps/agents/maintenance/downtime-analyzer/tests/test_oee.py`
- **Commit:** 70c5e6e

**3. [Rule 1 - Bug] test_by_asset_bounds.py mock compute_oee returned 6-tuple**
- **Found during:** Task 2 implementation
- **Issue:** The `_patched_compute_oee` mocks in `test_by_asset_bounds.py` (written in Task 1) returned 6-element tuples. After extending compute_oee's return arity, these caused `ValueError` when the agent tried to unpack 7 elements.
- **Fix:** Updated all patched mock returns in `test_by_asset_bounds.py` to return 7-tuples with a `quality_source` sentinel value.
- **Files modified:** `apps/agents/maintenance/downtime-analyzer/tests/test_by_asset_bounds.py`
- **Commit:** 70c5e6e

## Verification Results

```
# Downtime-analyzer unit suite
cd apps/agents/maintenance/downtime-analyzer
uv run pytest -m "not integration" tests/test_pareto_grand_total.py tests/test_by_asset_bounds.py tests/test_oee.py tests/test_pareto.py -x
Result: 32 passed, 1 deselected in 0.30s ✓

# Gateway datetime regression test
cd apps/api-gateway
uv run python -m pytest tests/test_da_report_datetime.py -m "not integration" -x
Result: 2 passed, 1 deselected in 3.60s ✓
```

## Acceptance Criteria Check

| Criterion | Status |
|-----------|--------|
| WR-03: No `.isoformat()` in post_da_report state dict | PASS — lines 646-647 pass datetime objects |
| WR-04: grand_total from `sum(r[1] for r in sorted_rows)` | PASS — oee.py uses all rows before trimming |
| CR-05: `_MAX_BY_ASSET` defined and used (≥2 occurrences) | PASS — 3 occurrences (definition + comment + use) |
| CR-05: `asyncio.gather` used in by_asset block | PASS — 2 occurrences |
| CR-05: `compute_quality_cross_cluster` invoked ≤1 time in aggregate path | PASS — 0 direct calls from agent.py; 1 call inside compute_oee only |
| All Task 1 regression tests pass | PASS — all green |
| Existing test_oee/test_pareto/test_repository still pass | PASS — 34 total downtime-analyzer tests pass |

## Self-Check: PASSED

- `apps/api-gateway/tests/test_da_report_datetime.py` — EXISTS ✓
- `apps/agents/maintenance/downtime-analyzer/tests/test_pareto_grand_total.py` — EXISTS ✓
- `apps/agents/maintenance/downtime-analyzer/tests/test_by_asset_bounds.py` — EXISTS ✓
- Commit 61ac6c8 — EXISTS ✓
- Commit 70c5e6e — EXISTS ✓
