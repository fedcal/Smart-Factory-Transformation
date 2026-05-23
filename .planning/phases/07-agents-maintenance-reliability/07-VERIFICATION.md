---
phase: 07-agents-maintenance-reliability
verified: 2026-05-23T14:00:00Z
status: gaps_found
score: 3/5
overrides_applied: 0
gaps:
  - truth: "MaintenanceCoach retrieves the correct step-by-step procedure from the RAG store for the current repair, tracks MTTR contribution, and escalates when the technician requests it"
    status: partial
    reason: >
      MTTR tracking and escalation wiring are implemented and substantive.
      However, the RAG store retrieval is critically broken at runtime: the
      `_get_graph()` method opens `AsyncPostgresSaver.from_conn_string(pg_dsn)`
      in an `async with` block, stores the compiled graph in `self._graph`, then
      exits the context manager — closing the saver's connection. The cached graph
      retains a reference to the now-closed saver. Every subsequent `ainvoke` or
      `aget_state` call will hit `InterfaceError`/`ConnectionDoesNotExistError` for
      all but the first request (CR-01). Additionally, `resume_after_help` writes
      two audit rows per resume (WR-02). The RAG retrieval itself is wired via
      tool-binding (LLM decides to call `rag_search`), so the "retrieves correct
      procedure" claim is LLM-dependent and untestable without the real agent
      running; the E2E tests bypass this with a mock synthesizer that never goes
      through the graph (confirmed in conftest.py lines 528-574).
    artifacts:
      - path: apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py
        issue: "Use-after-close: AsyncPostgresSaver closed before graph can use it (CR-01, line 435-445). Production HITL persistence broken for every call after the first."
      - path: apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py
        issue: "resume_after_help writes two audit rows (WR-02, lines 862-878): one AUTO from step(), one HITL_SUPERVISOR from resume_after_help — double-write on append-only audit table."
    missing:
      - "Fix CR-01: inject a long-lived saver via lifespan resource OR require saver injection at construction; remove the async-with pattern from _get_graph()"
      - "Fix WR-02: pass skip_audit=True to step() when called from resume_after_help, write only one authoritative audit row"

  - truth: "RCASpecialist generates a 5-Why chain for a simulated downtime event, cites knowledge base sources with provenance, and routes the corrective action recommendation to supervisor-level HITL"
    status: partial
    reason: >
      The 5-Why chain (WhyStep×5 form schema), citation provenance (full PG
      source_uri lookup via RCAChainValidator), and ALWAYS-supervisor HITL
      (Decision.HITL_SUPERVISOR) are all implemented substantively. The critical
      defect (CR-02) is that the audit write never executes on the FIRST graph
      run: `_escalate_to_supervisor` calls the EscalateToSupervisorTool which
      calls `langgraph.types.interrupt()` internally, unwinding the call stack
      before reaching `await self._write_audit(...)`. The audit row is produced on
      the SECOND execution (LangGraph resume), and a third execution produces a
      double-write. This violates the "one-row-per-invocation" audit contract and
      the explicitly-documented Pitfall §3 the code claims to solve. Additionally,
      `tool_calls_log` is initialized as `[]` and never populated (WR-05), so the
      audit trail's evidence panel contains no forensic record of which tools the
      LLM called — the primary forensic value of the panel is absent. The E2E tests
      use a mock synthesizer that does not exercise the LangGraph interrupt mechanism.
    artifacts:
      - path: apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py
        issue: "CR-02: audit write unreachable on first execution because _escalate_to_supervisor raises GraphInterrupt; audit row appears on resumed run only, double-written on re-execution."
      - path: apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py
        issue: "WR-05: tool_calls_log never populated (line 410 always []), evidence panel tool_calls always empty for every successful RCA invocation."
    missing:
      - "Fix CR-02: call interrupt() directly (not via tool) in the node, place audit write after the resume return value as documented in the fix pattern in 07-REVIEW.md"
      - "Fix WR-05: parse tool call records from LangGraph ReAct result messages and populate tool_calls_log"

  - truth: "PredictiveMaintenance estimates Remaining Useful Life for spindle, loom, and warper assets using degradation curves adapted from NASA C-MAPSS methodology; the model feature set includes ambient temperature and humidity sensors"
    status: partial
    reason: >
      The RUL estimation is substantively implemented: Ridge joblib model from
      sft-ml (C-MAPSS FD001+FD003), textile→C-MAPSS feature mapping, and
      health_index derivation are all wired correctly. Ambient humidity is mapped
      via OP_SETTING_MAP "ambient_humidity" → "op_setting_3" in feature_map.py.
      The critical defect (CR-03) is that when health_index < 0.3 triggers the
      HITL supervisor path, `_write_audit` generates a random fabricated
      `approval_id = _uuid4()` (lines 329-331) labeled as "placeholder UUID so
      the audit record is schema-valid during testing" — but this code runs in
      production. Any downstream SQL JOIN on `audit.actions.approval_id` will
      find no matching row in `hitl.approvals`, making forensic audit tools
      falsely conclude escalations were approved. Additionally, `state["asset_id"]`
      raises a bare KeyError if the key is absent (CR-04), leaking the internal
      field name in 500 error responses. These are correctness defects in the
      audit chain, not just test scaffolding issues.
    artifacts:
      - path: apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py
        issue: "CR-03: fabricated approval_id = uuid4() injected in production HITL audit rows (lines 329-331) — breaks audit trail JOIN integrity with hitl.approvals"
      - path: apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py
        issue: "CR-04: state['asset_id'] bare KeyError at line 171 leaks field name in 500 responses"
    missing:
      - "Fix CR-03: set approval_id=None until real supervisor approval arrives; update post-approval or use a separate audit row"
      - "Fix CR-04: use state.get('asset_id') with explicit ValueError for missing key"

  - truth: "DowntimeAnalyzer calculates OEE decomposition (Availability, Performance, Quality) and produces a Pareto of downtime causes from the event store"
    status: partial
    reason: >
      OEE A×P×Q computation and Pareto are substantively implemented and wired to
      the event store. Three defects impair correctness at runtime:
      (1) WR-03 BLOCKER: The API gateway passes `body.window_start.isoformat()`
      (ISO string) to the state dict at lines 646-647, but asyncpg requires Python
      `datetime` objects as TIMESTAMPTZ parameters. Every `/report` endpoint call
      will raise `asyncpg.exceptions.DataError` — the endpoint is non-functional
      at runtime despite tests passing (tests use mock that never hits asyncpg).
      (2) WR-04: `compute_pareto` computes `grand_total` from `trimmed[:top_n]` not
      from all rows — `cumulative_percent` misrepresents the Pareto distribution.
      (3) CR-05: `by_asset=True` issues 3N sequential asyncpg queries with no
      concurrency limit and no asset-count cap — unbounded DoS vector for large
      registries; also triggers a redundant double-call to compute_quality_cross_cluster.
    artifacts:
      - path: apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py
        issue: "WR-03 BLOCKER: .isoformat() at lines 646-647 passes ISO string to asyncpg TIMESTAMPTZ parameters — DataError at runtime for every /report call"
      - path: apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py
        issue: "WR-04: grand_total computed from trimmed[:top_n] not all rows — cumulative_percent always shows 100.0 at last entry regardless of true dataset coverage"
      - path: apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py
        issue: "CR-05: by_asset=True unbounded sequential iteration + no semaphore — DoS vector; also double-calls compute_quality_cross_cluster"
    missing:
      - "Fix WR-03: remove .isoformat() from gateway state dict — pass datetime objects directly"
      - "Fix WR-04: compute grand_total = sum(r[1] for r in sorted_rows) before trimming"
      - "Fix CR-05: cap by_asset at configurable max (50), use asyncio.gather with semaphore, deduplicate compute_quality_cross_cluster call"
deferred: []
human_verification:
  - test: "Run the API gateway /v1/agents/maintenance/downtime-analyzer/report endpoint with a real asyncpg-backed DB and a valid time window"
    expected: "Should return OEEReport; currently will raise DataError due to ISO string datetime bug (WR-03)"
    why_human: "Cannot run the full docker stack + real asyncpg in static analysis"
  - test: "Run MaintenanceCoach through a full intervention (start → step → step → complete) with a real PG instance (not injected saver)"
    expected: "Second and subsequent step calls should succeed; currently will fail with ConnectionDoesNotExistError after first call (CR-01)"
    why_human: "Requires live PG + LangGraph checkpoint stack"
  - test: "Trigger RCASpecialist with a real LLM and verify the audit row exists after the FIRST invocation (before supervisor resume)"
    expected: "One audit row should appear; currently no audit row exists on first execution (CR-02)"
    why_human: "Requires real LangGraph interrupt/resume cycle"
---

# Phase 07: Maintenance Cluster Verification Report

**Phase Goal:** All four Maintenance cluster agents (PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer) are implemented with C-MAPSS-adapted RUL estimation, 5-Why RCA, humidity-aware modeling, and integration with the asset registry and event store.
**Verified:** 2026-05-23T14:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PredictiveMaintenance estimates RUL for spindle/loom/warper assets using C-MAPSS-adapted model; feature set includes ambient temperature and humidity sensors | PARTIAL | Model, feature map, and humidity sensor (op_setting_3) all wired. Broken by CR-03 (fabricated approval_id in production HITL path) and CR-04 (bare KeyError on missing asset_id leaks to 500). Core ML estimation path is functional; audit integrity is not. |
| 2 | RCASpecialist generates a 5-Why chain, cites knowledge base sources with provenance, routes corrective action to supervisor-level HITL | PARTIAL | WhyStep×5 form schema, full PG source_uri lookup, ALWAYS-supervisor gate all present. Broken by CR-02: audit write unreachable on first execution (LangGraph interrupt fires before `_write_audit`). WR-05: tool_calls_log never populated — evidence panel has no forensic record. E2E tests bypass the LangGraph interrupt mechanism via mock synthesizer. |
| 3 | MaintenanceCoach retrieves step-by-step procedure from RAG store for current repair, tracks MTTR, escalates when technician requests it | PARTIAL | MTTR tracking (`compute_mttr_minutes`, mttr_start/end) and request_help escalation are substantively implemented. RAG retrieval is wired via tool-binding. Critically broken at runtime by CR-01: AsyncPostgresSaver closed before graph can use it — all checkpoint reads/writes fail after the first request in production path. WR-02: double audit row on resume. |
| 4 | DowntimeAnalyzer calculates OEE decomposition (A, P, Q) and produces Pareto of downtime causes from event store | PARTIAL | OEE A×P×Q, Pareto, event store SQL, cross-cluster quality query all implemented and wired to hypertable. Critically broken at runtime by WR-03: gateway passes ISO strings to asyncpg TIMESTAMPTZ — every `/report` call raises DataError. WR-04 misrepresents Pareto cumulative_percent. CR-05 DoS vector on by_asset=True. |
| 5 | Textile maintenance event taxonomy documented and used consistently across all four agents | VERIFIED | `failure_modes.yaml` extended with `MaintenanceSpec.reason_code` (7 entries), `event-taxonomy.md` published bilingual (IT+EN), downtime_event_generator reads reason_codes from taxonomy, DowntimeAnalyzer Pareto groups by reason_code. Cross-agent usage documented in taxonomy table. |

**Score:** 1/5 truths fully verified (SC-5); 4/5 truths partially implemented with runtime-breaking defects.

Note on scoring: SC-5 (taxonomy) is VERIFIED. SC-1 through SC-4 are PARTIAL — they each have substantive implementations but also runtime-breaking defects that prevent the claimed behavior from working in production. The defects are not test-only concerns: CR-01, CR-02, and WR-03 each make specific production API paths completely non-functional.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py` | PredictiveMaintenance LangGraph node | STUB_IN_PROD (351 lines, substantive) | Core ML path works; CR-03 fabricates approval_id in HITL path; CR-04 bare KeyError |
| `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/inference.py` | Model loader + predict_with_ci | VERIFIED | load_pretrained_model, compute_health_index, predict_rul all present and substantive |
| `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py` | RCASpecialist ReAct LangGraph node | STUB_IN_PROD (556 lines, substantive) | CR-02 audit write unreachable on first execution; WR-05 tool_calls_log empty always |
| `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/validators.py` | RCAChainValidator + PG lookup | VERIFIED | SELECT 1 FROM documents WHERE source_uri = $1 implemented with asyncpg |
| `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py` | MaintenanceCoach LangGraph thread | BROKEN_IN_PROD (889 lines, substantive) | CR-01 use-after-close saver breaks all production checkpoint ops; WR-02 double audit on resume |
| `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/mttr.py` | MTTR computation helpers | VERIFIED | compute_mttr_minutes and compute_active_work_minutes correct |
| `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py` | DowntimeAnalyzer LangGraph node | BROKEN_IN_PROD (408 lines, substantive) | Takes datetime from state, passes to generate_report — internal path correct; broken by WR-03 at gateway layer |
| `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py` | OEE A×P×Q + Pareto computation | PARTIAL | Availability/Performance/Quality correct; WR-04: Pareto cumulative_percent uses trimmed grand_total not all-rows total |
| `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/repository.py` | DowntimeEventRepository + QualityVerdictReader | VERIFIED | asyncpg parameterized queries, validate_asset_exists via sft_assets |
| `packages/sft-domain/src/sft_domain/failure_modes/models.py` | MaintenanceSpec + FailureMode.maintenance | VERIFIED | MaintenanceSpec frozen+extra=forbid, reason_code pattern ^[A-Z][A-Z0-9-]+$, optional field |
| `packages/sft-domain/src/sft_domain/failure_modes.yaml` | 7 textile defects with maintenance subkey | VERIFIED | 7 reason_codes (WEAVING-BE-001, WEAVING-MP-002, WEAVING-SF-003, SPINNING-SL-001, SPINNING-NP-002, DYEING-SD-001, DYEING-UD-002) |
| `packages/sft-ml/src/sft_ml/cmapss/feature_map.py` | TEXTILE_TO_CMAPSS_FEATURE_MAP + ambient_humidity | VERIFIED | humidity mapped as op_setting_3, loom/spinning/dyeing/warping families covered |
| `packages/sft-ml/models/ridge-fd001-fd003-v1.0.joblib` | Pre-trained Ridge model | VERIFIED (by plan) | Referenced via _MODEL_PATH; inference path confirmed |
| `docs/docs/agents/maintenance/event-taxonomy.md` | Taxonomy documentation (MNT-05) | VERIFIED | Bilingual IT+EN, 7 reason_codes, cross-agent usage table |
| `infra/migrations/timescale/008_create_downtime_events.sql` | maintenance.downtime_events hypertable | VERIFIED | CREATE TABLE + create_hypertable + CAGG + reason_code index |
| `infra/migrations/timescale/009_extend_audit_mnt.sql` | Audit schema extension for MNT | VERIFIED (by plan) | Exists on disk |
| `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py` | FastAPI maintenance router | BROKEN (lines 646-647) | WR-03: passes ISO strings not datetime objects to DowntimeAnalyzer state |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| PredictiveMaintenance agent | sft-ml Ridge model | load_pretrained_model via sft_ml.cmapss.load_model | WIRED | inference.py delegates to sft_ml.cmapss |
| PredictiveMaintenance agent | NATS maintenance.predict.* | pm-consumer pull_subscribe durable=pm-consumer | WIRED | consumer.py wired correctly |
| AnomalyDetector → PM audit chain | triggered_by_action_id cross-cluster | evidence_panel.tool_calls[0].args.triggered_by_action_id | WIRED | MNT-06 SQL JOIN resolvable |
| RCASpecialist → PG documents table | source_uri validation | SELECT 1 FROM documents WHERE source_uri = $1 | WIRED | validators.py asyncpg fetchval |
| RCASpecialist → EscalateToSupervisorTool | ALWAYS-supervisor HITL | _escalate_to_supervisor → _escalate._arun | WIRED (but broken by CR-02 on first execution) | Wiring exists; interrupt ordering broken |
| MaintenanceCoach → AsyncPostgresSaver | LangGraph checkpoint persistence | AsyncPostgresSaver.from_conn_string + langgraph_checkpoints | BROKEN | CR-01: saver closed before graph use in production path |
| MaintenanceCoach → RequestHelpTool | technician escalation | tool registration in build_coach_graph | WIRED | tools = [rag_search, request_help, escalate] |
| DowntimeAnalyzer → maintenance.downtime_events | asyncpg INSERT/SELECT | DowntimeEventRepository.insert_event / fetch_window | WIRED | SQL_INSERT_EVENT, SQL_FETCH_WINDOW parameterized |
| DowntimeAnalyzer → audit.actions cross-cluster | OEE.Q QUALITY_VERDICT | QualityVerdictReader SQL WHERE action_type='QUALITY_VERDICT' | WIRED | Cross-cluster query implemented |
| Gateway → DowntimeAnalyzer | datetime parameters | state["window_start"] → generate_report → asyncpg | BROKEN | WR-03: ISO string passed, asyncpg requires datetime object |
| failure_modes.yaml → downtime_event_generator | reason_code taxonomy | _reason_codes_for_family via load_failure_modes() | WIRED | Confirmed: generator reads taxonomy, MNT-05 consistent |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| PM agent._write_audit HITL path | approval_id | CR-03: fabricated uuid4() not from hitl.approvals | No | HOLLOW — production HITL audit rows have fake approval_id |
| DA agent.__call__ | window_start/window_end | Gateway passes isoformat() string | No | DISCONNECTED — asyncpg rejects string for TIMESTAMPTZ (WR-03) |
| RCA agent._write_audit | tool_calls_log | [] never populated (WR-05) | No | HOLLOW — evidence panel tool_calls always empty |
| Coach agent._get_graph cached graph | saver (AsyncPostgresSaver) | saver closed when async with exits | No | HOLLOW — checkpoints non-functional in production path (CR-01) |
| DA oee.compute_pareto | cumulative_percent | grand_total from trimmed not all rows | Incorrect | STATIC — always 100% at last entry regardless of true coverage (WR-04) |

### Behavioral Spot-Checks

Step 7b: All runnable checks require docker stack (asyncpg, NATS, LangGraph checkpointer). Skipped — no runnable entry points without docker compose.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MNT-01 | 07-06 | PredictiveMaintenance RUL estimation adapted from C-MAPSS | PARTIAL | Core ML path implemented; CR-03 breaks HITL audit integrity, CR-04 unsafe error handling |
| MNT-02 | 07-07 | RCASpecialist 5-Whys + citations from knowledge base | PARTIAL | 5-Why chain, PG citation validation present; CR-02 audit write skipped on first execution, WR-05 empty evidence panel |
| MNT-03 | 07-08 | MaintenanceCoach step-by-step guidance with HITL + MTTR | PARTIAL | MTTR, escalation, step loop present; CR-01 production saver broken, WR-02 double audit on resume |
| MNT-04 | 07-09 | DowntimeAnalyzer OEE + MTTR/MTBF + Pareto patterns | PARTIAL | OEE A×P×Q, Pareto, event store wired; WR-03 gateway datetime bug makes /report endpoint non-functional, WR-04 Pareto semantics wrong, CR-05 DoS |
| MNT-05 | 07-02, 07-11 | Maintenance event taxonomy documented and used consistently | SATISFIED | 7 reason_codes in failure_modes.yaml, event-taxonomy.md bilingual, used in sim generator and DowntimeAnalyzer Pareto |
| MNT-06 | 07-06, 07-08, 07-09 | Integration with asset registry and event store | PARTIAL | PM uses sft_assets.models.Asset registry; DA uses validate_asset_exists; audit chain triggered_by_action_id wired; broken by CR-01/CR-03 at runtime |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py` | 435-445 | Use-after-close: AsyncPostgresSaver closed before graph use (comment: "WARNING: saver is closed when this async with exits") | BLOCKER | Every production MaintenanceCoach request after first will fail with ConnectionDoesNotExistError |
| `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py` | 510-531 | Audit write unreachable on first LangGraph execution — interrupt() raises before _write_audit | BLOCKER | Audit contract violated: first invocation produces no audit row; second produces one; third produces double-write |
| `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py` | 329-331 | `approval_id = _uuid4()` with comment "placeholder UUID ... during testing" runs in production | BLOCKER | Fabricated approval_id in production audit rows — downstream forensic tools falsely see approved escalations |
| `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py` | 646-647 | `body.window_start.isoformat()` passes string to asyncpg TIMESTAMPTZ parameter | BLOCKER | Every /v1/agents/maintenance/downtime-analyzer/report request raises DataError |
| `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py` | 171 | `state["asset_id"]` bare KeyError leaks field name in 500 response body | WARNING | Internal field name exposed in error responses |
| `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py` | 320 | `grand_total = sum(r[1] for r in trimmed)` should use all rows not trimmed | WARNING | Pareto cumulative_percent always 100% at last entry — misrepresents distribution |
| `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py` | 410 | `tool_calls_log: list[dict[str, Any]] = []` never appended to | WARNING | Evidence panel tool_calls always empty — primary forensic value absent |
| `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py` | 862-878 | resume_after_help calls step() then _write_audit — two audit rows per resume | WARNING | Double-write on append-only audit table |
| `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py` | 229-252 | by_asset=True unbounded sequential iteration + double compute_quality_cross_cluster | WARNING | DoS vector for large asset registries; redundant DB queries |
| `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py` | 107-116 | _trim_messages can duplicate system messages when tail overlaps with first-5 | INFO | Duplicate system messages in state when message count just above threshold |

### Human Verification Required

**1. MaintenanceCoach Production Saver Lifecycle**

**Test:** Start docker compose, invoke `/v1/agents/maintenance/maintenance-coach/start`, then `/v1/agents/maintenance/maintenance-coach/step` twice with the same intervention_id.
**Expected:** Both step calls should succeed with checkpoint persistence. Currently the second step call will fail with `ConnectionDoesNotExistError` (CR-01 — saver closed after `_get_graph()` returns).
**Why human:** Requires full docker stack + LangGraph checkpoint runtime.

**2. RCASpecialist First-Execution Audit Row**

**Test:** Invoke `/v1/agents/maintenance/rca-specialist/analyze` with a valid problem_statement and check the audit.actions table before supervisor responds.
**Expected:** One audit row should appear immediately after the agent suspends at the supervisor interrupt. Currently no row appears on first execution (CR-02).
**Why human:** Requires real LangGraph interrupt/resume cycle with real LLM.

**3. DowntimeAnalyzer /report Endpoint with Real DB**

**Test:** POST `/v1/agents/maintenance/downtime-analyzer/report` with valid window_start and window_end datetimes via the API gateway.
**Expected:** Should return OEEReport. Currently raises `asyncpg.exceptions.DataError` because gateway passes ISO strings (WR-03).
**Why human:** Confirms runtime behavior of asyncpg parameter type rejection.

### Gaps Summary

Four of five success criteria are substantively implemented but broken at runtime due to confirmed bugs from the code review (07-REVIEW.md).

**Root causes cluster into three groups:**

**Group 1: LangGraph lifecycle mismanagement (CR-01 + CR-02)**
Both MaintenanceCoach and RCASpecialist share the same fundamental misunderstanding of when LangGraph operations occur relative to `interrupt()`. CR-01 closes the PostgreSQL saver before the graph can use it. CR-02 places the audit write after a call that raises `GraphInterrupt`, making the write unreachable on the first execution. Both are correctness defects that make the agents non-functional in production for their core LangGraph-dependent behaviors.

**Group 2: Gateway type mismatch (WR-03)**
The FastAPI gateway converts datetime objects to ISO strings before placing them into the state dict passed to DowntimeAnalyzer. asyncpg requires Python `datetime` objects for TIMESTAMPTZ columns. The fix is one line (remove `.isoformat()`). This makes the entire DowntimeAnalyzer `/report` endpoint non-functional at runtime.

**Group 3: Audit integrity violations (CR-03 + WR-05)**
PredictiveMaintenance fabricates `approval_id` in production HITL audit rows. RCASpecialist never populates `tool_calls_log`, leaving evidence panels forensically empty. Both are audit trail defects that undermine the HITL governance model.

**E2E test pass rate is misleading:** All 12 E2E tests pass because the conftest mock synthesizer bypasses the real agent imports when the packages are not installed in the test environment (confirmed at conftest.py lines 528-574). The tests verify fixture shapes and mock response assertions, not actual agent runtime behavior. The bugs were not caught by tests because the affected code paths (LangGraph interrupt lifecycle, asyncpg type enforcement) are only exercisable with a running docker stack.

MNT-05 (taxonomy) is the only success criterion fully satisfied: 7 reason_codes in failure_modes.yaml, bilingual event-taxonomy.md doc pages, and consistent usage in the simulator and DowntimeAnalyzer Pareto confirmed by code trace.

---

_Verified: 2026-05-23T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
