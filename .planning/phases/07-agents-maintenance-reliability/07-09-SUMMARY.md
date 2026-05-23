---
phase: 07-agents-maintenance-reliability
plan: "09"
plan_id: "07-09"
subsystem: maintenance-agents
tags: [downtime-analyzer, oee, pareto, nats-consumer, cross-cluster, timescaledb, asyncpg, tdd]
dependency_graph:
  requires: [07-00, 07-01, 07-04, 07-05]
  provides: [mnt-downtime-analyzer-package, downtime-event-repository, oee-computation, da-consumer]
  affects: [07-10-api-gateway, 07-12-e2e-scenarios]
tech_stack:
  added:
    - "mnt-downtime-analyzer Python package (asyncpg, nats-py, structlog, pydantic)"
  patterns:
    - "Repository pattern: DowntimeEventRepository wraps all maintenance.downtime_events SQL"
    - "Cross-cluster read-only: QualityVerdictReader queries audit.actions (Phase 6, no schema change)"
    - "PG-first dual-write in da-consumer (insert_event THEN audit write THEN ack)"
    - "In-memory sft-assets registry via asyncio.to_thread for validate_asset_exists"
    - "quality_source tuple return from compute_quality_cross_cluster for audit observability"
key_files:
  created:
    - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/models.py
    - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/repository.py
    - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/consumer.py
    - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py
    - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py
    - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/metadata.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_repository.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_consumer.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_oee.py
    - apps/agents/maintenance/downtime-analyzer/tests/test_pareto.py
  modified:
    - apps/agents/maintenance/downtime-analyzer/pyproject.toml
    - apps/agents/maintenance/downtime-analyzer/project.json
    - apps/agents/maintenance/downtime-analyzer/README.md
    - apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/__init__.py
decisions:
  - "sft-assets validate_asset_exists uses in-memory YAML registry via asyncio.to_thread (no PG table for assets)"
  - "JSONB path deviation: Phase 6 QualityInspector stores score/severity, not good_parts/total_parts — COALESCE chain handles both"
  - "CAGG vs raw hypertable: always raw hypertable scan for PoC; CAGG path documented but not wired"
  - "quality_source tuple return added to compute_quality_cross_cluster for audit-friendly forensic tracking"
  - "ON CONFLICT (event_id, timestamp) for idempotent hypertable inserts (composite PK from migration 008)"
metrics:
  duration: "11 minutes"
  completed: "2026-05-23T19:45:00Z"
  tasks_completed: 4
  files_created: 10
  files_modified: 4
  tests_written: 36
  tests_passing: 36
  tests_skipped: 1
---

# Phase 7 Plan 09: DowntimeAnalyzer Agent Summary

Shipped the DowntimeAnalyzer agent: NATS durable consumer `da-consumer` on `maintenance.downtime.>`, asyncpg persistence to migration-008 hypertable, OEE A×P×Q decomposition with cross-cluster audit-first + sim-textile fallback, and Pareto top-N computation.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Scaffold package + failing tests (RED) | 73db8f6 |
| 2a | models.py — OEEReport + ParetoEntry + OEEMetrics + ReportRequest | 3955082 |
| 2b | repository.py — DowntimeEventRepository + QualityVerdictReader | bdf7de0 |
| 2c | consumer.py — da-consumer + stubs | 18f6cec |
| 3 | oee.py — compute_oee/availability/performance/quality/pareto (GREEN) | 66105cc |
| 4 | agent.py — DowntimeAnalyzer + _write_audit + _write_event_audit | 790e832 |

## Key Implementation Decisions

### sft-assets validate_asset_exists

The sft-assets registry is a YAML file loaded with `lru_cache` (no PG table). The `validate_asset_exists` method uses `asyncio.to_thread` to keep the async interface consistent without blocking the event loop. This was verified by reading `packages/sft-assets/src/sft_assets/_loader.py`.

### JSONB Path for QualityVerdictReader (T-V7-da-cross-cluster-jsonb-drift)

Verified against Phase 6 QualityInspector source at `apps/agents/ops/quality-inspector/src/ops_quality_inspector/agent.py` lines 230-247.

**Finding:** Phase 6 stores `result={"score": verdict.score, "severity": verdict.severity}` in the EvidencePanel ToolCall — NOT `good_parts/total_parts` as specified in the 07-09 plan interface section.

**Resolution:** The `SQL_QUALITY_CROSS_CLUSTER` constant uses a COALESCE chain:
- Tries `result->>'good_parts'` first (future-compatible if Phase 6 ships explicit good_parts)
- Falls back to `ROUND(result->>'score'::NUMERIC * 1000)` with `total_sum = 1000`

This is documented in repository.py module docstring. The test `test_quality_verdict_reader_returns_parsed_values` seeds an audit row with `good_parts/total_parts` in the `result` dict (which the COALESCE first branch handles correctly).

### CAGG vs Raw Hypertable

Per D-DA-03: when window is exactly hour-aligned, `maintenance.oee_hourly` CAGG (5min refresh) gives O(1) lookup. For PoC, all paths use raw hypertable scan via `DowntimeEventRepository.fetch_window`. The CAGG preference is documented in `oee.py` module docstring with the rationale that exposing the CAGG path requires additional SQL wiring. Phase 11 can implement the CAGG-first strategy.

### quality_source Tuple Return (Plan Extension)

The plan's Task 4 action note said "return a tuple (quality, source) instead of just float" for `compute_quality_cross_cluster`. This was implemented: the function returns `tuple[float, QualitySource]` where `QualitySource = Literal["audit", "simfallback", "no-data"]`. Tests assert the source marker alongside the quality value.

### OEE Computation

- **Availability:** `(planned - downtime) / planned`, clamped to [0,1]. Default planned = window length (100% PoC assumption documented).
- **Performance:** `output / target` from production_state_reader; fallback 1.0 + structlog WARN.
- **Quality:** Cross-cluster audit first (score-based proxy), sim fallback, then 1.0 default.
- **OEE:** `A × P × Q` with `OEEReport` model cross-validator asserting product within 1e-6.

### Consumer PG-first Dual-Write

Per T-V7-da-audit-write-failure: `insert_event` is the operational truth. Audit write failure logs + acks (no infinite redelivery). PG insert failure triggers `nak(delay=5)` for JetStream retry.

### Subject/Payload Mismatch

`maintenance.downtime.LOOM-01` subject with `asset_id=LOOM-02` payload: consumer logs WARN and proceeds with **payload** value (source of truth). Documented in consumer.py docstring.

## SQL Parameterization (T-V5-sql Gate)

All SQL ClassVar constants verified by `test_sql_uses_parameterization` meta-test:
- No `%s`, `%(`, or `{...}` placeholders
- All constants contain at least one `$N` asyncpg placeholder
- Meta-test passes at CI time without Docker

## OEE.P Production State Field Names

The `production_state.py` (Phase 6 06-09) tracks `current_dye_lot_id` and rotation state — it does NOT expose `good_meters/target_meters` directly. The reader interface was designed to accept any async callable returning `(good, target)` tuple. The production_state_reader is wired at agent init time (07-10 api-gateway). For tests, AsyncMock stubs return controlled tuples.

## Per-event Audit Policy

- DOWNTIME_VERDICT: written via `_write_event_audit` callback in consumer.py. In production wiring (07-10), `write_event_audit=analyzer._write_event_audit` is passed.
- OEE_REPORT: written directly by `generate_report` after building the OEEReport.
- Both use `Decision.AUTO` (no HITL for analytics agents per HITL_TIER_DEFAULT="none").

## Test Results

36 tests passing, 1 skipped (test_evidence_panel.py Wave 0 stub — 07-11 plan):

- `test_sql_uses_parameterization`: T-V5-sql gate PASSED
- `test_sql_constants_are_strings`: all ClassVars are str PASSED
- 10 consumer tests: all PASSED (happy path, PG-first ordering, poison-pill, nak-on-error, stop_event, CancelledError, mismatch, subscribe params)
- 11 OEE tests: all PASSED (availability math, performance fallback, quality cross-cluster, sim fallback, no-data, oee integration)
- 9 Pareto tests: all PASSED (empty, ordering, cumulative, top_n, round-trip JSON, validation)
- 12 integration tests: DESELECTED (testcontainers — run in full CI with Docker)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Stub files created for Tasks 2/3 to enable TDD progression**
- **Found during:** Task 2 (agent.py / oee.py / metadata.py not yet implemented)
- **Issue:** `__init__.py` imports from agent.py/oee.py/metadata.py which don't exist yet
- **Fix:** Created minimal stub files (NotImplementedError bodies) so that consumer/repository tests could run in isolation as intended by the TDD flow
- **Files modified:** agent.py (stub → full Task 4), oee.py (stub → full Task 3), metadata.py (stub → full Task 4)

**2. [Rule 1 - Schema Discovery] JSONB path deviation: score vs good_parts**
- **Found during:** Task 2 (repository.py implementation)
- **Issue:** Plan interface spec referenced `good_parts/total_parts` in QUALITY_VERDICT result dict, but Phase 6 QualityInspector actually stores `score/severity`
- **Fix:** COALESCE chain tries good_parts first (forward-compatible), falls back to score×1000 approximation. Documented in repository.py module docstring.
- **Commit:** bdf7de0

**3. [Rule 2 - Missing OEE.Q source observability] quality_source tuple return added**
- **Found during:** Task 3 / Task 4 integration
- **Issue:** Plan's Task 4 action note explicitly requested `compute_quality_cross_cluster` return `(quality, source)` not just float — not yet in Task 3 stub
- **Fix:** Extended return type to `tuple[float, QualitySource]`. Updated test_oee.py assertions to unpack tuple. test_consumer.py unaffected (no direct oee call).
- **Commit:** 66105cc

## Known Stubs

None — all stubs from Wave 0 are replaced with real implementations:
- test_repository.py: fully implemented (Wave 0 placeholder replaced)
- test_consumer.py: fully implemented (Wave 0 placeholder replaced)
- test_oee.py: fully implemented (Wave 0 placeholder replaced)
- test_pareto.py: fully implemented (Wave 0 placeholder replaced)
- test_evidence_panel.py: remains Wave 0 stub (belongs to plan 07-11 docs)

## Threat Flags

No new threat surface beyond what was planned in the 07-09 threat model.

## Self-Check: PASSED

Files created/exist:
- apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/models.py: FOUND
- apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/repository.py: FOUND
- apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/oee.py: FOUND
- apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/consumer.py: FOUND
- apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/agent.py: FOUND
- apps/agents/maintenance/downtime-analyzer/src/mnt_downtime_analyzer/metadata.py: FOUND

Commits verified:
- 73db8f6: scaffold + failing tests
- 3955082: models.py
- bdf7de0: repository.py
- 18f6cec: consumer.py + stubs
- 66105cc: oee.py + test_oee.py + test_pareto.py
- 790e832: agent.py (full) + metadata.py (full)
