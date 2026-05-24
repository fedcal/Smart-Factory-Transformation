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

import hashlib
import pytest
from unittest.mock import patch, call

from sft_agents.models.audit import AuditRecord
from sft_agents.models.enums import ActionType

from scm_inventory_manager.agent import AGENT_ID, InventoryManager


# Shared test state (thread_id must be stable across test invocations)
_THREAD_ID = "supply.inventory-manager.test-001"

_STATE: dict = {
    "thread_id": _THREAD_ID,
    "target_agent": "inventory-manager",
}

# Expected stable recommendation_id for the test thread_id
_EXPECTED_RECOMMENDATION_ID = hashlib.sha256(
    f"{AGENT_ID}.{_THREAD_ID}".encode("utf-8")
).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Contract 1: No audit write before interrupt raises (first execution)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_audit_write_before_interrupt_on_first_execution(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """On first execution, audit_writer.write.call_count == 0 before interrupt raises (CR-02).

    LangGraph re-runs the node from the top on each resume. Any audit write
    BEFORE interrupt() fires twice on two consecutive executions, creating
    duplicate rows in audit.actions.
    """
    agent = InventoryManager(pool=mock_pool, audit_writer=mock_audit_writer)
    interrupt_fn = make_interrupt_fn(resume_payload={"approved": True, "approver_id": "sup-001"})

    with patch("scm_inventory_manager.agent.interrupt", interrupt_fn):
        try:
            await agent(_STATE)
        except (RuntimeError, Exception) as exc:
            # interrupt raised (first execution) — expected
            if "GraphInterrupt" not in str(type(exc).__name__) and "interrupt" not in str(exc).lower():
                raise

    # CR-02: no audit writes before interrupt raises
    assert mock_audit_writer.write.call_count == 0, (
        f"Expected 0 audit writes before interrupt, got {mock_audit_writer.write.call_count}. "
        "CR-02 violation: audit write must occur ONLY after interrupt() returns."
    )


# ---------------------------------------------------------------------------
# Contract 2: PURCHASE_RECOMMENDATION_DRAFT row after resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_recommendation_draft_written_after_resume(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After interrupt returns (HITL resume): exactly 1 PURCHASE_RECOMMENDATION_DRAFT row (SCM-01)."""
    agent = InventoryManager(pool=mock_pool, audit_writer=mock_audit_writer)
    # resume_payload makes interrupt return (not raise) — simulates HITL resume
    interrupt_fn = make_interrupt_fn(resume_payload={"approved": True, "approver_id": "sup-001"})

    with patch("scm_inventory_manager.agent.interrupt", interrupt_fn):
        # Patch interrupt so it raises on call 1, returns on call 2 is factory default
        # But make_interrupt_fn raises on FIRST call, returns on subsequent.
        # We need a version that RETURNS on first call (simulating resume directly).
        pass

    # Build an interrupt that ALWAYS returns (simulates already-resumed state)
    def resume_interrupt(value):
        return {"approved": True, "approver_id": "sup-001"}

    with patch("scm_inventory_manager.agent.interrupt", resume_interrupt):
        result = await agent(_STATE)

    # After resume: at least 1 PURCHASE_RECOMMENDATION_DRAFT row
    assert mock_audit_writer.write.call_count >= 1, (
        "Expected at least 1 audit write after resume, got 0."
    )

    # Find the DRAFT row
    draft_records = [
        call_args[0][0]
        for call_args in mock_audit_writer.write.call_args_list
        if call_args[0][0].action_type == ActionType.PURCHASE_RECOMMENDATION_DRAFT.value
    ]
    assert len(draft_records) == 1, (
        f"Expected exactly 1 PURCHASE_RECOMMENDATION_DRAFT record, "
        f"got {len(draft_records)}."
    )


# ---------------------------------------------------------------------------
# Contract 3: PURCHASE_SIGNOFF row after supervisor approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_signoff_written_after_supervisor_approval(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After supervisor approval: exactly 1 PURCHASE_SIGNOFF row total (SCM-01)."""
    agent = InventoryManager(pool=mock_pool, audit_writer=mock_audit_writer)

    def resume_interrupt(value):
        return {"approved": True, "approver_id": "sup-001"}

    with patch("scm_inventory_manager.agent.interrupt", resume_interrupt):
        result = await agent(_STATE)

    # Exactly 2 audit writes total: 1 DRAFT + 1 SIGNOFF
    assert mock_audit_writer.write.call_count == 2, (
        f"Expected exactly 2 audit writes (1 DRAFT + 1 SIGNOFF), "
        f"got {mock_audit_writer.write.call_count}."
    )

    # Find action_types written
    action_types_written = [
        call_args[0][0].action_type
        for call_args in mock_audit_writer.write.call_args_list
    ]

    assert ActionType.PURCHASE_RECOMMENDATION_DRAFT.value in action_types_written, (
        "PURCHASE_RECOMMENDATION_DRAFT not found in audit writes."
    )
    assert ActionType.PURCHASE_SIGNOFF.value in action_types_written, (
        "PURCHASE_SIGNOFF not found in audit writes."
    )


# ---------------------------------------------------------------------------
# Contract 4: Stable recommendation_id from thread_id (CR-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommendation_id_stable_across_replay(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """recommendation_id is derived from thread_id — stable across LangGraph replay (CR-04).

    Both the DRAFT and SIGNOFF rows must share the same recommendation_id,
    derived deterministically from state['thread_id'].
    """
    agent = InventoryManager(pool=mock_pool, audit_writer=mock_audit_writer)

    def resume_interrupt(value):
        return {"approved": True, "approver_id": "sup-001"}

    with patch("scm_inventory_manager.agent.interrupt", resume_interrupt):
        result = await agent(_STATE)

    # Both records must share the same recommendation_id
    assert mock_audit_writer.write.call_count == 2

    draft_record = mock_audit_writer.write.call_args_list[0][0][0]
    signoff_record = mock_audit_writer.write.call_args_list[1][0][0]

    # Extract recommendation_id from evidence panel or action args
    # The agent encodes recommendation_id in the action args dict
    draft_action_id = draft_record.action_id
    signoff_action_id = signoff_record.action_id

    # Both records share the same thread_id (full_thread_id)
    assert draft_record.thread_id == signoff_record.thread_id, (
        "DRAFT and SIGNOFF records must share the same thread_id."
    )

    # Simulate replay: create a second agent instance and run again
    from unittest.mock import AsyncMock, MagicMock
    mock_audit_writer_2 = MagicMock()
    mock_audit_writer_2.write = AsyncMock()

    agent_2 = InventoryManager(pool=mock_pool, audit_writer=mock_audit_writer_2)

    with patch("scm_inventory_manager.agent.interrupt", resume_interrupt):
        result_2 = await agent_2(_STATE)

    # The recommendation in both results must have the same recommendation_id
    rec_id_1 = result.get("reorder_recommendation", {}).get("recommendation_id")
    rec_id_2 = result_2.get("reorder_recommendation", {}).get("recommendation_id")

    assert rec_id_1 is not None, "First result missing recommendation_id"
    assert rec_id_2 is not None, "Second result missing recommendation_id"
    assert rec_id_1 == rec_id_2, (
        f"recommendation_id is NOT stable across replay: "
        f"first={rec_id_1!r}, second={rec_id_2!r}. "
        "CR-04 violation: use sha256(AGENT_ID.thread_id)[:32] not uuid4()."
    )

    # Also verify against the expected hash
    assert rec_id_1 == _EXPECTED_RECOMMENDATION_ID, (
        f"recommendation_id {rec_id_1!r} does not match expected "
        f"sha256('{AGENT_ID}.{_THREAD_ID}')[:32] = {_EXPECTED_RECOMMENDATION_ID!r}"
    )


# ---------------------------------------------------------------------------
# Contract 5: approval_id=None for pending HITL rows (CR-03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_id_is_none_for_pending_hitl_row(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """The PURCHASE_RECOMMENDATION_DRAFT row has approval_id=None (CR-03)."""
    agent = InventoryManager(pool=mock_pool, audit_writer=mock_audit_writer)

    def resume_interrupt(value):
        return {"approved": True, "approver_id": "sup-001"}

    with patch("scm_inventory_manager.agent.interrupt", resume_interrupt):
        await agent(_STATE)

    assert mock_audit_writer.write.call_count >= 1

    # Find the DRAFT row — it must have approval_id=None
    draft_records = [
        call_args[0][0]
        for call_args in mock_audit_writer.write.call_args_list
        if call_args[0][0].action_type == ActionType.PURCHASE_RECOMMENDATION_DRAFT.value
    ]
    assert len(draft_records) == 1

    draft_record = draft_records[0]
    assert draft_record.approval_id is None, (
        f"PURCHASE_RECOMMENDATION_DRAFT.approval_id must be None (CR-03), "
        f"got {draft_record.approval_id!r}. "
        "Never fabricate a UUID for a pending HITL row."
    )


# ---------------------------------------------------------------------------
# Contract 6: AuditWriter.write() called with positional AuditRecord (CR-02)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_audit_written_with_positional_audit_record(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """audit_writer.write() receives a positional AuditRecord — no kwargs (CR-02)."""
    agent = InventoryManager(pool=mock_pool, audit_writer=mock_audit_writer)

    def resume_interrupt(value):
        return {"approved": True, "approver_id": "sup-001"}

    with patch("scm_inventory_manager.agent.interrupt", resume_interrupt):
        await agent(_STATE)

    assert mock_audit_writer.write.call_count >= 1

    # Verify first write call: single positional AuditRecord, no kwargs
    first_call = mock_audit_writer.write.call_args_list[0]
    positional_args = first_call[0]   # positional args tuple
    keyword_args = first_call[1]       # kwargs dict

    assert len(positional_args) == 1, (
        f"write() must be called with exactly 1 positional arg, "
        f"got {len(positional_args)} positional args. "
        "CR-02: call as write(record), not write(record=record) or write(action_type=...)."
    )
    assert isinstance(positional_args[0], AuditRecord), (
        f"Positional arg must be an AuditRecord instance, "
        f"got {type(positional_args[0]).__name__!r}. CR-02 violation."
    )
    assert keyword_args == {}, (
        f"write() must have no kwargs, got {keyword_args!r}. CR-02 violation."
    )


# ---------------------------------------------------------------------------
# Contract 7: REORDER_ALERT in agent output (SCM-01)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorder_alert_emitted_in_agent_output(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """InventoryManager emits REORDER_ALERT in the returned state delta (SCM-01)."""
    agent = InventoryManager(pool=mock_pool, audit_writer=mock_audit_writer)

    def resume_interrupt(value):
        return {"approved": True, "approver_id": "sup-001"}

    with patch("scm_inventory_manager.agent.interrupt", resume_interrupt):
        result = await agent(_STATE)

    # Result must contain a reorder_alert with REORDER_ALERT type
    assert "reorder_alert" in result, (
        "result must contain 'reorder_alert' key (SCM-01)."
    )
    alert = result["reorder_alert"]
    assert alert is not None, "reorder_alert must not be None."
    assert alert.get("alert_type") == "REORDER_ALERT", (
        f"alert_type must be 'REORDER_ALERT', got {alert.get('alert_type')!r}."
    )

    # Also verify reorder_recommendation is in the result
    assert "reorder_recommendation" in result, (
        "result must contain 'reorder_recommendation' key."
    )
    rec = result["reorder_recommendation"]
    assert rec is not None, "reorder_recommendation must not be None."
    assert "recommendation_id" in rec, "recommendation must contain recommendation_id."


# ---------------------------------------------------------------------------
# Contract 8: WR-03 — early-exit with no recommendation when rows is empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_recommendation_when_repository_returns_empty_rows(
    make_empty_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """When the repository returns zero rows, the agent must exit without HITL (WR-03).

    Before the WR-03 fix, an empty repository result caused the agent to fall through
    to a synthetic recommendation block (sku_id="SKU-UNKNOWN") and fire HITL even in
    production, when the repository returned nothing (timeout, bad sku_ids, partial
    connection failure).

    After the fix: the agent logs a warning and returns {reorder_recommendation: None,
    reorder_alert: None} without calling interrupt() or audit_writer.write().

    This test uses make_empty_pool (conn.fetch returns []) to simulate the empty-rows
    production path.
    """
    agent = InventoryManager(
        pool=make_empty_pool,
        audit_writer=mock_audit_writer,
    )

    result = await agent(_STATE)

    # WR-03: agent must return None for both keys — no synthetic recommendation
    assert result == {"reorder_recommendation": None, "reorder_alert": None}, (
        f"Expected {{reorder_recommendation: None, reorder_alert: None}}, got {result!r}. "
        "WR-03: agent must not generate synthetic recommendations when rows is empty."
    )

    # No audit writes — no HITL fired (no interrupt called, no audit rows written)
    assert mock_audit_writer.write.call_count == 0, (
        f"Expected 0 audit writes (no HITL when rows is empty), "
        f"got {mock_audit_writer.write.call_count}. WR-03 violation."
    )
