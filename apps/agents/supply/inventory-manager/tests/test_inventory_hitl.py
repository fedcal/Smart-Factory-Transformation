"""Contract tests for InventoryManager HITL interrupt-then-audit lifecycle (SCM-01, CR-02/CR-04).

CONTRACT: interrupt-then-audit ordering + stable-id-from-thread_id:
  1. On first run (initial node execution):
     - interrupt() is called BEFORE any audit write
     - audit_writer.write.call_count == 0 before interrupt raises
  2. On resume (after HITL approval):
     - Exactly 1 PURCHASE_RECOMMENDATION_DRAFT row written
     - Then exactly 1 PURCHASE_SIGNOFF row written after sign-off
     - recommendation_id is STABLE across replay (derived from thread_id, NOT uuid4 — CR-04)
  3. approval_id is None on the pending HITL row (CR-03)
  4. audit_writer.write() called with a positional AuditRecord, not kwargs (CR-02)
  5. REORDER_ALERT emitted in agent output (SCM-01)

Phase 8 anti-bug guardrails encoded here:
  - CR-02: audit write AFTER interrupt() returns (not before — no double-write on replay)
  - CR-03: approval_id=None for pending HITL rows
  - CR-04: stable ID from thread_id hash (never uuid4() inline)

Implementation target: scm_inventory_manager.agent.InventoryManager
(Wave 2-3 plan: 09-02)
"""

from __future__ import annotations

import pytest


# Shared test state (thread_id must be stable across test invocations)
_THREAD_ID = "supply.inventory-manager.test-001"

_STATE: dict = {
    "thread_id": _THREAD_ID,
    "target_agent": "inventory-manager",
}


# ---------------------------------------------------------------------------
# Contract 1: No audit write before interrupt raises (first execution)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_audit_write_before_interrupt_on_first_execution(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """On first execution, audit_writer.write.call_count == 0 before interrupt raises (CR-02).

    LangGraph re-runs the node from the top on each resume. Any audit write
    BEFORE interrupt() fires twice on two consecutive executions, creating
    duplicate rows in audit.actions.

    Implementation target: scm_inventory_manager.agent.InventoryManager.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-02) — contract (CR-02): "
        "On first execution, interrupt() raises BEFORE any audit_writer.write() call. "
        "Patch 'scm_inventory_manager.agent.interrupt' with a function that raises "
        "GraphInterrupt on first call; assert audit_writer.write.call_count == 0 "
        "after the GraphInterrupt is caught."
    )


# ---------------------------------------------------------------------------
# Contract 2: PURCHASE_RECOMMENDATION_DRAFT row after resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_recommendation_draft_written_after_resume(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After interrupt returns (HITL resume): exactly 1 PURCHASE_RECOMMENDATION_DRAFT row (SCM-01).

    The DRAFT row records the pending recommendation before supervisor sign-off.
    The action_type must be ActionType.PURCHASE_RECOMMENDATION_DRAFT.

    Implementation target: scm_inventory_manager.agent.InventoryManager.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-02) — contract: after interrupt() returns (first resume), "
        "audit_writer.write called once with a positional AuditRecord whose "
        "action_type == ActionType.PURCHASE_RECOMMENDATION_DRAFT.value. "
        "Patch 'scm_inventory_manager.agent.interrupt' to return on first call."
    )


# ---------------------------------------------------------------------------
# Contract 3: PURCHASE_SIGNOFF row after supervisor approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_signoff_written_after_supervisor_approval(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After supervisor approval: exactly 1 PURCHASE_SIGNOFF row total (SCM-01).

    The SIGNOFF row confirms procurement approval. Together with the DRAFT row,
    exactly 2 audit writes occur: 1 DRAFT + 1 SIGNOFF (or single combined write
    per implementation design — the contract is that PURCHASE_SIGNOFF is present).

    Implementation target: scm_inventory_manager.agent.InventoryManager.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-02) — contract: after full HITL lifecycle "
        "(interrupt raises then returns), audit.actions contains exactly 1 "
        "PURCHASE_RECOMMENDATION_DRAFT + 1 PURCHASE_SIGNOFF row. "
        "Both must use the same stable recommendation_id."
    )


# ---------------------------------------------------------------------------
# Contract 4: Stable recommendation_id from thread_id (CR-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommendation_id_stable_across_replay(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """recommendation_id is derived from thread_id — stable across LangGraph replay (CR-04).

    Phase 8 critical bug: uuid4() inline re-generates a new ID on every node
    execution. After resume, the SIGNOFF row has a different ID from the DRAFT row,
    making cross-row correlation in audit.actions impossible.

    Contract: both the DRAFT and SIGNOFF rows must share the same recommendation_id,
    derived deterministically from state['thread_id'] (e.g. via hashlib.sha256).

    NEVER: recommendation_id = str(uuid4())  ← generates new ID on replay
    ALWAYS: recommendation_id = sha256(f"{AGENT_ID}.{thread_id}").hexdigest()[:32]

    Implementation target: scm_inventory_manager.agent.InventoryManager._stable_id
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-02) — contract (CR-04): "
        "thread_id='supply.inventory-manager.test-001' must produce the SAME "
        "recommendation_id on two separate __call__ invocations (simulating replay). "
        "Search test for 'thread_id' to confirm this contract is enforced."
    )


# ---------------------------------------------------------------------------
# Contract 5: approval_id=None for pending HITL rows (CR-03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_id_is_none_for_pending_hitl_row(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """The PURCHASE_RECOMMENDATION_DRAFT row has approval_id=None (CR-03).

    Phase 8 critical bug: fabricating a UUID for approval_id at write time
    creates a non-null value for a field that only becomes meaningful after
    the external HITL system records an approval decision.

    Implementation target: scm_inventory_manager.agent.InventoryManager.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-02) — contract (CR-03): "
        "The AuditRecord written for PURCHASE_RECOMMENDATION_DRAFT must have "
        "approval_id=None. Never fabricate a UUID for a pending HITL row."
    )


# ---------------------------------------------------------------------------
# Contract 6: AuditWriter.write() called with positional AuditRecord (CR-02)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_written_with_positional_audit_record(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """audit_writer.write() receives a positional AuditRecord — no kwargs (CR-02).

    Phase 8 critical bug: TrainingCoach called write(action_type=..., decision=...)
    with keyword arguments → TypeError: write() got unexpected keyword argument.

    Contract: call_args_list[0][0][0] is an AuditRecord instance (positional arg 0).
    call_args_list[0][1] must be an empty dict (no kwargs passed).

    Implementation target: scm_inventory_manager.agent.InventoryManager.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-02) — contract (CR-02): "
        "audit_writer.write must be called as write(record) — single positional AuditRecord. "
        "Verify: call_args_list[0][0][0] is AuditRecord instance, "
        "call_args_list[0][1] == {} (empty kwargs)."
    )


# ---------------------------------------------------------------------------
# Contract 7: REORDER_ALERT in agent output (SCM-01)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_alert_emitted_in_agent_output(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """InventoryManager emits REORDER_ALERT in the returned state delta (SCM-01).

    The agent's output state must include an alert or recommendation that downstream
    agents and the gateway can route. The REORDER_ALERT signals that procurement
    action is pending.

    Implementation target: scm_inventory_manager.agent.InventoryManager.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-02) — contract (SCM-01): "
        "result from InventoryManager.__call__(state) must contain a REORDER_ALERT "
        "key or an alert with action_type=ActionType.REORDER_ALERT. "
        "The alert is what triggers the HITL procurement approval flow."
    )
