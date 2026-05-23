---
phase: 07-agents-maintenance-reliability
plan: 08
subsystem: maintenance-agent
tags: [langgraph, checkpoint, postgres, mttr, hitl, request-help, bilingual, pydantic, asyncpg]

requires:
  - phase: 07-04
    provides: RequestHelpTool + RequestHelpInput from packages/sft-agents/src/sft_agents/tools/hitl.py
  - phase: 04-core-agentic-runtime-hitl
    provides: langgraph_checkpoints PG table (migration 005) + AsyncPostgresSaver pattern + EscalateToSupervisorTool
  - phase: 07-00
    provides: Wave 0 stubs for test_mttr.py + test_checkpoint_resume.py

provides:
  - MaintenanceCoach async LangGraph agent with cross-shift checkpoint resume
  - CoachThreadState + StepReport Pydantic models (frozen+extra=forbid, tz-aware)
  - MTTR helpers: compute_mttr_minutes (pause-inclusive) + compute_active_work_minutes (active-only)
  - Bilingual IT+EN prompts + keyword detection (HELP_KEYWORDS_IT/EN + detect_help_keyword)
  - Per-step COACH_STEP audit rows with technician_id guard + escalation_trigger marker
  - build_ops05_evidence_panel metadata for MNT-05 compliance

affects:
  - 07-10 (api-gateway: 3 endpoints start/step/resume consume MaintenanceCoach)
  - 07-11 (evidence panel docs)
  - 07-12 (E2E test scenarios for multi-turn coach flow)

tech-stack:
  added:
    - langgraph>=0.4,<0.6 (StateGraph + interrupt + Command)
    - langgraph-checkpoint-postgres>=3.1.0,<4.0.0 (AsyncPostgresSaver)
  patterns:
    - LangGraph interrupt/resume pattern for cross-shift conversational coaching
    - coach-<intervention_id> thread_id naming (Open Q6 RESOLVED)
    - Pitfall §3 compliance: audit written AFTER ainvoke returns (not before interrupt)
    - State compression at _MESSAGE_TRIM_THRESHOLD=50 (system-preserving trim)
    - Defense-in-depth keyword detection (LLM tool call + heuristic fallback)
    - AsyncPostgresSaver injected saver pattern (test injection + prod PG_DSN fallback)

key-files:
  created:
    - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/models.py
    - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/mttr.py
    - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/prompts.py
    - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/metadata.py
    - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py
  modified:
    - apps/agents/maintenance/maintenance-coach/pyproject.toml
    - apps/agents/maintenance/maintenance-coach/README.md
    - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/__init__.py
    - apps/agents/maintenance/maintenance-coach/tests/test_mttr.py
    - apps/agents/maintenance/maintenance-coach/tests/test_checkpoint_resume.py

key-decisions:
  - "D-MC-01 REUSE: langgraph_checkpoints table from Phase 4 migration 005; no new migration needed"
  - "Open Q6 RESOLVED: thread_id = coach-<intervention_id> (kebab prefix, audit-greppable, no collision with ops.* threads)"
  - "AsyncPostgresSaver: from_conn_string constructor (takes conn_string not pool); injected saver for tests, PG_DSN fallback for prod"
  - "State type: CoachThreadState Pydantic frozen model (not TypedDict) — LangGraph StateGraph supports Pydantic models returning delta dicts from nodes"
  - "langchain-core version: widened from >=0.3,<0.4 to >=0.3 to resolve ops-production-planner conflict (>=1.0,<2.0)"
  - "Audit thread_id format: maintenance.maintenance-coach.<intervention_id>.<step_no> (per-step, mirror 06-09 multi-step pattern)"
  - "Pitfall §3: _write_audit called AFTER ainvoke returns — no audit before interrupt — identical to Phase 6 D-OA-04 contract"

requirements-completed: [MNT-03, MNT-06]

duration: 42min
completed: 2026-05-23
---

# Phase 7 Plan 08: MaintenanceCoach Summary

**Async LangGraph coaching agent with cross-shift PG checkpoint resume, bilingual IT/EN help-keyword detection, MTTR helpers, and per-step COACH_STEP audit rows with technician_id HITL guard**

## Performance

- **Duration:** ~42 min
- **Started:** 2026-05-23T19:00:00Z
- **Completed:** 2026-05-23T19:43:30Z
- **Tasks:** 3 (TDD: scaffold RED → models/mttr/prompts/metadata GREEN → agent.py GREEN)
- **Files created/modified:** 11

## Accomplishments

- Shipped MaintenanceCoach LangGraph agent satisfying MNT-03 (procedural coaching + cross-shift resume + MTTR) and MNT-06 (audit chain via COACH_STEP rows).
- Implemented 5 source modules (models, mttr, prompts, metadata, agent) plus updated pyproject.toml, README, `__init__.py`, and 2 test files — all within plan scope.
- 26 tests pass: 13 MTTR pure-unit tests (compute_mttr_minutes, compute_active_work_minutes, Pydantic edge cases) + 13 graph-structure tests (thread_id naming, build_coach_graph, agent constants, _trim_messages, CoachResponse literals).

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffold + failing tests (RED)** - `6d7edb5` (feat)
2. **Task 2a: CoachThreadState + StepReport + MTTR helpers (GREEN)** - `54fe144` (feat)
3. **Task 2b: Bilingual prompts + metadata (GREEN)** - `970200d` (feat)
4. **Task 3: MaintenanceCoach agent.py (GREEN)** - `adc185c` (feat)

## Files Created/Modified

- `apps/agents/maintenance/maintenance-coach/pyproject.toml` - Full deps (langgraph, langgraph-checkpoint-postgres, sft-agents/knowledge/domain, asyncpg, structlog, pytest-asyncio)
- `apps/agents/maintenance/maintenance-coach/README.md` - Role + async thread + checkpoint resume + MTTR + request_help semantics
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/__init__.py` - Re-exports all public surface
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/models.py` - CoachThreadState + StepReport + CoachStartRequest/StepRequest/Response (frozen+extra=forbid, tz-aware)
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/mttr.py` - compute_mttr_minutes (raises ValueError on negative MTTR) + compute_active_work_minutes (dict/Pydantic polymorphic)
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/prompts.py` - SYSTEM_PROMPT_IT/EN, HELP_KEYWORDS_IT/EN, build_step_prompt (last-3-step context, token-efficient), detect_help_keyword (heuristic)
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/metadata.py` - TOOL_INVENTORY, DATA_SOURCES, KPIS_IMPACTED, build_ops05_evidence_panel with hitl_tier override
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py` - MaintenanceCoach class + build_coach_graph + step_node + complete_node + _trim_messages + _write_audit
- `apps/agents/maintenance/maintenance-coach/tests/test_mttr.py` - 13 unit tests (RED then GREEN)
- `apps/agents/maintenance/maintenance-coach/tests/test_checkpoint_resume.py` - 13 structure/contract tests (RED then GREEN)

## Decisions Made

### D-MC-01 Architecture (reuse + thread_id)

Phase 4 `langgraph_checkpoints` table (migration 005) reused as-is — no new migration. The table lives in `public` schema (not `langgraph` schema as the migration name suggests — confirmed by migration 005 SQL comment). Each intervention binds a `coach-<intervention_id>` thread_id which is distinct from Phase 4's `ops.<agent>.<uuid>` pattern.

### Open Q6 RESOLVED: `coach-<intervention_id>`

Rationale: audit-greppable (`grep "coach-" audit.log`), no collision with `ops.*` / `maintenance.*` LangGraph threads, stable across resume, verbose over terse.

### AsyncPostgresSaver Constructor

The `langgraph-checkpoint-postgres 3.1.x` `AsyncPostgresSaver.__init__` accepts a `conn` parameter (not `pool`), and `from_conn_string` returns an async context manager. For long-lived agents (production), the saver should be injected at construction. For per-invocation use (compatibility), the async-with pattern is documented. Test injection (`saver=AsyncMock()`) works cleanly.

### State Schema: Pydantic vs TypedDict

Used Pydantic `CoachThreadState(BaseModel)` as LangGraph state schema. LangGraph `StateGraph` compiles cleanly with Pydantic models — nodes return delta dicts that LangGraph merges with the prior state. This is consistent with D-MC-01 interfaces and enables Pydantic re-validation on checkpoint load.

### langchain-core Version

Plan specified `>=0.3,<0.4`. Workspace has `ops-production-planner` requiring `>=1.0,<2.0`. Fixed to `>=0.3` (no upper cap) — compatible with both since langchain-core is backward-compatible in this range.

### Pitfall §3 Compliance

`_write_audit` is called from `start()`, `step()`, and `resume_after_help()` AFTER the `ainvoke` / `GraphInterrupt` catch — never from within `step_node` before `interrupt()`. This matches the Phase 6 D-OA-04 contract exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] langchain-core version constraint widened**
- **Found during:** Task 1 (pyproject.toml scaffold)
- **Issue:** `langchain-core>=0.3,<0.4` conflicts with `ops-production-planner` requiring `>=1.0,<2.0`; workspace dependency resolution failed
- **Fix:** Widened to `langchain-core>=0.3` (no upper bound)
- **Files modified:** `apps/agents/maintenance/maintenance-coach/pyproject.toml`
- **Verification:** `uv run pytest` succeeds after fix; workspace resolves cleanly
- **Committed in:** `6d7edb5` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking dependency conflict)
**Impact on plan:** Essential fix; no scope creep. langchain-core API is backward compatible in the 0.3+ range.

## Implementation Notes: AsyncPostgresSaver

Confirmed annotation per plan deviation_rules Rule 4:

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Constructor | `AsyncPostgresSaver.from_conn_string` (not `pool=` injection) | v3.1.x takes `conn` not `pool`; from_conn_string returns async context manager |
| Long-lived usage | Inject pre-built `saver` at `MaintenanceCoach.__init__` | Avoids per-call async-with overhead; tests inject AsyncMock |
| Per-call fallback | `async with from_conn_string(PG_DSN)` | For backward compat when saver not injected (rare) |
| Namespace safety | `coach-` prefix confirmed distinct from Phase 4 `ops.<agent>.*` format | No collision risk |
| State compression | `_MESSAGE_TRIM_THRESHOLD=50` trims oldest non-system messages | structlog event `coach_state_compressed` emitted with old/new lengths |
| Recursion limit | 50 (heuristic) | Supports multi-step interventions; document increase path in Phase 11 if 100-step SOPs emerge |
| intervention_id uniqueness | Server-side validation in `start()` (409 on collision) | Documented; implementation placeholder in 07-10 api-gateway |

## Known Stubs

None — all public surfaces are fully implemented. The `duration_minutes=0` in `StepReport` built by `step_node` is intentional: duration tracking (from technician timing signals) is the responsibility of the 07-10 API gateway layer, not the graph node. This is documented in the code and is not a correctness gap for this plan's scope.

## Delegated to Future Plans

- **07-10:** API gateway 3 endpoints (start/step/resume) that wrap MaintenanceCoach.start/step/resume_after_help
- **07-12:** Multi-turn E2E scenarios (5-step happy path, mid-flow help request, technician-abandoned failure) with mock LLM fixtures
- **07-11:** Evidence panel documentation page for MaintenanceCoach

## Threat Surface Scan

No new network endpoints or trust boundaries introduced by this plan. The endpoints will be implemented in 07-10 (separate plan). The models validate all inputs at boundaries (frozen+extra=forbid, length caps, tz-aware datetimes). No new DB tables added (migration 005 reuse confirmed).

## Self-Check: PASSED

Files confirmed:
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/models.py` - FOUND
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/mttr.py` - FOUND
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/prompts.py` - FOUND
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/metadata.py` - FOUND
- `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py` - FOUND

Commits confirmed:
- `6d7edb5` scaffold+tests - FOUND
- `54fe144` models+mttr - FOUND
- `970200d` prompts+metadata - FOUND
- `adc185c` agent.py - FOUND

Tests: 26 passed (13 unit + 13 structure) - CONFIRMED

---
*Phase: 07-agents-maintenance-reliability*
*Completed: 2026-05-23*
