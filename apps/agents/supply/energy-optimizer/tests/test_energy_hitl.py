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

import pytest


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
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """On first execution, audit_writer.write.call_count == 0 before interrupt raises (CR-02).

    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract (CR-02): "
        "On first execution, interrupt() raises BEFORE any audit_writer.write() call. "
        "Patch 'scm_energy_optimizer.agent.interrupt' with a raise-on-first-call function; "
        "assert audit_writer.write.call_count == 0 after GraphInterrupt is caught."
    )


# ---------------------------------------------------------------------------
# Contract 2: ENERGY_PROPOSAL row after resume
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_energy_proposal_written_after_resume(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After interrupt returns (HITL resume): exactly 1 ENERGY_PROPOSAL row (SCM-02).

    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: after interrupt() returns, "
        "audit_writer.write called with positional AuditRecord whose "
        "action_type == ActionType.ENERGY_PROPOSAL.value. "
        "Patch 'scm_energy_optimizer.agent.interrupt' to return on first call."
    )


# ---------------------------------------------------------------------------
# Contract 3: ENERGY_SIGNOFF row after supervisor approval
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_energy_signoff_written_after_supervisor_approval(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """After supervisor approval: ENERGY_SIGNOFF row present in audit (SCM-02).

    Together: 1 ENERGY_PROPOSAL + 1 ENERGY_SIGNOFF. Both share the same stable proposal_id.
    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract: after full HITL lifecycle, "
        "audit.actions contains ENERGY_PROPOSAL + ENERGY_SIGNOFF rows. "
        "Both rows must use the same stable proposal_id derived from thread_id."
    )


# ---------------------------------------------------------------------------
# Contract 4: Stable proposal_id from thread_id (CR-04)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_proposal_id_stable_across_replay(
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
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract (CR-04): "
        "thread_id='supply.energy-optimizer.test-001' must produce the SAME "
        "proposal_id on two separate __call__ invocations (simulating replay). "
        "Search test for 'thread_id' to confirm this contract is enforced."
    )


# ---------------------------------------------------------------------------
# Contract 5: approval_id=None for pending HITL rows (CR-03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_id_is_none_for_pending_energy_proposal(
    mock_audit_writer,
    make_interrupt_fn,
) -> None:
    """The ENERGY_PROPOSAL row has approval_id=None (CR-03).

    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract (CR-03): "
        "The AuditRecord written for ENERGY_PROPOSAL must have approval_id=None. "
        "Never fabricate a UUID for a pending HITL row."
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

    Implementation target: scm_energy_optimizer.agent.EnergyOptimizer.__call__
    """
    pytest.fail(
        "NOT IMPLEMENTED YET (09-03) — contract (CR-02): "
        "audit_writer.write must be called as write(record) — single positional AuditRecord. "
        "Verify: call_args_list[0][0][0] is AuditRecord instance, "
        "call_args_list[0][1] == {} (empty kwargs)."
    )
