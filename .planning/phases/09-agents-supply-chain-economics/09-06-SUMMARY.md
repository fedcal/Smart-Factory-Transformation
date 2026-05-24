---
phase: "09"
plan: "06"
subsystem: api-gateway / supply-agents
tags: [fastapi, router, supply-chain, hitl, autonomous, dependency-injection]
dependency_graph:
  requires: ["09-01", "09-02", "09-03", "09-04", "09-05"]
  provides: ["SCM-01-http", "SCM-02-http", "SCM-03-http", "SCM-04-http"]
  affects: ["api-gateway", "sft-agents/runtime/clusters"]
tech_stack:
  added: []
  patterns:
    - "Supply cluster HTTP router mirroring Phase 8 knowledge_agents.py pattern"
    - "Frozen Pydantic models + extra=forbid + tz-aware @field_validator (WR-02)"
    - "Generic 500 body with server-side-only str(exc) logging (WR-05)"
    - "build_supply_subgraph DI via lifespan with cost-analyzer fallback (D-SCM-AUTO)"
key_files:
  created:
    - apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py
    - apps/api-gateway/tests/test_supply_agents_router.py
  modified:
    - apps/api-gateway/src/svc_api_gateway/dependencies.py
    - apps/api-gateway/src/svc_api_gateway/lifespan.py
    - apps/api-gateway/src/svc_api_gateway/main.py
    - apps/api-gateway/pyproject.toml
decisions:
  - "CostAnalyzer.__init__ takes positional args (not keyword-only *-args) — constructed as CostAnalyzer(pool, audit_writer, None)"
  - "EnergyOptimizeRequest and CostAnalyzeRequest datetime fields (ts_from/ts_to) are Optional — validator only fires when value is not None"
  - "cost-analyzer/analyze has no resume endpoint — autonomous SCM-03 (D-SCM-AUTO); test verifies 404/405 on /cost-analyzer/resume"
metrics:
  duration: "20min"
  completed_date: "2026-05-24"
  tasks: 2
  files: 6
---

# Phase 9 Plan 06: Supply Agents API Gateway Router + DI Summary

**One-liner:** FastAPI supply router (7 endpoints) wiring InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster via build_supply_subgraph DI, with tz-aware validators, user_roles ACL, and generic-500-body guards from Phase 8 review.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | supply_agents.py router + request models (WR-02/WR-03/WR-05) | 50a2d13 | supply_agents.py (new) |
| 2 | DI wiring (dependencies + lifespan + main) + router test (CR-01) | b3ba09c | dependencies.py, lifespan.py, main.py, test file, pyproject.toml |

## What Was Built

### Supply Agents Router (`supply_agents.py`)

7 endpoints exposing the supply cluster:

| Endpoint | Method | Status | Agent | Pattern |
|----------|--------|--------|-------|---------|
| `/v1/agents/inventory-manager/check` | POST | 202 | InventoryManager | HITL async |
| `/v1/agents/inventory-manager/resume` | POST | 200 | InventoryManager | HITL resume |
| `/v1/agents/energy-optimizer/optimize` | POST | 202 | EnergyOptimizer | HITL async |
| `/v1/agents/energy-optimizer/resume` | POST | 200 | EnergyOptimizer | HITL resume |
| `/v1/agents/cost-analyzer/analyze` | POST | 200 | CostAnalyzer | Autonomous (D-SCM-AUTO) |
| `/v1/agents/demand-forecaster/forecast` | POST | 202 | DemandForecaster | HITL async |
| `/v1/agents/demand-forecaster/resume` | POST | 200 | DemandForecaster | HITL resume |

**Phase 8 review fixes applied at boundary:**
- WR-02: `@field_validator` on all datetime fields (ts_from, ts_to) rejects naive datetimes with 422
- WR-03: `user_roles: list[str]` on all 4 core request models
- WR-05: `_handle_agent_error` logs `str(exc)` server-side only; HTTP body is always `{"error": "internal_agent_error", "thread_id": ...}`
- CR-01: all 4 supply agent classes imported by EXACT exported name (`InventoryManager`, `EnergyOptimizer`, `CostAnalyzer`, `DemandForecaster`)

### DI Wiring

- `dependencies.py`: `get_supply_children()` returning `app.state.supply_children` or 503
- `lifespan.py`: constructs 4 supply agents, assembles `supply_children` dict (cost-analyzer REQUIRED as fallback), calls `build_supply_subgraph(supply_children)`
- `main.py`: `include_router(supply_agents_router.router)` after knowledge router
- `pyproject.toml`: added `scm-{inventory-manager,energy-optimizer,cost-analyzer,demand-forecaster}` workspace deps

### Tests (`test_supply_agents_router.py`)

24 tests, all passing:
- All 7 endpoints return correct status codes
- cost-analyzer/analyze has no resume endpoint (404/405 verified)
- Naive datetime → 422, not 500 (WR-02)
- Agent exception → generic 500 body without str(exc) (WR-05)
- RecursionError → 503 + Retry-After (T-09-24)
- extra=forbid → 422 on unexpected fields (T-09-22)

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written.

**Note on CostAnalyzer constructor:** The plan mentioned `CostAnalyzer` takes arguments like other agents. Inspecting `scm_cost_analyzer/agent.py` revealed its `__init__` takes positional args (not keyword-only `*`-style). Constructed as `CostAnalyzer(pool, audit_writer, None)` instead of keyword form. No plan deviation — this is a minor implementation detail resolved by reading the source (CR-01 verification step).

## Verification Results

```
24 passed in 7.02s
```

All success criteria met:
- All 7 endpoints registered
- lifespan wires build_supply_subgraph with cost-analyzer fallback
- tz validators + user_roles + generic-500 boundary fixes verified

## Threat Surface Scan

No new security-relevant surface beyond the plan's threat register:
- 7 endpoints mirroring the existing knowledge/maintenance pattern
- No new auth paths introduced (dev-mode user_roles, Phase 11 will add JWT)
- No new file access or schema changes

## Self-Check

- [x] `apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py` created
- [x] `apps/api-gateway/tests/test_supply_agents_router.py` created
- [x] Commits exist: `50a2d13` (Task 1), `b3ba09c` (Task 2)
- [x] 24/24 tests pass

## Self-Check: PASSED
