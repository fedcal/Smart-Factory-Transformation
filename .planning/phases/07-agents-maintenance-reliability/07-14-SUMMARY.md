---
phase: 07-agents-maintenance-reliability
plan: 14
subsystem: testing
tags: [langgraph, interrupt, audit, rca, evidence-panel, tool-calls]

# Dependency graph
requires:
  - phase: 07-agents-maintenance-reliability
    provides: RCASpecialist agent with _invoke_react_loop and _write_audit

provides:
  - "CR-02 fix: direct interrupt() call in __call__ with audit write placed after resume return"
  - "WR-05 fix: tool_calls_log populated from LangGraph ReAct result messages"
  - "Regression test suite verifying one-write-on-resume and non-empty evidence panel"

affects: [07-agents-maintenance-reliability, audit-trail, hitl-governance, rca-specialist]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Direct interrupt() in LangGraph node: call interrupt() at module level (not via tool), place side-effectful writes after interrupt() return value — they execute only on resume"
    - "Tuple return from _invoke_react_loop: returns (content, tool_call_records) to give callers access to intermediate tool call evidence without breaking encapsulation"
    - "Immutable list concatenation in retry loop: tool_calls_log = tool_calls_log + new_tool_calls (never in-place mutation)"
    - "ImportError guard for langgraph.types.interrupt: try/except at module level preserves test-env compatibility without conditional branches in hot path"

key-files:
  created:
    - apps/agents/maintenance/rca-specialist/tests/test_interrupt_audit_lifecycle.py
  modified:
    - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py

key-decisions:
  - "Replace _escalate_to_supervisor() call in __call__ with direct interrupt() — the tool-internal interrupt was the root cause of the audit ordering violation"
  - "Return (content, tool_call_records) tuple from _invoke_react_loop — avoids mutable shared state and keeps the tool-call accumulation co-located with the ReAct result consumption"
  - "Patch interrupt() at mnt_rca_specialist.agent module level in unit tests — langgraph.types.interrupt() requires a live LangGraph runnable context and raises outside it"

patterns-established:
  - "LangGraph interrupt pattern: import interrupt at module top (with ImportError guard), call in node body, place audit writes after return — the interrupt-then-write sequence is the contract"
  - "ReAct tool-call extraction: iterate final_messages from safe_invoke result, read getattr(msg, 'tool_calls', None) for each message to capture all intermediate tool invocations"

requirements-completed: [MNT-02, MNT-06]

# Metrics
duration: 35min
completed: 2026-05-23
---

# Phase 07 Plan 14: RCASpecialist CR-02 + WR-05 Gap Closure Summary

**Direct interrupt() call in RCASpecialist node with post-resume audit write, plus tool_calls_log populated from ReAct message trace — restoring one-row-per-invocation audit contract and non-empty evidence panel**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-05-23T20:20:00Z
- **Completed:** 2026-05-23T20:59:47Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- CR-02 fixed: `__call__` now calls `interrupt()` directly from `langgraph.types` instead of routing through `_escalate_to_supervisor()`. The line after `interrupt()` executes only on the resumed execution — `_write_audit` fires exactly once per logical invocation, never on the first run (where `GraphInterrupt` aborts the node).
- WR-05 fixed: `_invoke_react_loop` returns `(content, tool_call_records)` tuple. It iterates `final_messages` from `safe_invoke` result, reads `getattr(msg, "tool_calls", None)` on each message, and accumulates records. `__call__` extends `tool_calls_log` via immutable concatenation; the populated list flows into `_write_audit` so `EvidencePanel.tool_calls` is non-empty.
- Regression tests authored (Test A: interrupt-lifecycle audit contract; Test B: tool_calls_log non-empty) — confirmed RED against pre-fix code, GREEN after fix; all 55 tests in the suite pass.

## Task Commits

1. **Task 1: Write failing regression tests for CR-02 and WR-05** - `4a5a1c1` (test)
2. **Task 2: Fix CR-02 interrupt ordering and WR-05 tool_calls_log** - `0a14abf` (feat)

## Files Created/Modified

- `apps/agents/maintenance/rca-specialist/tests/test_interrupt_audit_lifecycle.py` — Regression tests: Test A (audit written once on resume, not on first run; escalate_tool._arun no longer called from `__call__`), Test B (tool_calls_log populated with rag_search entry from ReAct messages)
- `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py` — CR-02: added `interrupt` import with ImportError guard; replaced `await self._escalate_to_supervisor(...)` with `_supervisor_decision = interrupt({...})`; moved `_write_audit` to execute after interrupt return. WR-05: `_invoke_react_loop` now returns `(str, list[dict])` tuple; iterates `final_messages` for tool_calls; `__call__` accumulates via `tool_calls_log = tool_calls_log + new_tool_calls`.

## Decisions Made

- Used `try/except ImportError` at module level for `langgraph.types.interrupt` import — consistent with existing pattern in `_invoke_react_loop` (`create_react_agent` / `safe_invoke` imports). Fallback stub raises `NotImplementedError` to surface clearly if called outside LangGraph.
- `_invoke_react_loop` returns tuple `(content, tool_call_records)` rather than accepting a mutable `tool_calls_log` list parameter — keeps the function pure (returns new data, doesn't mutate caller's state).
- `_escalate_to_supervisor()` method retained (not deleted) — it may still be useful for side-effects outside `__call__`, and removing it would be a broader structural change. The critical fix is removing it from the `__call__` escalation path.
- Unit tests patch `interrupt` at `mnt_rca_specialist.agent` module level — `langgraph.types.interrupt` requires `get_config()` from a LangGraph runnable context, which is absent in pure unit tests. Module-level patching is the standard approach.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test mock return value after _invoke_react_loop signature change**
- **Found during:** Task 2 (Fix implementation)
- **Issue:** Task 1 test mocked `_invoke_react_loop` to return a plain string. After Task 2 changed the return type to `(content, tool_call_records)` tuple, the test mock needed updating.
- **Fix:** Updated `AsyncMock(return_value=json.dumps(...))` to `AsyncMock(return_value=(json.dumps(...), []))` in Test A.
- **Files modified:** `tests/test_interrupt_audit_lifecycle.py`
- **Verification:** Both tests pass after update
- **Committed in:** `0a14abf` (Task 2 commit)

**2. [Rule 2 - Missing Critical] Added interrupt() patch to Test B**
- **Found during:** Task 2 (Fix implementation)
- **Issue:** Test B drove `__call__` through the full path after the fix; `interrupt()` (now called directly in `__call__`) raised `RuntimeError("Called get_config outside of a runnable context")` in the test environment.
- **Fix:** Added `patch("mnt_rca_specialist.agent.interrupt", return_value={"approved": True})` to Test B's context manager.
- **Files modified:** `tests/test_interrupt_audit_lifecycle.py`
- **Verification:** Test B passes after patch
- **Committed in:** `0a14abf` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes are necessary consequences of the CR-02 fix itself. No scope creep.

## Issues Encountered

- `langgraph.types.interrupt()` fails outside a LangGraph runnable context with `RuntimeError("Called get_config outside of a runnable context")`. Unit tests must patch `mnt_rca_specialist.agent.interrupt` at module level.
- Pre-existing `AuditRecord` Pydantic constraint: `approval_id` is required non-null when `decision=HITL_SUPERVISOR`, but `_write_audit` currently passes `approval_id=None`. This would cause `_write_audit` to raise a `ValueError` in production. This is a separate bug (related to CR-03 pattern from PredictiveMaintenance) outside this plan's scope. Tests patch `_write_audit` directly to isolate CR-02/WR-05 from this constraint. Deferred to future gap-closure plan.

## Known Stubs

None — both fixes are fully wired. The `interrupt` ImportError fallback stub in agent.py is intentional (documented test-env compatibility) and never reached in production.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. The `interrupt()` call is a LangGraph-internal mechanism; the audit write ordering change reduces (not expands) the attack surface by eliminating the double-write vector.

## Next Phase Readiness

- SC-2 (RCASpecialist) partially restored: audit ordering and evidence panel tool_calls are fixed.
- Remaining pre-existing issue: `approval_id=None` with `HITL_SUPERVISOR` fails `AuditRecord` Pydantic validation — needs a separate fix (set `approval_id` to a real UUID from the HITL system, or restructure the approval flow).
- All 55 existing rca-specialist tests continue to pass.

## Self-Check: PASSED

Files verified:
- `apps/agents/maintenance/rca-specialist/tests/test_interrupt_audit_lifecycle.py` — EXISTS
- `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py` — EXISTS (modified)

Commits verified:
- `4a5a1c1` — test(07-14): add failing regression tests for CR-02 and WR-05
- `0a14abf` — feat(07-14): fix CR-02 interrupt ordering + WR-05 tool_calls_log in RCASpecialist

---
*Phase: 07-agents-maintenance-reliability*
*Completed: 2026-05-23*
