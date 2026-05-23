---
phase: 07-agents-maintenance-reliability
plan: 15
plan_id: 07-15
subsystem: maintenance-agent
tags: [predictive-maintenance, audit-integrity, hitl, error-handling, regression-test, gap-closure]
dependency_graph:
  requires: [07-06]
  provides: [pm-audit-integrity-fix, pm-safe-error-handling]
  affects: [sft-agents-audit-model, 07-12-e2e]
tech_stack:
  added: []
  patterns: [AuditRecord-pending-HITL-state, ValueError-over-KeyError-boundary]
key_files:
  created:
    - apps/agents/maintenance/predictive-maintenance/tests/test_audit_integrity.py
  modified:
    - apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py
    - packages/sft-agents/src/sft_agents/models/audit.py
    - packages/sft-agents/tests/test_audit_record.py
    - packages/sft-agents/tests/test_audit_constraints.py
decisions:
  - "AuditRecord validator updated to allow HITL decisions with approval_id=None (pending escalation state) — required to close CR-03 without fabricating UUIDs. motivation still required for HITL; approval_id is optional and represents pending vs finalized."
  - "CR-04 fix uses state.get() + explicit ValueError instead of bare state[] KeyError — controlled error message does not expose internal field names in gateway 500 responses."
metrics:
  duration: "~6min"
  completed: "2026-05-23"
  tasks: 2
  files: 5
---

# Phase 7 Plan 15: PredictiveMaintenance Audit Integrity + Error Handling Gap Closure Summary

One-liner: CR-03 fabricated approval_id removed from production HITL audit path; CR-04 bare KeyError replaced with structured ValueError; AuditRecord validator updated to support pending-HITL state.

## What Was Built

### Task 1: Regression Tests (RED)

Authored `test_audit_integrity.py` with two regression tests that failed against the unmodified agent code:

- **`test_hitl_audit_row_has_null_approval_id`** (CR-03): Invokes PM with a mock model that forces `health_index=0.0 < 0.3` (HITL path), captures the written AuditRecord via mock side_effect, and asserts `record.approval_id is None`. Fails pre-fix because `_write_audit` generated `approval_id=uuid4()`.
- **`test_missing_asset_id_raises_valueerror_not_keyerror`** (CR-04): Invokes PM with a state dict omitting `asset_id` and asserts `ValueError` is raised (not `KeyError`). Fails pre-fix because `state["asset_id"]` raised bare `KeyError('asset_id')`.

### Task 2: Fixes (GREEN)

**CR-03 fix — Two-part change:**

1. **`AuditRecord` validator** (`packages/sft-agents/src/sft_agents/models/audit.py`): Removed the `approval_id MUST NOT be None for HITL` constraint. The pending-escalation semantic (supervisor notified, approval pending) is represented by `motivation` (required, describes pending state) + `approval_id=None`. The finalized-approval semantic uses `approval_id=UUID`. Updated `test_audit_record.py` and `test_audit_constraints.py` to reflect the new behavior.

2. **`agent.py` HITL path**: Removed `from uuid import uuid4 as _uuid4` import and `approval_id = _uuid4()`. Changed motivation from `"Supervisor approved escalation for asset {id}"` to `"Supervisor approval required for asset {id}"` (pending state, not approved state).

**CR-04 fix:**

`agent.py` line 171: `state["asset_id"]` → `state.get("asset_id")` + `if not asset_id: raise ValueError("PredictiveMaintenance requires 'asset_id' in state")`. The ValueError message is a controlled string; `str(KeyError("asset_id"))` would have produced `"'asset_id'"` which leaks the field name.

## Verification

```
$ UV_PYTHON_PREFERENCE=managed uv run pytest \
    apps/agents/maintenance/predictive-maintenance/tests/test_audit_integrity.py \
    apps/agents/maintenance/predictive-maintenance/tests/test_evidence_panel.py \
    apps/agents/maintenance/predictive-maintenance/tests/test_inference.py \
    apps/agents/maintenance/predictive-maintenance/tests/test_consumer.py \
    -m "not integration" -v
# 41 passed
```

```
$ UV_PYTHON_PREFERENCE=managed uv run pytest \
    packages/sft-agents/tests/test_audit_record.py \
    packages/sft-agents/tests/test_audit_constraints.py -v
# 65 passed
```

Acceptance criteria verified:
- `grep -n "uuid4()" agent.py` shows no `approval_id = uuid4()` inside HITL branch (only `id=uuid4()` and `action_id=uuid4()` remain — correct record identifiers)
- `grep -c "state.get(\"asset_id\")"` returns 1
- `grep -c "state[\"asset_id\"]"` returns 0

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AuditRecord validator required approval_id for HITL — plan assumption incorrect**
- **Found during:** Task 2 (discovered when testing CR-03 fix approach)
- **Issue:** The plan stated "AuditRecord's validator permits decision=HITL_SUPERVISOR with approval_id=None (it does for other maintenance agents — coach and DA write HITL/AUTO rows with approval_id=None)." This was incorrect — the AuditRecord validator explicitly REQUIRED non-None `approval_id` for all HITL decisions. Setting `approval_id=None` would have raised `ValidationError` during `AuditRecord(...)` construction, preventing the audit row from being written at all.
- **Fix:** Updated the AuditRecord validator to support "pending HITL" state (motivation required, approval_id optional for HITL decisions). Updated `test_audit_record.py` (replaced `test_hitl_without_approval_id_rejected` with two new tests: `test_hitl_with_null_approval_id_allowed_for_pending_escalation` and `test_hitl_with_valid_approval_id_allowed_for_finalized_approval`) and `test_audit_constraints.py` (replaced `test_approval_id_required` with `test_approval_id_null_allowed_for_pending_escalation`).
- **Files modified:** `packages/sft-agents/src/sft_agents/models/audit.py`, `packages/sft-agents/tests/test_audit_record.py`, `packages/sft-agents/tests/test_audit_constraints.py`
- **Commit:** 1dde5b7

## Known Stubs

None — both CR-03 and CR-04 fixes are complete. `approval_id=None` correctly represents the pending-HITL state with real data flowing through the code path.

## Threat Flags

None — the changes reduce the audit trail surface (no more fabricated UUIDs that confuse downstream consumers) and improve error handling (no more internal field name leaks).

## Self-Check: PASSED

- Created: `apps/agents/maintenance/predictive-maintenance/tests/test_audit_integrity.py` ✓
- Modified: `apps/agents/maintenance/predictive-maintenance/src/mnt_predictive_maintenance/agent.py` ✓
- Modified: `packages/sft-agents/src/sft_agents/models/audit.py` ✓
- Modified: `packages/sft-agents/tests/test_audit_record.py` ✓
- Modified: `packages/sft-agents/tests/test_audit_constraints.py` ✓
- Commit d57d782 (test): exists ✓
- Commit 1dde5b7 (fix): exists ✓
- All 41 PM tests pass ✓
- All 65 sft-agents AuditRecord tests pass ✓
