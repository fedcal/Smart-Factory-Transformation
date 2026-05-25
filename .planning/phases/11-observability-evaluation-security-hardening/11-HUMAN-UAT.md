---
status: partial
phase: 11-observability-evaluation-security-hardening
source: [11-VERIFICATION.md]
started: 2026-05-25T00:00:00Z
updated: 2026-05-25T00:00:00Z
---

## Current Test

[awaiting human testing — requires live stack: Docker + GitHub CI]

## Tests

### 1. Grafana dashboards live
expected: `docker compose -f infra/compose/obs.yml up` brings up Grafana on :3001 with the 3 provisioned dashboards (agent-kpis, factory-kpis, cost-dashboard) loaded and datasources (Prometheus/Tempo) wired.
result: [pending]

### 2. Langfuse trace "phase11" end-to-end
expected: after invoking an agent endpoint with the stack up, a single correlated trace tagged "phase11" appears in Langfuse with LLM token counts, latency, and HITL metadata (SC-1).
result: [pending]

### 3. Migration 014 on TimescaleDB
expected: `make migrate-timescale` applies 014 idempotently; audit_actions CHECK includes RESTRICTED_DOC_ACCESS; lockstep with enums.py.
result: [pending]

### 4. DeepEval CI gate blocks a real PR
expected: a PR that degrades the RAG eval dataset above thresholds is blocked by the non-skippable CI eval step (SC-2) on GitHub.
result: [pending]

### 5. Crafted prompt-injection PDF E2E
expected: ingesting a malicious PDF through the live pipeline produces Qdrant chunks with injection patterns stripped; no agent action is influenced (SC-3).
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
