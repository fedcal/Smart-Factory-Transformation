"""Contract tests for ShiftHandover dual-supervisor sequential interrupt (TRN-03 / D-SH-03).

CONTRACT: Two sequential interrupt() calls in ShiftHandover.__call__():
  1. After first interrupt (outgoing supervisor resume):
     - First HANDOVER_SIGNOFF audit row written
     - Second audit row NOT yet written
  2. After second interrupt (incoming supervisor resume):
     - Second HANDOVER_SIGNOFF audit row written
  3. Total: exactly 2 HANDOVER_SIGNOFF audit rows in correct order

Pattern mirrors: apps/agents/maintenance/rca-specialist/tests/test_interrupt_audit_lifecycle.py
Phase 7 CR-02 fix: audit write AFTER interrupt() returns, not before.
Phase 7 CR-03 fix: approval_id=None for pending HITL rows.

Implementation target: trn_shift_handover.agent.ShiftHandover
(Wave 2-3 plan: 08-04)

Wave 0 scaffold: test functions fail explicitly with a message naming the
unimplemented contract. NOT module-level pytest.skip (Phase 6/7 Wave 0 decision).
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Contract 1: First HANDOVER_SIGNOFF written between the two interrupts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_handover_signoff_written_after_first_resume() -> None:
    """After first interrupt returns (outgoing supervisor): exactly 1 HANDOVER_SIGNOFF row.

    Simulates two sequential interrupts in ShiftHandover.__call__:
    - First execution: raises GraphInterrupt for outgoing supervisor.
    - First resume: interrupt() returns → write 1 HANDOVER_SIGNOFF row → raise
      GraphInterrupt for incoming supervisor.
    - After first resume: audit_writer.write.call_count == 1.
    - The first row's action_type must be HANDOVER_SIGNOFF.

    CR-02 pattern: audit write AFTER interrupt() returns (not before).

    Implementation target: trn_shift_handover.agent.ShiftHandover.__call__()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: after first interrupt() returns (outgoing "
        "supervisor resume), exactly 1 HANDOVER_SIGNOFF audit row is written BEFORE "
        "the second interrupt() is called. CR-02 pattern required. "
        "Implement in plan 08-04 (shift-handover agent). "
        "Module: trn_shift_handover.agent"
    )


@pytest.mark.asyncio
async def test_second_handover_signoff_written_after_second_resume() -> None:
    """After second interrupt returns (incoming supervisor): exactly 2 HANDOVER_SIGNOFF rows total.

    Simulates both resume executions:
    - After second resume: audit_writer.write.call_count == 2.
    - Both rows have action_type == HANDOVER_SIGNOFF.
    - First row has motivation containing 'outgoing' or 'handover_step=outgoing_approval'.
    - Second row has motivation containing 'incoming' or 'handover_step=incoming_confirmation'.

    Implementation target: trn_shift_handover.agent.ShiftHandover.__call__()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: after second interrupt() returns (incoming "
        "supervisor resume), exactly 2 HANDOVER_SIGNOFF audit rows written in order. "
        "First written between interrupts, second after second resume. "
        "Implement in plan 08-04 (shift-handover agent). "
        "Module: trn_shift_handover.agent"
    )


@pytest.mark.asyncio
async def test_no_audit_rows_on_first_execution_before_interrupt() -> None:
    """On first execution (before any resume): audit_writer.write.call_count == 0.

    When ShiftHandover.__call__ is invoked for the first time, it compiles the
    report and calls interrupt() for the outgoing supervisor. Before interrupt()
    returns (i.e. on first execution), NO audit rows must be written.

    CR-02 contract: audit write is strictly AFTER interrupt() returns on resume.

    Implementation target: trn_shift_handover.agent.ShiftHandover.__call__()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: on first execution (GraphInterrupt raised), "
        "audit_writer.write.call_count == 0. No HANDOVER_SIGNOFF written before "
        "interrupt() returns. CR-02 pattern required. "
        "Implement in plan 08-04 (shift-handover agent). "
        "Module: trn_shift_handover.agent"
    )


@pytest.mark.asyncio
async def test_approval_id_is_none_for_pending_hitl_rows() -> None:
    """Both HANDOVER_SIGNOFF rows use approval_id=None (CR-03 fix).

    CR-03 pattern (Phase 7): approval_id must be None for pending HITL rows;
    never fabricate a UUID at write time.

    Implementation target: trn_shift_handover.agent.ShiftHandover.__call__()
    """
    pytest.fail(
        "NOT IMPLEMENTED — contract: both HANDOVER_SIGNOFF audit rows use "
        "approval_id=None (CR-03 fix; never fabricate UUID for pending HITL). "
        "Implement in plan 08-04 (shift-handover agent). "
        "Module: trn_shift_handover.agent"
    )
