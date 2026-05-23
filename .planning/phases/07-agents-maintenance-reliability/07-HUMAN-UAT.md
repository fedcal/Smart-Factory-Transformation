---
status: partial
phase: 07-agents-maintenance-reliability
source: [07-VERIFICATION.md]
started: 2026-05-23T00:00:00Z
updated: 2026-05-23T00:00:00Z
---

## Current Test

[awaiting human testing — requires docker compose stack: PostgreSQL/TimescaleDB, NATS, LangGraph checkpointer]

## Tests

### 1. MaintenanceCoach production saver lifecycle
expected: Start docker compose, invoke `/v1/agents/maintenance/maintenance-coach/start`, then `/v1/agents/maintenance/maintenance-coach/step` twice with the same intervention_id. Both step calls succeed with checkpoint persistence — no `ConnectionDoesNotExistError` on the second call (confirms CR-01 fix: injected long-lived saver).
result: [pending]

### 2. RCASpecialist interrupt/resume audit sequence
expected: Invoke `/v1/agents/maintenance/rca-specialist/analyze` with a valid problem_statement. Zero audit rows before supervisor responds; exactly one `hitl_supervisor` row after resume; `evidence_panel.tool_calls` is non-empty with real rag_search/traverse_graph records (confirms CR-02 + WR-05 fixes).
result: [pending]

### 3. DowntimeAnalyzer /report endpoint with real DB
expected: POST `/v1/agents/maintenance/downtime-analyzer/report` with valid window_start/window_end datetimes via the API gateway. Returns OEEReport with no `asyncpg.DataError`; Pareto `cumulative_percent` reflects true coverage (not always 100.0 at last entry) (confirms WR-03 + WR-04 fixes).
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
