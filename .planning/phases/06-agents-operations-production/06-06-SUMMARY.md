---
phase: 06-agents-operations-production
plan: 06
plan_id: 06-06
subsystem: ops-anomaly-detector
tags: [agent, deterministic, rate-limit, audit, ops-cluster, langgraph-node]
requires: [06-00, 06-01, 06-02, 06-04, 06-05]
provides:
  - AnomalyDetector            # apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py
  - AGENT_ID                   # "anomaly-detector"
  - CLUSTER                    # "ops"
  - select_baseline            # baseline.py — machine-override aware lookup
  - BaselineRegistry           # baseline.py — registry type alias
  - AnomalyScanRequest         # models.py — out-of-LangGraph caller input model
  - AnomalyScanResponse        # models.py — out-of-LangGraph caller output model
affects:
  - apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/__init__.py  # re-exports
  - apps/agents/ops/anomaly-detector/pyproject.toml                        # +workspace deps
tech-stack:
  added: []
  patterns:
    - Async-first agent class with keyword-only constructor + injectable collaborators (PATTERNS Shared Pattern 7)
    - State-delta return shape, no input-state mutation (LangGraph reducer convention)
    - Deterministic audit row (`Decision.AUTO` / `Decision.SUPPRESSED` + `ActionType.ANOMALY_ALERT`) via `AuditWriter.write(AuditRecord)`
    - Synthetic `ToolCall` inside `EvidencePanel.tool_calls[0]` carries the suppressed payload (LogEventTool convention from Plan 06-05)
    - `RateLimiter.check_and_emit(action_type)` per-anomaly gate; agent never silent-drops (always writes audit row)
    - `select_baseline` per-machine override precedence over per-asset-family baseline (D-AD-02)
key-files:
  created:
    - apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py
    - apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/baseline.py
    - apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/models.py
    - apps/agents/ops/anomaly-detector/tests/conftest.py
    - apps/agents/ops/anomaly-detector/tests/test_baseline.py
  modified:
    - apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/__init__.py
    - apps/agents/ops/anomaly-detector/pyproject.toml
    - apps/agents/ops/anomaly-detector/tests/test_anomaly_detector.py
    - apps/agents/ops/anomaly-detector/tests/test_rate_limit.py
decisions:
  - "AnomalyDetector reuses the existing `Decision.AUTO` enum value (not a new `Decision.ANOMALY_ALERT`) because `Decision` enumerates audit-row outcomes (auto / hitl_* / suppressed / logged / ...) — `ANOMALY_ALERT` is the *action-type* dimension. Suppressed alerts use `Decision.SUPPRESSED` per Plan 06-02 + migration 007."
  - "Per-machine override implemented via key reuse: `baselines` dict accepts both `(asset_family, sensor_id)` and `(machine_id, sensor_id)` keys. `select_baseline` checks the machine key first. This avoids a second YAML loader / a new schema and keeps the baseline registry a single, immutable injected mapping (Pitfall §3 single-source-of-truth)."
  - "Agent never silently drops anomalies: even when the 12/h rate limit fires, a `Decision.SUPPRESSED` audit row is written with the original anomaly payload inside `EvidencePanel.tool_calls[0].args`. Audit consumers can therefore reconstruct the full anomaly stream from the audit row alone."
  - "`AnomalyDetector.__init__` is keyword-only: `pool`, `baselines`, `asset_registry`, `audit_writer` are mandatory; `query_tool` and `rate_limiter` default to production constructors (`QueryTimescaleTool()` / `RateLimiter(pool, agent_id='anomaly-detector', limit=12)`) but can be overridden for tests. `audit_writer` has no sane default — passing `None` raises `ValueError` at init time."
  - "Tests use pure-Python mocks (mock_pool / mock_query_tool / mock_audit_writer) instead of testcontainers PG. The integration coverage of the RateLimiter SQL path is already supplied by `packages/sft-agents/tests/runtime/test_rate_limiter.py` (Plan 06-02). Repeating it here would add Docker dependency without strengthening the agent's contract."
  - "Plan 06-06 listed `test_evidence_panel.py` as a Wave 0 stub for plan 06-13; left unchanged (still `pytest.skip`)."
metrics:
  duration_minutes: 25
  completed: 2026-05-23
  tests_added: 18
  tests_skipped: 1   # evidence_panel placeholder for 06-13
  files_added: 5
  files_modified: 4
---

# Phase 06 Plan 06: AnomalyDetector Summary

The AnomalyDetector LangGraph node — first of the 4 OPS-cluster agents — ships at `apps/agents/ops/anomaly-detector/`. It is fully deterministic (no LLM, no NATS consumer, no JetStream subscription): a single `async __call__(state) -> dict` pulls a `window_minutes` slice of sensor history per asset, compares each sample against the per-asset-family (or per-machine override) baseline from `anomaly_baselines.yaml`, gates each candidate through the 12-alert/h `RateLimiter`, and writes one `audit.actions` row per anomaly with the original payload preserved inside `EvidencePanel.tool_calls`.

This plan also validates the agent skeleton pattern that plans 06-07 (ProductionPlanner), 06-08 (QualityInspector), and 06-10 (OperatorAssistant) will follow.

## What landed

### `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py` — `AnomalyDetector`

**Constructor** (keyword-only):

```python
AnomalyDetector(
    *,
    pool: asyncpg.Pool,                              # mandatory — RateLimiter dep
    baselines: BaselineRegistry,                     # mandatory — Plan 06-04 dict
    asset_registry: Sequence[Asset],                 # mandatory — sft-assets
    audit_writer: AuditWriter,                       # mandatory — Plan 04-02 writer
    query_tool: QueryTimescaleTool | None = None,    # default: QueryTimescaleTool()
    rate_limiter: RateLimiter | None = None,         # default: RateLimiter(pool, ...)
)
```

`None` for any mandatory dep raises `ValueError` at init time (defensive boundary).

**Node body** `async __call__(state: Mapping[str, Any]) -> dict[str, Any]`:

1. `window_minutes = int(state.get("window_minutes", 15))` — the default the plan calls for.
2. `now = datetime.now(UTC)`; `time_range = (now - timedelta(minutes=window_minutes), now)` — tz-aware UTC (T-V6-naive-datetime).
3. For each `asset in self._assets`:
   - `df = await self._query._arun(asset_id=asset.asset_id, time_range=time_range)`.
   - For each DataFrame row → `select_baseline(self._baselines, asset_family=asset.asset_family.value, sensor_id=row.sensor_id, machine_id=asset.asset_id)`:
     - `None` → structlog `missing_baseline` + skip row.
     - `in_band` → skip row.
     - Out-of-band → build `Anomaly(...)` and call `(allowed, count) = await self._limiter.check_and_emit("ANOMALY_ALERT")`.
       - `allowed=True` → write audit row `Decision.AUTO` + `ActionType.ANOMALY_ALERT`, append to result.
       - `allowed=False` → write audit row `Decision.SUPPRESSED` + `ActionType.ANOMALY_ALERT`, structlog `anomaly_suppressed`, skip emission.
4. Return `{"anomalies": list[Anomaly]}` — a LangGraph state delta. Never mutates `state`.

### `baseline.py` — `select_baseline`

```python
def select_baseline(
    baselines: BaselineRegistry,
    *,
    asset_family: str,
    sensor_id: str,
    machine_id: str | None = None,
) -> AnomalyBaseline | None
```

Lookup priority: `(machine_id, sensor_id)` (override) → `(asset_family, sensor_id)` (family) → `None`. Empty `asset_family` / `sensor_id` raises `ValueError` so silently-passed garbage cannot mask a missing baseline.

### `models.py` — out-of-LangGraph I/O contracts

- `AnomalyScanRequest` (`frozen=True, extra="forbid"`): `window_minutes: int ∈ [1, 180] = 15`, `triggered_by: Literal["scheduler","operator","agent"] = "scheduler"`.
- `AnomalyScanResponse` (`frozen=True, extra="forbid"`): `anomalies: list[Anomaly]`, `suppressed_count: int >= 0`.

### `pyproject.toml`

Adds workspace deps `sft-agents`, `sft-assets`, `sft-domain`, `sft-tools` plus runtime `asyncpg`, `pandas`, `pydantic`, `structlog` and `[project.optional-dependencies] dev` for `pytest`, `pytest-asyncio`, `pytest-mock`. Also adds `[tool.uv.sources]` workspace entries and `[tool.pytest.ini_options] asyncio_mode = "auto"`.

## Audit decision matrix used

| Outcome | `decision` | `action_type` | `evidence_panel.tool_calls[0]` |
|---|---|---|---|
| Emit anomaly | `Decision.AUTO` | `ActionType.ANOMALY_ALERT` | synthetic `ToolCall(name="anomaly_detect", args={asset_id, sensor_id, value, baseline_low, baseline_high, severity, rate_count})` |
| Suppress anomaly | `Decision.SUPPRESSED` | `ActionType.ANOMALY_ALERT` | same `ToolCall` shape — payload preserved for forensic reconstruction |

`decision_actor`, `motivation`, `approval_id` are all `None` (no HITL involvement); `budget_snapshot` is the zero snapshot (no LLM tokens spent).

## Tests

**Total: 18 passed + 1 skipped (evidence_panel placeholder for plan 06-13).**

`tests/test_baseline.py` (5 tests):
- `test_is_within_band_inclusive` — band edges inclusive (must-haves truth: in-band → no anomaly).
- `test_severity_for_uses_mapping` — minor/major/critical chosen by deviation magnitude.
- `test_select_baseline_machine_override_wins` — per-machine override precedes family baseline.
- `test_select_baseline_returns_none_when_missing` — missing → `None` (caller logs).
- `test_select_baseline_rejects_invalid_inputs` — empty family / sensor → `ValueError`.

`tests/test_anomaly_detector.py` (9 tests):
- `test_happy_path_emits_anomaly` — out-of-band value → 1 Anomaly + 1 audit (`Decision.AUTO` / `ANOMALY_ALERT`).
- `test_no_false_positive_on_normal_loom_vibration` — in-band value=0.5 → 0 anomalies, 0 audit rows (success criterion #3).
- `test_per_machine_override_applied` — `(LOOM-01, warp_tension)` override band `[0.3, 0.6]` flags value=0.7 even though family band `[0.2, 0.8]` would accept it.
- `test_missing_baseline_logs_warning_no_crash` — empty baseline registry → no exception, no anomaly.
- `test_handles_multiple_assets_in_one_scan` — 3 assets, 2 with anomalies → 2 returned in scan order.
- `test_window_minutes_parameter_passed_to_timescale_tool` — `state.window_minutes=30` → `_arun(time_range=(now-30min, now))`.
- `test_window_minutes_defaults_to_15` — missing key → 15-minute window.
- `test_state_delta_only_no_mutation` — returned dict keys = `{"anomalies"}`; input state untouched.
- `test_default_collaborators_when_omitted` — constructor builds defaults for `query_tool` / `rate_limiter`.

`tests/test_rate_limit.py` (4 tests):
- `test_12h_window_caps_emission` — seed COUNT=12 → 5 new candidates all suppressed; 5 `Decision.SUPPRESSED` audit rows; `{"anomalies": []}`.
- `test_11_existing_plus_1_new_emits` — seed COUNT=11 → exactly 1 emission (12th allowed).
- `test_suppressed_audit_row_includes_original_payload` — asserts `evidence_panel.tool_calls[0].args` carries `asset_id` / `sensor_id` / `value`.
- `test_below_limit_emits_normally` — COUNT=0 → 3 candidates all emit (sanity around the cap).

## Verification commands

```bash
# Tests
nx run ops-anomaly-detector:test
# → 18 passed, 1 skipped in 1.36s

# Lint
nx run ops-anomaly-detector:lint
# → All checks passed!

# Module import
uv run python -c "from ops_anomaly_detector import AnomalyDetector; print('OK', AnomalyDetector)"
# → OK <class 'ops_anomaly_detector.agent.AnomalyDetector'>
```

## Threat-model coverage (mitigations applied)

| Threat | Disposition | Where mitigated |
|---|---|---|
| `T-V6-baseline` | mitigate | Plan 06-04 schema validation on YAML load; this plan does not load YAML directly — receives the immutable registry by injection. |
| `T-V6-throttle` | mitigate | `RateLimiter.check_and_emit` per anomaly + `Decision.SUPPRESSED` audit row for excess (no silent drop). |
| `T-V6-naive-datetime` | mitigate | `datetime.now(UTC)`; `Anomaly.timestamp` and `AuditRecord.ts` both reject naive datetimes; `_ensure_utc` helper normalises DataFrame timestamps. |
| `T-V6-audit-double-write` | mitigate | On-demand only — no NATS consumer, no retry path. |
| `T-V6-acl-bypass` | mitigate | Reads only `sensor_events` via `QueryTimescaleTool` (no PII). |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Plan said `Decision.ANOMALY_ALERT` but `Decision` enum has no such value.**
- **Found during:** Task 2 implementation.
- **Issue:** Plan body referenced `Decision.ANOMALY_ALERT` which does not exist — the enum dimensions are `(decision, action_type)`; `ANOMALY_ALERT` is the action-type.
- **Fix:** Used `Decision.AUTO` (emit) / `Decision.SUPPRESSED` (rate-limited) combined with `ActionType.ANOMALY_ALERT` — consistent with Plan 06-02 PRD and migration 007.
- **Files modified:** `src/ops_anomaly_detector/agent.py`
- **Commit:** `0327c00`

### Auth gates

None — the agent injects collaborators (pool / audit_writer / query_tool); no external auth boundary crossed during implementation.

## Known Stubs

None.

## TDD Gate Compliance

- **RED gate:** `2859abc` — `test(06-06): add failing tests for AnomalyDetector agent + baseline helpers` (16 failed on `ModuleNotFoundError`, 2 passed on Pydantic-only baseline behaviors, 1 skipped placeholder).
- **GREEN gate:** `0327c00` — `feat(06-06): implement AnomalyDetector agent (deterministic, rate-limited)` (18 passed, 1 skipped).

No REFACTOR commit was necessary — ruff auto-fix was applied to the same files as the GREEN implementation in a single commit.

## Self-Check

- Created files exist:
  - `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/agent.py` ✓
  - `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/baseline.py` ✓
  - `apps/agents/ops/anomaly-detector/src/ops_anomaly_detector/models.py` ✓
  - `apps/agents/ops/anomaly-detector/tests/conftest.py` ✓
  - `apps/agents/ops/anomaly-detector/tests/test_baseline.py` ✓
- Commits exist on `worktree-agent-a91007594a2036b68`:
  - `2859abc` (RED) ✓
  - `0327c00` (GREEN) ✓

**## Self-Check: PASSED**
