---
phase: 06-agents-operations-production
plan: 05
plan_id: 06-05
subsystem: sft-agents
tags: [hitl, tools, langgraph, routing, ops-cluster]
requires: [06-00, 06-01, 06-04]
provides:
  - EscalateToSupervisorTool   # tools/hitl.py
  - EscalateInput              # tools/hitl.py
  - LogEventTool               # tools/audit.py
  - LogEventInput              # tools/audit.py
  - EventType                  # tools/audit.py — Literal whitelist
  - build_ops_subgraph         # runtime/clusters.py
  - AgentState.target_agent    # runtime/state.py — additive field for OPS routing
affects:
  - packages/sft-agents/src/sft_agents/tools/__init__.py     # merged exports
  - packages/sft-agents/src/sft_agents/runtime/__init__.py   # merged exports
  - packages/sft-agents/src/sft_agents/runtime/state.py      # +target_agent
tech-stack:
  added: []
  patterns:
    - LangChain BaseTool async-only (PATTERNS Shared Pattern 7)
    - Pydantic v2 frozen + extra=forbid input schemas (T-V6-injection)
    - LangGraph `interrupt()` deferred audit (Pitfall §3 — idempotent replay)
    - SafetyInterlockMiddleware uniform gate (Pitfall §9)
    - `add_conditional_edges` for intra-cluster routing (RESEARCH §Pattern 9)
key-files:
  created:
    - packages/sft-agents/src/sft_agents/tools/hitl.py
    - packages/sft-agents/src/sft_agents/tools/audit.py
  modified:
    - packages/sft-agents/src/sft_agents/tools/__init__.py
    - packages/sft-agents/src/sft_agents/runtime/__init__.py
    - packages/sft-agents/src/sft_agents/runtime/state.py
    - packages/sft-agents/src/sft_agents/runtime/clusters.py
    - packages/sft-agents/tests/tools/test_escalate_tool.py
    - packages/sft-agents/tests/tools/test_log_event_tool.py
    - packages/sft-agents/tests/runtime/test_clusters_ops.py
decisions:
  - "EscalateToSupervisorTool uses ProposedAction.from_payload(thread_id='escalate_to_supervisor', ...) so the synthetic action id is sha256-deterministic from the (reason/suggested_action/evidence_summary) tuple — replay-safe across LangGraph re-execution."
  - "LogEventTool uses ActionType.GOVERNOR_ALERT as a placeholder informational action_type (per plan note: a dedicated OPERATOR_LOG enum value may land in a later phase)."
  - "LogEventTool stashes the structured payload inside EvidencePanel.tool_calls[] as a synthetic ToolCall so the original event_type + summary + payload remain queryable in audit.actions without a JSONB ad-hoc scan."
  - "AgentState gains a new optional field `target_agent: str | None`. LangGraph's StateGraph(AgentState) filters update dicts to declared TypedDict keys, so the ops router's `state.get('target_agent')` only works when the field is declared on the schema. Additive change — no existing readers needed it."
  - "build_ops_subgraph enforces operator-assistant in child_callables at build time (raises ValueError). The fallback target is the only sane default; missing it would silently send unknown targets to a non-existent node."
metrics:
  duration_minutes: 14
  completed: 2026-05-23
---

# Phase 06 Plan 05: ops-shared-tools Summary

Two LangChain BaseTool subclasses (`EscalateToSupervisorTool`, `LogEventTool`) and one runtime router (`build_ops_subgraph`) ship in `sft-agents`, ready for Wave 3 OPS agent plans (OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector) to register them.

## What landed

### `packages/sft-agents/src/sft_agents/tools/hitl.py` — EscalateToSupervisorTool

**Input schema** `EscalateInput(BaseModel, frozen=True, extra="forbid")`:

| Field | Type | Constraints |
|-------|------|-------------|
| `reason` | `str` | `Field(min_length=10, max_length=2000)` |
| `suggested_action` | `str` | `Field(min_length=10, max_length=2000)` |
| `evidence_summary` | `str` | `Field(min_length=10, max_length=2000)` |

**Behaviour** (D-OA-02 #4, Pitfall §3 + §9):

1. Builds `ProposedAction.from_payload(thread_id="escalate_to_supervisor", action_type=ActionType.ESCALATION_REQUEST, args=...)` — deterministic UUID derived from the input tuple so resume-replay is idempotent.
2. Calls `await self._safety.check(action, **forwarded_ctx)` — forwards `agent_id` / `thread_id` / `cluster` / `evidence_panel` / `budget_snapshot` from `**kwargs` so the real `SafetyInterlockMiddleware.check` signature is satisfied; tests pass an `AsyncMock` that swallows any kwargs.
3. Imports `from langgraph.types import interrupt` at module top (single import; replaceable in tests via `monkeypatch.setattr("sft_agents.tools.hitl.interrupt", ...)`).
4. `decision = interrupt({"tool": "escalate_to_supervisor", "tier": Tier.SUPERVISOR.value, "payload": action.model_dump(mode="json")})` — returns the supervisor's dict verbatim to the LLM as ToolMessage content.
5. **No PG/NATS side-effects before `interrupt()`** — Pitfall §3 (the human_approval_node owns the post-resume audit write).

`SafetyInterlockRejection` propagates without swallowing.

### `packages/sft-agents/src/sft_agents/tools/audit.py` — LogEventTool

**Input schema** `LogEventInput(BaseModel, frozen=True, extra="forbid")`:

| Field | Type | Constraints |
|-------|------|-------------|
| `event_type` | `Literal["shift_handover_input", "operator_question", "operator_note", "kpi_observation"]` | starter set per plan |
| `summary` | `str` | `Field(min_length=1, max_length=2000)` |
| `payload` | `dict[str, Any]` | `Field(default_factory=dict)` |

**Behaviour** (D-OA-02 #5, observability-only):

1. Constructs one `AuditRecord` with `decision=Decision.LOGGED`, `action_type=ActionType.GOVERNOR_ALERT.value`, `approval_id=None`.
2. `EvidencePanel` is minimally populated: the operator text → `input_summary` (capped at 500 chars, `input_truncated` flag set when needed); the full `event_type` + `summary` + `payload` stashed in `tool_calls[]` as a synthetic `ToolCall(name="log_event", args=..., result={"logged": True})` so Phase 11 dashboards can query the original event without a JSONB scan.
3. `evidence_panel.model = "log-only@sft-agents"`, `prompt_hash = "0"*64`, `tokens = TokenUsage(0, 0, 0)` — sentinel values for log-only rows that still match the EvidencePanel regex / nonnegative constraints.
4. Calls `await self._audit_writer.write(record)`; returns `{"logged": True, "action_id": str(action_id)}`.
5. **No `interrupt()`, no queue insert, no NATS publish** — purely observability.

### `packages/sft-agents/src/sft_agents/runtime/clusters.py` — build_ops_subgraph

```python
def build_ops_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    ...
```

**Routing semantics** (RESEARCH §Pattern 9, D-X OPS-routing):

- `add_conditional_edges(START, _route, {slug: slug for slug in children})`.
- `_route(state)` reads `state.get("target_agent")`.
- If the value is missing or not in `child_callables`, the router emits a structlog `ops_route_unknown_target` warning (with the bad target + the fallback) and returns `"operator-assistant"`.
- Each child node is wired to `END`.

**Build-time guards** (raise `ValueError`):

- `child_callables` cannot be empty.
- `child_callables` MUST contain `"operator-assistant"` (the fallback). Missing it would silently send unknown targets to a non-existent node.

`build_cluster_subgraph` (the Phase 4 linear placeholder) is unchanged — used by maintenance / knowledge / supply until those phases wire real callables.

### `packages/sft-agents/src/sft_agents/runtime/state.py` — AgentState.target_agent

Additive optional field on `AgentState` TypedDict: `target_agent: str | None`. LangGraph's `StateGraph(AgentState)` filters state-update dicts to declared TypedDict keys; without this declaration, the ops router's `state.get("target_agent")` would always observe `None` because the field would be stripped at the supervisor → cluster boundary.

### `packages/sft-agents/src/sft_agents/tools/__init__.py` — merged exports

Existing exports (`BUILTIN_TOOLS`, `ToolRegistry`, `export_tool_schemas`) are kept; new exports (`EscalateInput`, `EscalateToSupervisorTool`, `EventType`, `LogEventInput`, `LogEventTool`) merged into `__all__` alphabetically.

### `packages/sft-agents/src/sft_agents/runtime/__init__.py` — merged exports

Existing `RateLimiter` (Plan 06-02) preserved; `build_ops_subgraph` added to `__all__` and the lazy `__getattr__` hook so the import cost is paid only on first access.

## Test counts

| File | Tests | Outcome |
|------|-------|---------|
| `packages/sft-agents/tests/tools/test_escalate_tool.py` | 11 | all green |
| `packages/sft-agents/tests/tools/test_log_event_tool.py` | 11 | all green |
| `packages/sft-agents/tests/runtime/test_clusters_ops.py` | 7 | all green |
| `packages/sft-agents/tests/test_clusters.py` (regression) | 10 | all green |
| **Full sft-agents suite** | **358 + 10 skipped (integration markers)** | all green |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing critical functionality] `_arun` forwards safety-check kwargs**

- **Found during:** Task 2 GREEN
- **Issue:** `SafetyInterlockMiddleware.check` is `async + keyword-only` with required kwargs `agent_id` / `thread_id` / `cluster` / `evidence_panel` / `budget_snapshot`. A bare `await self._safety.check(action)` works under `AsyncMock` in tests but raises `TypeError` against the real middleware at integration time.
- **Fix:** `_arun` extracts those keys from `**kwargs` (forwarded by the calling ReAct node) and re-passes them. Plan's tests do not provide context (they mock with `AsyncMock`), but the production wiring now satisfies the real signature.
- **Files modified:** `packages/sft-agents/src/sft_agents/tools/hitl.py`
- **Commit:** `50b8edd`

**2. [Rule 3 — Blocking issue] AgentState gained `target_agent: str | None`**

- **Found during:** Task 3 GREEN
- **Issue:** `build_ops_subgraph` test `_route` always observed `target_agent == None` even when the test passed `{"target_agent": "quality-inspector"}` to `ainvoke`. Root cause: LangGraph's `StateGraph(AgentState)` filters input/update dicts to the keys declared on the TypedDict; undeclared keys are stripped.
- **Fix:** Added `target_agent: str | None` to the `AgentState` TypedDict declaration. Additive — no existing reader needed the field.
- **Files modified:** `packages/sft-agents/src/sft_agents/runtime/state.py`
- **Commit:** `b01c1e3`

**3. [Rule 1 — Test bug] Mock children write to a declared AgentState field**

- **Found during:** Task 3 GREEN
- **Issue:** Initial test mocks returned `{"_last_child": slug}` and `{"anomalies": [...]}`. Those keys are not declared on `AgentState`, so LangGraph's TypedDict reducer dropped them before the final state was returned — the `await_count` assertions passed (the child WAS called) but the value assertions failed.
- **Fix:** Mock children now write to `thread_id` (and `cluster` for the state-delta test) — both declared `AgentState` fields. The semantic equivalent of the original test is preserved.
- **Files modified:** `packages/sft-agents/tests/runtime/test_clusters_ops.py`
- **Commit:** `b01c1e3`

### Plan Note

Plan §Task 1 description specifies "~13 tests" across the two tool test files. The implementation lands at 22 (11 + 11) — extra tests cover Pydantic frozen + max_length boundaries explicitly, plus tool-metadata stability assertions. All adhere to the plan's behaviour bullets.

## TDD Gate Compliance

- `test(06-05): add failing tests …` → RED gate present (`f5380a2`).
- `feat(06-05): implement EscalateToSupervisorTool + LogEventTool` → GREEN gate (`50b8edd`).
- `feat(06-05): add build_ops_subgraph router …` → GREEN for Task 3 (`b01c1e3`); Task 3's RED phase tests were added in the same RED→GREEN window as the implementation, so they did not get a separate commit. The plan's frontmatter `type: tdd` is satisfied at the plan level (test commits precede feat commits in the gate sequence).

## Self-Check: PASSED

**Created files:**
- FOUND: `packages/sft-agents/src/sft_agents/tools/hitl.py`
- FOUND: `packages/sft-agents/src/sft_agents/tools/audit.py`

**Modified files:**
- FOUND: `packages/sft-agents/src/sft_agents/tools/__init__.py` (merged exports)
- FOUND: `packages/sft-agents/src/sft_agents/runtime/__init__.py` (merged with RateLimiter)
- FOUND: `packages/sft-agents/src/sft_agents/runtime/state.py` (+target_agent)
- FOUND: `packages/sft-agents/src/sft_agents/runtime/clusters.py` (+build_ops_subgraph)
- FOUND: `packages/sft-agents/tests/tools/test_escalate_tool.py` (un-skipped, 11 tests)
- FOUND: `packages/sft-agents/tests/tools/test_log_event_tool.py` (un-skipped, 11 tests)
- FOUND: `packages/sft-agents/tests/runtime/test_clusters_ops.py` (un-skipped, 7 tests)

**Commits:**
- FOUND: `f5380a2` — test(06-05) RED
- FOUND: `50b8edd` — feat(06-05) tools GREEN
- FOUND: `b01c1e3` — feat(06-05) router GREEN + AgentState.target_agent

**Test verification:** full `pytest packages/sft-agents/tests/ -x` → 358 passed, 10 skipped (integration). Imports `from sft_agents.tools import EscalateToSupervisorTool, LogEventTool` + `from sft_agents.runtime import build_ops_subgraph` both succeed.
