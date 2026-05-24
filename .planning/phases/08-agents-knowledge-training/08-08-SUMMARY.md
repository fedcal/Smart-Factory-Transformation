---
phase: 08-agents-knowledge-training
plan: 08
subsystem: api
tags: [fastapi, pydantic, langgraph, langfuse, knowledge, http-router, di]

# Dependency graph
requires:
  - phase: 08-agents-knowledge-training
    provides: "08-01 build_knowledge_subgraph, 08-04 ShiftHandover, 08-05 TrainingCoach, 08-06 KnowledgeCurator, 08-07 DocumentationSynthesizer"
  - phase: 07-agents-maintenance-reliability
    provides: "07-10 maintenance_agents.py router pattern, lifespan DI pattern"
  - phase: 04-core-agentic-runtime-hitl
    provides: "supervisor graph, HybridRouter, AsyncPostgresSaver checkpointer, dependencies.py factories"
provides:
  - "FastAPI router /v1/agents/knowledge-agents with 5 endpoints (TRN-02/03/04/05)"
  - "POST /v1/agents/shift-handover/compile (202, D-SH-01 manual trigger)"
  - "POST /v1/agents/training-coach/session (200, TRN-02 quiz start)"
  - "POST /v1/agents/training-coach/resume (200, TRN-02 post-HITL resume)"
  - "POST /v1/agents/knowledge-curator/ingest (200, D-KC-04 autonomous)"
  - "POST /v1/agents/documentation-synthesizer/draft (202, TRN-04 async HITL)"
  - "get_knowledge_children DI factory in dependencies.py"
  - "knowledge_children dict in lifespan.py app.state"
affects:
  - Phase 10 demo UI (knowledge endpoints visible)
  - Phase 11 (full supervisor multi-cluster wiring)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "knowledge-agents router mirrors maintenance_agents.py pattern exactly (prefix=/v1/agents, tags=[knowledge-agents], _RECURSION_LIMIT=5)"
    - "ShiftHandoverCompileRequest: tz-aware datetime + model_validator end>start (422 on inversion)"
    - "knowledge-curator/ingest: autonomous endpoint without Idempotency-Key (D-KC-04 — no HITL, deterministic verdict)"
    - "202 endpoints (shift-handover/compile, documentation-synthesizer/draft): return JSONResponse with hitl_status='supervisor_pending'"
    - "knowledge_children dict in lifespan: all 4 agents constructed; Phase 11 collaborators (llm, retrieval_pipeline, indexer) injected as None until Phase 5/11 wiring"

key-files:
  created:
    - apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py
    - apps/api-gateway/tests/test_knowledge_agents_router.py
  modified:
    - apps/api-gateway/src/svc_api_gateway/dependencies.py
    - apps/api-gateway/src/svc_api_gateway/lifespan.py
    - apps/api-gateway/src/svc_api_gateway/main.py
    - apps/api-gateway/pyproject.toml

key-decisions:
  - "knowledge-curator/ingest uses 200 (not 202) + no Idempotency-Key: autonomous D-KC-04 design — verdict is deterministic, caller can safely retry"
  - "Lifespan constructs agents with llm=None / retrieval_pipeline=None for Phase 5 deps: raises at call time not construction; acceptable for DI layer (Phase 11 will inject real impls)"
  - "build_knowledge_subgraph called in lifespan but not wired into supervisor graph: Phase 11 will replace the placeholder; for Phase 8 tests use mocked supervisor_graph"
  - "pyproject.toml extended with trn-* workspace deps: required for lifespan import correctness at gateway startup"
  - "TrainingResumeRequest uses body.thread_id as config thread_id for LangGraph checkpoint replay (same as maintenance-coach resume pattern)"

requirements-completed: [TRN-02, TRN-03, TRN-04, TRN-05]

# Metrics
duration: 40min
completed: 2026-05-24
---

# Phase 8 Plan 08: Knowledge Agents HTTP Router Summary

**FastAPI router exposing 5 knowledge endpoints (ShiftHandover/TrainingCoach.session+resume/KnowledgeCurator/DocumentationSynthesizer) with Pydantic-validated bodies, Langfuse tags, Idempotency-Key caching, recursion_limit=5, and DI-wired knowledge_children dict — mirrors Phase 7 07-10 maintenance_agents.py pattern**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-05-24
- **Completed:** 2026-05-24
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

### Task 1: knowledge_agents.py router + request models
- Created `knowledge_agents.py` with APIRouter(prefix="/v1/agents", tags=["knowledge-agents"])
- Implemented all 5 endpoints: shift-handover/compile (202), training-coach/session (200), training-coach/resume (200), knowledge-curator/ingest (200), documentation-synthesizer/draft (202)
- Frozen + extra=forbid Pydantic request models; ShiftHandoverCompileRequest includes model_validator for shift_end > shift_start
- Copied `_handle_recursion_error` and `_handle_agent_error` verbatim from maintenance_agents.py with `knowledge_agent_` log key prefix
- All 5 endpoints set `state["target_agent"]` to the correct slug

### Task 2: DI wiring (dependencies + lifespan + main) + router tests
- Added `get_knowledge_children()` factory to dependencies.py mirroring `get_maintenance_children`
- Extended lifespan.py to construct all 4 knowledge agents and populate `app.state.knowledge_children`; called `build_knowledge_subgraph` (Phase 11 will wire into supervisor)
- Added `include_router(knowledge_agents_router.router)` to main.py `build_app()` after maintenance router
- Created 18 tests in `test_knowledge_agents_router.py` — all pass (18 passed)
- Extended `pyproject.toml` with `trn-*` workspace deps

## Verification Results

```
pytest apps/api-gateway/tests/test_knowledge_agents_router.py -x -q
18 passed in 9.46s

pytest apps/api-gateway/tests/ -x -q
66 passed, 1 skipped in 8.55s
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Added pyproject.toml trn-* dependencies**
- **Found during:** Task 2
- **Issue:** lifespan.py imports trn_shift_handover, trn_training_coach, trn_knowledge_curator, trn_documentation_synthesizer — not declared in pyproject.toml
- **Fix:** Added `trn-shift-handover`, `trn-training-coach`, `trn-knowledge-curator`, `trn-documentation-synthesizer` as workspace deps
- **Files modified:** apps/api-gateway/pyproject.toml, uv.lock
- **Commit:** a20ef48

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | 5f252d5 | feat(08-08): add knowledge_agents.py router — 5 HTTP endpoints |
| Task 2 | a20ef48 | feat(08-08): wire knowledge cluster DI, lifespan, main.py + router tests |

## Self-Check: PASSED

Files verified:
- FOUND: apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py
- FOUND: apps/api-gateway/tests/test_knowledge_agents_router.py
- FOUND commit 5f252d5
- FOUND commit a20ef48
