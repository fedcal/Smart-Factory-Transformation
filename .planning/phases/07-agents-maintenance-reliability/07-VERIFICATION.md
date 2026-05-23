---
phase: 07-agents-maintenance-reliability
verified: 2026-05-23T22:30:00Z
status: human_needed
score: 5/5
overrides_applied: 0
gaps: []
deferred: []
re_verification:
  previous_status: gaps_found
  previous_score: 3/5
  gaps_closed:
    - "CR-01 MaintenanceCoach use-after-close saver: _get_graph() now raises RuntimeError if graph not injected; self-compile async-with block removed; skip_audit=True on step() call from resume_after_help writes exactly one HITL audit row (plan 07-13)"
    - "WR-02 MaintenanceCoach double audit row: step(skip_audit=True) suppresses internal _write_audit; resume_after_help writes exactly one hitl_supervisor row (plan 07-13)"
    - "CR-02 RCASpecialist audit unreachable on first run: __call__ now calls interrupt() directly (not via _escalate_to_supervisor tool); _write_audit placed after interrupt() return — fires only on resumed execution (plan 07-14)"
    - "WR-05 RCASpecialist tool_calls_log empty: _invoke_react_loop returns (content, tool_call_records) tuple; iterates final_messages extracting getattr(msg, 'tool_calls', None); __call__ accumulates via immutable concatenation (plan 07-14)"
    - "CR-03 PredictiveMaintenance fabricated approval_id: removed uuid4() fabrication; approval_id=None for pending HITL state; AuditRecord validator updated to allow HITL+None (plan 07-15)"
    - "CR-04 PredictiveMaintenance bare KeyError: state.get('asset_id') + explicit ValueError replaces state['asset_id'] (plan 07-15)"
    - "WR-03 Gateway isoformat() mismatch: body.window_start / body.window_end passed as datetime objects directly to state dict; .isoformat() calls removed from lines 646-647 (plan 07-16)"
    - "WR-04 Pareto grand_total from trimmed rows: grand_total now computed from sum(r[1] for r in sorted_rows) before trimming (plan 07-16)"
    - "CR-05 DowntimeAnalyzer unbounded by_asset + dup quality call: _MAX_BY_ASSET=50, _BY_ASSET_CONCURRENCY=10, asyncio.gather with Semaphore; compute_oee returns 7-tuple including quality_source, eliminating standalone compute_quality_cross_cluster call (plan 07-16)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Start docker compose, invoke /v1/agents/maintenance/maintenance-coach/start, then /v1/agents/maintenance/maintenance-coach/step twice with the same intervention_id"
    expected: "Both step calls must succeed with checkpoint persistence (no ConnectionDoesNotExistError). The saver must remain open across calls because it is injected via lifespan, not opened/closed in _get_graph()."
    why_human: "Requires full docker stack + LangGraph checkpoint runtime to exercise the async context-manager lifetime boundary"
  - test: "Invoke /v1/agents/maintenance/rca-specialist/analyze with a valid problem_statement; inspect audit.actions table BEFORE the supervisor responds"
    expected: "No audit row should appear until supervisor resume (interrupt on first run unwinds the stack before _write_audit). After supervisor resume, exactly one RCA_CHAIN/HITL_SUPERVISOR row should appear with non-empty tool_calls in evidence_panel."
    why_human: "Requires real LangGraph interrupt/resume cycle with real LLM to verify one-row-per-invocation contract and tool_calls_log population"
  - test: "POST /v1/agents/maintenance/downtime-analyzer/report with valid window_start and window_end via the API gateway"
    expected: "Should return OEEReport with correct cumulative_percent values (not forced to 100.0 at last entry). No asyncpg.exceptions.DataError should occur."
    why_human: "Confirms that datetime objects are accepted by asyncpg TIMESTAMPTZ parameters at runtime and that Pareto percentages reflect true dataset coverage"
---

# Phase 07: Maintenance Cluster Verification Report

**Phase Goal:** All four Maintenance cluster agents (PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer) are implemented with C-MAPSS-adapted RUL estimation, 5-Why RCA, humidity-aware modeling, and integration with the asset registry and event store.
**Verified:** 2026-05-23T22:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (plans 07-13 through 07-16)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PredictiveMaintenance estimates RUL for spindle/loom/warper assets using C-MAPSS-adapted model; feature set includes ambient temperature and humidity sensors | VERIFIED | Core ML path intact. CR-03 fixed: `approval_id = None` at agent.py:329; no `uuid4()` fabrication in HITL branch (only `id=uuid4()` and `action_id=uuid4()` remain for record identifiers — correct). CR-04 fixed: `state.get("asset_id")` + explicit `ValueError` at line 171-173. AuditRecord validator updated to allow HITL+None (audit.py). |
| 2 | RCASpecialist generates a 5-Why chain, cites knowledge base sources with provenance, routes corrective action to supervisor-level HITL | VERIFIED | CR-02 fixed: `interrupt()` called directly in `__call__` at line 558; `_write_audit` placed after `interrupt()` return (line 574) — fires only on resume. `_escalate_to_supervisor()` no longer called from `__call__` (only referenced in comment at line 555). WR-05 fixed: `_invoke_react_loop` returns `(content, tool_call_records)` tuple; iterates `final_messages` extracting `getattr(msg, "tool_calls", None)`; `__call__` accumulates via immutable concatenation at line 458; flows into `_write_audit` at line 578. |
| 3 | MaintenanceCoach retrieves step-by-step procedure from RAG store for current repair, tracks MTTR, escalates when technician requests it | VERIFIED | CR-01 fixed: `_get_graph()` raises `RuntimeError("MaintenanceCoach._graph is None...")` if graph not pre-built (line 441-448); all 3 occurrences of `async with AsyncPostgresSaver.from_conn_string` are docstring/string literals — no executable self-compile block exists. WR-02 fixed: `step()` has `skip_audit: bool = False` parameter (line 688); two internal `_write_audit` calls guarded by `if not skip_audit:` (lines 755, 800); `resume_after_help` calls `step(skip_audit=True)` (line 882) then writes exactly one authoritative `hitl_supervisor` row. |
| 4 | DowntimeAnalyzer calculates OEE decomposition (A, P, Q) and produces Pareto of downtime causes from event store | VERIFIED | WR-03 fixed: gateway lines 646-647 pass `body.window_start` / `body.window_end` as `datetime` objects directly — no `.isoformat()` calls (confirmed in maintenance_agents.py). WR-04 fixed: `grand_total = sum(r[1] for r in sorted_rows)` at oee.py line 326 computed before trimming. CR-05 fixed: `_MAX_BY_ASSET=50`, `_BY_ASSET_CONCURRENCY=10`, `asyncio.Semaphore` + `asyncio.gather` at agent.py lines 241/270; `compute_oee` returns 7-tuple including `quality_source`, eliminating duplicate `compute_quality_cross_cluster` call (agent.py:214 confirms no standalone call). |
| 5 | Textile maintenance event taxonomy documented and used consistently across all four agents | VERIFIED (unchanged) | `failure_modes.yaml` extended with 7 reason_codes, `event-taxonomy.md` bilingual, downtime_event_generator reads taxonomy, DowntimeAnalyzer Pareto groups by reason_code. No regression observed. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py` | PredictiveMaintenance LangGraph node | VERIFIED | CR-03: approval_id=None; CR-04: state.get() + ValueError. Core ML path unchanged. |
| `apps/agents/maintenance/rca-specialist/src/mnt_rca_specialist/agent.py` | RCASpecialist ReAct LangGraph node | VERIFIED | CR-02: direct interrupt() in __call__; WR-05: _invoke_react_loop returns tool_call_records tuple. |
| `apps/agents/maintenance/maintenance-coach/src/mnt_maintenance_coach/agent.py` | MaintenanceCoach LangGraph thread | VERIFIED | CR-01: RuntimeError guard replaces self-compile; WR-02: skip_audit=True in resume_after_help. |
| `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py` | OEE A×P×Q + Pareto computation | VERIFIED | WR-04: grand_total from sorted_rows before trimming. |
| `apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py` | DowntimeAnalyzer LangGraph node | VERIFIED | CR-05: _MAX_BY_ASSET=50, asyncio.gather+Semaphore, 7-tuple compute_oee eliminates duplicate quality call. |
| `apps/api-gateway/src/svc_api_gateway/routers/maintenance_agents.py` | FastAPI maintenance router | VERIFIED | WR-03: datetime objects passed directly, .isoformat() removed from state dict lines 646-647. |
| `packages/sft-agents/src/sft_agents/models/audit.py` | AuditRecord validator | VERIFIED | approval_id=None allowed for HITL decisions (pending escalation state); `auto` still requires approval_id=None. |

### Gap-Closure Regression Tests Added

| Test File | Gap Covered | Status |
|-----------|-------------|--------|
| `apps/agents/maintenance/maintenance-coach/tests/test_coach_saver_lifecycle.py` | CR-01, WR-02 | Created — Test A (RuntimeError on missing saver), Test B (single audit row on resume), Test C (integration, requires docker) |
| `apps/agents/maintenance/rca-specialist/tests/test_interrupt_audit_lifecycle.py` | CR-02, WR-05 | Created — Test A (one audit row on resume, not on first run), Test B (tool_calls_log non-empty) |
| `apps/agents/maintenance/predictive-maintenance/tests/test_audit_integrity.py` | CR-03, CR-04 | Created — test_hitl_audit_row_has_null_approval_id, test_missing_asset_id_raises_valueerror_not_keyerror |
| `apps/api-gateway/tests/test_da_report_datetime.py` | WR-03 | Created — 2 tests |
| `apps/agents/maintenance/downtime-analyzer/tests/test_pareto_grand_total.py` | WR-04 | Created |
| `apps/agents/maintenance/downtime-analyzer/tests/test_by_asset_bounds.py` | CR-05 | Created |
| `packages/sft-agents/tests/test_audit_record.py` | CR-03 (AuditRecord change) | Updated — replaced test_hitl_without_approval_id_rejected with two new tests permitting HITL+None |
| `packages/sft-agents/tests/test_audit_constraints.py` | CR-03 (AuditRecord change) | Updated — replaced test_approval_id_required with test_approval_id_null_allowed_for_pending_escalation |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| PredictiveMaintenance agent | sft-ml Ridge model | load_pretrained_model via sft_ml.cmapss.load_model | WIRED | Unchanged from initial verification |
| PredictiveMaintenance agent | NATS maintenance.predict.* | pm-consumer pull_subscribe durable=pm-consumer | WIRED | Unchanged |
| PredictiveMaintenance HITL path | audit.actions | approval_id=None (pending) | WIRED | CR-03 fix: no fabricated UUID; AuditRecord validator permits HITL+None |
| RCASpecialist → interrupt() | LangGraph GraphInterrupt | direct interrupt() call in __call__ at line 558 | WIRED | CR-02 fix confirmed |
| RCASpecialist → _write_audit | RCA_CHAIN audit row after resume | line 574 executes only on resume | WIRED | CR-02 fix: audit fires exactly once per logical invocation |
| RCASpecialist → tool_calls_log | EvidencePanel.tool_calls | _invoke_react_loop tuple return → __call__ accumulation | WIRED | WR-05 fix: non-empty tool_calls flows to audit |
| MaintenanceCoach → AsyncPostgresSaver | LangGraph checkpoint persistence | Injected saver; RuntimeError if not injected | WIRED (requires DI) | CR-01 fix: no self-compile; saver must be injected via lifespan |
| MaintenanceCoach resume_after_help | single audit row | step(skip_audit=True) + explicit _write_audit(hitl_supervisor) | WIRED | WR-02 fix confirmed |
| Gateway → DowntimeAnalyzer | datetime TIMESTAMPTZ parameters | body.window_start/end as datetime objects in state dict | WIRED | WR-03 fix confirmed (lines 646-647) |
| DowntimeAnalyzer oee.compute_pareto | grand_total from all rows | sum(r[1] for r in sorted_rows) before trimming | WIRED | WR-04 fix confirmed |
| DowntimeAnalyzer by_asset | bounded concurrent OEE queries | asyncio.gather + Semaphore(10), cap 50 | WIRED | CR-05 fix confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| PM agent HITL audit path | approval_id | None (pending escalation — not fabricated UUID) | Correct | FIXED — no hollow approval_id |
| DA gateway → asyncpg | window_start/window_end | body.window_start / body.window_end datetime objects | Real | FIXED — asyncpg receives correct type |
| RCA agent._write_audit | tool_calls_log | _invoke_react_loop tuple return, accumulated in __call__ | Real (from LLM messages) | FIXED — evidence panel no longer empty |
| Coach agent._get_graph | saver (AsyncPostgresSaver) | Injected at construction via lifespan | Real (requires DI) | FIXED — no use-after-close; raises clearly if not injected |
| DA oee.compute_pareto | cumulative_percent | grand_total from all sorted_rows before trimming | Correct | FIXED — represents true Pareto coverage |

### Behavioral Spot-Checks

Step 7b: All runnable checks require docker stack (asyncpg, NATS, LangGraph checkpointer). Skipped — no runnable entry points without docker compose.

### Probe Execution

No `probe-*.sh` scripts defined for phase 07. Skipped.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MNT-01 | 07-06, 07-15 | PredictiveMaintenance RUL estimation adapted from C-MAPSS | SATISFIED | CR-03 + CR-04 fixed; core ML path intact; audit integrity restored |
| MNT-02 | 07-07, 07-14 | RCASpecialist 5-Whys + citations from knowledge base | SATISFIED | CR-02 + WR-05 fixed; one-row audit contract restored; evidence panel non-empty |
| MNT-03 | 07-08, 07-13 | MaintenanceCoach step-by-step guidance with HITL + MTTR | SATISFIED | CR-01 + WR-02 fixed; saver lifecycle correct; single audit row on resume |
| MNT-04 | 07-09, 07-16 | DowntimeAnalyzer OEE + MTTR/MTBF + Pareto patterns | SATISFIED | WR-03 + WR-04 + CR-05 fixed; /report endpoint unblocked; Pareto semantics correct; bounded concurrency |
| MNT-05 | 07-02, 07-11 | Maintenance event taxonomy documented and used consistently | SATISFIED | Unchanged — 7 reason_codes in failure_modes.yaml, bilingual event-taxonomy.md |
| MNT-06 | 07-06, 07-08, 07-09 | Integration with asset registry and event store | SATISFIED | PM asset registry lookup intact; DA event store wired; audit chain approval_id=None no longer breaks downstream JOIN forensics |

### Anti-Patterns Resolved

| Gap ID | File | Original Pattern | Resolution |
|--------|------|-----------------|------------|
| CR-01 | maintenance-coach/agent.py | Use-after-close: async with saver closed before graph use | RuntimeError guard; self-compile block removed entirely |
| WR-02 | maintenance-coach/agent.py | Double audit row on resume_after_help | skip_audit=True suppresses internal writes; one authoritative row written |
| CR-02 | rca-specialist/agent.py | Audit write unreachable: interrupt raised before _write_audit | interrupt() called directly; _write_audit after interrupt() return |
| WR-05 | rca-specialist/agent.py | tool_calls_log never populated | _invoke_react_loop returns (content, records) tuple; accumulated in __call__ |
| CR-03 | predictive-maintenance/agent.py | fabricated approval_id=uuid4() in production HITL path | approval_id=None; AuditRecord validator updated |
| CR-04 | predictive-maintenance/agent.py | state["asset_id"] bare KeyError | state.get("asset_id") + explicit ValueError |
| WR-03 | maintenance_agents.py (gateway) | .isoformat() on datetime for asyncpg TIMESTAMPTZ | datetime objects passed directly (lines 646-647) |
| WR-04 | oee.py | grand_total from trimmed[:top_n] | grand_total from sorted_rows before trimming |
| CR-05 | downtime-analyzer/agent.py | Unbounded sequential by_asset + duplicate quality call | _MAX_BY_ASSET=50, asyncio.gather+Semaphore, 7-tuple compute_oee |

### Human Verification Required

**1. MaintenanceCoach Production Saver Lifecycle**

**Test:** Start docker compose, invoke `/v1/agents/maintenance/maintenance-coach/start`, then `/v1/agents/maintenance/maintenance-coach/step` twice with the same intervention_id.
**Expected:** Both step calls must succeed with checkpoint persistence. The saver injected via lifespan must remain open across calls. No `ConnectionDoesNotExistError` should occur. The integration regression test (Test C in `test_coach_saver_lifecycle.py`) covers this but requires docker and is marked `@pytest.mark.integration`.
**Why human:** Requires full docker stack + LangGraph checkpoint runtime to exercise the async context-manager lifetime boundary.

**2. RCASpecialist First-Execution / Resume Audit Row Sequence**

**Test:** Invoke `/v1/agents/maintenance/rca-specialist/analyze` with a valid problem_statement. Inspect `audit.actions` table immediately after the agent suspends at the supervisor interrupt (before supervisor responds). Then send supervisor approval and check audit again.
**Expected:** Zero audit rows before resume; exactly one `RCA_CHAIN` / `HITL_SUPERVISOR` row after resume, with `evidence_panel.tool_calls` non-empty (contains at least one `rag_search` record).
**Why human:** Requires real LangGraph interrupt/resume cycle with real LLM and live PG.

**3. DowntimeAnalyzer /report Endpoint with Real DB**

**Test:** POST `/v1/agents/maintenance/downtime-analyzer/report` with valid `window_start` and `window_end` datetimes via the API gateway.
**Expected:** Returns `OEEReport` without `asyncpg.exceptions.DataError`. Pareto `cumulative_percent` at last entry should reflect true dataset coverage (not forced to 100.0) when fewer than `top_n` reasons account for all downtime.
**Why human:** Confirms asyncpg TIMESTAMPTZ parameter acceptance and Pareto correctness at runtime.

### Gaps Summary

All 9 originally-identified defects (4 critical-runtime + 5 warning-level) have been fixed in the actual source files, verified against the codebase. No gaps remain in the static code analysis.

The 3 human verification items above are carry-over from the initial verification's human-needed section, now re-scoped to confirm the fixes are effective at runtime. These require the docker compose stack and cannot be verified by static analysis.

---

_Initial verification: 2026-05-23T14:00:00Z_
_Re-verification: 2026-05-23T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
