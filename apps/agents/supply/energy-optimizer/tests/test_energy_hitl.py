"""Contract tests for EnergyOptimizer HITL interrupt-then-audit lifecycle (SCM-02, CR-02/CR-04).

CONTRACT: interrupt-then-audit ordering for ENERGY_PROPOSAL then ENERGY_SIGNOFF:
  1. On first run (initial node execution):
     - interrupt() is called BEFORE any audit write
     - audit_writer.write.call_count == 0 before interrupt raises
  2. On resume (after HITL approval):
     - Exactly 1 ENERGY_PROPOSAL row written (the energy schedule proposal)
     - Exactly 1 ENERGY_SIGNOFF row written after supervisor sign-off
     - proposal_id is STABLE across replay (derived from thread_id, NOT uuid4 — CR-04)
  3. approval_id is None on the pending HITL row (CR-03)
  4. audit_writer.write() called with a positional AuditRecord, not kwargs (CR-02)

Phase 8 anti-bug guardrails encoded here:
  - CR-02: audit write AFTER interrupt() returns (no double-write on replay)
  - CR-03: approval_id=None for pending HITL rows
  - CR-04: stable ID from thread_id hash (never uuid4() inline)

Implementation target: scm_energy_optimizer.agent.EnergyOptimizer
(Wave 2-3 plan: 09-03)
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sft_agents.models.audit import AuditRecord
from sft_agents.models.enums import ActionType

from scm_energy_optimizer.agent import EnergyOptimizer


# Shared test state
_THREAD_ID = "supply.energy-optimizer.test-001"

_STATE: dict = {
    "thread_id": _THREAD_ID,
    "target_agent": "energy-optimizer",
}


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

    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    interrupt_fn = make_interrupt_fn()
    agent = EnergyOptimizer(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_energy_optimizer.agent.interrupt", interrupt_fn):
        try:
            await agent(dict(_STATE))
        except (RuntimeError, Exception) as exc:
            # On first call, interrupt raises (GraphInterrupt or RuntimeError fallback)
            # Verify no audit write happened before the raise
            assert mock_audit_writer.write.call_count == 0, (
                f"Expected 0 audit writes before interrupt raised, "
                f"got {mock_audit_writer.write.call_count}. "
                f"Exception was: {exc}"
            )


# ---------------------------------------------------------------------------
# Contract 2: ENERGY_PROPOSAL row after resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_energy_proposal_written_after_resume(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After interrupt returns (HITL resume): exactly 1 ENERGY_PROPOSAL row (SCM-02).

    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    # interrupt_fn: first call raises, second call returns resume payload
    interrupt_fn = make_interrupt_fn(resume_payload={"approved": True, "approver_id": "sup-001"})
    agent = EnergyOptimizer(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_energy_optimizer.agent.interrupt", interrupt_fn):
        # Second call simulates resume: interrupt returns instead of raising
        # We call the agent twice to simulate first-run + resume
        # In LangGraph, this is the node being re-executed after HITL approval.
        # For the test: call once with interrupt that will return (not raise).
        # The factory's second call returns payload.
        # Simulate resume by calling with second call returning (call_count[0] starts at 0,
        # first call raises; we catch that, then call again with same interrupt — 2nd call returns).
        try:
            await agent(dict(_STATE))
        except (RuntimeError, Exception):
            pass  # First call raises

        # Reset audit write count to isolate resume behavior
        mock_audit_writer.write.reset_mock()

        # Second call (resume): interrupt returns payload
        await agent(dict(_STATE))

    # After resume: exactly 1 ENERGY_PROPOSAL row
    proposal_calls = [
        call
        for call in mock_audit_writer.write.call_args_list
        if (
            len(call[0]) > 0
            and isinstance(call[0][0], AuditRecord)
            and call[0][0].action_type == ActionType.ENERGY_PROPOSAL.value
        )
    ]
    assert len(proposal_calls) == 1, (
        f"Expected exactly 1 ENERGY_PROPOSAL write after resume, "
        f"got {len(proposal_calls)}. All calls: {mock_audit_writer.write.call_args_list}"
    )


# ---------------------------------------------------------------------------
# Contract 3: ENERGY_SIGNOFF row after supervisor approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_energy_signoff_written_after_supervisor_approval(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After supervisor approval: ENERGY_SIGNOFF row present in audit (SCM-02).

    Together: 1 ENERGY_PROPOSAL + 1 ENERGY_SIGNOFF. Both share the same stable proposal_id.
    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    interrupt_fn = make_interrupt_fn(resume_payload={"approved": True, "approver_id": "sup-001"})
    agent = EnergyOptimizer(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_energy_optimizer.agent.interrupt", interrupt_fn):
        try:
            await agent(dict(_STATE))
        except (RuntimeError, Exception):
            pass  # First call raises

        mock_audit_writer.write.reset_mock()
        await agent(dict(_STATE))  # Resume call

    all_calls = mock_audit_writer.write.call_args_list
    action_types = [
        call[0][0].action_type
        for call in all_calls
        if len(call[0]) > 0 and isinstance(call[0][0], AuditRecord)
    ]

    assert ActionType.ENERGY_PROPOSAL.value in action_types, (
        f"Expected ENERGY_PROPOSAL in audit rows. Got: {action_types}"
    )
    assert ActionType.ENERGY_SIGNOFF.value in action_types, (
        f"Expected ENERGY_SIGNOFF in audit rows. Got: {action_types}"
    )
    assert len(all_calls) == 2, (
        f"Expected exactly 2 audit writes (PROPOSAL + SIGNOFF), got {len(all_calls)}"
    )


# ---------------------------------------------------------------------------
# Contract 4: Stable proposal_id from thread_id (CR-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_proposal_id_stable_across_replay(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """proposal_id is derived from thread_id — stable across LangGraph replay (CR-04).

    Both ENERGY_PROPOSAL and ENERGY_SIGNOFF rows must share the same proposal_id,
    derived deterministically from state['thread_id'] via hashlib.sha256.

    NEVER: proposal_id = str(uuid4())  ← re-generates on every replay
    ALWAYS: proposal_id = sha256(f"{AGENT_ID}.{thread_id}").hexdigest()[:32]

    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer._stable_id
    """
    agent = EnergyOptimizer(pool=mock_pool, audit_writer=mock_audit_writer)

    # Compute expected stable id using the same formula as the agent
    import hashlib
    from scm_energy_optimizer.metadata import AGENT_ID

    expected_id = hashlib.sha256(
        f"{AGENT_ID}.{_THREAD_ID}".encode("utf-8")
    ).hexdigest()[:32]

    # Run two separate resume calls (simulating replay) — both must use the same id
    for _run in range(2):
        interrupt_fn = make_interrupt_fn(resume_payload={"approved": True, "approver_id": "sup-001"})
        mock_audit_writer.write.reset_mock()

        with patch("scm_energy_optimizer.agent.interrupt", interrupt_fn):
            try:
                await agent(dict(_STATE))
            except (RuntimeError, Exception):
                pass  # First call raises
            await agent(dict(_STATE))  # Resume call

        # Check all proposal_id fields in the written records
        for call in mock_audit_writer.write.call_args_list:
            if len(call[0]) > 0 and isinstance(call[0][0], AuditRecord):
                record = call[0][0]
                # The proposal_id is encoded in the action args
                if record.action_type in (
                    ActionType.ENERGY_PROPOSAL.value,
                    ActionType.ENERGY_SIGNOFF.value,
                ):
                    # Extract proposal_id from the ProposedAction args via evidence_panel summary
                    assert expected_id in record.evidence_panel.input_summary, (
                        f"Expected stable proposal_id={expected_id} in audit record "
                        f"input_summary, got: {record.evidence_panel.input_summary!r}"
                    )


# ---------------------------------------------------------------------------
# Contract 5: approval_id=None for pending HITL rows (CR-03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_id_is_none_for_pending_energy_proposal(
    mock_pool,
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """The ENERGY_PROPOSAL row has approval_id=None (CR-03).

    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    interrupt_fn = make_interrupt_fn(resume_payload={"approved": True, "approver_id": "sup-001"})
    agent = EnergyOptimizer(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_energy_optimizer.agent.interrupt", interrupt_fn):
        try:
            await agent(dict(_STATE))
        except (RuntimeError, Exception):
            pass

        mock_audit_writer.write.reset_mock()
        await agent(dict(_STATE))  # Resume call

    # Check ENERGY_PROPOSAL row has approval_id=None
    for call in mock_audit_writer.write.call_args_list:
        if len(call[0]) > 0 and isinstance(call[0][0], AuditRecord):
            record = call[0][0]
            if record.action_type == ActionType.ENERGY_PROPOSAL.value:
                assert record.approval_id is None, (
                    f"Expected approval_id=None for pending ENERGY_PROPOSAL, "
                    f"got {record.approval_id!r}"
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
    """audit_writer.write() receives a positional AuditRecord — no kwargs (CR-02).

    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    interrupt_fn = make_interrupt_fn(resume_payload={"approved": True, "approver_id": "sup-001"})
    agent = EnergyOptimizer(pool=mock_pool, audit_writer=mock_audit_writer)

    with patch("scm_energy_optimizer.agent.interrupt", interrupt_fn):
        try:
            await agent(dict(_STATE))
        except (RuntimeError, Exception):
            pass

        mock_audit_writer.write.reset_mock()
        await agent(dict(_STATE))  # Resume call

    assert mock_audit_writer.write.call_count >= 1, (
        "Expected at least 1 audit write after resume"
    )

    for call in mock_audit_writer.write.call_args_list:
        # CR-02: positional argument check
        assert len(call[0]) >= 1, (
            f"Expected positional AuditRecord argument, got args={call[0]}"
        )
        assert isinstance(call[0][0], AuditRecord), (
            f"Expected AuditRecord as first positional arg, got {type(call[0][0])}"
        )
        assert call[1] == {}, (
            f"Expected no kwargs for write(), got {call[1]}"
        )
