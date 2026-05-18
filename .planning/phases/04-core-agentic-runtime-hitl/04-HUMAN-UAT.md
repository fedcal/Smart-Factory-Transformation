---
status: partial
phase: 04-core-agentic-runtime-hitl
source: [04-VERIFICATION.md]
started: 2026-05-18T17:56:14Z
updated: 2026-05-18T17:56:14Z
---

## Current Test

[awaiting human testing — all 5 items deferred to Phase 10/11 infrastructure work]

## Tests

### 1. Live PG migration run on production-grade PG instance
expected: All four Phase 4 migrations (002–005) apply cleanly + idempotent re-run no-op; agent_role created NOLOGIN; REVOKE UPDATE/DELETE on audit.actions enforced
result: pending
note: Operator-approved during plan 04-02 execution; documented here for milestone audit traceability.

### 2. Live NATS AUDIT_STREAM bootstrap against a real JetStream node
expected: scripts/nats-bootstrap-streams.py exit 0 first run; second run idempotent (BadRequestError → update_stream); AUDIT_STREAM declared with 90-day retention
result: pending
note: Production NATS deployment is a Phase 11 concern; testcontainer tests pass.

### 3. Langfuse v3 callback emits spans against a live Langfuse server
expected: supervisor/cluster/agent spans visible in Langfuse UI; metadata field langfuse_session_id propagates via config['metadata']
result: pending
note: Langfuse server self-hosting deferred to Phase 11.

### 4. vLLM Hermes tool-calling smoke against real GPU-served Qwen2.5-14B-Instruct-AWQ
expected: vLLM serve command from docs/architecture/llm-serving.md runs; agent issues function-call request and receives a structured tool response
result: pending
note: Requires GPU; documentation is verified; behaviour cannot be validated in CI.

### 5. Full HITL UI walkthrough by an operator persona
expected: Operator clicks approve in (future) UI, decision flows REST → PG row update → NATS resolved publish → AgentState resume from checkpoint → audit row written with motivation
result: pending
note: Phase 10 UI not yet built; flow currently verified via REST + asyncpg in tests/e2e/test_hitl_cycle.py.

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
