---
phase: 08-agents-knowledge-training
plan: "04"
subsystem: shift-handover
tags: [knowledge, HITL, dual-signoff, NATS, langgraph, interrupt, TRN-03, TRN-05]
dependency_graph:
  requires: ["08-00a", "08-00b", "08-02"]
  provides: ["ShiftHandover agent node", "NATS sh-consumer"]
  affects: ["08-08 api-gateway routing", "audit.actions HANDOVER_SIGNOFF rows"]
tech_stack:
  added: []
  patterns:
    - "Dual-supervisor sequential HITL (novel Phase 8 — no prior codebase precedent): interrupt(outgoing) → write SIGNOFF#1 → interrupt(incoming) → write SIGNOFF#2 → write DRAFT"
    - "CR-02: interrupt() called directly in __call__, audit writes strictly after resume"
    - "CR-03: approval_id=None for pending HITL rows (never fabricate UUID)"
    - "CR-01: saver injected at construction, RuntimeError guard if None"
    - "Pattern G: ImportError fallback for langgraph.types.interrupt"
    - "NATS JetStream durable pull consumer with injectable invoke_fn for testability"
    - "ShiftWindow Pydantic validation as trust boundary guard (T-08-07)"
key_files:
  created:
    - apps/agents/knowledge/shift-handover/src/trn_shift_handover/agent.py
    - apps/agents/knowledge/shift-handover/src/trn_shift_handover/consumer.py
  modified:
    - apps/agents/knowledge/shift-handover/src/trn_shift_handover/__init__.py
    - apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py
decisions:
  - "Dual-supervisor HITL test strategy: simulate each interrupt boundary in a fresh __call__ invocation rather than replaying LangGraph checkpoint — simpler and correct for unit isolation"
  - "HANDOVER_DRAFT row written after both resumes (post-second-interrupt) per RF-2: draft persisted only once fully signed off, never before any resume"
  - "3 total audit writes per full handover execution: 2 HANDOVER_SIGNOFF + 1 HANDOVER_DRAFT"
  - "consumer.py uses injectable invoke_fn pattern (not direct graph reference) for testability without live NATS server"
metrics:
  duration: "25min"
  completed_date: "2026-05-24"
  tasks: 2
  files: 4
---

# Phase 8 Plan 04: ShiftHandover HITL Node + NATS Consumer Summary

**One-liner:** Dual-supervisor sequential HITL node (interrupt→SIGNOFF#1→interrupt→SIGNOFF#2→DRAFT) with NATS shift.boundary.> consumer for scheduled trigger.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Contract tests for dual-supervisor HITL | ae68af9 | test_dual_signoff.py |
| 1 (GREEN) | ShiftHandover node + __init__ exports | 00458a4 | agent.py, __init__.py, test_dual_signoff.py |
| 2 | NATS shift.boundary consumer | 7bcdfa9 | consumer.py |

## What Was Built

### Task 1: ShiftHandover dual-supervisor HITL node (SC-1, D-SH-03)

`agent.py` implements `ShiftHandover` with the novel Phase 8 dual-supervisor sequential sign-off pattern:

```
__call__(state):
  1. compile HandoverReport via aggregator (LLM-free, Pitfall §4)
  2. interrupt(outgoing) → raises on first exec; returns on first resume
  3. write HANDOVER_SIGNOFF #1 (outgoing, approval_id=None)
  4. interrupt(incoming)  → raises on first resume; returns on second resume
  5. write HANDOVER_SIGNOFF #2 (incoming, approval_id=None)
  6. write HANDOVER_DRAFT (once, after both sign-offs)
  7. return {"handover_report": report, "shift_status": "signed_off"}
```

CR constraints enforced:
- **CR-02**: no audit writes on first execution (before any resume)
- **CR-03**: `approval_id=None` on all HANDOVER_SIGNOFF rows
- **CR-01**: `saver=None` raises `RuntimeError` at construction

### Task 2: NATS shift.boundary consumer (D-SH-01)

`consumer.py` implements `run_sh_consumer` subscribing to `shift.boundary.>` on `KNOWLEDGE_STREAM` (durable: `sh-consumer`). On each boundary event:
- Parses JSON payload → validates as `ShiftWindow` (T-08-07: rejects naive datetimes, inverted windows)
- Builds state dict with `target_agent="shift-handover"` and validated window
- Calls injectable `invoke_fn` (testable without live NATS)
- ack on success; nak(delay=5) on invoke failure; poison-pill ack on invalid payload

## Verification

```
$ python -m pytest apps/agents/knowledge/shift-handover/tests/test_dual_signoff.py -q
....                                                                     [100%]
4 passed in 0.24s
```

All 4 contract tests pass:
- `test_first_handover_signoff_written_after_first_resume` — exactly 1 SIGNOFF row after first resume
- `test_second_handover_signoff_written_after_second_resume` — exactly 2 SIGNOFF rows (outgoing + incoming)
- `test_no_audit_rows_on_first_execution_before_interrupt` — CR-02: 0 writes on first exec
- `test_approval_id_is_none_for_pending_hitl_rows` — CR-03: all rows have approval_id=None

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test simulation strategy for dual-interrupt boundary**
- **Found during:** Task 1 test refinement
- **Issue:** Initial test design used cumulative interrupt_call_count across multiple agent.__call__ invocations, but without LangGraph checkpointing each call replays from the top, causing the simulation to be incorrect (SIGNOFF rows counted from wrong invocation)
- **Fix:** Changed test strategy to simulate each interrupt boundary in a fresh agent instance per scenario. Phase A tests "first exec" (interrupt#1 raises, 0 writes). Phase B tests "first resume" (interrupt#1 returns, interrupt#2 raises, 1 write). Full completion tests both interrupts returning in one call (2 SIGNOFF + 1 DRAFT = 3 writes total).
- **Files modified:** `tests/test_dual_signoff.py`
- **Commit:** 00458a4

**2. [Rule 2 - Critical Function] HANDOVER_DRAFT row written after second resume**
- **Found during:** Task 1 implementation
- **Decision:** Per RF-2 architecture: HANDOVER_DRAFT persisted only once the handover is fully signed off (after second interrupt returns). This ensures the draft is never written before any approval, consistent with CR-02 and the audit trail integrity goal.
- **Files modified:** `agent.py`
- **Commit:** 00458a4

## Threat Surface Scan

No new threat surface beyond what the plan's `<threat_model>` documented:
- T-08-06 (Repudiation): mitigated by 2 HANDOVER_SIGNOFF rows with motivation per supervisor, approval_id=None (CR-03)
- T-08-07 (Tampering): mitigated by ShiftWindow Pydantic validation in consumer.py _parse_boundary_payload()
- T-08-08 (DoS/SLA): aggregation path is LLM-free (Pitfall §4) — deterministic counts under 30s

## Known Stubs

None — agent.py and consumer.py are fully wired. The narrative_summary LLM enrichment in `_compile_report` is best-effort (non-blocking failure path) and gracefully degrades to empty string.

## Self-Check: PASSED

- `apps/agents/knowledge/shift-handover/src/trn_shift_handover/agent.py` FOUND
- `apps/agents/knowledge/shift-handover/src/trn_shift_handover/consumer.py` FOUND
- `apps/agents/knowledge/shift-handover/src/trn_shift_handover/__init__.py` FOUND (exports ShiftHandover)
- Commits ae68af9, 00458a4, 7bcdfa9 all present in git log
- 4 contract tests GREEN
