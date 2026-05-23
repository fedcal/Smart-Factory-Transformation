---
phase: 07-agents-maintenance-reliability
plan: 13
subsystem: maintenance-coach
tags: [bug-fix, regression-test, langgraph, checkpoint, audit, hitl]
depends_on: []
provides: [cr-01-saver-lifecycle-fix, wr-02-single-audit-row]
affects: [MNT-03, MNT-06]

dependency_graph:
  requires: []
  provides:
    - MaintenanceCoach._get_graph raises RuntimeError for missing saver (no self-compile)
    - step(skip_audit=True) suppresses internal audit write
    - resume_after_help writes exactly one hitl_supervisor audit row
  affects:
    - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py
    - apps/agents/maintenance/maintenance-coach/tests/test_coach_saver_lifecycle.py

tech_stack:
  modified: [langgraph, asyncpg, pytest-asyncio]
  patterns:
    - Dependency injection for AsyncPostgresSaver lifetime management
    - skip_audit flag to suppress internal writes from delegating callers

key_files:
  created:
    - apps/agents/maintenance/maintenance-coach/tests/test_coach_saver_lifecycle.py
  modified:
    - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py

decisions:
  - "_get_graph raises RuntimeError instead of self-compiling to prevent use-after-close"
  - "skip_audit=True in step() rather than adding escalation_trigger parameter"
  - "Docstring examples kept in _get_graph to guide production wiring"

metrics:
  duration_minutes: 18
  completed_date: "2026-05-23T20:55:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 07 Plan 13: MaintenanceCoach CR-01 + WR-02 Fix Summary

**One-liner:** Removed use-after-close saver self-compile from _get_graph() and eliminated double audit write in resume_after_help via skip_audit=True parameter.

## What Was Built

Two runtime defects in MaintenanceCoach that made the agent non-functional after the first request and double-wrote the append-only audit table.

### CR-01 Fix (saver lifecycle)

`_get_graph()` previously opened `AsyncPostgresSaver.from_conn_string(pg_dsn)` inside an `async with` block, compiled the graph, cached it in `self._graph`, then exited the context manager — closing the saver's underlying PostgreSQL connection. The cached graph retained a reference to the now-closed saver. Any subsequent `ainvoke` or `aget_state` call would raise `ConnectionDoesNotExistError`.

**Fix applied:**

The entire self-compile block was removed. `_get_graph()` now raises `RuntimeError("MaintenanceCoach._graph is None. Inject a pre-built saver at construction...")` if `self._graph` is `None`. The production path must inject a long-lived saver via the FastAPI lifespan (existing pattern in `app.state.checkpointer`). The `__init__` injected-saver branch already compiled correctly — no change there.

The unused `import os` (only used by the deleted self-compile path) was also removed.

### WR-02 Fix (double audit row)

`resume_after_help` called `step()` (which internally calls `_write_audit(decision='auto')`) then called `_write_audit(decision='hitl_supervisor')` again — producing two audit rows per resume on an append-only table.

**Fix applied:**

Added `skip_audit: bool = False` keyword parameter to `step()`. When `True`, the two internal `_write_audit(decision='auto')` calls inside `step()` are skipped (guarded with `if not skip_audit:`). `resume_after_help` now calls `step(skip_audit=True)` and writes exactly one authoritative `_write_audit(decision='hitl_supervisor', escalation_trigger='technician_request')` row. Net: one row per resume.

## Tasks Completed

| Task | Description | Commit | Status |
|------|-------------|--------|--------|
| 1 | Write failing regression tests (Test A: CR-01, Test B: WR-02, Test C: integration) | dbbd18c | DONE |
| 2 | Fix CR-01 + WR-02 in agent.py; verify all 46 unit tests pass | 0e08c92 | DONE |

## Regression Tests

**Test A** (`test_get_graph_requires_injected_saver_no_self_compile`): Asserts `_get_graph()` raises `RuntimeError` with `'_graph is None'` and `'Inject a pre-built saver'` message. Was RED against old code (raised different message), GREEN after fix.

**Test B** (`test_resume_after_help_writes_single_audit_row`): Asserts `_write_audit` is called exactly once with `decision='hitl_supervisor'`. Was RED against old code (called twice), GREEN after fix.

**Test C** (`test_step_persists_across_calls`): Integration test (testcontainers PG) verifying second `step()` call does not raise `ConnectionDoesNotExistError`. Marked `@pytest.mark.integration`, skipped without docker. Present and runnable.

## Deviations from Plan

None - plan executed exactly as written.

The only minor observation: the acceptance criterion `grep -c "async with AsyncPostgresSaver.from_conn_string" agent.py` returns 3, not 0. However all 3 occurrences are in docstrings/string literals (documentation examples), not executable code. The actual self-compile `async with` code block is fully removed.

## Verification Results

```
46 passed, 1 deselected (integration test) in 0.30s
```

Tests run: `test_coach_saver_lifecycle.py -m "not integration"`, `test_checkpoint_resume.py`, `test_evidence_panel.py`, `test_mttr.py`

- No `async with AsyncPostgresSaver.from_conn_string` executable code in agent.py (only docstring examples)
- `skip_audit` appears 6 times in agent.py (definition, docstring, 2 guards, 1 call from resume_after_help, 1 docstring mention)
- Integration test (Test C) present with `@pytest.mark.integration`

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- `/run/media/federicocalo/D/prj/Smart Factory Transformation/.claude/worktrees/agent-a51897037c7e42593/apps/agents/maintenance/maintenance-coach/tests/test_coach_saver_lifecycle.py` — FOUND
- `/run/media/federicocalo/D/prj/Smart Factory Transformation/.claude/worktrees/agent-a51897037c7e42593/apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py` — FOUND (modified)
- Commit dbbd18c — FOUND (test)
- Commit 0e08c92 — FOUND (fix)
