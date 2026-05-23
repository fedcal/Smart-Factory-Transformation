---
phase: 07-agents-maintenance-reliability
reviewed: 2026-05-23T12:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py
  - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/consumer.py
  - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/metadata.py
  - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/models.py
  - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py
  - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/repository.py
  - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py
  - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/metadata.py
  - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/models.py
  - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/mttr.py
  - apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/prompts.py
  - apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py
  - apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/consumer.py
  - apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/inference.py
  - apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/metadata.py
  - apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/models.py
  - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py
  - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/metadata.py
  - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/models.py
  - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/prompts.py
  - apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/validators.py
  - apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py
  - apps/api-gateway/src/svc_api_gateway/dependencies.py
  - apps/api-gateway/src/svc_api_gateway/main.py
  - apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py
  - infra/migrations/timescale/008_create_downtime_events.sql
  - infra/migrations/timescale/009_extend_audit_mnt.sql
findings:
  critical: 5
  warning: 7
  info: 4
  total: 16
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-05-23T12:00:00Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Reviewed 27 source files spanning 4 new LangGraph maintenance agents (PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer), the additive NATS hook on AnomalyDetector, the FastAPI gateway maintenance router, and two SQL migrations. No SQL injection was found — all SQL constants use positional parameters exclusively. Five critical-severity defects were identified; the most serious is a dangling saver handle in the MaintenanceCoach production path that closes the AsyncPostgresSaver connection mid-use, which will cause checkpoint reads/writes to fail silently for every request after the first. A second critical issue is the audit-write ordering violation in RCASpecialist: the audit row is written unconditionally even when `escalate_to_supervisor` raises an interrupt (i.e., on the first graph execution), which contradicts the explicitly-documented Pitfall §3 contract and risks double-writes on LangGraph replay. Three further critical issues cover a fake `approval_id` injected into HITL audit rows, a hard `KeyError` when `asset_id` is absent from PM state, and a denial-of-service vector via unbounded `by_asset` iteration.

---

## Critical Issues

### CR-01: MaintenanceCoach saver closed before graph can use it (use-after-close)

**File:** `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py:435-445`

**Issue:** `_get_graph()` opens `AsyncPostgresSaver.from_conn_string(pg_dsn)` in an `async with` block, compiles the graph against the saver, caches `self._graph`, then **exits the `async with` — closing the saver's underlying connection**. The cached graph retains a reference to the now-closed saver. Any subsequent graph `ainvoke` or `aget_state` call will attempt to use the closed connection, producing `InterfaceError` / `ConnectionDoesNotExistError` that propagates as a 500 to the caller. Every `step()` and `resume_after_help()` call shares the same broken cached graph.

The comment at line 443 itself warns: *"WARNING: saver is closed when this async with exits"* — this is a documented known-broken state that was never fixed.

**Fix:** The production path must keep the saver alive for the graph's lifetime. Either inject a long-lived saver at construction (preferred — matches the test path) or manage the saver as an application lifespan resource and always inject it:

```python
# In lifespan (api-gateway) — create once, close on shutdown:
async with AsyncPostgresSaver.from_conn_string(pg_dsn) as saver:
    await saver.setup()
    coach = MaintenanceCoach(..., saver=saver)
    app.state.maintenance_coach = coach
    yield  # FastAPI lifespan yield
# saver closed here on shutdown — correct

# In _get_graph(): always require saver to be injected; raise clearly if not:
async def _get_graph(self) -> Any:
    if self._graph is None:
        raise RuntimeError(
            "MaintenanceCoach._graph is None. "
            "Inject a pre-built saver at construction or wire via lifespan."
        )
    return self._graph
```

---

### CR-02: RCASpecialist audit write executes BEFORE interrupt resolves — Pitfall §3 violation

**File:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py:510-531`

**Issue:** The docstring (lines 27-30) explicitly states the audit write must happen *after* `escalate_to_supervisor` resolves, because the escalate tool calls `langgraph.types.interrupt()` internally. On the **first** graph execution, `interrupt()` raises `GraphInterrupt`, unwinding the call stack. The `await self._write_audit(...)` call at line 521 is therefore **never reached on the first execution**. On LangGraph resume (second execution), the node runs top-to-bottom again: `_escalate_to_supervisor` is called again (second escalation), then the audit write fires. This means:

1. The audit row is written on the **second execution** only — the first graph run produces no audit row, violating the one-row-per-invocation contract.
2. If the graph is re-executed again (e.g., supervisor retries), a second audit row is written — double-write.

The same agent.py comments at lines 473 and 516 acknowledge "Pitfall §3 — no double-write on LangGraph resume", but the implementation does not actually solve it: the escalate call still raises on first execution, so the audit write is never reached.

**Fix:** Use LangGraph's `Command(resume=...)` / checkpoint-aware pattern: check whether this is a resumed execution before calling escalate again; write the audit row exactly once after the first execution completes (not on resumed runs). The correct approach for "write audit after interrupt resolves" is to write inside a post-interrupt wrapper that only runs on the resumed execution:

```python
# Pattern: use langgraph.types.interrupt() return value to detect resume
supervisor_decision = interrupt({
    "reason": escalate_reason,
    "suggested_action": escalate_suggested,
    "evidence_summary": escalate_evidence,
})
# This line only executes on RESUME (not on first run)
await self._write_audit(...)
```

Removing the explicit `_escalate_to_supervisor` call and instead using `interrupt()` directly avoids both the double-escalation and the missing-audit-row problems.

---

### CR-03: PredictiveMaintenance fabricates `approval_id` for HITL_SUPERVISOR audit records

**File:** `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py:329-331`

**Issue:** When `health_index < 0.3` triggers the HITL path, `_write_audit` generates a random `approval_id = _uuid4()` with the comment "placeholder UUID so the audit record is schema-valid during testing." This fabricated UUID is written to `audit.actions.approval_id` in **production** (not just tests). Any downstream query joining `audit.actions` to `hitl.approvals` on `approval_id` will find no matching approval record for these rows. Forensic audit tools will incorrectly conclude that maintenance escalations were "approved" (because approval_id is non-null) while the actual approval workflow was never triggered.

**Fix:** `approval_id` must be `None` until a real approval is created and its UUID is assigned back. The HITL flow should be: escalate → LangGraph interrupt → supervisor approves in HITL system → resume with real `approval_id`. Pass `approval_id=None` in the initial audit row and update it post-approval, or use a separate post-approval audit row.

```python
# In _write_audit:
motivation = None
approval_id = None
if decision is Decision.HITL_SUPERVISOR:
    motivation = f"Supervisor approval required for asset {estimate.asset_id}"
    # approval_id remains None until supervisor approves
    # The HITL system updates this via a separate mechanism
```

---

### CR-04: PredictiveMaintenance hard `KeyError` on missing `asset_id` in state

**File:** `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py:171`

**Issue:** `asset_id = state["asset_id"]` raises `KeyError` if the key is absent from the state dict. The comment says "KeyError if absent → fail-fast", but in a LangGraph graph this becomes an unhandled exception that propagates through the supervisor graph to the API gateway, returning a 500 error with the raw `KeyError` message (including the key name) as the error body — this leaks internal field names in error responses.

```python
# In _handle_agent_error (maintenance_agents.py:263):
content={"error": str(exc), "thread_id": thread_id},
```

`str(KeyError("asset_id"))` produces `"'asset_id'"` — the key name is exposed in the 500 response body.

**Fix:** Validate the required state keys explicitly and raise a structured error:

```python
asset_id = state.get("asset_id")
if not asset_id:
    raise ValueError("PredictiveMaintenance requires 'asset_id' in state")
```

---

### CR-05: DowntimeAnalyzer `by_asset=True` — unbounded iteration over all assets without concurrency limit

**File:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py:229-252`

**Issue:** When `by_asset=True`, `generate_report` iterates sequentially over every asset in `self._asset_registry`, calling `compute_oee` (which performs 3 DB queries) for each. There is no upper bound on the asset count and no concurrency limit. A registry of N assets issues 3N asyncpg queries sequentially in a single HTTP request. For N=100 assets (well within the "Phase 11 may add PG-backed registry if asset set grows beyond O(100)" comment in repository.py) this is 300 sequential DB round-trips per request. More critically, a malicious caller with `by_asset=True` can hold a DB connection for the full duration of all queries, starving the pool.

Additionally, `compute_quality_cross_cluster` is called **twice** for the aggregate path: once inside `compute_oee` (line 203) and once explicitly at line 214 to obtain `quality_source`. Both calls execute the same expensive cross-cluster `audit.actions` query. This is a redundant double-query.

**Fix for DoS:** Cap `by_asset` computation at a configurable asset count (e.g., 50), and use `asyncio.gather` with a semaphore to bound concurrency:

```python
_MAX_BY_ASSET: int = 50
# ...
sem = asyncio.Semaphore(10)
async def _per_asset(asset_id):
    async with sem:
        return await compute_oee(asset_id=asset_id, ...)
results = await asyncio.gather(*[_per_asset(a.asset_id) for a in assets[:_MAX_BY_ASSET]])
```

**Fix for double-query:** Return `quality_source` from `compute_oee` (extend its return tuple) instead of calling `compute_quality_cross_cluster` a second time.

---

## Warnings

### WR-01: MaintenanceCoach `_get_graph()` closes saver and stores stale graph — silent failure path

**File:** `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py:419-445`

**Issue:** Even aside from the use-after-close in CR-01, storing `self._graph` after the `async with` exits means the graph is cached permanently with a closed saver. Future calls to `_get_graph()` return `self._graph` (line 421) without re-opening the saver, making the graph permanently broken in the production (no-injected-saver) path. The `RuntimeError` for missing `PG_DSN` (line 428) is correct, but the broken-saver path silently continues.

**Fix:** Remove the `self._graph = graph` assignment inside the `async with` block entirely. Require saver injection at construction. (Addressed by CR-01 fix above.)

---

### WR-02: `resume_after_help` writes two audit rows per resume — double-write

**File:** `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py:862-878`

**Issue:** `resume_after_help` calls `await self.step(resume_request)` which internally calls `await self._write_audit(...)` with `decision="auto"`. Then `resume_after_help` calls `await self._write_audit(...)` again at line 871 with `decision="hitl_supervisor"`. This produces **two audit rows** for the same step: one with decision `AUTO` and one with decision `HITL_SUPERVISOR`. The second call is documented as "overriding" but it actually produces an additional row — audit tables are append-only.

**Fix:** Pass an `escalation_trigger` parameter to `step()` so it can write the correct audit row directly, or suppress the inner `_write_audit` call and write only the authoritative one:

```python
# Option: skip step()'s internal audit write when called from resume_after_help
response = await self.step(resume_request, skip_audit=True)
await self._write_audit(
    intervention_id=intervention_id,
    step_no=response.current_step,
    completed_step=response.completed_step,
    decision="hitl_supervisor",
    escalation_trigger="technician_request",
)
```

---

### WR-03: DowntimeAnalyzer `__call__` passes ISO string datetimes when repository expects `datetime` objects

**File:** `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py:646-649`

**Issue:** The gateway endpoint calls `body.window_start.isoformat()` before placing datetimes into the state dict:

```python
state: dict[str, Any] = {
    "window_start": body.window_start.isoformat(),  # string
    "window_end": body.window_end.isoformat(),       # string
    ...
}
```

The `DowntimeAnalyzer.__call__` reads `state["window_start"]` and `state["window_end"]` and passes them directly to `generate_report`, `compute_oee`, and ultimately `conn.fetch(self._SQL_FETCH_WINDOW, window_start, window_end, asset_id)`. asyncpg does not accept ISO string datetimes as `TIMESTAMPTZ` parameters — it requires Python `datetime` objects. This causes a `asyncpg.exceptions.DataError` at runtime for every `/report` request.

**Fix:** Remove `.isoformat()` in the gateway state dict:

```python
state: dict[str, Any] = {
    "window_start": body.window_start,  # datetime object
    "window_end": body.window_end,      # datetime object
    ...
}
```

---

### WR-04: `compute_pareto` uses `grand_total` of only `top_n` entries, not all entries

**File:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py:320`

**Issue:** `compute_pareto` computes `grand_total = sum(r[1] for r in trimmed)` where `trimmed = sorted_rows[:top_n]`. This means `cumulative_percent` is computed relative to the top-N entries only, not the total downtime across all reason codes. The last entry in the returned list will always show `cumulative_percent = 100.0` regardless of whether the top-N entries actually account for 100% of total downtime.

For a Pareto analysis this is semantically incorrect: `cumulative_percent` should show "what percentage of total downtime does this set of reasons explain?" If the top-10 reasons account for 70% of all downtime, the last entry should show 70.0, not 100.0. This misrepresents the Pareto distribution to consumers.

**Fix:** Accept the full-dataset total separately, or compute `grand_total` from all rows before trimming:

```python
grand_total = sum(r[1] for r in sorted_rows)  # all rows, not just trimmed
trimmed = sorted_rows[:top_n]
```

---

### WR-05: RCASpecialist `tool_calls_log` is never populated — empty evidence panel

**File:** `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py:410`

**Issue:** `tool_calls_log: list[dict[str, Any]] = []` is initialized at line 410 and never appended to anywhere in the retry loop. The `_invoke_react_loop` result is a raw string; no tool call records are extracted from it. The `EvidencePanel.tool_calls` in the audit row is therefore always an empty list for every successful RCA invocation. The entire `_build_evidence_panel` function with its ToolCall construction is dead code for the normal path — the list built in lines 269-280 always processes `tool_calls_log=[]`.

This is not just a quality issue: the audit trail for RCA steps contains no evidence of which tools the LLM called, which is the primary forensic value of the evidence panel.

**Fix:** Parse tool call records from the LangGraph ReAct result:

```python
final_messages = result.get("messages", [])
for msg in final_messages:
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        for tc in tool_calls:
            tool_calls_log.append({
                "name": tc.get("name", "unknown"),
                "args": tc.get("args", {}),
                "result": None,
                "duration_ms": 0,
                "ts": datetime.now(timezone.utc),
            })
```

---

### WR-06: `_trim_messages` can return a list with overlapping entries when tail overlaps with `system_msgs`

**File:** `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py:107-116`

**Issue:** `system_msgs` is built from `messages[:5]` and `tail` is `messages[-tail_size:]`. If `tail_size >= len(messages) - 5`, the tail will include messages that are also in `system_msgs`, producing duplicate messages. Example: 51 messages, 2 system messages in first 5. `threshold=50`, `tail_size = 50 - 2 = 48`. `tail = messages[-48:]` which starts at index 3, overlapping with `system_msgs` entries at indices 0-1 (both have `type="system"`). The final list will have those system messages twice.

**Fix:** Build tail starting only after the preserved system messages:

```python
non_system_tail = [m for m in messages[5:] if not (
    getattr(m, "type", None) == "system"
    or (isinstance(m, dict) and m.get("type") == "system")
)]
tail_size = max(0, threshold - n_system)
tail = non_system_tail[-tail_size:] if tail_size > 0 else []
```

---

### WR-07: `PredictRequest.severity` accepts `"minor"` but the consumer silently invokes the agent for it

**File:** `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/consumer.py:236-250` and `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/models.py:104-107`

**Issue:** `PredictRequest.severity` allows `"minor"`, and the model docstring says "minor is included for completeness but the consumer can ack-drop minor messages if received." However, `_process_one` (lines 236-250) does NOT check severity — it invokes the agent for all validated messages including `minor`. The AnomalyDetector publish hook (anomaly-detector/agent.py:267) filters `_PM_SEVERITY_TRIGGER = frozenset({"major", "critical"})` before publishing, so minor messages should never arrive. But if a message is published by another producer or replayed, the PM agent runs a full ML inference cycle on a minor anomaly without any HITL gate intention.

**Fix:** Either restrict `PredictRequest.severity` to `Literal["major", "critical"]` (cleaner — matches the publish-side filter), or add an explicit ack-drop in `_process_one`:

```python
if req.severity not in ("major", "critical"):
    logger.info("pm_consumer_minor_severity_ack_drop", asset_id=req.asset_id)
    await msg.ack()
    return
```

---

## Info

### IN-01: Constant duplication between `agent.py` and `consumer.py` in downtime-analyzer

**File:** `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/consumer.py:218-231`

**Issue:** `_write_minimal_audit` in consumer.py re-declares `_AGENT_ID`, `_CLUSTER`, `_NO_LLM_MODEL`, `_NO_PROMPT_HASH`, and `_EMPTY_BUDGET` as local variables (lines 218-231), all with the same values already defined as module-level constants in `agent.py`. If the agent_id or cluster name changes, the fallback path will produce mismatched audit rows.

**Fix:** Import the constants from `agent.py`:

```python
from mnt_downtime_analyzer.agent import AGENT_ID as _AGENT_ID, CLUSTER as _CLUSTER, _NO_LLM_MODEL, _NO_PROMPT_HASH, _EMPTY_BUDGET
```

---

### IN-02: `compute_health_index` does integer division without float cast

**File:** `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/inference.py:83`

**Issue:** `return min(max(rul_cycles / RUL_MAX_CYCLES, 0.0), 1.0)` — in Python 3 `int / int` produces float so this is safe. However `rul_cycles` is annotated `int` and `RUL_MAX_CYCLES = 125` is `int`. The division is correct but the lack of explicit `float()` cast makes the intent ambiguous to future maintainers who might port this to a language where integer division truncates.

**Fix:** Explicit cast for clarity: `return min(max(float(rul_cycles) / RUL_MAX_CYCLES, 0.0), 1.0)`

---

### IN-03: `CoachResumeRequestHTTP.supervisor_input` can be passed as `None` without error when `technician_id` is provided, but then silently ignored

**File:** `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py:580-581`

**Issue:** Path (a) resume sets `state["supervisor_input"] = body.supervisor_input` even when `body.technician_id is not None` (the code takes the `else` branch only when `technician_id is None`, but both branches are correct). No issue here per se, but: when `technician_id is not None` (path b), `supervisor_input` is also allowed to be non-None (the validator only requires at least one, not exactly one). The `supervisor_input` value on path (b) is silently discarded — callers may be confused why their supervisor message had no effect.

**Fix:** Add a `model_validator` that makes the two fields mutually exclusive or document the precedence clearly in the schema description.

---

### IN-04: `downtime_events` table missing unique constraint on `event_id` alone

**File:** `infra/migrations/timescale/008_create_downtime_events.sql:56`

**Issue:** The composite `PRIMARY KEY (event_id, timestamp)` satisfies the TimescaleDB requirement, but there is no unique index on `event_id` alone. The `ON CONFLICT (event_id, timestamp) DO NOTHING` clause in `SQL_INSERT_EVENT` is idempotent for exact duplicates (same UUID + same timestamp). However, it is possible to insert two rows with the same `event_id` but different `timestamp` values — e.g., if the simulator regenerates an event with a corrected timestamp. This violates the business invariant that `event_id` should be globally unique.

**Fix:** Add a unique index on `event_id`:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_downtime_event_id_unique
  ON maintenance.downtime_events (event_id);
```

Note: TimescaleDB allows unique indexes that include the partition key, but a unique index on `event_id` alone works on the logical table and is enforced by TimescaleDB 2.x. The existing `ON CONFLICT` clause would need to be updated to `ON CONFLICT (event_id) DO NOTHING` if this index is added.

---

_Reviewed: 2026-05-23T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
